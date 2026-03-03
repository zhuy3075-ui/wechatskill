# 微信公众号自动发文技术整理

> 来源：《公众号躺更神器！OpenClaw+Claude Skill 实现自动读对标 + 写文 + 配图 + 存入草稿箱》
> 作者：后端小肥肠
> 链接：https://mp.weixin.qq.com/s/41lLEd-8nRB1VIqWTWtASw

---

## 一、整体流程概览

六步全自动核心工作流：

```
AI生成文章 → AI生成封面图 → AI智能配图 → 图片压缩优化 → Markdown转微信HTML → 推送草稿箱
```

对应 6 个 Python 脚本（概念拆分命名，用于技术讲解）：

| 脚本 | 功能 | 依赖 |
|------|------|------|
| `write_article.py` | AI 生成文章 | DeepSeek API |
| `generate_image.py` | AI 生成封面图 | 豆包 AI生图 (Seedream4.5) |
| `add_article_images.py` | 智能配图（正文内插图） | 本地图片生成后进行智能配图 |
| `compress_image.py` | 图片压缩优化 | Pillow（Python） |
| `format_article.py` | Markdown 转微信 HTML | requests（Python） |
| `publish_draft.py` | 推送草稿箱 | requests（Python） |

> 实际仓库落地脚本与上表映射关系：
> - `scripts/generate_images.py` ≈ `generate_image.py` + `add_article_images.py` + `compress_image.py`
> - `scripts/publish_wechat.py` ≈ `format_article.py` + `publish_draft.py`
> - `write_article.py` 由主流程提示词与代理执行，不单独落地为脚本

---

## 二、Markdown 转微信 HTML（概念脚本：format_article.py；仓库实现：scripts/publish_wechat.py）

### 2.1 为什么需要转换

微信公众号后台**不支持直接贴 Markdown**，必须转成微信兼容的 HTML 格式。

### 2.2 核心功能

1. **解析 Markdown**：处理标题、段落、列表、图片等元素
2. **转换为微信兼容的 HTML + 内联 CSS**：微信编辑器不支持外部样式表，所有样式必须内联
3. **上传图片到微信素材库**：本地图片必须先上传到微信永久素材库，然后替换为微信 URL，否则发出后图片无法显示

### 2.3 核心代码结构

```python
import re

def md_to_wechat_html(md_content, base_dir=None, access_token=None):
    # 1. 解析 Markdown（标题、段落、列表、图片）
    # 2. 转换为微信兼容的 HTML + 内联 CSS
    # 3. 上传图片到微信素材库（使用 access_token）
    pass
```

### 2.4 关键技术要点

- 微信HTML必须使用**内联CSS**（inline style），不支持 `<style>` 标签或外部样式表
- 图片不能使用本地路径或外部URL，必须上传到微信永久素材库后使用返回的微信URL
- 需要处理的 Markdown 元素：标题（h1-h6）、段落（p）、列表（ul/ol）、图片（img）、代码块、加粗/斜体等

---

## 三、上传到公众号后台 / 推送草稿箱（publish_draft.py）

### 3.1 前置条件

- 需要微信公众号的 `appid` 和 `appsecret`
- 获取方式：微信公众平台 → 开发 → 基本配置

### 3.2 核心 API 流程

```
获取 access_token → 上传封面图（永久素材）→ 创建草稿
```

### 3.3 核心代码结构

```python
import requests

def get_access_token(appid, appsecret):
    # 获取微信 access_token（带缓存）
    # API: https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}
    pass

def upload_thumb(access_token, image_path):
    # 上传封面图为永久素材
    # API: https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={ACCESS_TOKEN}&type=image
    pass

def add_draft(access_token, title, html_content, thumb_media_id):
    # 创建草稿，返回 media_id
    # API: https://api.weixin.qq.com/cgi-bin/draft/add?access_token={ACCESS_TOKEN}
    pass
```

### 3.4 微信 API 要点

| API | 用途 | 关键参数 |
|-----|------|---------|
| `/cgi-bin/token` | 获取 access_token | appid, appsecret |
| `/cgi-bin/material/add_material` | 上传永久素材（图片） | access_token, type=image, 图片文件 |
| `/cgi-bin/draft/add` | 创建草稿 | access_token, title, content(HTML), thumb_media_id |

---

## 四、文章中插入图片（add_article_images.py）

### 4.1 核心逻辑

自动扫描文章中的 `##` 小标题，在合适的位置自动插入正文配图。

### 4.2 核心代码结构

```python
def analyze_article_structure(md_content):
    # 1. 分析文章结构（找出 ## 标题）
    # 2. 选择合适的插入位置
    # 3. 生成配图并插入 Markdown
    pass
```

### 4.3 插图策略

- 扫描 Markdown 中的 `##` 二级标题
- 在标题后的合适位置插入 `![图片描述](图片路径)` 格式的图片引用
- 图片需要先由 AI 生成，然后插入到 Markdown 中
- 最终在 `format_article.py` 阶段会将本地图片上传到微信素材库并替换 URL

### 4.4 图片上传到微信的完整链路

```
AI 生成图片（本地文件）
  → compress_image.py 压缩优化
  → 插入 Markdown 文本中
  → format_article.py 中统一上传到微信永久素材库
  → 替换为微信 URL
  → 最终 HTML 中使用微信 URL 的 <img> 标签
```

---

## 五、封面图（generate_image.py + compress_image.py）

### 5.1 封面图生成

使用豆包 AI 生图接口（Seedream4.5），根据文章语义生成封面图。

```python
import requests

def generate_cover_image(topic, title="", style="干货"):
    # 1. 构建提示词（根据主题+风格）
    # 2. 调用豆包 API 生成图片
    # 3. 下载并保存图片
    pass
```

### 5.2 封面图压缩（关键！）

**微信公众号封面图不能超过 64KB**，这是经常导致上传报错的痛点。

```python
from PIL import Image

def compress_image(input_path, output_path=None, target_size=(900, 500), quality=85):
    # 1. 打开图片
    # 2. 裁剪到目标比例（900x500 即 9:5 比例）
    # 3. 缩放并压缩保存
    pass
```

### 5.3 封面图技术要点

| 项目 | 要求 |
|------|------|
| 大小限制 | **≤ 64KB**（超过会上传失败） |
| 推荐尺寸 | 900 × 500 px（9:5 比例） |
| 压缩工具 | Pillow 库（无损裁剪 + 极致压缩） |
| 压缩质量 | quality=85 起步，按需降低 |
| 上传方式 | 通过 `/cgi-bin/material/add_material` API 上传为永久素材 |
| 返回值 | `thumb_media_id`，用于创建草稿时关联封面 |

---

## 六、配置文件（config.json）

```json
{
  "deepseek_api_key": "sk-xxxxxxxxxxxxxxxx",
  "deepseek_model": "deepseek-chat",
  "doubao_api_key": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "appid": "wx1234567890abcdef",
  "appsecret": "1234567890abcdef1234567890abcdef"
}
```

| 配置项 | 说明 | 获取方式 |
|--------|------|---------|
| `deepseek_api_key` | DeepSeek API 密钥 | DeepSeek 开放平台 |
| `deepseek_model` | 使用的模型 | 默认 `deepseek-chat` |
| `doubao_api_key` | 豆包 API 密钥 | 豆包开放平台 |
| `appid` | 微信公众号 AppID | 微信公众平台 → 开发 → 基本配置 |
| `appsecret` | 微信公众号 AppSecret | 同上 |

---

## 七、关键技术总结

### 7.1 微信公众号发文 API 核心链路

```
1. 获取 access_token（appid + appsecret）
2. 上传封面图 → 得到 thumb_media_id
3. 上传正文图片 → 得到各图片的微信 URL
4. Markdown → HTML（内联CSS） + 替换图片URL
5. 调用 draft/add API → 草稿箱
```

### 7.2 必须注意的坑

1. **图片必须上传到微信素材库**：外部 URL 和本地路径在公众号文章中无法显示
2. **封面图 ≤ 64KB**：超过会导致上传失败，必须压缩
3. **HTML 必须内联 CSS**：微信不支持 `<style>` 标签或外部样式表
4. **access_token 有效期 2 小时**：需要缓存机制，避免频繁请求
5. **Markdown 不能直接贴**：必须转换为微信兼容的 HTML 格式

### 7.3 技术栈

- Python + requests（API 调用）
- Pillow（图片处理和压缩）
- 微信公众平台 API（素材上传、草稿创建）
- DeepSeek API（文章生成）
- 豆包 AI / Seedream4.5（图片生成）

---

## 八、微信公众平台官方 API 文档详解

> 以下内容基于微信官方文档整理，所有 API 均需在服务端调用，不可从前端直接调用。

### 8.1 获取 access_token

**access_token 是所有微信 API 调用的凭证。**

| 项目 | 说明 |
|------|------|
| 接口 | `getAccessToken`（基础版）/ `getStableAccessToken`（推荐） |
| 请求方式 | GET |
| URL | `https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET` |
| 有效期 | **2 小时（7200 秒）** |
| 刷新机制 | 刷新时旧 token 仍有效 5 分钟，确保平滑过渡 |
| 存储要求 | 至少预留 **512 字符**存储空间 |

**请求参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `grant_type` | 是 | 固定值 `client_credential` |
| `appid` | 是 | 公众号唯一凭证（微信公众平台 → 开发 → 基本配置） |
| `secret` | 是 | 公众号唯一凭证密钥 |

**返回示例：**

```json
{
  "access_token": "ACCESS_TOKEN_VALUE",
  "expires_in": 7200
}
```

**IP 白名单配置（必须）：**

- 路径：微信公众平台 → 开发 → 基本配置 → IP白名单
- 只有白名单内的 IP 才能调用需要 AppSecret 的接口
- 支持单个 IP（如 `172.0.0.1`）和 CIDR 网段（如 `172.0.0.1/24`）
- 不支持 `172.0.0.*` 通配符格式，不支持 `IP:Port` 格式
- 未配置白名单会返回错误码 `40164`（invalid ip, not in whitelist）

**常见错误码：**

| 错误码 | 说明 |
|--------|------|
| 40001 | access_token 无效或不是最新的 |
| 40125 | appsecret 无效 |
| 40164 | IP 地址不在白名单中 |
| 42001 | access_token 已过期 |

**最佳实践：**
- 使用中央服务器统一获取和刷新 token，避免多服务器并发刷新导致覆盖
- 做好缓存，在 token 过期前主动刷新
- 推荐使用 `getStableAccessToken` 接口

> 参考：[微信官方文档 - 获取AccessToken](https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html)

---

### 8.2 上传永久素材（add_material）

**用于上传封面图和正文配图到微信素材库。**

| 项目 | 说明 |
|------|------|
| 请求方式 | POST（form-data） |
| URL | `https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=ACCESS_TOKEN&type=TYPE` |

**请求参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `access_token` | 是 | 接口调用凭证 |
| `type` | 是 | 媒体类型：`image`（图片）/ `voice`（语音）/ `video`（视频）/ `thumb`（缩略图） |
| `media` | 是 | 媒体文件（form-data 格式） |
| `description` | 视频必填 | JSON 对象，含 `title` 和 `introduction` |

**各类型素材限制：**

| 类型 | 大小限制 | 格式 | 数量上限 |
|------|---------|------|---------|
| 图片 image | **≤ 10MB** | bmp/png/jpeg/jpg/gif | 100,000 |
| 缩略图 thumb | **≤ 64KB** | jpg | 100,000 |
| 语音 voice | ≤ 2MB，≤ 60s | mp3/wma/wav/amr | 1,000 |
| 视频 video | ≤ 10MB | mp4 | 1,000 |

**返回示例：**

```json
{
  "media_id": "MEDIA_ID",
  "url": "http://mmbiz.qpic.cn/XXXXX"
}
```

- 图片类型会同时返回 `media_id` 和 `url`
- `media_id` 用于草稿创建时关联封面（`thumb_media_id`）
- `url` 仅限在腾讯域名内使用

**curl 示例：**

```bash
curl "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=ACCESS_TOKEN&type=image" \
  -F media=@cover.jpg
```

> 参考：[微信官方文档 - 新增永久素材](https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/Adding_Permanent_Assets.html)

---

### 8.3 上传图文消息内的图片（uploadimg）

**专门用于上传正文内嵌图片，不占用素材库配额。**

| 项目 | 说明 |
|------|------|
| 请求方式 | POST（form-data） |
| URL | `https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=ACCESS_TOKEN` |

**请求参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `access_token` | 是 | 接口调用凭证 |
| `media` | 是 | 图片文件（form-data），JPG/PNG 格式，≤ 1MB |

**返回示例：**

```json
{
  "url": "http://mmbiz.qpic.cn/XXXXX",
  "errcode": 0,
  "errmsg": "ok"
}
```

**与 add_material 的区别：**

| 对比项 | uploadimg | add_material |
|--------|-----------|--------------|
| 用途 | 图文消息正文内的图片 | 封面图、独立素材 |
| 占用配额 | **不占用** 100,000 素材配额 | 占用配额 |
| 返回值 | 仅返回 `url` | 返回 `media_id` + `url` |
| 图片大小 | ≤ 1MB | ≤ 10MB |
| 格式 | JPG/PNG | bmp/png/jpeg/jpg/gif |

**curl 示例：**

```bash
curl -F media=@article_image.jpg \
  "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=ACCESS_TOKEN"
```

**常见错误码：**

| 错误码 | 说明 |
|--------|------|
| 40005 | 不合法的文件类型 |
| 40009 | 图片大小超过限制 |

> 参考：[微信官方文档 - 上传图文消息内的图片](https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/New_temporary_material.html)

---

### 8.4 新增草稿（draft/add）

**将 HTML 文章内容存入公众号草稿箱。**

| 项目 | 说明 |
|------|------|
| 请求方式 | POST（JSON） |
| URL | `https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN` |

**请求体（JSON）：**

```json
{
  "articles": [
    {
      "title": "文章标题",
      "author": "作者",
      "digest": "文章摘要（≤120字，超出自动截断）",
      "content": "<p style='...'>文章HTML正文</p>",
      "content_source_url": "https://原文链接（可选）",
      "thumb_media_id": "封面图的media_id",
      "need_open_comment": 0,
      "only_fans_can_comment": 0
    }
  ]
}
```

**articles 数组字段说明：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `title` | 是 | 文章标题 |
| `author` | 否 | 作者 |
| `digest` | 否 | 摘要，≤ 120 字，不填则自动从正文截取 |
| `content` | 是 | HTML 正文（**内联 CSS**，图片须用微信 URL） |
| `content_source_url` | 否 | 原文链接 |
| `thumb_media_id` | 是 | 封面图的 media_id（通过 add_material 上传获得） |
| `need_open_comment` | 否 | 是否打开评论，0-关闭，1-打开 |
| `only_fans_can_comment` | 否 | 是否仅粉丝可评论，0-所有人，1-仅粉丝 |

**返回示例：**

```json
{
  "media_id": "MEDIA_ID"
}
```

**草稿相关 API 全家桶：**

| API | 用途 |
|-----|------|
| `draft/add` | 新增草稿 |
| `draft/update` | 修改草稿 |
| `draft/get` | 获取草稿详情 |
| `draft/delete` | 删除草稿 |
| `draft/batchget` | 获取草稿列表 |
| `draft/count` | 获取草稿总数 |

> 参考：[微信官方文档 - 草稿箱](https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Add_draft.html)

---

### 8.5 发布接口（freepublish/submit）

**将草稿箱中的文章正式发布。**

| 项目 | 说明 |
|------|------|
| 请求方式 | POST |
| URL | `https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token=ACCESS_TOKEN` |

**请求体：**

```json
{
  "media_id": "MEDIA_ID"
}
```

- `media_id` 是通过 `draft/add` 创建草稿后返回的 ID

**发布相关 API 全家桶：**

| API | 用途 |
|-----|------|
| `freepublish/submit` | 提交发布 |
| `freepublish/get` | 查询发布状态 |
| `freepublish/getarticle` | 获取已发布文章信息 |
| `freepublish/batchget` | 获取已发布文章列表 |
| `freepublish/delete` | 删除已发布文章 |

**注意：** 自 2025 年 7 月起，个人账号、未认证企业账号、不支持认证的账号将被收回该接口调用权限。

> 参考：[微信官方文档 - 发布能力](https://developers.weixin.qq.com/doc/offiaccount/Publish/Publish.html)

---

## 九、Markdown 转微信 HTML 开源方案

### 9.1 主流 Python 方案

| 项目 | 语言 | 特点 |
|------|------|------|
| [MaxPress](https://github.com/nickliqian/MaxPress) | Python 3 | 一键排版，使用 `mistune` + `premailer` + `lesscpy`，支持自定义 CSS |
| [md2wx](https://github.com/davycloud/md2wx) | Python | 转 HTML + 自定义样式 + JS 辅助复制到公众号 |
| [md2oa](https://github.com/shaogefenhao/md2oa) | Node.js | 图片 Base64 内嵌、代码高亮、内联 CSS、VS Code 插件 |

### 9.2 关键技术点

**微信 HTML 的特殊要求：**

1. **内联 CSS 是唯一选择**：微信编辑器会过滤掉 `<style>` 标签和外部样式表，所有样式必须写在元素的 `style` 属性中
2. **图片处理**：
   - 正文图片须通过 `uploadimg` API 上传，获取微信 URL 后替换 `<img src="...">`
   - 封面图须通过 `add_material` API 上传为永久素材
3. **列表处理**：微信对 `<ol>`/`<ul>` 的渲染不稳定，一些方案会将列表转为普通段落 + 手动编号
4. **代码块**：需自行处理语法高亮（转为带颜色的 `<span>` 标签）
5. **推荐 Python 库组合**：
   - `mistune` 或 `markdown`：Markdown 解析
   - `premailer`：将 `<style>` 中的 CSS 转为内联样式
   - `Pillow`：图片处理和压缩
   - `requests`：调用微信 API 上传图片

---

## 十、完整 API 调用链路总结

```
┌──────────────────────────────────────────────────────────────────┐
│                     前置：配置 IP 白名单                          │
│         微信公众平台 → 开发 → 基本配置 → IP白名单                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1：获取 access_token                                       │
│ GET /cgi-bin/token?grant_type=client_credential                 │
│     &appid=APPID&secret=APPSECRET                               │
│ → 返回 access_token（有效期 2h，需缓存）                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│ Step 2a：上传   │ │ Step 2b：上传     │ │ Step 2c：Markdown    │
│ 封面图          │ │ 正文图片          │ │ 转 HTML              │
│                 │ │                  │ │                      │
│ POST            │ │ POST             │ │ • 解析 Markdown      │
│ /cgi-bin/       │ │ /cgi-bin/media/  │ │ • 转 HTML+内联CSS    │
│ material/       │ │ uploadimg        │ │ • 替换图片URL        │
│ add_material    │ │                  │ │   为微信URL          │
│ type=thumb      │ │ ≤1MB, JPG/PNG   │ │                      │
│ ≤64KB, JPG      │ │ 不占素材配额     │ │                      │
│                 │ │                  │ │                      │
│ → thumb_media_id│ │ → 图片 url       │ │ → HTML content       │
└────────┬────────┘ └────────┬─────────┘ └──────────┬───────────┘
         │                   │                      │
         └───────────────────┼──────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3：创建草稿                                                 │
│ POST /cgi-bin/draft/add                                         │
│ Body: { articles: [{ title, content(HTML), thumb_media_id }] }  │
│ → 返回 media_id                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4（可选）：发布                                              │
│ POST /cgi-bin/freepublish/submit                                │
│ Body: { media_id }                                              │
│ → 文章正式发布                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 参考来源

- [微信官方文档 - 获取AccessToken](https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html)
- [微信官方文档 - 新增永久素材](https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/Adding_Permanent_Assets.html)
- [微信官方文档 - 上传图文消息内图片](https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/New_temporary_material.html)
- [微信官方文档 - 草稿箱](https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Add_draft.html)
- [微信官方文档 - 发布能力](https://developers.weixin.qq.com/doc/offiaccount/Publish/Publish.html)
- [MaxPress - Python 微信排版工具](https://github.com/nickliqian/MaxPress)
- [md2wx - Markdown转微信HTML](https://github.com/davycloud/md2wx)
- [md2oa - Markdown转公众号](https://github.com/shaogefenhao/md2oa)
