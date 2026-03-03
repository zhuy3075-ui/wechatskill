# 配置文件索引

本目录包含所有 API 和服务配置文件。为避免敏感信息误提交，默认使用 `*.local.yaml` 作为可写配置。

| 文件 | 用途 | 必填项 | 获取方式 |
|------|------|--------|---------|
| `image-gen.local.yaml` | 云雾API配图生成（默认读取） | `api_key` | 云雾平台 |
| `wechat.local.yaml` | 微信公众号API（默认读取） | `appid`, `appsecret` | 微信公众平台 → 开发 → 基本配置 |
| `image-gen.local.yaml.example` | 本地配置示例 | - | 复制后改名为 `image-gen.local.yaml` |
| `wechat.local.yaml.example` | 本地配置示例 | - | 复制后改名为 `wechat.local.yaml` |
| `image-gen.yaml` | 兼容旧路径/模板（不建议填真实密钥） | - | 历史兼容 |
| `wechat.yaml` | 兼容旧路径/模板（不建议填真实密钥） | - | 历史兼容 |

## 注意事项

- `.wechat_token_cache.json` 是自动生成的缓存文件，**不要**手动编辑或提交到 git
- `*.local.yaml` 已加入 `.gitignore`，建议只在本地文件中填写密钥
- 配置文件中的 API Key 属于敏感信息，**不要**提交到公开仓库
