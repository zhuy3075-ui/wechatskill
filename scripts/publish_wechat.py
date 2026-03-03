#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_wechat.py — 微信公众号草稿箱上传工具

功能：
  1. 读取 Markdown 文章 + 配图
  2. Markdown → 微信兼容 HTML（内联 CSS）
  3. 上传封面图（永久素材）+ 正文图片（uploadimg）
  4. 推送草稿箱

用法：
  # 完整参数
  python scripts/publish_wechat.py \
    --article outputs/犀利派/2026-03-03-干货-时间管理/article.md \
    --title "时间管理的5个底层逻辑" \
    --cover outputs/犀利派/2026-03-03-干货-时间管理/images/图片_1.png \
    --digest "你以为的时间管理，可能从第一步就错了"

  # 最小参数
  python scripts/publish_wechat.py \
    --article outputs/默认风格/2026-03-03-干货-时间管理/article.md \
    --title "时间管理的5个底层逻辑"

  # 仅校验配置
  python scripts/publish_wechat.py --validate
"""

import os
import sys
import io
import re
import json
import time
import argparse

# Windows 终端 UTF-8 兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
from typing import Optional

# ---- 依赖检查 ----
try:
    import yaml
except ImportError:
    print("[ERROR] 缺少 pyyaml 依赖，请运行: pip install pyyaml")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[ERROR] 缺少 requests 依赖，请运行: pip install requests")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("[ERROR] 缺少 Pillow 依赖，请运行: pip install Pillow")
    sys.exit(1)

try:
    import mistune
except ImportError:
    print("[ERROR] 缺少 mistune 依赖，请运行: pip install mistune")
    sys.exit(1)

try:
    import premailer
except ImportError:
    print("[ERROR] 缺少 premailer 依赖，请运行: pip install premailer")
    sys.exit(1)


# ============================================================
# 异常定义
# ============================================================

class WechatPublishError(Exception):
    """微信发布相关异常基类"""
    pass

class ConfigError(WechatPublishError):
    """配置错误"""
    pass

class AuthError(WechatPublishError):
    """认证错误"""
    pass

class UploadError(WechatPublishError):
    """上传错误"""
    pass


# ============================================================
# 配置管理
# ============================================================

class WechatConfig:
    """微信公众号 API 配置管理"""

    DEFAULT_CONFIG = {
        "appid": "",
        "appsecret": "",
        "default_author": "",
        "token_cache_file": "config/.wechat_token_cache.json",
        "cover_max_size_kb": 64,
        "cover_target_width": 900,
        "cover_target_height": 500,
        "cover_initial_quality": 85,
    }

    TEMPLATE = """\
# ============================================================
# 微信公众号 API 配置
# ============================================================
#
# 【如何获取 AppID 和 AppSecret】
#
# 1. 登录微信公众平台：https://mp.weixin.qq.com
# 2. 左侧菜单 →「开发」→「基本配置」
# 3. 页面上方即可看到「开发者ID (AppID)」
# 4. 「开发者密码 (AppSecret)」→ 点击「重置」→ 管理员扫码确认
#    ⚠️ AppSecret 只显示一次，获取后务必立即保存！丢失只能重置。
#
# 【如何设置 IP 白名单】（必须，否则报错 40164）
#
# 1. 同一页面下方「IP白名单」→ 点击「查看」→「修改」
# 2. 填入你当前电脑的公网 IP
#    查看方式：终端运行 curl ifconfig.me 或访问 https://ifconfig.me
# 3. 管理员扫码确认
#
# ============================================================

# ---- 必填：公众号凭证 ----
appid: ""              # 开发者ID（AppID）
appsecret: ""          # 开发者密码（AppSecret）

# ---- 可选设置 ----
# 草稿中的作者字段（不填则留空）
default_author: ""

# access_token 缓存文件路径（自动管理，无需手动修改）
token_cache_file: "config/.wechat_token_cache.json"

# ---- 封面图压缩参数 ----
cover_max_size_kb: 64       # 微信限制：封面图 ≤ 64KB
cover_target_width: 900     # 推荐宽度
cover_target_height: 500    # 推荐高度（9:5 比例）
cover_initial_quality: 85   # 压缩起始质量
"""

    def __init__(self, config_path: Optional[str] = None):
        script_dir = Path(__file__).resolve().parent
        self.project_root = script_dir.parent
        self.local_config_path = self.project_root / "config" / "wechat.local.yaml"
        self.legacy_config_path = self.project_root / "config" / "wechat.yaml"
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
            # Backward compatibility: only fallback when legacy file has real credentials.
            with open(self.legacy_config_path, "r", encoding="utf-8") as f:
                legacy_config = yaml.safe_load(f) or {}
            if legacy_config.get("appid") or legacy_config.get("appsecret"):
                load_path = self.legacy_config_path
        if not load_path.exists():
            self._create_template()
            raise ConfigError(
                f"配置文件已创建：{self.config_path}\n"
                f"请填写 appid 和 appsecret 后重试。"
            )

        with open(load_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}
        self.loaded_from_path = load_path

        for key, default in self.DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = default

        return self.config

    def validate(self) -> None:
        """校验必填配置"""
        if not self.config.get("appid"):
            raise ConfigError(
                f"appid 未配置。\n"
                f"请编辑 {self.loaded_from_path}，填写 appid 字段。\n"
                f"获取方式：微信公众平台 → 开发 → 基本配置"
            )
        if not self.config.get("appsecret"):
            raise ConfigError(
                f"appsecret 未配置。\n"
                f"请编辑 {self.loaded_from_path}，填写 appsecret 字段。"
            )

    def _create_template(self):
        """创建配置模板文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(self.TEMPLATE)

    def get(self, key: str, default=None):
        return self.config.get(key, default)


# ============================================================
# access_token 管理
# ============================================================

class WechatAuth:
    """微信 access_token 获取与缓存"""

    TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"

    def __init__(self, config: WechatConfig):
        self.config = config
        self._resolve_cache_path()

    def _resolve_cache_path(self):
        """解析缓存文件的绝对路径"""
        cache_file = self.config.get("token_cache_file", "config/.wechat_token_cache.json")
        cache_path = Path(cache_file)
        if not cache_path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            cache_path = project_root / cache_path
        self.cache_path = cache_path

    def get_token(self) -> str:
        """获取 access_token（优先读缓存，过期则刷新）"""
        cached = self._read_cache()
        if cached:
            return cached

        token = self._request_token()
        self._write_cache(token)
        return token

    def _read_cache(self) -> Optional[str]:
        """读取缓存的 token，过期返回 None"""
        if not self.cache_path.exists():
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            expires_at = data.get("expires_at", 0)
            # 提前 5 分钟刷新
            if time.time() < expires_at - 300:
                return data.get("access_token")
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _request_token(self) -> str:
        """调用微信 API 获取新 token"""
        params = {
            "grant_type": "client_credential",
            "appid": self.config.get("appid"),
            "secret": self.config.get("appsecret"),
        }
        try:
            resp = requests.get(self.TOKEN_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise AuthError(f"请求 access_token 失败：{e}")

        if "errcode" in data and data["errcode"] != 0:
            errcode = data["errcode"]
            errmsg = data.get("errmsg", "")
            hint = ""
            if errcode == 40001:
                hint = "access_token 无效，请检查 appid/appsecret。"
            elif errcode == 40125:
                hint = "appsecret 无效，请检查 config/wechat.yaml。"
            elif errcode == 40164:
                hint = ("IP 地址不在白名单中。\n"
                        "请前往：微信公众平台 → 开发 → 基本配置 → IP白名单，添加当前服务器 IP。")
            elif errcode == 42001:
                hint = "access_token 已过期，正在自动刷新..."
            raise AuthError(f"获取 access_token 失败 [{errcode}]: {errmsg}\n{hint}")

        return data["access_token"]

    def _write_cache(self, token: str):
        """缓存 token（有效期 2 小时）"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "access_token": token,
            "expires_at": time.time() + 7200,
        }
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def clear_cache(self):
        """清除 token 缓存"""
        if self.cache_path.exists():
            self.cache_path.unlink()


# ============================================================
# 图片压缩
# ============================================================

class ImageCompressor:
    """封面图和正文图压缩"""

    @staticmethod
    def compress_cover(
        input_path: str,
        max_kb: int = 64,
        target_width: int = 900,
        target_height: int = 500,
        initial_quality: int = 85,
    ) -> bytes:
        """
        压缩封面图至微信限制以内（≤ 64KB）

        Returns:
            压缩后的图片字节数据（JPEG 格式）
        """
        img = Image.open(input_path)

        # 转换为 RGB（去除 alpha 通道）
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        # 1. 裁剪到目标比例（居中裁剪）
        target_ratio = target_width / target_height
        img_ratio = img.width / img.height

        if img_ratio > target_ratio:
            # 图片更宽，裁剪两侧
            new_width = int(img.height * target_ratio)
            offset = (img.width - new_width) // 2
            img = img.crop((offset, 0, offset + new_width, img.height))
        elif img_ratio < target_ratio:
            # 图片更高，裁剪上下
            new_height = int(img.width / target_ratio)
            offset = (img.height - new_height) // 2
            img = img.crop((0, offset, img.width, offset + new_height))

        # 2. 缩放到目标尺寸
        img = img.resize((target_width, target_height), Image.LANCZOS)

        # 3. quality 递减直到文件 ≤ max_kb
        max_bytes = max_kb * 1024
        quality = initial_quality

        while quality >= 10:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if buf.tell() <= max_bytes:
                return buf.getvalue()
            quality -= 5

        # 4. quality=10 仍超标 → 进一步缩小尺寸
        for scale in (0.8, 0.6, 0.5, 0.4):
            w = int(target_width * scale)
            h = int(target_height * scale)
            small = img.resize((w, h), Image.LANCZOS)
            buf = io.BytesIO()
            small.save(buf, format="JPEG", quality=10, optimize=True)
            if buf.tell() <= max_bytes:
                return buf.getvalue()

        raise UploadError(f"封面图压缩失败：无法将图片压缩到 {max_kb}KB 以内")

    @staticmethod
    def compress_content_image(input_path: str, max_kb: int = 1024) -> bytes:
        """
        压缩正文配图至 ≤ 1MB

        Returns:
            压缩后的图片字节数据
        """
        img = Image.open(input_path)
        img_format = "JPEG"
        suffix = Path(input_path).suffix.lower()

        # PNG 保持 PNG 格式
        if suffix == ".png":
            img_format = "PNG"

        # 转换模式
        if img_format == "JPEG" and img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        max_bytes = max_kb * 1024

        # 先试原图
        buf = io.BytesIO()
        if img_format == "JPEG":
            img.save(buf, format="JPEG", quality=90, optimize=True)
        else:
            img.save(buf, format="PNG", optimize=True)

        if buf.tell() <= max_bytes:
            return buf.getvalue()

        # 需要压缩 → 统一转 JPEG
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        quality = 85
        while quality >= 20:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if buf.tell() <= max_bytes:
                return buf.getvalue()
            quality -= 10

        # 缩小尺寸
        for scale in (0.75, 0.5, 0.4):
            w = int(img.width * scale)
            h = int(img.height * scale)
            small = img.resize((w, h), Image.LANCZOS)
            buf = io.BytesIO()
            small.save(buf, format="JPEG", quality=30, optimize=True)
            if buf.tell() <= max_bytes:
                return buf.getvalue()

        raise UploadError(f"正文图片压缩失败：无法将 {input_path} 压缩到 {max_kb}KB 以内")


# ============================================================
# 图片上传
# ============================================================

class WechatUploader:
    """微信图片上传"""

    MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
    UPLOADIMG_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
    TOKEN_REFRESH_ERRCODES = {40001, 42001}

    def __init__(self, auth: WechatAuth):
        self.auth = auth

    def upload_thumb(self, image_data: bytes, filename: str = "cover.jpg") -> str:
        """
        上传封面图为永久素材

        Args:
            image_data: JPEG 格式的图片字节
            filename: 文件名

        Returns:
            thumb_media_id
        """
        files = {"media": (filename, image_data, "image/jpeg")}
        data = self._post_json_with_token_refresh(
            lambda token: f"{self.MATERIAL_URL}?access_token={token}&type=thumb",
            files,
            op_name="封面图上传",
        )

        if "errcode" in data and data["errcode"] != 0:
            raise UploadError(
                f"封面图上传失败 [{data['errcode']}]: {data.get('errmsg', '')}"
            )

        media_id = data.get("media_id")
        if not media_id:
            raise UploadError(f"封面图上传返回异常：{data}")

        return media_id

    def upload_content_image(self, image_data: bytes, filename: str = "image.jpg") -> str:
        """
        上传正文配图（不占素材配额）

        Args:
            image_data: 图片字节数据
            filename: 文件名

        Returns:
            微信图片 URL
        """
        content_type = "image/jpeg"
        if filename.lower().endswith(".png"):
            content_type = "image/png"

        files = {"media": (filename, image_data, content_type)}
        data = self._post_json_with_token_refresh(
            lambda token: f"{self.UPLOADIMG_URL}?access_token={token}",
            files,
            op_name="正文图片上传",
        )

        if "errcode" in data and data["errcode"] != 0:
            raise UploadError(
                f"正文图片上传失败 [{data['errcode']}]: {data.get('errmsg', '')}"
            )

        img_url = data.get("url")
        if not img_url:
            raise UploadError(f"正文图片上传返回异常：{data}")

        return img_url

    def _post_json_with_token_refresh(self, url_builder, files: dict, op_name: str) -> dict:
        """POST 并在 token 失效时自动清缓存重试一次。"""
        data = {}
        for attempt in range(2):
            token = self.auth.get_token()
            url = url_builder(token)
            resp = self._post_with_retry(url, files=files)
            data = resp.json()
            errcode = data.get("errcode")
            if errcode in self.TOKEN_REFRESH_ERRCODES and attempt == 0:
                self.auth.clear_cache()
                continue
            return data
        raise UploadError(f"{op_name}失败：token 刷新后仍失败：{data}")

    def _post_with_retry(self, url: str, files: dict, max_retries: int = 3) -> requests.Response:
        """带重试的 POST 请求"""
        last_error = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, files=files, timeout=30)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    time.sleep(wait)

        raise UploadError(f"上传请求失败（重试 {max_retries} 次）：{last_error}")


# ============================================================
# Markdown → 微信 HTML
# ============================================================

# 微信排版 CSS 模板（参照 rules/formatting.md）
WECHAT_CSS = """\
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    line-height: 1.8;
    color: #3f3f3f;
    font-size: 15px;
}
h1 {
    font-size: 22px;
    font-weight: bold;
    color: #333;
    margin: 24px 0 16px;
    line-height: 1.4;
}
h2 {
    font-size: 18px;
    font-weight: bold;
    color: #333;
    margin: 20px 0 12px;
    line-height: 1.4;
}
h3 {
    font-size: 16px;
    font-weight: bold;
    color: #333;
    margin: 16px 0 8px;
    line-height: 1.4;
}
p {
    font-size: 15px;
    color: #3f3f3f;
    line-height: 1.8;
    margin: 0 0 16px;
}
blockquote {
    border-left: 3px solid #ddd;
    padding: 8px 16px;
    color: #666;
    margin: 16px 0;
    background: #f9f9f9;
}
strong {
    font-weight: bold;
    color: #333;
}
em {
    font-style: italic;
}
img {
    max-width: 100%;
    height: auto;
    margin: 16px auto;
    display: block;
}
ul, ol {
    padding-left: 24px;
    margin: 8px 0 16px;
}
li {
    font-size: 15px;
    color: #3f3f3f;
    line-height: 1.8;
    margin: 4px 0;
}
hr {
    border: none;
    border-top: 1px solid #eee;
    margin: 24px 0;
}
a {
    color: #576b95;
    text-decoration: none;
}
code {
    background: #f5f5f5;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 14px;
    color: #c7254e;
}
pre {
    background: #f5f5f5;
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
}
pre code {
    background: none;
    padding: 0;
    color: #333;
}
"""


class MarkdownToWechatHTML:
    """Markdown → 微信兼容 HTML（内联 CSS）"""

    def __init__(self, uploader: Optional[WechatUploader] = None):
        self.uploader = uploader
        self._image_map = {}  # 本地路径 → 微信 URL

    def convert(self, md_content: str, base_dir: str = "") -> str:
        """
        完整转换流程

        Args:
            md_content: Markdown 文本
            base_dir: Markdown 文件所在目录（用于解析相对图片路径）

        Returns:
            微信兼容的 HTML（内联 CSS）
        """
        # 1. 提取并上传图片
        md_content = self._upload_images(md_content, base_dir)

        # 2. Markdown → HTML
        html = mistune.html(md_content)

        # 3. 套入 CSS 模板
        full_html = f"""\
<html>
<head>
<style>
{WECHAT_CSS}
</style>
</head>
<body>
{html}
</body>
</html>
"""

        # 4. premailer 内联化
        inlined = premailer.transform(
            full_html,
            remove_classes=True,
            strip_important=True,
            keep_style_tags=False,
        )

        # 5. 提取 body 内容
        body_match = re.search(r"<body[^>]*>(.*?)</body>", inlined, re.DOTALL)
        if body_match:
            return body_match.group(1).strip()

        return inlined

    def _upload_images(self, md_content: str, base_dir: str) -> str:
        """扫描 Markdown 中的图片引用，上传到微信并替换 URL"""
        if not self.uploader:
            return md_content

        # 匹配 ![alt](path)
        img_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

        def replace_image(match):
            alt = match.group(1)
            img_path = match.group(2)

            # 已经是 URL，不处理
            if img_path.startswith(("http://", "https://")):
                return match.group(0)

            # 解析本地路径
            if base_dir:
                full_path = Path(base_dir) / img_path
            else:
                full_path = Path(img_path)

            if not full_path.exists():
                print(f"  [WARN] 图片不存在，跳过：{full_path}")
                return match.group(0)

            # 检查缓存
            path_key = str(full_path.resolve())
            if path_key in self._image_map:
                return f"![{alt}]({self._image_map[path_key]})"

            # 压缩并上传
            try:
                filename = full_path.name
                image_data = ImageCompressor.compress_content_image(str(full_path))
                wechat_url = self.uploader.upload_content_image(
                    image_data, filename=filename
                )
                self._image_map[path_key] = wechat_url
                print(f"  [OK] 图片上传成功：{filename}")
                return f"![{alt}]({wechat_url})"
            except (UploadError, Exception) as e:
                print(f"  [FAIL] 图片上传失败：{full_path} - {e}")
                return f"![{alt}]({img_path})"

        return img_pattern.sub(replace_image, md_content)

    def get_uploaded_count(self) -> int:
        return len(self._image_map)


# ============================================================
# 草稿推送
# ============================================================

class DraftPublisher:
    """微信草稿箱推送"""

    DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
    TOKEN_REFRESH_ERRCODES = {40001, 42001}

    def __init__(self, auth: WechatAuth):
        self.auth = auth

    def create_draft(
        self,
        title: str,
        content: str,
        thumb_media_id: str,
        author: str = "",
        digest: str = "",
    ) -> str:
        """
        创建草稿

        Args:
            title: 文章标题
            content: HTML 正文（内联 CSS）
            thumb_media_id: 封面图的 media_id
            author: 作者
            digest: 摘要（≤120字）

        Returns:
            草稿的 media_id
        """
        # 摘要截断到 120 字
        if digest and len(digest) > 120:
            digest = digest[:117] + "..."

        article = {
            "title": title,
            "content": content,
            "thumb_media_id": thumb_media_id,
        }
        if author:
            article["author"] = author
        if digest:
            article["digest"] = digest

        payload = {"articles": [article]}

        data = {}
        for attempt in range(2):
            token = self.auth.get_token()
            url = f"{self.DRAFT_URL}?access_token={token}"
            try:
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                raise WechatPublishError(f"创建草稿请求失败：{e}")
            errcode = data.get("errcode")
            if errcode in self.TOKEN_REFRESH_ERRCODES and attempt == 0:
                self.auth.clear_cache()
                continue
            break

        if "errcode" in data and data["errcode"] != 0:
            raise WechatPublishError(
                f"创建草稿失败 [{data['errcode']}]: {data.get('errmsg', '')}"
            )

        media_id = data.get("media_id")
        if not media_id:
            raise WechatPublishError(f"创建草稿返回异常：{data}")

        return media_id


# ============================================================
# 入口函数
# ============================================================

def publish_to_wechat(
    article_md_path: str,
    title: str,
    digest: str = "",
    cover_image_path: str = "",
    author: str = "",
    config_path: str = None,
) -> dict:
    """
    一键发布到微信草稿箱

    Args:
        article_md_path: Markdown 文件路径
        title: 文章标题
        digest: 摘要（≤120字，不填自动截取）
        cover_image_path: 封面图路径（不填则用第一张配图）
        author: 作者（不填则读 config）
        config_path: 配置文件路径

    Returns:
        {
            "status": "success" / "failed",
            "media_id": "草稿media_id",
            "title": "文章标题",
            "images_uploaded": N,
            "cover_uploaded": True/False,
            "errors": []
        }
    """
    result = {
        "status": "failed",
        "media_id": "",
        "title": title,
        "images_uploaded": 0,
        "cover_uploaded": False,
        "errors": [],
    }

    try:
        # ---- Step 1: 加载配置 ----
        print("📋 加载配置...")
        config = WechatConfig(config_path)
        config.load()
        config.validate()

        if not author:
            author = config.get("default_author", "")

        # ---- Step 2: 获取 access_token ----
        print("🔑 获取 access_token...")
        auth = WechatAuth(config)
        token = auth.get_token()
        print(f"  [OK] access_token 获取成功")

        # ---- Step 3: 读取文章 ----
        print("📖 读取文章...")
        md_path = Path(article_md_path)
        if not md_path.exists():
            raise WechatPublishError(f"文章文件不存在：{article_md_path}")

        # 使用 utils.read_text 的编码逻辑
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                md_content = md_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise WechatPublishError(f"无法解码文章文件：{article_md_path}")

        base_dir = str(md_path.parent)

        # ---- Step 4: 自动推断封面图 ----
        if not cover_image_path:
            images_dir = md_path.parent / "images"
            if images_dir.exists():
                for name in ("图片_1.png", "图片_1.jpg", "cover.png", "cover.jpg"):
                    candidate = images_dir / name
                    if candidate.exists():
                        cover_image_path = str(candidate)
                        break

        if not cover_image_path:
            raise WechatPublishError(
                "未找到封面图。请通过 --cover 参数指定，或确保 images/ 目录下有配图。"
            )

        # ---- Step 5: 压缩并上传封面图 ----
        print("🖼️  压缩封面图...")
        cover_data = ImageCompressor.compress_cover(
            cover_image_path,
            max_kb=config.get("cover_max_size_kb", 64),
            target_width=config.get("cover_target_width", 900),
            target_height=config.get("cover_target_height", 500),
            initial_quality=config.get("cover_initial_quality", 85),
        )
        print(f"  [OK] 封面图压缩完成：{len(cover_data) / 1024:.1f}KB")

        print("📤 上传封面图...")
        uploader = WechatUploader(auth)
        thumb_media_id = uploader.upload_thumb(cover_data)
        result["cover_uploaded"] = True
        print(f"  [OK] 封面图上传成功：{thumb_media_id[:20]}...")

        # ---- Step 6: Markdown → HTML（含正文图片上传） ----
        print("📝 转换文章格式...")
        converter = MarkdownToWechatHTML(uploader=uploader)
        html_content = converter.convert(md_content, base_dir)
        result["images_uploaded"] = converter.get_uploaded_count()
        print(f"  [OK] 格式转换完成，{result['images_uploaded']} 张正文图片已上传")

        # ---- Step 7: 自动截取摘要 ----
        if not digest:
            # 从正文提取前 120 字
            text_only = re.sub(r"[#*\[\]()!`>-]", "", md_content)
            text_only = re.sub(r"\s+", " ", text_only).strip()
            digest = text_only[:120]

        # ---- Step 8: 创建草稿 ----
        print("📮 创建草稿...")
        publisher = DraftPublisher(auth)
        media_id = publisher.create_draft(
            title=title,
            content=html_content,
            thumb_media_id=thumb_media_id,
            author=author,
            digest=digest,
        )

        result["status"] = "success"
        result["media_id"] = media_id
        print(f"\n✅ 上传成功！草稿ID：{media_id}")

    except ConfigError as e:
        result["errors"].append(str(e))
        print(f"\n❌ 配置错误：{e}")
    except AuthError as e:
        result["errors"].append(str(e))
        print(f"\n❌ 认证错误：{e}")
    except UploadError as e:
        result["errors"].append(str(e))
        print(f"\n❌ 上传错误：{e}")
    except WechatPublishError as e:
        result["errors"].append(str(e))
        print(f"\n❌ 发布错误：{e}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"\n❌ 未知错误：{e}")

    return result


# ============================================================
# 本地预览
# ============================================================

def preview_article(article_md_path: str, title: str = "") -> str:
    """
    将 Markdown 文章转为微信兼容 HTML 并保存到本地供预览。
    不需要微信凭证，图片使用本地路径。

    Args:
        article_md_path: Markdown 文件路径
        title: 文章标题（可选，用于 HTML <title>）

    Returns:
        生成的 HTML 文件路径
    """
    md_path = Path(article_md_path)
    if not md_path.exists():
        print(f"❌ 文章文件不存在：{article_md_path}")
        sys.exit(1)

    # 读取文章
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            md_content = md_path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        print(f"❌ 无法解码文章文件：{article_md_path}")
        sys.exit(1)

    base_dir = md_path.parent

    # 自动提取标题
    if not title:
        first_line = md_content.strip().split("\n")[0]
        title = re.sub(r"^#+\s*", "", first_line).strip() or "预览"

    # 将图片相对路径转为绝对路径（file:// 协议，浏览器可直接显示）
    def fix_image_path(match):
        alt = match.group(1)
        img_path = match.group(2)
        if img_path.startswith(("http://", "https://")):
            return match.group(0)
        full_path = (base_dir / img_path).resolve()
        if full_path.exists():
            # file:// URI 在 Windows 上需要三斜线
            file_uri = full_path.as_uri()
            return f"![{alt}]({file_uri})"
        return match.group(0)

    md_content = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", fix_image_path, md_content)

    # Markdown → HTML
    html_body = mistune.html(md_content)

    # 构建完整 HTML（带微信 CSS + 手机宽度模拟）
    full_html = f"""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - 微信预览</title>
<style>
/* ---- 模拟微信公众号阅读环境 ---- */
body {{
    max-width: 680px;
    margin: 0 auto;
    padding: 20px 16px;
    background: #f5f5f5;
}}
.article-container {{
    background: #fff;
    padding: 24px 20px;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}}
.preview-banner {{
    background: #07c160;
    color: #fff;
    text-align: center;
    padding: 8px;
    font-size: 13px;
    border-radius: 8px 8px 0 0;
    margin: -24px -20px 20px;
}}

/* ---- 微信排版 CSS ---- */
{WECHAT_CSS}
</style>
</head>
<body>
<div class="article-container">
<div class="preview-banner">微信公众号排版预览（模拟 680px 宽度）</div>
{html_body}
</div>
</body>
</html>
"""

    # 保存到 article 同目录
    html_path = md_path.with_suffix(".preview.html")
    html_path.write_text(full_html, encoding="utf-8")

    return str(html_path)

def main():
    parser = argparse.ArgumentParser(description="微信公众号草稿箱上传工具")
    parser.add_argument("--article", help="Markdown 文件路径")
    parser.add_argument("--title", help="文章标题")
    parser.add_argument("--cover", default="", help="封面图路径（可选，默认自动查找）")
    parser.add_argument("--digest", default="", help="文章摘要（可选，≤120字）")
    parser.add_argument("--author", default="", help="作者（可选）")
    parser.add_argument("--config", default=None, help="配置文件路径（可选）")
    parser.add_argument("--validate", action="store_true", help="仅校验配置")
    parser.add_argument("--preview", action="store_true", help="本地预览（生成 HTML 并在浏览器中打开，无需微信凭证）")

    args = parser.parse_args()

    if args.validate:
        print("🔍 校验配置...")
        try:
            config = WechatConfig(args.config)
            config.load()
            config.validate()
            print("✅ 配置校验通过")
            print(f"  appid: {config.get('appid')[:8]}...")
            print(f"  author: {config.get('default_author') or '(未设置)'}")
        except (ConfigError, WechatPublishError) as e:
            print(f"❌ 配置校验失败：{e}")
            sys.exit(1)
        return

    if args.preview:
        if not args.article:
            parser.error("预览模式需要提供 --article 参数")
        html_path = preview_article(args.article, title=args.title or "")
        print(f"✅ 预览文件已生成：{html_path}")
        # 在浏览器中打开
        import webbrowser
        webbrowser.open(Path(html_path).resolve().as_uri())
        print("🌐 已在浏览器中打开预览")
        return

    if not args.article or not args.title:
        parser.error("请提供 --article 和 --title 参数")

    result = publish_to_wechat(
        article_md_path=args.article,
        title=args.title,
        digest=args.digest,
        cover_image_path=args.cover,
        author=args.author,
        config_path=args.config,
    )

    # 输出结果摘要
    print("\n" + "=" * 50)
    if result["status"] == "success":
        print("📤 上传成功！")
        print(f"  标题：{result['title']}")
        print(f"  封面图：{'✅' if result['cover_uploaded'] else '❌'}")
        print(f"  正文配图：{result['images_uploaded']} 张上传成功")
        print(f"  草稿ID：{result['media_id']}")
        print(f"\n👉 请前往「微信公众平台 → 草稿箱」查看并发布")
    else:
        print("📤 上传失败")
        for err in result["errors"]:
            print(f"  ❌ {err}")
        print("\n常见问题排查：")
        print("  1. appid/appsecret 错误 → 检查 config/wechat.yaml")
        print("  2. IP 不在白名单 → 微信公众平台 → 开发 → 基本配置 → IP白名单")
        print("  3. 封面图过大 → 自动压缩失败时，手动调整图片大小")
        print("  4. access_token 过期 → 系统会自动刷新，如仍失败请稍后重试")
        sys.exit(1)

    # 输出 JSON 结果供程序调用
    print(f"\n[JSON] {json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
