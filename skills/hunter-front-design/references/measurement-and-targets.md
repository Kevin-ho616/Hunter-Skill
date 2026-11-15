# 参考测量、校准与项目参数

在参考研究阶段使用；原创无参考项目可跳过像素测量，在真实控制字阶段建立目标。先看骨架和关键结构，再用度量约束候选。实测值、设计目标和用户确认分别记录。

## 测量入口

使用项目已有的隔离 Python 环境。字体测量需要 fontTools；图片与像素校准另需 Pillow。以下 `SKILL` 表示当前 skill 的绝对目录，`PYTHON` 表示该环境解释器；示例路径替换为项目路径。所有输出使用新路径，保留旧版证据。

```bash
"$PYTHON" "$SKILL/scripts/measure_reference.py" font "/project/reference.ttf" --out "/project/audit/reference-font.json"
"$PYTHON" "$SKILL/scripts/measure_reference.py" calibrate "/project/known.ttf" --px 240 --out "/project/audit/calibration.json"
"$PYTHON" "$SKILL/scripts/measure_reference.py" image "/project/reference.png" --text "Hnxo" --calibration "/project/audit/calibration.json" --out "/project/audit/reference-image.json"
```

- 字体读真实轮廓：H 顶部相对基线为大写高度，x 顶部为 x-height；`n_stem` 是 n 中部左侧截面，`o_side/o_thin` 是 o 中部的水平／垂直截面；曲线每段取 64 个采样点，字面框另用精确 BoundsPen。上下伸部只统计实际存在的指定字母。
- 长度统一为**大写高度归一到 700**，只是比较单位，不要求设计 cap-height=700。`contrast` 为 o 的薄截面／侧截面比值。截面不是全字最小笔宽，斜笔和特殊结构仍需专门法线审校。
- 图片只支持清晰、高反差、单行、字母可分离的字样。提供真实文字，不做 OCR 猜字；字符数量与分组不符时停止。连接字、复杂背景、极小图、严重压缩和多行图先换合适局部或另做人工测量。
- 灰度截面会忽略累计覆盖不足半像素的孤立噪点；亚像素细线需更大参考图，不能据此声称极细笔画不存在。
- 默认需要图中真实 H/x/n。没有 H 时大写归一长度为 unknown；确有依据才用 `--cap-char A --xheight-chars r --stem-chars rd` 等代理，并保留 low 置信度。没有的字不补画来凑测量。原图的 em、边距、占位宽和字偶值不能从普通 Logo 字样中恢复。
- 校准使用已知字体的 HnxodnH，4 倍灰度栅格化后缩回，比较像素读数和轮廓读数，并保存样图及逐项误差。按参考的可见大写像素高度调整 `--px`；参考与校准大写高度相差超过约 20–25% 会提示重做。它只证明该字体、渲染器和尺寸下的读数误差，不是任意截图的准确率。
- 报告保留路径、SHA-256、测量方法、置信度和 unknown。可变字体只测默认实例；轴端、插值和其他文字另验。图片代理值不能自动提升为高置信度。

## 同一份项目参数

复制 [参数示例](../assets/font-targets.example.json) 到项目作为 `font-targets.json`。示例的 ASCII 范围不是默认承诺，按本次委托修改。设计规则表继续记录造型意图、来源、确认状态和光学理由；JSON 供工具读取已明确的可计算部分。

| 字段 | 含义与单位 |
| --- | --- |
| `coverage.ranges` / `characters` | `U+0020-007E` 等范围与补充字符，合并去重；不允许代理区码点 |
| `expect.family` / `style` | 可选的内部名称目标；不同样式需要各自目标时分别运行 |
| `metrics` | 可选 cap/xh/asc/desc/n_stem/o_side/o_thin/contrast；每项为 `{"value": 目标, "tolerance": 非负容差}`，单位同上 |
| `reference_measurements` | 相对 JSON 所在目录的测量报告路径；技术册展示来源与置信度，不自动采用为目标 |
| `shaping.samples` | 实际塑形短语，可换行；缺字应失败 |
| `shaping.pairs` | 两个字符的字偶探针，先完成边距再看字偶 |
| `shaping.minimum_gap` | 可选的水平截面最小间隙，**em 归一到 1000**；null 只记录，不判阈值 |
| `shaping.exceptions` | 字偶到光学例外理由的映射；例外记录为 INFO，不冒充阈值通过 |
| `shaping.features` | 如 `{"tag":"kern","text":"AV","must_change":true}`，检查存在和开关后的真实效果；仅查存在时可设 false |

目标或容差来自已选方案、真实控制字和目标尺寸下的审校，不为过测试临时放宽。绘制程序读取其中适用的已确认参数；改字体、目标或测量依据后，重做受影响报告、试排和册页。脚本不替你决定造型，也不回写字体。

## 可选的开源骨架路线

仅在用户选择衍生或混合路线时比较底字。先筛骨架、比例、关键字形和字族气质，再用同尺度真实字样与测量筛候选；数值接近不能弥补 A、r、g 等结构不同。

从本地或可信官方来源核对许可证、保留字体名、修改与分发条件、覆盖、可用轴及目标样式。记录采用版本、来源与哈希，展示少量可比较候选供已有授权范围内决策。许可未明确的字体不作为可交付底字。测量工具不查询字体目录，不依赖外部 skill 或云端字体服务。

保留继承字形与新绘部分的来源区别；用户授权还原优先时可补绘特殊结构并按原流程推导全套。不要将“全部轮廓只能来自底字”、固定双字重、固定拉伸幅度或某种许可证写成原创设计的通用限制。
