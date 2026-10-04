#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_images.py — 云雾 API 配图生成工具

功能：
  1. 读取配置文件（config/image-gen.yaml）
  2. 接收提示词列表，并发调用云雾 API 生成图片
  3. 保存图片到指定目录
  4. 完善的错误处理和重试机制

用法：
  # 作为模块被 agent 调用
  from scripts.generate_images import ImageGenerator
  gen = ImageGenerator()
  results = gen.generate_batch(tasks)

  # 命令行测试单张生成
  python scripts/generate_images.py --prompt "测试提示词" --output test.png
"""

import os
import sys
import json
import base64
import time
import asyncio
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Windows 终端 UTF-8 兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---- 依赖检查 ----
try:
    import yaml
except ImportError:
    print("[ERROR] 缺少 pyyaml 依赖，请运行: pip install pyyaml")
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    # 降级为同步模式
    aiohttp = None

try:
    import requests
except ImportError:
    print("[ERROR] 缺少 requests 依赖，请运行: pip install requests")
    sys.exit(1)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ImageTask:
    """单张图片生成任务"""
    task_id: str              # 任务ID，如 "cover", "img-01"
    prompt: str               # 中文提示词
    output_path: str          # 输出文件路径
    aspect_ratio: str = "16:9"
    image_size: str = "1K"
    position_desc: str = ""   # 位置描述，如 "封面图", "第350字后"


@dataclass
class ImageResult:
    """单张图片生成结果"""
    task_id: str
    status: str               # "success" / "failed" / "filtered"
    output_path: str = ""
    error: str = ""
    retries: int = 0


@dataclass
class BatchResult:
    """批量生成结果"""
    total: int = 0
    success: int = 0
    failed: int = 0
    filtered: int = 0
    results: list = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"生成结果：{self.success}/{self.total} 张成功"]
        if self.failed > 0:
            lines.append(f"  失败：{self.failed} 张")
        if self.filtered > 0:
            lines.append(f"  安全过滤：{self.filtered} 张")
        for r in self.results:
            icon = "✅" if r.status == "success" else ("🚫" if r.status == "filtered" else "❌")
            lines.append(f"  {icon} {r.task_id}: {r.status}" + (f" ({r.error})" if r.error else ""))
        return "\n".join(lines)


# ============================================================
# 配置管理
# ============================================================

class ConfigManager:
    """配置文件管理"""

    DEFAULT_CONFIG = {
        "api_url": "https://yunwu.ai",
        "api_key": "",
        "default_model": "gemini-3-pro-image-preview",
        "default_aspect_ratio": "16:9",
        "default_image_size": "1K",
        "max_concurrent": 3,
        "max_retries": 3,
        "retry_delay": 2,
        "timeout": 60,
    }

    def __init__(self, config_path: Optional[str] = None):
        script_dir = Path(__file__).resolve().parent
        self.project_root = script_dir.parent
        self.local_config_path = self.project_root / "config" / "image-gen.local.yaml"
        self.legacy_config_path = self.project_root / "config" / "image-gen.yaml"
        if config_path is None:
            # Prefer local config to avoid accidental secret commit.
            config_path = self.local_config_path
        self.config_path = Path(config_path)
        self.loaded_from_path = self.config_path
        self.config = {}

    def load(self) -> dict:
        """加载配置，文件不存在时创建模板"""
        load_path = self.config_path
        if (
            not load_path.exists()
            and self.config_path == self.local_config_path
            and self.legacy_config_path.exists()
        ):
            # Backward compatibility: only fallback when legacy file has a real key.
            with open(self.legacy_config_path, "r", encoding="utf-8") as f:
                legacy_config = yaml.safe_load(f) or {}
            if legacy_config.get("api_key"):
                load_path = self.legacy_config_path
        if not load_path.exists():
            self._create_template()
            raise ConfigError(
                f"配置文件已创建：{self.config_path}\n"
                f"请填写 api_key 后重试。"
            )

        with open(load_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}
        self.loaded_from_path = load_path

        # 合并默认值
        for key, default in self.DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = default

        return self.config

    def validate(self) -> None:
        """校验配置"""
        if not self.config.get("api_key"):
            raise ConfigError(
                f"API Key 未配置。\n"
                f"请编辑 {self.loaded_from_path}，填写 api_key 字段。"
            )
        if not self.config.get("api_url"):
            raise ConfigError("API URL 未配置。")

        model = self.config.get("default_model", "")
        valid_models = [
            "gemini-3-pro-image-preview",
            "gemini-3.1-flash-image-preview",
        ]
        if model not in valid_models:
            raise ConfigError(
                f"模型名无效：{model}\n"
                f"可选：{', '.join(valid_models)}"
            )

    def _create_template(self):
        """创建配置模板文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        template = """# 云雾 API 配图生成配置
# 首次使用请填写 api_key

api_url: "https://yunwu.ai"
api_key: ""                  # 必填：你的云雾 API Key

# 模型选择
# banana pro: gemini-3-pro-image-preview
# banana 2:   gemini-3.1-flash-image-preview
default_model: "gemini-3-pro-image-preview"

# 图片参数
default_aspect_ratio: "16:9"
default_image_size: "1K"

# 并发与重试
max_concurrent: 3
max_retries: 3
retry_delay: 2
timeout: 60
"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(template)

    def update_key(self, key: str, value) -> None:
        """更新单个配置项并保存"""
        self.config[key] = value
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)


# ============================================================
# 异常定义
# ============================================================

class ConfigError(Exception):
    """配置错误"""
    pass


class APIError(Exception):
    """API 调用错误"""
    def __init__(self, message, status_code=None, retryable=False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


# ============================================================
# 图片生成器
# ============================================================

class ImageGenerator:
    """云雾 API 图片生成器"""

    def __init__(self, config_path: Optional[str] = None, model: Optional[str] = None):
        self.config_mgr = ConfigManager(config_path)
        self.config = self.config_mgr.load()
        self.config_mgr.validate()
        # 允许运行时覆盖模型
        if model:
            self.config["default_model"] = model

    @property
    def api_url(self) -> str:
        return self.config["api_url"]

    @property
    def api_key(self) -> str:
        return self.config["api_key"]

    @property
    def model(self) -> str:
        return self.config["default_model"]

    @property
    def max_retries(self) -> int:
        return self.config.get("max_retries", 3)

    @property
    def retry_delay(self) -> int:
        return self.config.get("retry_delay", 2)

    @property
    def timeout(self) -> int:
        return self.config.get("timeout", 60)

    @property
    def max_concurrent(self) -> int:
        return self.config.get("max_concurrent", 3)

    def _build_request_body(self, prompt: str, aspect_ratio: str, image_size: str) -> dict:
        """构建 API 请求体"""
        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": image_size,
                }
            }
        }

    def _build_url(self) -> str:
        """构建完整 API URL"""
        base = self.api_url.rstrip("/")
        return f"{base}/v1beta/models/{self.model}:generateContent"

    def _build_headers(self) -> dict:
        """构建请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _parse_response(self, response_data: dict) -> Optional[bytes]:
        """从 API 响应中提取图片 bytes"""
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                return None
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                inline_data = part.get("inlineData") or part.get("inline_data")
                if inline_data:
                    b64_data = inline_data.get("data", "")
                    if b64_data:
                        return base64.b64decode(b64_data)
            return None
        except (KeyError, IndexError, TypeError):
            return None

    def _classify_error(self, status_code: int, response_text: str) -> APIError:
        """根据 HTTP 状态码分类错误"""
        if status_code == 401 or status_code == 403:
            return APIError(
                "API Key 无效或已过期，请检查 config/image-gen.yaml",
                status_code=status_code,
                retryable=False,
            )
        elif status_code == 429:
            return APIError(
                "API 限流，等待后重试",
                status_code=status_code,
                retryable=True,
            )
        elif status_code >= 500:
            return APIError(
                f"服务暂时不可用 (HTTP {status_code})",
                status_code=status_code,
                retryable=True,
            )
        elif status_code == 400:
            # 检查是否是内容安全过滤
            if "safety" in response_text.lower() or "blocked" in response_text.lower():
                return APIError(
                    "提示词可能触发安全过滤，建议修改提示词内容",
                    status_code=status_code,
                    retryable=False,
                )
            return APIError(
                f"请求参数错误 (HTTP 400): {response_text[:200]}",
                status_code=status_code,
                retryable=False,
            )
        else:
            return APIError(
                f"未知错误 (HTTP {status_code}): {response_text[:200]}",
                status_code=status_code,
                retryable=False,
            )

    # ---- 同步生成（单张） ----

    def generate_single_sync(self, task: ImageTask) -> ImageResult:
        """同步生成单张图片（带重试）"""
        url = self._build_url()
        headers = self._build_headers()
        body = self._build_request_body(task.prompt, task.aspect_ratio, task.image_size)

        last_error = ""
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    url,
                    headers=headers,
                    json=body,
                    timeout=self.timeout,
                )

                if resp.status_code == 200:
                    image_bytes = self._parse_response(resp.json())
                    if image_bytes:
                        # 保存图片
                        output_path = Path(task.output_path)
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(image_bytes)
                        return ImageResult(
                            task_id=task.task_id,
                            status="success",
                            output_path=str(output_path),
                            retries=attempt,
                        )
                    else:
                        # 响应成功但无图片数据
                        error = APIError(
                            "响应中无图片数据，可能触发了安全过滤",
                            retryable=False,
                        )
                        return ImageResult(
                            task_id=task.task_id,
                            status="filtered",
                            error=str(error),
                            retries=attempt,
                        )
                else:
                    error = self._classify_error(resp.status_code, resp.text)
                    if not error.retryable:
                        status = "filtered" if resp.status_code == 400 and "safety" in resp.text.lower() else "failed"
                        return ImageResult(
                            task_id=task.task_id,
                            status=status,
                            error=str(error),
                            retries=attempt,
                        )
                    last_error = str(error)

            except requests.exceptions.Timeout:
                last_error = f"请求超时（{self.timeout}秒）"
            except requests.exceptions.ConnectionError:
                last_error = "网络连接失败，请检查网络"
            except Exception as e:
                last_error = f"未知错误: {str(e)}"

            # 重试等待（指数退避）
            if attempt < self.max_retries - 1:
                wait = self.retry_delay * (2 ** attempt)
                print(f"  [重试] {task.task_id} 第 {attempt + 1} 次失败，{wait}秒后重试...")
                time.sleep(wait)

        return ImageResult(
            task_id=task.task_id,
            status="failed",
            error=f"重试 {self.max_retries} 次后仍失败: {last_error}",
            retries=self.max_retries,
        )

    # ---- 异步生成（批量并发） ----

    async def _generate_single_async(self, session: "aiohttp.ClientSession", task: ImageTask, semaphore: asyncio.Semaphore) -> ImageResult:
        """异步生成单张图片（带重试和并发控制）"""
        url = self._build_url()
        headers = self._build_headers()
        body = self._build_request_body(task.prompt, task.aspect_ratio, task.image_size)

        last_error = ""
        async with semaphore:
            for attempt in range(self.max_retries):
                try:
                    async with session.post(
                        url,
                        headers=headers,
                        json=body,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as resp:
                        resp_text = await resp.text()
                        if resp.status == 200:
                            resp_data = json.loads(resp_text)
                            image_bytes = self._parse_response(resp_data)
                            if image_bytes:
                                output_path = Path(task.output_path)
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                with open(output_path, "wb") as f:
                                    f.write(image_bytes)
                                return ImageResult(
                                    task_id=task.task_id,
                                    status="success",
                                    output_path=str(output_path),
                                    retries=attempt,
                                )
                            else:
                                return ImageResult(
                                    task_id=task.task_id,
                                    status="filtered",
                                    error="响应中无图片数据，可能触发了安全过滤",
                                    retries=attempt,
                                )
                        else:
                            error = self._classify_error(resp.status, resp_text)
                            if not error.retryable:
                                status = "filtered" if "safety" in resp_text.lower() else "failed"
                                return ImageResult(
                                    task_id=task.task_id,
                                    status=status,
                                    error=str(error),
                                    retries=attempt,
                                )
                            last_error = str(error)

                except asyncio.TimeoutError:
                    last_error = f"请求超时（{self.timeout}秒）"
                except aiohttp.ClientError as e:
                    last_error = f"网络错误: {str(e)}"
                except Exception as e:
                    last_error = f"未知错误: {str(e)}"

                if attempt < self.max_retries - 1:
                    wait = self.retry_delay * (2 ** attempt)
                    print(f"  [重试] {task.task_id} 第 {attempt + 1} 次失败，{wait}秒后重试...")
                    await asyncio.sleep(wait)

        return ImageResult(
            task_id=task.task_id,
            status="failed",
            error=f"重试 {self.max_retries} 次后仍失败: {last_error}",
            retries=self.max_retries,
        )

    async def _generate_batch_async(self, tasks: list) -> BatchResult:
        """异步批量生成"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        batch = BatchResult(total=len(tasks))

        async with aiohttp.ClientSession() as session:
            coros = [
                self._generate_single_async(session, task, semaphore)
                for task in tasks
            ]
            results = await asyncio.gather(*coros, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                batch.results.append(ImageResult(
                    task_id="unknown",
                    status="failed",
                    error=str(r),
                ))
                batch.failed += 1
            else:
                batch.results.append(r)
                if r.status == "success":
                    batch.success += 1
                elif r.status == "filtered":
                    batch.filtered += 1
                else:
                    batch.failed += 1

        return batch

    def generate_batch(self, tasks: list) -> BatchResult:
        """
        批量生成图片（自动选择异步或同步模式）

        Args:
            tasks: ImageTask 列表

        Returns:
            BatchResult 包含所有结果
        """
        if not tasks:
            return BatchResult()

        print(f"\n📸 开始生成 {len(tasks)} 张配图...")
        print(f"   模型：{self.model}")
        print(f"   并发数：{self.max_concurrent}")
        print()

        if aiohttp and len(tasks) > 1:
            # 异步并发模式
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 已有事件循环（如在 Jupyter 中）
                    import nest_asyncio
                    nest_asyncio.apply()
                    result = loop.run_until_complete(self._generate_batch_async(tasks))
                else:
                    result = loop.run_until_complete(self._generate_batch_async(tasks))
            except RuntimeError:
                result = asyncio.run(self._generate_batch_async(tasks))
        else:
            # 同步模式（逐张生成）
            result = BatchResult(total=len(tasks))
            for i, task in enumerate(tasks):
                print(f"  [{i+1}/{len(tasks)}] 生成 {task.task_id}...")
                r = self.generate_single_sync(task)
                result.results.append(r)
                if r.status == "success":
                    result.success += 1
                    print(f"    ✅ 成功 → {r.output_path}")
                elif r.status == "filtered":
                    result.filtered += 1
                    print(f"    🚫 安全过滤: {r.error}")
                else:
                    result.failed += 1
                    print(f"    ❌ 失败: {r.error}")

        print()
        print(result.summary())
        return result

    def retry_failed(self, tasks: list, previous_results: BatchResult) -> BatchResult:
        """重试之前失败的任务"""
        failed_ids = {r.task_id for r in previous_results.results if r.status == "failed"}
        retry_tasks = [t for t in tasks if t.task_id in failed_ids]
        if not retry_tasks:
            print("没有需要重试的任务")
            return BatchResult()
        print(f"\n🔄 重试 {len(retry_tasks)} 张失败的图片...")
        return self.generate_batch(retry_tasks)


# ============================================================
# 输出目录管理
# ============================================================

class OutputManager:
    """输出目录结构管理"""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent
            self.base_dir = project_root / "outputs"
        else:
            self.base_dir = Path(base_dir)

    def get_article_dir(self, style_name: str, article_type: str, topic: str, date: Optional[str] = None) -> Path:
        """
        获取文章输出目录

        Args:
            style_name: 风格名，如 "犀利派"、"默认风格"
            article_type: 文章类型，如 "干货"
            topic: 主题关键词
            date: 日期字符串，默认今天

        Returns:
            Path: outputs/{风格名}/{日期-类型-主题}/
        """
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")

        # 清理文件名中的非法字符
        safe_topic = "".join(c for c in topic if c not in r'\/:*?"<>|').strip()[:30]
        folder_name = f"{date}-{article_type}-{safe_topic}"

        article_dir = self.base_dir / style_name / folder_name
        article_dir.mkdir(parents=True, exist_ok=True)
        (article_dir / "images").mkdir(exist_ok=True)
        return article_dir

    def get_image_path(self, article_dir: Path, index: int) -> str:
        """获取图片保存路径，按顺序命名：图片_1.png, 图片_2.png, ..."""
        return str(article_dir / "images" / f"图片_{index}.png")


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="云雾 API 配图生成工具")
    parser.add_argument("--prompt", type=str, help="生图提示词")
    parser.add_argument("--output", type=str, default="test_output.png", help="输出文件路径")
    parser.add_argument("--model", type=str, help="模型名（覆盖配置文件）")
    parser.add_argument("--aspect-ratio", type=str, default="16:9", help="宽高比")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--validate", action="store_true", help="仅校验配置")

    args = parser.parse_args()

    try:
        gen = ImageGenerator(config_path=args.config, model=args.model)

        if args.validate:
            print("✅ 配置校验通过")
            print(f"   API URL: {gen.api_url}")
            print(f"   模型: {gen.model}")
            print(f"   并发数: {gen.max_concurrent}")
            return

        if not args.prompt:
            parser.error("请提供 --prompt 参数")

        task = ImageTask(
            task_id="cli-test",
            prompt=args.prompt,
            output_path=args.output,
            aspect_ratio=args.aspect_ratio,
        )
        result = gen.generate_single_sync(task)

        if result.status == "success":
            print(f"✅ 生成成功: {result.output_path}")
        else:
            print(f"❌ 生成失败: {result.error}")
            sys.exit(1)

    except ConfigError as e:
        print(f"⚠️ 配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
