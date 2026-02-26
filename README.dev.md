# wechat-writer（开发维护版）

## 1. 目标与范围

本仓库用于微信公众号写作 skill 的开发维护，包含：

1. 主流程规则（写作/学习/复盘/回写）
2. 风格与人格系统（`soul.md` + `personality.md` + `styles/`）
3. 素材与数据闭环（`memory/`）
4. 自动化脚本（`scripts/`）

## 2. 架构与职责

- `SKILL.md`：执行流程与裁决优先级（唯一流程来源）
- `prompt.md`：可复制提示词模板（不定义总流程）
- `style-guide.md`：风格/用词/标点规范
- `risk-check.md`：发布前合规标准
- `self-evolution.md`：进化、防污染、锁定策略
- `templates/`：五类文章结构模板
- `styles/`：学习生成的作者风格
- `memory/`：素材、标题、金句、表现数据、对标账号、排期

## 3. 主流程（开发视角）

1. 唤醒人格：加载 `soul.md`、`personality.md`、`memory/feedback.md`
2. 参数推断：最小追问，缺失时走回退模板
3. 输出大纲：标题候选 + 结构 + 结尾策略
4. 生文：模板 + 风格规则 + 素材匹配
5. 风险检查：10 项必检 + 风险评级
6. 质量闸门：原创度/AI味/人味 + 结构波动指标
7. 成果交付：`md/json/both/wechat` + 交付回执
8. 自动回写：素材、金句、标题、表现、进化记录

## 4. 规则优先级

`--style` 模式下合并顺序：

1. `soul.md`（最高，不可突破）
2. `styles/[name].md`（语气/结构/文风/金句）
3. `personality.md`（未覆盖维度）
4. `style-guide.md + templates/ + formatting.md`（兜底）

说明：风格只改“怎么写”，不改“我是谁”。
补充：偏好分层为“全局偏好 > 风格偏好”，风格间偏好互不继承。

## 5. 学习与防污染

1. 范文学习必须提供作者名/账号名
2. 风格档案固定写入：`styles/[作者名].md`
3. 冲突检测通过才允许人格微调
4. 可启用风格锁定，冻结全部或单维度

## 6. 质量闸门参数

默认阈值：

- `originality_score >= 70`
- `ai_tone_score <= 30`
- `humanity_score >= 60`
- `source_trace_hits = 0`
- `template_sentence_ratio <= 0.12`
- `sentence_cv >= 0.35`
- `paragraph_cv >= 0.45`

修复策略：

1. 默认定向修复（只改问题段落）
2. 仅高风险条件整篇重写
3. 最多 3 轮复检

## 7. 脚本说明

### 7.1 风格推荐

```bash
python scripts/style_recommender.py --list-only
python scripts/style_recommender.py --content "AI教育带来的机会和焦虑" --article-type 观点 --top-k 3
```

### 7.2 质量闸门

```bash
python scripts/originality_quality_gate.py -a article.md -s source1.md source2.md --min-originality 70 --max-ai-tone 30 --min-humanity 60 --strict-source-trace
```

### 7.3 成果格式化

```bash
python scripts/article_output_formatter.py -i article.md --mode wechat --style 理性派 --article-type 观点 --originality 78 --ai-tone 22 --humanity 65
```

### 7.4 素材导出

```bash
python scripts/export_materials_csv.py
python scripts/export_golden_sentences_csv.py
python scripts/export_titles_csv.py
```

### 7.5 中文路径清单

```bash
python scripts/path_manifest.py --dir "C:\\你的目录" --pattern "*.txt"
```

## 8. 分发与发布规范

发布前检查：

1. 删除本地私有数据：`.claude/`
2. 删除测试输出：`output_draft.md`、`outputs_test/`
3. 检查 `styles/` 是否包含个人投喂风格
4. 检查 `personality.md` 是否为可公开状态
5. 运行回归样例（写作/学习/复盘/改写/素材检索）

## 9. 建议提交流程

1. 仅暂存目标文件：`git add <files>`
2. 本地自检：脚本可编译、关键命令可运行
3. 中文 commit message 说明改动范围
4. `git push` 前确认无私有残留文件
