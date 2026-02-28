# 上下文记忆库

本文件夹用于保存优质的上下文记忆，帮助 AI 在后续创作中复用高质量的素材、观点和经验。

## 文件夹结构

```
memory/
├── README.md              # 本说明文件
├── golden-sentences.md    # 金句库：收集每次创作中产生的优质金句（含风格标签和句式模式）
├── viewpoints.md          # 观点与立场库：用户核心观点、价值判断、立场倾向
├── titles.md              # 标题自学习库：标题效果档案、高效模式、偏好画像
├── topics.md              # 选题库：CSV 格式管理，按赛道分类，含爆款潜力评分
├── performance.md         # 数据复盘：文章发布效果追踪、高效写作模式、效果基准线
├── benchmarks.md          # 对标账号：竞品档案、爆款规律、差异化分析
├── calendar.md            # 内容日历：发布排期、节假日规划、内容搭配
├── feedback.md            # 反馈记录：用户对文章的修改意见和偏好
├── materials.md           # 素材库：案例、数据、故事等可复用素材
├── materials.csv          # 素材库导出：用于表格查看、外部系统导入
├── golden-sentences.csv   # 金句库导出：用于表格查看、外部系统导入
├── titles.csv             # 标题库导出：用于表格查看、外部系统导入
└── audience.md            # 读者画像：目标读者的特征和偏好
```

## 使用规范

### 写入规则
1. 每次完成一篇文章后，自动提取以下内容写入记忆库：
   - 产生的优质金句 → `golden-sentences.md`（含风格标签和句式类型）
   - 标题选择和效果 → `titles.md`
   - 选题信息和效果 → `topics.md`（CSV 格式，按赛道分类）
   - 用户的修改反馈 → `feedback.md`
   - 使用的案例素材 → `materials.md`

2. 用户提供文章时，自动提取：
   - 核心观点和用户立场 → `viewpoints.md`
   - 文章中的金句 → 自创金句存 `golden-sentences.md`，外部金句存 `materials.md`
   - 用户风格特征 → `feedback.md` + `self-evolution.md` 习惯档案

3. 对话过程中持续捕捉：
   - 用户表达的观点和态度 → `viewpoints.md`
   - 用户的风格偏好信号 → `feedback.md`

4. 发布后效果数据写入：
   - 文章效果数据 → `performance.md`（阅读量、分享率、涨粉等）
   - 对标账号分析 → `benchmarks.md`
   - 排期更新 → `calendar.md`

5. 写入格式：
   - **materials.md**：使用素材卡片格式（`[M-XXX] 摘要 + 来源/赛道/标签` 字段），详见 materials.md 使用说明
   - **viewpoints.md**：使用观点卡片格式（`[V-XXX] 观点 + 来源/话题/立场强度`），详见 viewpoints.md 使用说明
   - **golden-sentences.md**：使用金句卡片格式（`[G-XXX] 金句 + 风格/句式/话题`），详见 golden-sentences.md 使用说明
   - **其他文件**：使用日期+标题格式：
   ```
   ## [日期] [文章标题]
   - 内容条目
   - 来源/备注
   ```

6. 素材导出（CSV）：
   - 执行：`python scripts/export_materials_csv.py`
   - 默认输入：`memory/materials.md`
   - 默认输出：`memory/materials.csv`
   - 可选参数：`-i` 指定输入文件，`-o` 指定输出文件

7. 金句/标题导出（CSV）：
   - 金句：`python scripts/export_golden_sentences_csv.py` → `memory/golden-sentences.csv`
   - 标题：`python scripts/export_titles_csv.py` → `memory/titles.csv`
   - 两个脚本都支持 `-i/-o` 参数自定义输入输出

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
   - viewpoints.md（用户立场和观点倾向）
   - performance.md（效果数据指导策略）
   - titles.md（标题偏好和高效模式）
   - topics.md（选题库，避免重复选题）
   - calendar.md（排期，确认当前任务）
   - benchmarks.md（对标情报）
   - audience.md（读者画像）
   - golden-sentences.md（金句复用，含风格匹配）
   - materials.md（素材复用）

3. 自学习联动：
   - 金句生成前，先读取 `materials.md` 的「金句观点/类比比喻」分区提炼表达模式
   - 标题生成前，先读取 `materials.md` 的「标题技巧」分区提炼句式
   - **标题/摘要生成后，全部候选自动存入 `titles.md` 的「AI 生成备选库」对应风格分区**
   - 仅学习质量分 `>=4` 素材，不直接复制原文

### 维护规则

#### 容量限制
| 文件 | 上限 | 淘汰规则 |
|------|------|---------|
| golden-sentences.md | 100 条 | 删除使用次数最少的、超过 6 个月未使用的 |
| viewpoints.md | 150 条 | 「不确定」立场超 3 个月未确认的移入待确认区 |
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
- 每月初 → 执行 materials.md 的「月度健康检查模板」
- 每季度 → 检查 benchmarks.md，标记不活跃账号
- 金句库满 100 条时 → 触发淘汰，保留效果最好的 80 条

## 文件职责边界

> 避免数据重复存储，每类数据只存一个地方。

| 数据类型 | 存储位置 | 不要存到 |
|---------|---------|---------|
| 自创金句（创作中产出的） | golden-sentences.md | ~~materials.md~~ |
| 外部金句/观点（对标文章提取的） | materials.md 第三节 | ~~golden-sentences.md~~ |
| 用户核心观点和立场 | viewpoints.md | ~~feedback.md~~ ~~materials.md~~ |
| 案例/数据/结构/标题技巧/类比 | materials.md（按分类） | ~~golden-sentences.md~~ |
| 标题效果数据 | titles.md | ~~performance.md~~ |
| 文章整体效果数据 | performance.md | ~~feedback.md~~ |
| 用户修改偏好 | feedback.md | ~~performance.md~~ |
| 选题信息 | topics.md | ~~performance.md~~ |
| 对标账号信息 | benchmarks.md | ~~topics.md~~ |
| 排期计划 | calendar.md | ~~topics.md~~ |
