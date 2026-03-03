# 方案：微信公众号后台上传功能

## Context

用户希望在写作系统完成文章生成后，能通过自然语言触发「一键上传到公众号草稿箱」的功能。目前系统只能生成 Markdown 文件和配图到本地 outputs/ 目录，缺少从 Markdown → 微信 HTML → 上传图片 → 推送草稿箱的完整链路。

同时，项目中配置分散（历史上仅 `config/image-gen.yaml` 用于配图），需要整合为统一配置管理。

---

## 一、要改动的文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `config/wechat.local.yaml` | **新建** | 微信公众号 API 配置（appid、appsecret 等，默认读取） |
| `config/image-gen.local.yaml` | **新建** | 配图生成本地配置（默认读取） |
| `config/wechat.yaml` | 保持兼容 | 微信配置模板/兼容文件 |
| `config/image-gen.yaml` | 保持兼容 | 配图配置模板/兼容文件 |
| `config/README.md` | **新建** | 统一配置说明文档，索引所有 config 文件 |
| `scripts/publish_wechat.py` | **新建** | 核心脚本：MD→HTML + 上传图片 + 推送草稿箱 |
| `SKILL.md` | **修改** | 新增触发关键词、写作流程第十步 |
| `wechat-publish-tech-notes.md` | 保持不变 | 技术参考（不改动，供实现参考） |

---

## 二、统一配置管理

### 2.1 现状分析

| 配置 | 文件 | 状态 |
|------|------|------|
| 云雾API配图 | `config/image-gen.local.yaml` | ✅ 默认读取本地配置，兼容 `config/image-gen.yaml` |
| 微信公众号API | 无 | ❌ 缺失 |
| 统一索引 | 无 | ❌ 缺失 |

### 2.2 方案：保持 YAML 分文件 + 新增 config/README.md 索引

**不合并为一个大文件**，原因：
- 兼容历史 `image-gen.yaml`，但默认优先读取 `image-gen.local.yaml`
- 不同配置的更新频率不同（API Key 很少改，微信 token 需要自动缓存）
- 分文件更易于理解和维护

### 2.3 新建 `config/wechat.local.yaml`

```yaml
# ============================================================
# 微信公众号 API 配置
# ============================================================
#
# 获取方式：微信公众平台 → 开发 → 基本配置
# 首次使用请填写 appid 和 appsecret
# ============================================================

# ---- 必填：公众号凭证 ----
appid: ""              # 公众号 AppID
appsecret: ""          # 公众号 AppSecret

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
```

### 2.4 新建 `config/README.md`

```markdown
# 配置文件索引

本目录包含所有 API 和服务配置文件。首次使用请填写对应的 API Key。

| 文件 | 用途 | 必填项 | 获取方式 |
|------|------|--------|---------|
| `image-gen.local.yaml` | 云雾API配图生成（默认） | `api_key` | 云雾平台 |
| `wechat.local.yaml` | 微信公众号API（上传草稿箱，默认） | `appid`, `appsecret` | 微信公众平台 → 开发 → 基本配置 |
| `image-gen.yaml` | 配图模板/兼容 | - | 历史兼容 |
| `wechat.yaml` | 微信模板/兼容 | - | 历史兼容 |

## 注意事项
- `.wechat_token_cache.json` 是自动生成的缓存文件，**不要**手动编辑或提交到 git
- 配置文件中的 API Key 属于敏感信息，**不要**提交到公开仓库
```

---

## 三、核心脚本 `scripts/publish_wechat.py`

### 3.1 模块架构

```
publish_wechat.py（约 400 行）
│
├── WechatConfig              # 加载 config/wechat.local.yaml（兼容旧路径）
│   ├── load()                # 读取配置，不存在则创建模板
│   └── validate()            # 校验 appid/appsecret 非空
│
├── WechatAuth                # access_token 管理
│   ├── get_token()           # 获取 token（优先读缓存，过期则刷新）
│   ├── _request_token()      # 调用 GET /cgi-bin/token
│   └── _cache_token()        # 写入 .wechat_token_cache.json
│
├── ImageCompressor           # 封面图压缩
│   └── compress_cover()      # Pillow 裁剪+压缩至 ≤64KB
│
├── WechatUploader            # 图片上传
│   ├── upload_thumb()        # POST /cgi-bin/material/add_material → thumb_media_id
│   └── upload_content_image()# POST /cgi-bin/media/uploadimg → 微信 URL
│
├── MarkdownToWechatHTML      # Markdown → 微信 HTML
│   ├── convert()             # 完整转换流程
│   ├── _parse_markdown()     # mistune 解析
│   ├── _apply_inline_css()   # premailer 内联化
│   └── _replace_images()     # 替换本地图片为微信 URL
│
└── DraftPublisher            # 草稿推送
    └── create_draft()        # POST /cgi-bin/draft/add → media_id
```

### 3.2 API 调用链路

```
Step 1: WechatConfig.load()
  → 读取 config/wechat.local.yaml（兼容 config/wechat.yaml），校验 appid/appsecret

Step 2: WechatAuth.get_token()
  → GET https://api.weixin.qq.com/cgi-bin/token
      ?grant_type=client_credential
      &appid=APPID
      &secret=APPSECRET
  → 返回 access_token（缓存 2h，旧 token 5min 过渡期）

Step 3: ImageCompressor.compress_cover()
  → Pillow 裁剪至 900×500，压缩至 ≤ 64KB（quality 递减策略）

Step 4: WechatUploader.upload_thumb()
  → POST https://api.weixin.qq.com/cgi-bin/material/add_material
      ?access_token=TOKEN&type=thumb
  → form-data: media=@cover.jpg
  → 返回 { media_id, url }

Step 5: WechatUploader.upload_content_image()（逐张上传正文配图）
  → POST https://api.weixin.qq.com/cgi-bin/media/uploadimg
      ?access_token=TOKEN
  → form-data: media=@image.jpg (≤1MB, JPG/PNG)
  → 返回 { url }（不占素材配额）

Step 6: MarkdownToWechatHTML.convert()
  → mistune 解析 Markdown → 原始 HTML
  → 套入微信排版 CSS 模板（参照 rules/formatting.md）
  → premailer.transform() 将所有 CSS 转为内联
  → 扫描 <img src="本地路径">，替换为 Step 5 返回的微信 URL

Step 7: DraftPublisher.create_draft()
  → POST https://api.weixin.qq.com/cgi-bin/draft/add
      ?access_token=TOKEN
  → Body: {
      "articles": [{
        "title": "标题",
        "author": "作者",
        "digest": "摘要（≤120字）",
        "content": "<HTML正文>",
        "thumb_media_id": "Step 4 返回的 media_id"
      }]
    }
  → 返回 { media_id }（草稿ID）
```

### 3.3 图片处理策略对比

| 图片类型 | 上传 API | 大小限制 | 格式 | 占用配额 | 返回值 |
|----------|---------|---------|------|---------|--------|
| 封面图 | `add_material` (type=thumb) | **≤ 64KB** | JPG | 是（10万上限） | `media_id` + `url` |
| 正文配图 | `uploadimg` | **≤ 1MB** | JPG/PNG | **不占用** | 仅 `url` |

### 3.4 封面图压缩策略

```python
def compress_cover(input_path, output_path, max_kb=64, target=(900, 500)):
    """
    压缩封面图至微信限制以内
    策略：先裁剪比例 → 缩放 → 递减quality直到≤max_kb
    """
    img = Image.open(input_path)

    # 1. 裁剪到 9:5 比例（居中裁剪）
    # 2. 缩放到 900×500
    # 3. quality 从 85 开始，每次 -5，直到文件 ≤ 64KB
    # 4. 如果 quality=10 仍超标，进一步缩小尺寸
```

### 3.5 Markdown → 微信 HTML 的 CSS 模板

```css
/* 微信排版友好的 CSS（参照 rules/formatting.md） */
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
h1 { font-size: 22px; font-weight: bold; color: #333; margin: 24px 0 16px; }
h2 { font-size: 18px; font-weight: bold; color: #333; margin: 20px 0 12px; }
h3 { font-size: 16px; font-weight: bold; color: #333; margin: 16px 0 8px; }
p { font-size: 15px; color: #3f3f3f; line-height: 1.8; margin: 0 0 16px; }
blockquote { border-left: 3px solid #ddd; padding: 8px 16px; color: #666; margin: 16px 0; }
strong { font-weight: bold; color: #333; }
img { max-width: 100%; height: auto; margin: 16px auto; display: block; }
ul, ol { padding-left: 24px; margin: 8px 0 16px; }
li { font-size: 15px; color: #3f3f3f; line-height: 1.8; margin: 4px 0; }
code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 14px; color: #c7254e; }
pre { background: #f5f5f5; padding: 16px; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; color: #333; }
```

### 3.6 入口函数设计

```python
def publish_to_wechat(
    article_md_path: str,        # Markdown 文件路径
    title: str,                  # 文章标题
    digest: str = "",            # 摘要（≤120字，不填自动截取）
    cover_image_path: str = "",  # 封面图路径（不填则用第一张配图）
    author: str = "",            # 作者（不填则读 config）
    config_path: str = None,     # 配置文件路径
) -> dict:
    """
    一键发布到微信草稿箱

    Returns:
        {
            "status": "success" / "failed",
            "media_id": "草稿media_id",
            "title": "文章标题",
            "images_uploaded": 5,
            "cover_uploaded": True,
            "errors": []
        }
    """
```

### 3.7 CLI 用法

```bash
# 完整参数
python scripts/publish_wechat.py \
  --article outputs/犀利派/2026-03-03-干货-时间管理/article.md \
  --title "时间管理的5个底层逻辑" \
  --cover outputs/犀利派/2026-03-03-干货-时间管理/images/图片_1.png \
  --digest "你以为的时间管理，可能从第一步就错了"

# 最小参数（标题必填，其他自动推断）
python scripts/publish_wechat.py \
  --article outputs/默认风格/2026-03-03-干货-时间管理/article.md \
  --title "时间管理的5个底层逻辑"

# 仅校验配置
python scripts/publish_wechat.py --validate
```

---

## 四、用户触发方式与 SKILL.md 改动

### 4.1 新增触发关键词

在 SKILL.md 的「调用方式」板块中新增：

```markdown
### 上传公众号
/wechat-writer 上传公众号（将最近生成的文章上传到草稿箱）
/wechat-writer 发布到草稿箱
/wechat-writer 上传到后台
```

### 4.2 自然语言等价触发

以下自然语言可触发上传流程：
- "帮我上传到公众号"
- "发到公众号后台"
- "上传草稿箱" / "存到草稿箱"
- "推送到公众号"
- "我要上传到公众号后台中"

### 4.3 写作流程新增「第十步」

在 SKILL.md 第九步（记忆存档）之后新增：

```markdown
### 第十步：上传公众号草稿箱（用户触发，`MAY`）

> 仅在用户明确要求时执行。写作流程结束时在交付回执中提示可选操作。

#### 1. 配置检查（`MUST`）
- 首次使用时检测 `config/wechat.local.yaml`（兼容 `config/wechat.yaml`）
- 文件不存在 → 自动创建模板，提示用户填写 appid 和 appsecret
- appid/appsecret 为空 → 提示"请先在 config/wechat.local.yaml 中配置公众号凭证"，跳过上传
- IP 白名单提醒：首次使用时提示用户确认服务器 IP 已加入白名单

#### 2. 确认上传内容（`MUST`）
向用户确认以下信息（大部分自动推断）：

| 信息 | 推断规则 | 追问？ |
|------|---------|--------|
| 标题 | 用户在第四步选定的标题 | 仅在用户未选时 |
| 摘要 | 用户在第八步选定的摘要（≤120字） | 永不追问，自动截取 |
| 封面图 | 默认使用 images/图片_1.png | 仅在无配图时 |
| 作者 | 读取 config/wechat.local.yaml 的 default_author | 永不追问 |

确认格式：
```
📤 即将上传到公众号草稿箱：

标题：{标题}
摘要：{摘要前30字}...
封面图：{图片路径}
作者：{作者}
正文配图：{N}张

确认上传？（Y/修改标题/修改摘要/换封面图/取消）
```

#### 3. 执行上传（`MUST`）
调用 `scripts/publish_wechat.py`：
1. Markdown → 微信兼容 HTML（内联CSS + 图片上传替换）
2. 封面图压缩（≤64KB）→ 上传永久素材 → 获取 thumb_media_id
3. 正文图片 → 逐张上传 uploadimg → 替换为微信 URL
4. 创建草稿 → 返回 media_id

#### 4. 反馈结果（`MUST`）

成功时输出：
```
📤 上传成功！

标题：{标题}
摘要：{摘要}
封面图：✅ 已上传
正文配图：{N}/{Total}张上传成功
草稿ID：{media_id}

👉 请前往「微信公众平台 → 草稿箱」查看并发布
```

失败时输出：
```
📤 上传失败

错误原因：{具体错误信息}
建议操作：{修复建议}

常见问题排查：
1. appid/appsecret 错误 → 检查 config/wechat.local.yaml
2. IP 不在白名单 → 微信公众平台 → 开发 → 基本配置 → IP白名单
3. 封面图过大 → 自动压缩失败时，手动调整图片大小
4. access_token 过期 → 系统会自动刷新，如仍失败请稍后重试
5. 图片格式不支持 → 正文图仅支持 JPG/PNG，封面图仅支持 JPG
```
```

### 4.4 交付回执扩展

在第八步的交付回执中新增字段：

```
publish_hint: "输入「上传公众号」可一键推送到草稿箱"
```

---

## 五、依赖安装

```bash
pip install mistune premailer Pillow requests pyyaml
```

| 依赖 | 用途 | 是否已有 |
|------|------|---------|
| `requests` | API 调用 | ✅ 已有 |
| `Pillow` | 图片压缩 | ✅ 已有 |
| `pyyaml` | 配置读取 | ✅ 已有 |
| `mistune` | Markdown 解析 | ❌ 新增 |
| `premailer` | CSS 内联化 | ❌ 新增 |

---

## 六、错误处理与边界情况

| 场景 | 处理方式 |
|------|---------|
| config/wechat.local.yaml 不存在 | 自动创建模板，提示填写 |
| appid/appsecret 为空 | 提示配置后重试，不崩溃 |
| IP 不在白名单（40164） | 明确提示白名单配置路径 |
| access_token 过期（42001） | 自动清除缓存并重新获取 |
| 封面图 > 64KB 压缩后仍超 | 进一步缩小尺寸到 600×333 |
| 正文图 > 1MB | 自动压缩到 1MB 以内 |
| 图片格式不支持 | 自动转换为 JPG/PNG |
| 部分图片上传失败 | 成功的保留，失败的在正文标注 `[图片上传失败]` |
| 全部图片上传失败 | 正文不含图片正常创建草稿，标注待补图 |
| 创建草稿失败 | 输出具体错误码和修复建议 |
| 网络超时 | 重试 3 次，间隔指数递增 |

---

## 七、验证方案

1. **配置校验**：`python scripts/publish_wechat.py --validate`
2. **MD转HTML测试**：准备一篇含图片的 Markdown，转换后在浏览器查看 HTML
3. **封面图压缩测试**：用大图测试压缩到 ≤64KB，验证尺寸和质量
4. **图片上传测试**：配置好凭证后，上传单张图片到微信素材库
5. **端到端测试**：上传完整文章到草稿箱，在微信后台查看排版效果
6. **错误场景测试**：
   - 错误的 appid → 应返回清晰错误提示
   - IP 不在白名单 → 应提示配置白名单
   - 无配图文章 → 应正常上传（无封面图时提示）

---

## 八、文件改动摘要

| 操作 | 文件路径 | 工作量 |
|------|---------|--------|
| 新建 | `config/wechat.local.yaml` | 配置模板（默认读取） |
| 新建 | `config/README.md` | 配置索引文档 |
| 新建 | `scripts/publish_wechat.py` | ~400行（核心脚本） |
| 修改 | `SKILL.md` | 新增触发词 + 第十步 + 回执扩展 |
| 修改 | `README.md` | 文件索引补充 |
| 修改 | `WORKFLOW.md` | 流程图更新 |
| 修改 | `.gitignore` | 添加 `config/.wechat_token_cache.json` |
