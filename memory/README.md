# 上下文记忆库

本文件夹用于保存优质的上下文记忆，帮助 AI 在后续创作中复用高质量的素材、观点和经验。

## 文件夹结构

```
memory/
├── README.md              # 本说明文件
├── golden-sentences.md    # 金句库：收集每次创作中产生的优质金句
├── titles.md              # 标题自学习库：标题效果档案、高效模式、偏好画像
├── topics.md              # 选题库：CSV 格式管理，按赛道分类，含爆款潜力评分
├── performance.md         # 数据复盘：文章发布效果追踪、高效写作模式、效果基准线
├── benchmarks.md          # 对标账号：竞品档案、爆款规律、差异化分析
├── calendar.md            # 内容日历：发布排期、节假日规划、内容搭配
├── feedback.md            # 反馈记录：用户对文章的修改意见和偏好
├── materials.md           # 素材库：案例、数据、故事等可复用素材
└── audience.md            # 读者画像：目标读者的特征和偏好
```

## 使用规范

### 写入规则
1. 每次完成一篇文章后，自动提取以下内容写入记忆库：
   - 产生的优质金句 → `golden-sentences.md`
   - 标题选择和效果 → `titles.md`
   - 选题信息和效果 → `topics.md`（CSV 格式，按赛道分类）
   - 用户的修改反馈 → `feedback.md`
   - 使用的案例素材 → `materials.md`

2. 发布后效果数据写入：
   - 文章效果数据 → `performance.md`（阅读量、分享率、涨粉等）
   - 对标账号分析 → `benchmarks.md`
   - 排期更新 → `calendar.md`

3. 写入格式统一使用：
   ```
   ## [日期] [文章标题]
   - 内容条目
   - 来源/备注
   ```

### 读取规则
1. 开始新文章创作前，扫描记忆库获取：
   - 用户偏好的写作风格
   - 可复用的素材和金句
   - 避免重复的选题
   - 目标读者画像
   - 高效写作模式（从 performance.md）
   - 对标账号情报（从 benchmarks.md）
   - 本周排期（从 calendar.md）

2. 记忆调用优先级：
   - feedback.md（用户偏好最优先）
   - performance.md（效果数据指导策略）
   - titles.md（标题偏好和高效模式）
   - topics.md（选题库，避免重复选题）
   - calendar.md（排期，确认当前任务）
   - benchmarks.md（对标情报）
   - audience.md（读者画像）
   - golden-sentences.md（金句复用）
   - materials.md（素材复用）

### 维护规则

#### 容量限制
| 文件 | 上限 | 淘汰规则 |
|------|------|---------|
| golden-sentences.md | 100 条 | 删除使用次数最少的、超过 6 个月未使用的 |
| titles.md 效果档案 | 200 条 | 保留全部（数据越多学习越准） |
| topics.md CSV | 500 条 | 已弃选题超过 3 个月的删除，已写选题保留 |
| performance.md 效果档案 | 不限 | 保留全部（核心数据资产） |
| benchmarks.md | 20 个账号 | 超过 6 个月未更新的标记为"不活跃" |
| calendar.md | 保留最近 3 个月 | 超过 3 个月的排期归档到底部"历史排期" |
| materials.md | 200 条 | 超过 6 个月未使用的移到"冷素材"区 |
| feedback.md | 不限 | 保留全部（用户偏好不过期） |

#### 定期清理触发
- 每积累 50 篇文章 → 全面清理一次
- 每月初 → 检查 calendar.md，归档上月排期
- 每季度 → 检查 benchmarks.md，标记不活跃账号
- 金句库满 100 条时 → 触发淘汰，保留效果最好的 80 条

## 文件职责边界

> 避免数据重复存储，每类数据只存一个地方。

| 数据类型 | 存储位置 | 不要存到 |
|---------|---------|---------|
| 标题效果数据 | titles.md | ~~performance.md~~ |
| 文章整体效果数据 | performance.md | ~~feedback.md~~ |
| 用户修改偏好 | feedback.md | ~~performance.md~~ |
| 选题信息 | topics.md | ~~performance.md~~ |
| 对标账号信息 | benchmarks.md | ~~topics.md~~ |
| 排期计划 | calendar.md | ~~topics.md~~ |
