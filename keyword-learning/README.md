# Keyword Learning Skill

通过“快速定向 -> 宽关键词全景 -> 厚到薄压缩 -> 深度概念卡 -> 支架渐隐练习 -> 迁移测试”系统进入陌生领域。Skill 先给领域故事、骨架和贯穿案例，再按领域镜头建立窄概念 25-50 词或宽领域 60-120 词的知识版图，必要时扩到 80-150 词。

## 包含内容

```text
keyword-learning/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── scripts/
    └── init_learning_workspace.py
```

- `SKILL.md`：完整学习方法与执行规则。
- `agents/openai.yaml`：Codex UI 名称、说明、默认提示词和调用策略。
- `scripts/init_learning_workspace.py`：生成可持续更新的 Markdown 学习工作区。

## 安装

将整个 `keyword-learning` 文件夹复制到 Codex Skills 目录：

```text
~/.codex/skills/keyword-learning/
```

重新加载 Codex 后，可以显式使用 `$keyword-learning`；配置也允许 Codex 在相关学习请求中自动选择本 Skill。

## 使用示例

```text
用 $keyword-learning 带我入门量子计算，我的目标是能看懂大众科普文章。
```

也可以直接提出：

- 给我建立【领域】的关键词地图。
- 建立【领域】的 60-120 个关键词全景，再找出最重要的基石词和阈限词。
- 梳理【概念 A】和【概念 B】的区别与关系。
- 根据我已经知道的概念，发现尚未意识到的知识盲区。
- 用闭卷解释、反例和迁移测试检查我是否真正理解了【概念】。

## 初始化长期学习工作区

脚本仅使用 Python 标准库，不需要安装依赖：

```bash
python3 scripts/init_learning_workspace.py "AI Agent" \
  --goal "能够设计和评估 Agent 产品" \
  --depth L3 \
  --output ai-agent-learning.md
```

可选深度：

- `L1`：认知；
- `L2`：理解；
- `L3`：应用；
- `L4`：专业。

脚本不会覆盖已有文件。如果需要换一份工作区，请指定新的 `--output` 路径。

## 自检

```bash
python3 scripts/init_learning_workspace.py --self-test
```

输出 `self-test passed` 即表示模板生成逻辑正常。

## 工作方式

1. 从真实终点任务倒推 Learning Contract，并诊断或推断现有基础。
2. 用领域故事、5-9 个骨架节点和贯穿案例快速定向。
3. 选择 Domain Lens，建立 Keyword Atlas 并做 Coverage Audit。
4. 筛选基石词、阈限词和隐藏先修，再把厚地图压成可带走的主线。
5. 每轮深入 3-5 个关键词，解释到因果、预测、边界、证据、失败和应用。
6. 用完整示范、补全、独立题、变式题和真实任务逐步撤掉支架。
7. 根据错误根因纠正并换题复测，更新掌握状态、未知队列、复习队列和 Parking Lot。

完成标准不是“收集了多少词”，而是能否解释核心概念、理解关键关系，并完成最初设定的目标。
