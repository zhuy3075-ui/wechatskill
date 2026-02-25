# wechat-writer Skill 使用手册

> 一个面向微信公众号创作的完整技能包，覆盖写作、学习、复盘、素材管理、风格进化与跨平台改写。

## 1. 能力总览

本 skill 提供以下核心能力：

1. 文章创作：干货 / 观点 / 故事 / 清单 / 热点
2. 范文学习：自动识别类型、提取风格、处理风格冲突
3. 风格系统：`--style` 定制表达，支持风格锁定与冲突防污染
4. 风险合规：基于微信规范的必检清单
5. 数据复盘：单篇录入 + 阶段复盘 + 自我优化闭环
6. 素材管理：`M-XXX` 素材主键、分类、标签、质量分、月度健康检查
7. 多平台改写：公众号 -> 小红书 / 知乎 / 短视频
8. 评论区与 SEO：互动运营方案 + 搜一搜关键词布局
9. 风格推荐：创作前列出可用风格 + 基于素材的 Top3 推荐
10. 成果输出：支持 `md/json/both` 三种交付模式
11. 对标学习：默认 20 篇样本，实验组/对照组分组验证策略

## 2. 目录说明

关键文件：

- `SKILL.md`：总控流程、优先级规则、执行级别、验收样例
- `prompt.md`：高频可复制提示词（1-7节）
- `prompts/advanced-reference.md`：低频参考（去 AI 味完整版 + 使用指南）
- `style-guide.md`：通用写作风格规则
- `templates/`：五类文章模板
- `memory/`：记忆库（标题、素材、复盘、对标、排期、反馈等）
- `self-evolution.md`：自我进化与风格防污染机制
- `personality.md` / `soul.md`：人格层与底线层
- `risk-check.md`：风险检测详细规则
- `scripts/style_recommender.py`：风格清单与 Top3 推荐
- `scripts/article_output_formatter.py`：成品输出为 `md/json/both`

## 3. 快速上手

### 3.1 最短路径（推荐）

写作：

1. 输入主题或素材  
2. 确认大纲  
3. 输出正文 + 风险评估

复盘：

1. 提供标题与数据  
2. 输出问题清单  
3. 输出可执行动作 + 回测计划

学习：

1. 提供范文  
2. 输出风格拆解 + 素材提取  
3. 处理风格冲突并决定是否更新人格

### 3.2 常用命令

写作：

- `/wechat-writer 干货 时间管理`
- `/wechat-writer 观点 AI对教育的影响 --style 犀利派`
- `/wechat-writer 风格参考`
- `/wechat-writer 风格推荐 AI教育素材`
- `/wechat-writer 输出格式 both`

学习：

- `/wechat-writer 学习这篇文章`
- `/wechat-writer 只学结构`

复盘与优化：

- `/wechat-writer 阶段复盘 最近10篇`
- `/wechat-writer 自我优化复盘 最近10篇`
- `/wechat-writer 导出优化方案`

素材管理：

- 使用 `prompt.md` 的 `7.15 素材库管理提示词`

## 4. 执行规则（必须知道）

### 4.1 `MUST / SHOULD / MAY`

- `MUST`：必须执行
- `SHOULD`：建议执行，条件不足可降级
- `MAY`：可选执行

以 `SKILL.md` 标注为准。

### 4.2 `--style` 合并优先级

优先级从高到低：

1. `soul.md`（底线红线）
2. `styles/[name].md`（语气/结构/文风/金句）
3. `personality.md`（未覆盖维度）
4. `style-guide.md + templates/ + formatting.md`（兜底）

关键原则：`--style` 改变“怎么写”，不改变“我是谁”。

### 4.3 冲突与回退

若信息不足或规则冲突，使用 `SKILL.md` 中的“失败回退模板”，先交付最小可用成果，再引导补齐信息。

## 5. 素材系统

### 5.1 素材主键

- 每条素材使用 `M-XXX` 编号
- 新增时取当前最大编号 +1
- 删除后编号不回收

### 5.2 素材字段

每条素材至少包含：

- 素材ID（`M-XXX`）
- 内容摘要
- 来源
- 赛道
- 适用类型
- 标签
- 质量分（1-5）
- 添加日期
- 使用记录

### 5.3 素材与金句分工

- 自创金句 -> `memory/golden-sentences.md`
- 外部提取素材（含外部金句/观点）-> `memory/materials.md`

### 5.4 导出 CSV（便于表格查看/复用）

可把 `memory/materials.md` 一键导出为 CSV：

```bash
python scripts/export_materials_csv.py
```

自定义输入/输出路径：

```bash
python scripts/export_materials_csv.py -i memory/materials.md -o memory/materials.csv
```

导出字段包括：`id, category, summary, source, track, use_type, tags, quality, added_date, used_in`。

金句库导出：

```bash
python scripts/export_golden_sentences_csv.py
```

标题库导出：

```bash
python scripts/export_titles_csv.py
```

默认输出文件：
- `memory/materials.csv`
- `memory/golden-sentences.csv`
- `memory/titles.csv`

### 5.5 金句/标题从素材库自学习

- 金句：写作前自动读取 `materials.md` 的「金句观点 + 类比比喻」分区，学习表达模式后生成原创金句
- 标题：写作前自动读取 `materials.md` 的「标题技巧」分区，学习句式后生成标题候选
- 约束：只学习质量分 `>=4` 且来源清晰的素材；不允许原句照抄；必要时记录 `M-XXX` 来源ID

### 5.6 原创度与去 AI 味自动量化

新增质检脚本：

```bash
python scripts/originality_quality_gate.py -a article.md -s source1.md source2.md --min-originality 70 --max-ai-tone 30 --min-humanity 60 --strict-source-trace
```

说明：
- `originality_score`：原创度分数（要求 >=70）
- `ai_tone_score`：AI 味分数（要求 <=30）
- `humanity_score`：人味分数（要求 >=60）
- `source_trace_hits`：来源痕迹命中（要求 =0）
- 不达标时按规则重写并复检，最多 3 轮
- 默认不整篇重生成：优先原稿定向修复，按未达标项逐轮处理（更省 token）

AI 写作特征清单见：`ai-writing-signatures.md`

### 5.7 风格参考与推荐

列出当前可用风格：

```bash
python scripts/style_recommender.py --list-only
```

按主题/素材推荐 Top3 风格：

```bash
python scripts/style_recommender.py --content "AI教育带来的机会和焦虑" --article-type 观点 --top-k 3
```

规则：
- 若用户未指定 `--style`，先给“可用风格清单 + 推荐风格”
- 若用户已指定 `--style`，以用户指定为准

### 5.8 成果输出模式

支持三种输出模式：
- `md`：默认，适合直接发布公众号
- `json`：结构化成果，适合系统入库/复盘
- `both`：同时输出 `md + json`

格式化命令：

```bash
python scripts/article_output_formatter.py -i article.md --mode both --style 犀利派 --article-type 观点 --originality 78 --ai-tone 22 --humanity 65
```

默认输出目录：`outputs/`

## 6. 质量保障链路

每篇文章默认经过：

1. 风险检测（合规）
2. 自检优化（结构、钩子、金句、排版、文风一致性）
3. 标准输出格式（标题/正文/摘要/标签/封面建议/风险评估）

复盘任务默认输出：

1. 核心结论
2. 问题清单
3. 优化动作
4. 可复制提示词
5. 指标目标
6. 回测计划

## 7. 跨 AI 使用方式

如果平台不支持 `/wechat-writer` 命令，使用自然语言等价调用：

- “写一篇[类型]公众号文章，主题是[主题]，风格用[风格名]”
- “学习这篇范文，只学结构”
- “基于最近10篇做自我优化复盘，输出可复制提示词”

高频提示词在 `prompt.md`，低频参考在 `prompts/advanced-reference.md`。

## 8. 维护与巡检

### 8.1 每次规则改动后回归

按 `SKILL.md` 的 5 个标准验收样例回归检查：

1. 写作
2. 学习
3. 复盘
4. 改写
5. 素材检索

### 8.2 月度巡检

执行 `memory/materials.md` 的月度健康检查模板，重点看：

- 素材总量
- 冷素材占比
- 高频素材占比
- 平均质量分
- 重复率

## 9. 常见问题

1. 风格不稳定怎么办？  
答：使用“锁定风格”或“锁定指定维度”，并通过冲突检测避免人格被污染。

2. 为什么同一主题写法差异大？  
答：检查是否使用 `--style`，以及 style 是否覆盖了结构/语气规则。

3. 素材太多找不到？  
答：使用 `7.15` 按赛道 + 类型 + 标签 + 质量分筛选。

4. 复盘有结论但不好执行？  
答：使用“导出优化方案”，要求输出可复制提示词和回测计划。

## 10. 当前状态

- 根目录完整手册：已配置（本文件）
- 规则变更记录：见 `SKILL.md` 的“规则变更日志”
- 主流程：稳定
- 素材系统：已主键化（`M-XXX`）
