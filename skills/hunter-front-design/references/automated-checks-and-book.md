# 通用验收与自动技术字样册

工程验收、交互试排和技术册共同引用当前真实字体及项目参数。它们在控制字阶段可做阶段校样，在成稿阶段形成同版本证据；发现问题回到设计或构建源修正。完整光学审校仍按 design-review.md 执行。

## 环境与证据

使用项目已有隔离环境：fontTools 为基础；声明塑形或容器塑形比较时需要 uharfbuzz，WOFF2 需要 brotli；图片测量需要 Pillow。导出 PDF 另需现有 Playwright 和可用 Chromium／Chrome。先核对已安装工具，不为几行脚本全局安装依赖。`SKILL`、`PYTHON` 与 `NODE_ROOT` 均为任务变量；最后一个指含 `node_modules/playwright` 的现有目录。

每次使用新的报告文件和册目录；字体源与旧证据不覆盖。测量、报告、试排和字样册都保留实际文件哈希。字体或 targets 字节变化必须重新验收，不能把旧报告放进新册页。

修改工具后用 `"$PYTHON" "$SKILL/scripts/test_font_tools.py"` 跑最小回归；它生成隔离的 TTF/CFF 测试字体，检查测量、异常数据、容器差异、陈旧报告和册页字节，不修改项目字体。浏览器导出另跑下述真实案例。

## 通用工程检查

```bash
"$PYTHON" "$SKILL/scripts/check_font.py" "/project/fonts/Family-Regular.ttf" "/project/webfonts/Family-Regular.woff2" --targets "/project/font-targets.json" --container-pair "/project/fonts/Family-Regular.ttf" "/project/webfonts/Family-Regular.woff2" --out "/project/audit/check-v001.json"
```

实际检查：解析与容器、表编译回读、声明码点覆盖及意外空白、轮廓与字宽数值、Windows 垂直度量是否容纳字面、PostScript 名称、可选的家族／样式、目标度量与容差、HarfBuzz 真实塑形无 .notdef、指定功能开关与字偶截面。长度目标按 cap=700；间隙按 em=1000，不混用。

项目明确要求标点上缘不超过大写线时，在 `font-targets.json` 顶层加入 `"punctuation_height": {"max_above_cap": 0, "extra_characters": "ªº¹²³¼½¾"}`；额外字符按实际字集填写，且须已列入 coverage。脚本逐份检查真实字体：以 H 轮廓上缘为大写基准，测声明覆盖中的 Unicode P/S 类及额外字符上缘，输出 `punctuation upper bounds` 的 PASS/FAIL、逐字测量与超限清单。`max_above_cap` 按 em=1000 计，0 为不许超高；仅忽略 1e-6 字体单位的浮点噪声。缺少真实 H 或可见目标字符时为 SKIP/incomplete，不以元数据或图片裁切代替。只比较上缘，保留逗号等下伸部；组合附标、带附标字母默认不纳入。没有此约束时省略该字段，不能把当前项目规则强制到所有字体。

`--container-pair` 仅用于同轮廓类型的完整网页包装：按 glyph ID 比较 cmap、真实轮廓、字宽及声明样本的塑形；允许 post 表不保留字形名。子集化、改 UPM、重排字形、TTF↔CFF 转换不属于这个相等判断，需要各自的转换／覆盖审校。字偶间隙每 4/1000 em 取水平截面，是有限采样，不证明任意方向无碰撞或光学字距良好。

状态以证据为准：

- PASS：该项在声明范围内通过。
- FAIL：有缺字、结构、阈值或容器不一致等错误，修源后重跑。
- INFO：实际测量、未设阈值或有理由的例外，不冒充检查通过。
- SKIP：工具未做的检查。缺 HarfBuzz 或必需字形导致已声明工程项未测时，总状态 incomplete；脚本退出码 pass=0、fail=1、incomplete=2。视觉和平台检查始终另列 SKIP，不改变工程状态，也不代表它们已完成。

当前工具面向常规静态 glyf/CFF 轮廓字体。可变字体只验默认实例；自交、提示、复杂文字附标位置、插值、彩色字层及完整格式合规另用适用工具。它不替代 FontBakery／OTS 专项检查、人工光学审校、系统安装、Adobe／Office、打印或跨平台检查。不能仅凭这一份工程 pass 宣称正式发行验收完成。

版权与许可另按 [专项封装关卡](copyright-and-license.md) 的 FontTools 写入／回读示例核验，并保存项目检查记录。当前 `check_font.py` 不判断版权方身份、授权合法性或上游许可是否完整保留；其 pass 不能代替这项检查。版权元数据改动后，重新验收当前字体并生成同哈希的试排与字样册。

## 生成技术字样册

```bash
"$PYTHON" "$SKILL/scripts/create_font_book.py" "/project/fonts/Family-Regular.ttf" --targets "/project/font-targets.json" --report "/project/audit/check-v001.json" --out "/project/book-v001"
node "$SKILL/scripts/render_font_book.cjs" "/project/book-v001" --node-root "$NODE_ROOT"
```

第一步复制原始字体，生成离线 `index.html` 与 `book-info.json`；报告可选，未提供就明确标为 not run。提供报告时核对 targets 与每个字体的 SHA-256，拒绝陈旧证据。一本可含多个实际字体，每份单独命名与载入，不通过 CSS 伪粗体凑字重。

内容包括真实字体封面与版本信息、轮廓测量和可选目标／参考置信度、96–12 px 字号阶梯、**声明码点**的分页字符表、字偶开关对照、表内功能与指定样例。未编码替代字形需另加光学样张；不从几枚字符推断整种语言支持。正文标签可用系统字体，示范字样必须用本次字体；缺字明确显示 missing。

第二步只在本机服务字体，核对浏览器收到的字体字节哈希，检查示范文字有无系统字体回退、缺字和越界，输出 `render-report.json` 与 `pages/*.png`。通过后才导出 `fontbook.pdf`；失败不产出 PDF。长标题只等比调字号，字号阶梯仅截短文字并保留标签字号，调整记录写入报告。

HTML 生成成功不等于 PDF 已完成；缺浏览器或依赖时如实交付当前状态。导出后实际看封面、字符表和含功能的代表页，并回读 PDF 页数。自动边框检查不能识别所有墨迹裁切、文字碰撞与审美问题。

技术册与 [交互试排](proof-tool.md) 并行互补：仍交付自由输入、字号、段落、网格和字偶／连字交互，并运行原有浏览器检查。技术册提供静态回读证据，不代替源网格、整套光学审校或用户的设计确认。

## 技术展示与使用场景海报

字体验收后按 [宣传海报流程](promotion-posters.md) 进入独立展示设计阶段。技术册提供字符、比例、测量和字偶素材；技术海报需要有表达重点和版式，使用场景海报需要由当前字体特性推导场景与构图。两类都用当前真实字体排主文字，逐张核对字样、标注、裁切和整组一致性。不要把自动册页直接称作已设计完成的宣传海报。
