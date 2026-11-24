#!/usr/bin/env python3
"""Create a Markdown workspace for a keyword-learning session."""

from __future__ import annotations

import argparse
from pathlib import Path


DEPTHS = {
    "L1": "认知",
    "L2": "理解",
    "L3": "应用",
    "L4": "专业",
}


def render_workspace(topic: str, goal: str, depth: str) -> str:
    return f"""# 关键词学习：{topic}

## Learning Brief

- 学习主题：{topic}
- 学习目标：{goal}
- 学习深度：{depth}｜{DEPTHS[depth]}
- 焦点问题：
- 学习者基础：
- 使用场景：
- 可用时间或篇幅：
- 终点任务及成功标准：
- 关键假设：
- 全景规模：窄概念 25-50 个词；宽领域 60-120 个词，必要时 80-150 个｜8-16 个主题簇
- 当前轮次：Round 0｜快速定向

## Entry Diagnostic

- 一句话定义与信心：
- 一条因果链与信心：
- 一个边界例判断与信心：
- 初始掌握状态：U0 / U1 / U2 / U3 / U4
- 诊断如何改变本轮路线：

## Thin Orientation

- 领域故事（现实问题 -> 核心对象 -> 关键机制 -> 结果/价值 -> 反馈/约束）：
- 5-9 节点骨架：
- 贯穿案例：
- 三条边界：
- 8-15 个中英双语路标词：
- 当前简化遗漏了什么：

## Domain Lens

- 类型：自然科学 / 工程技术 / 产业商业 / 医疗生命 / 法律政策 / 历史人文 / 社会科学 / 实践技能
- 本领域必须回答的特有问题：

## Keyword Atlas

从核心对象、问题需求、基础原理、构成架构、机制过程、方法策略、工具设施、数据表示、指标单位、分类路线、角色激励、标准治理、生命周期、历史演化、失败争议、场景案例和前沿方向中选择至少 8 个相关维度。窄概念建立 25-50 个词，宽领域建立 60-120 个词，必要时 80-150 个。

### 主题簇

| 主题簇 | 回答的问题 | 规范关键词及英文/缩写 | 关键关系命题 | 初学者常漏点 |
|---|---|---|---|---|
|  |  |  |  |  |

## Coverage Audit

- [ ] 已覆盖机制、指标、角色、边界或历史，而不只有名词。
- [ ] 已检查隐藏前置、反例、失败模式和替代方案。
- [ ] 已检查单一流派、地区、商业立场或时间阶段偏差。
- [ ] 已合并同义词，并拆分一词多义节点。
- [ ] 已覆盖对象/分类、机制/因果、方法/动作、指标/证据、边界/失败、历史/争议六类知识。
- [ ] 至少有一个贯穿案例、失败案例和边界案例。
- [ ] 地图足以支持终点任务；否则已补充程序性或条件性知识。
- [ ] 宽泛、专业或动态主题已用教材/课程、标准/协会、研究/手册、真实案例/复盘交叉校正，或标记待验证缺口。

## Keystone Keywords

| 顺序 | 关键词 | 节点角色 | 为什么现在学 | 先修概念 | 连接的主题簇 | 掌握状态 |
|---:|---|---|---|---|---|---|
| 1 |  |  |  |  |  | U0 陌生 |

## Learning Path

1. 入口：
2. 骨架：
3. 深潜：
4. 应用与输出：

## Thick-to-Thin Compression

- 用 8-15 条关系命题、一个端到端流程或一张判断清单重建领域：
- 每条主线压缩了哪些细节：
- 不能被压缩的边界或例外：

## Deep-Dive Cards

### 关键词

- 节点角色：
- 掌握状态：U0 陌生
- 当前信心：0-100%
- 核心问题：
- 准确定义：
- 直觉模型及其失效处：
- 问题来源：
- 先修概念：
- 运行机制（输入 -> 状态/步骤 -> 输出 -> 反馈）：
- 结构关系与跨簇连接：
- 对比、非例、反例与失败模式：
- 度量与证据：
- 条件变化预测：
- 完整案例：
- 练习阶梯位置：完整示范 / 补全 / 独立 / 变式 / 真实任务
- 迁移问题：
- 我的解释：
- 掌握证据：
- 下一节点：

## Relationship Views

### 依赖视图

使用 `A --[导致/依赖/包含/限制/替代/衡量]--> B：条件或原因` 记录完整命题。

### 第二视图

机制或因果视图。

### 第三视图

决策或证据视图；窄概念可改用分类、流程、对比、角色—激励或历史演化视图。

### 跨主题连接

记录连接不同主题簇的关键关系。

## Unknown Queue

| 优先级 | 关键词 | 节点角色 | 发现原因 | 阻塞的问题 | 下一步动作 |
|---:|---|---|---|---|---|
| 1 |  |  |  |  |  |

## Review Queue

| 关键词 | 当前状态 | 上次掌握证据 | 下次提取方式 |
|---|---|---|---|
|  |  |  |  |

## Parking Lot

| 关键词 | 暂缓原因 | 重新进入条件 |
|---|---|---|
|  |  |  |

## Practice Ladder

1. 完整示范及每一步理由：
2. 学习者补全一个关键步骤：
3. 独立完成同构题：
4. 改变关键条件的变式题：
5. 未演示过的真实任务：
6. 错误类型与最小纠正动作：
7. 换题复测结果：

## Output Tests

- [ ] 主动回忆：不用资料解释核心概念。
- [ ] 通俗教回：用 3-5 句话向外行说明并标出卡点。
- [ ] 关系重建：从空白重画 5-10 个节点及连接语。
- [ ] 条件预测：改变一个变量，先预测结果与信心，再检查证据。
- [ ] 对比或反例：区分易混概念并给出非例。
- [ ] 迁移应用：在一个未讲过的新情境中使用概念。
- [ ] 真实输出：完成目标相关任务。

## Round Log

### Round 0｜快速定向

- 新增节点：
- 修正关系：
- 掌握状态变化：
- 信心与表现偏差：
- 输出测试证据：
- 最大知识空白：
- 下一轮：
"""


def self_test() -> None:
    rendered = render_workspace("测试主题", "测试目标", "L2")
    assert "# 关键词学习：测试主题" in rendered
    assert "学习深度：L2｜理解" in rendered
    assert "## Keyword Atlas" in rendered
    assert "## Entry Diagnostic" in rendered
    assert "## Thin Orientation" in rendered
    assert "## Domain Lens" in rendered
    assert "## Coverage Audit" in rendered
    assert "## Relationship Views" in rendered
    assert "## Thick-to-Thin Compression" in rendered
    assert "## Practice Ladder" in rendered
    assert "## Output Tests" in rendered
    assert "## Review Queue" in rendered
    assert "## Parking Lot" in rendered


def main() -> None:
    parser = argparse.ArgumentParser(
        description="创建关键词学习法的 Markdown 工作区。"
    )
    parser.add_argument("topic", nargs="?", help="学习主题")
    parser.add_argument("--goal", default="快速建立完整的领域认知", help="学习目标")
    parser.add_argument("--depth", choices=DEPTHS, default="L2", help="学习深度")
    parser.add_argument("--output", default="learning.md", help="输出 Markdown 路径")
    parser.add_argument("--self-test", action="store_true", help="运行内置自检")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("self-test passed")
        return

    if not args.topic or not args.topic.strip():
        parser.error("请提供非空的学习主题")

    output = Path(args.output).expanduser()
    if output.exists():
        parser.error(f"目标文件已存在，不会覆盖：{output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_workspace(args.topic.strip(), args.goal.strip(), args.depth),
        encoding="utf-8",
    )
    print(output.resolve())


if __name__ == "__main__":
    main()
