# 专项生产、工具与验证

按[覆盖范围](coverage-and-specialties.md)选择本项目需要的项。这里提供实际构建与验证入口，技术样本不是已获认可的成品字体。完整流程包括设计和人的判断，不以某个工具代替语言、美学或目标平台验收。

## 工具环境与可重复样本

使用独立 Python 3.12 环境，避免改动现有字体项目依赖。在 Skill 根目录执行；所有输出目录使用新路径。

下列整套样本用于维护 Skill 或验证工具环境；普通字体项目只运行适用专项，不必每次下载/构建整套实验室。样本不能改名冒充用户的原创成品。

```bash
python3.12 -m venv /project/font-tools
/project/font-tools/bin/python -m pip install -r requirements-specialties.txt
/project/font-tools/bin/python scripts/fetch_specialty_samples.py /project/font-sources --download
/project/font-tools/bin/python scripts/build_specialty_samples.py /project/font-sources /project/font-lab/samples
/project/font-tools/bin/python scripts/validate_specialty_samples.py /project/font-sources /project/font-lab/samples /project/font-lab/report
```

下载器只取[固定版本登记表](../assets/specialty-sources.json)中的公开字体、许可和元数据，核对 SHA-256 与字节数；已有文件不同则停止，不覆盖。初次需要网络，之后可离线检查。生成器保留各上游 OFL、来源和版本；衍生字体使用新的 Skill Lab 名称。原始二进制转 UFO 是用于测试的轮廓快照，不能冒称取回了原作者的参数源、锚点、字偶或全部特性。

字体工具实际调用 Fontmake/ufo2ft、FontTools、HarfBuzz、PathOps、ttfautohint、OTS、FontBakery、FreeType 与 Verovio。版本锁是复现基线，不是永不更新的规定。升级后重跑本页样本、普通字体回归与失败案例，再更新版本和证据。缺失工具或原生依赖时报告失败/待补，不静默跳过必需项。网络、CPU 和磁盘不足先缩小技术测试字符集，不能缩小用户约定的交付字集。

已执行的维护基线见[实测摘要](../assets/specialty-validation-baseline.json)：包含版本/脚本哈希、19 个回归测试、26 个专项 case、36 个可变坐标、9 组 OTS、FontBakery 原始计数和真实 macOS/Word 证据范围。摘要是该次工具验证快照；新项目仍需取得当前字体的证据。

浏览器检查另外需要 Playwright 与本机 Chrome，沿用[现有浏览器工具说明](automated-checks-and-book.md)准备 Node 环境：

```bash
node scripts/check_specialty_browser.cjs /project/font-lab/report
```

它启动仅本机可访问的 HTTP 服务，检查实际下载哈希、字体 MIME、ETag 304、所有声明样本的自定义字体与回退、COLR/emoji/位图真实彩色像素、可变轴像素差异、竖排和 MathML，生成 PNG/PDF 后关闭服务。这只证明该本机服务与 Chrome；上线的 CDN/CORS、缓存更新、其他浏览器仍需在实际环境验收。

运行维护测试：

```bash
/project/font-tools/bin/python scripts/test_font_tools.py
/project/font-tools/bin/python scripts/test_specialties.py
```

项目检查可从[声明计划示例](../assets/specialty-plan.example.json)复制适用 case，替换相对于计划文件的字体/元数据路径和经审阅语料：

```bash
/project/font-tools/bin/python scripts/check_specialties.py /project/specialty-plan.json --out /project/reports/specialties-v001.json
```

支持 shape/family/subset/variable/color/math/mono/smufl 八种工程检查，12 类设计专项按本页组合使用。结果退出码 0=声明工程项通过，1=失败，2=必需依赖缺失未完成；报告保留每项条件、实际结果及输入哈希。不适用项不放入运行计划，但仍在项目规则表说明排除理由。

## 可编辑源、路径与依赖：各类字体共用

1. 确定权威构建源：参数绘制工程、UFO、Designspace、Glyphs 或其他编辑器源。保存构建命令、工具版本、字符清单与设计规则。TTX 只是指定成品的表快照；与原始设计工程分开标识。
2. 用 `scripts/check_source.py source.ufo --out new-source-report.json` 检查 UFO／Designspace／Glyphs：有限数值、开放路径、部件缺失/循环、非可逆变换、母版的点型/顺序与部件结构；输出正向及反向依赖。修改母字时复核所有直接和间接派生字、锚点、字偶组及替代字；参数生成器还应登记代码层依赖，不能只看字体复合字。
3. PathOps 将重叠、自交或方向产生的面积/轮廓变化列为候选，必须结合填充、内腔与造型判断。候选不是自动删节点指令；报告无候选也不证明所有极值或曲率正确。编辑器中复查闭合、顺逆方向、重复节点、微小段、尖点、自交、曲线极值、切向和多余点。保留节点结构的母版在编译阶段统一处理重叠；不能逐母版随意删点破坏兼容。
4. 使用 Fontmake `--validate-ufo --check-compatibility` 实际编译；二次曲线重叠处理使用已验证的 `--overlaps-backend pathops`。不要用改扩展名替代二次/三次曲线转换；同源 TTF 与 CFF OTF 分别检查容器、轮廓误差、方向和塑形。转换有容差时按目标字号检查，不能要求所有控制点逐项相同。
5. 本样本实际完成 Source Serif 轮廓→UFO/Designspace→四成员 TTF/CFF OTF、可变 TTF，以及原创中文 UFO→Glyphs→TTF 回编。测试只覆盖这些输入格式；FontLab、FontForge 等编辑器必须使用其真实导出器，不能声称任意源格式都能无损互转。

## 1. 衬线、强对比、书写与装饰

- 先定义书写工具/角度、主次笔画、衬线是否带括弧、接合、球端/泪滴、悬出和装饰层级；控制字按结构选，例如 H/O/n/o、a/e/g、f/r/s、斜笔与连接组。笔画对比、字腔和小尺寸灰度分开判断，不能套用无衬线的等粗规则。
- 用真实源网格、目标字号、反白和成段文本检查细笔断裂、接头过黑、衬线碰撞、装饰遮挡、书写连接及字距。书写体的必要连接由上下文替换/定位实现，不靠随意负 tracking 掩盖断连。
- 样本：重建衬线四样式、Dancing Script 实际子集；同页展示衬线/斜体/书写体。工具负责真实编译和塑形，造型是否成立仍逐字审查。没有把样本变成所有风格的通用自动造字器。

## 2. 多字重、多字宽与斜体家族

- 先定家族矩阵、共同参数与各成员必要差异。斜体明确是真斜体还是倾斜体，检查 a/g/f 的造型路线、角度、回钩、端头、悬出、重音及字距，不能仅做剪切变换就结束。
- 在母版和关键中间态核对点数/点型/起点/顺序、轮廓方向、部件、锚点、字偶组与 feature 兼容；用实际编译发现仅拓扑表面相同仍不能插值的问题。重量/宽度变化要保持可识别的内白和视觉梯度，不能用统一加粗/压缩替代设计。
- `check_specialties.py` 的 `family` 检查声明的权重、斜体位、角度、家族/样式和 PostScript 名、各成员编码范围。R/B/I/BI 的旧式分组、name 1/2/16/17、OS/2、head 与应用粗斜按钮还需按[命名流程](bilingual-naming.md)逐项核对。扩展家族不要强塞进一个四成员组。
- 样本实际编译四样式 TTF/CFF OTF 和直立/斜体可变 TTF；多字宽轴使用 Noto Mono 真实 wdth/wght 检查。共享行距以项目约定为准，不能机械要求所有家族度量完全相等。

## 3. 正文、小字、屏显与 hinting

- 用目标语言的实际段落、字号/行长/行距、阅读距离、缩放与屏幕倍率检查灰度、开口、易混字符、标点、多行重音和下伸部。测试低一档字号和反白；光学尺寸根据造型另定，不把字重或 CSS 字号当成 opsz。
- TrueType 示例：`python -m ttfautohint unhinted.ttf hinted.ttf`。回读 fpgm/prep/cvt 与字形指令，核对 hinting 前后轮廓、编码、度量、字偶和附标；在 8/10/12/14/16/24 ppem 用 FreeType/目标系统比较实际像素。保留处理前源，不能反复给已提示字体叠加自动提示。
- CFF 使用对应的 PostScript hinting 流程；ttfautohint 不能用于 CFF。手工 hinting、复杂光学尺寸设计或特殊渲染器需在实际编辑器中完成。hinting 不修复骨架、轮廓或错误字距。
- 样本实际运行 ttfautohint，确认生成指令且布局不变；Source Serif 的 opsz 多轴实例与 Chrome 小字阶梯另测。FreeType 栅格和本机 Chrome 不能代替 Windows ClearType、手机屏幕与人的阅读判断。
- `render_small_text.py before.ttf after.ttf new-pixels.png` 生成实际 FreeType 8/10/12/14/16/24 ppem 对照和像素哈希；当前脚本限 LTR 灰度轮廓字。hinting 后检查 head.flags 的整数 ppem 位并通过所选 profile；不用仅增加该标志冒充已生成指令。

## 4. 多语言、地区造型与附标

- 每种语言列出码点、真实词句、数字/标点及本地造型。Latin、Greek、Cyrillic 不按“长得像”套同一笔画；土耳其点、塞尔维亚/保加利亚西里尔、越南文多附标等按实际声明覆盖。
- 使用 `FontData.shape_run(text, language=..., script=..., direction=..., features=..., variations=...)`。报告含实际条件、Unicode 码点索引簇、GID、advance/offset；已有 `shape()` 调用保持兼容。无 `.notdef` 只是必要条件。
- `shape` 用例可指定 `expected_gids`、`zero_advance_mark`、特性开关对照及 NFC/NFD 等价。检查 locl、ccmp、mark/mkmk、大小写、附标堆叠与斜体相位，保留专业语言审阅和例外。
- 样本验证塞尔维亚/俄语 locl、ö 的 NFC/NFD 和叠加附标。其他语言必须新增自己的语料与条件；样本未覆盖的语言不能从 cmap 推定通过。

## 5. 原创中文与地区字形

扩展中文时使用[中文扩字与风格迁移](cjk-expansion.md)确定字表、部件位置变体、留出批次和单字例外；UFO 部件装配和缺字清单可用 `scripts/assemble_cjk.py`。

- 明确地区与字集依据，分解横竖撇捺点钩折、独体/左右/上下/包围结构；建立笔形、部件、中宫、重心、字面、疏密、避让和空间规则。控制字先覆盖这些结构，再按高频和部件依赖扩字。
- 源部件复用需要结构语义：部件在不同位置可以变形、缩短或减重，不把所有“木/口”机械复制为同一比例。中文等宽占位也需要逐字光学调整。简繁、异体与地区字形分别列码点/locl/语言；语言审校检查错笔、错结构和字义。
- 本样本真正绘制“一十口日田中人大小木林森”，通过布尔合并、共享木部件、UFO/Glyphs 编译和修改木后林/森变化的依赖回归。它是有限原创控制字，不能宣称已生产或审查整套原创汉字；实际整库沿同一流程分组扩展并逐组审校。
- 开源整库改造继续走[中文衍生流程](cjk-derived.md)，明确继承来源，不将改造样本归为逐字原创。

## 6. 竖排与版面

- 核对 vhea/vmtx、需要的 VORG、vert/vrt2 和垂直附标等，使用 HarfBuzz `ttb` 与实际 `writing-mode:vertical-rl`。中文/日文/地区标点各有规则，不以同一演示代表全部文字规范。
- 检查标点括号的位置与方向、直立/旋转、拉丁数字、短横排 text-combine-upright、跨文字基线、行盒和缺字；进一步测试目标应用的行首行尾禁则、标点挤压、断行/两端对齐。字体提供字形/度量，排版引擎负责的规则单独验收。
- 样本 Noto CJK 子集保留垂直度量和替换，验证 vert/vrt2 开关、纵向 advance、WOFF2 子集等价与浏览器竖排。原始 CFF OTF 未被伪装成 TTF。

## 7. 复杂文字

- 阿拉伯按实际连接形、lam-alef、附标和断词上下文检查；印度文字检查音节簇、重排、半形/合字和 matra；泰文检查基字、上/下标、音调和 sara am。其他脚本按其规则新增语料，不逐码点加字距破坏字素簇。
- 每个用例记录 language/script/direction/features、引擎/版本、簇和定位，必要时与目标引擎及经审阅 GID/图样比较。自动单调簇/无缺字不等于语言正确；双向混排、断行与编辑光标由目标应用另测。
- 样本为真实 Noto Arabic/Devanagari/Thai，检查原字体与子集的 GID 重排后轮廓/位置等价，并在 Chrome 确认实际自定义字体、无意外回退。保留语言专家确认门槛。

## 8. 可变字体

- 定义轴语义、范围、默认值、映射与命名实例；检查 fvar、avar（使用时）、STAT、度量/锚点/字偶的变化。多母版先做兼容检查，不能只检查默认导出。
- `variable` 用例在最小/最大/默认/中点的组合中实际实例化静态字库，核对 HarfBuzz 的 GID/位置（允许一单位舍入）、全部字形有限边界与 advance、代表轮廓确有变化。超过三轴或有特殊映射时显式提供关键 locations，包含映射转折及重要组合。
- 检查所有轴端和中间态的内腔堵塞、笔画反转/尖点、碰撞、极端字距，实际滑动轴并测试命名实例。有限坐标采样不能证明无限轴空间，发现异常要追加附近轨迹。
- 样本包括真正从 Designspace 编译的直立/斜体 wght 字体，以及 Source Serif opsz/wght、Noto Mono wdth/wght；浏览器还检查实际不同重量像素，不用只改 CSS 数字充当轴生效。

## 9. 彩色、emoji 与位图

- 根据目标客户端选 COLR v0/v1、SVG、CBDT/CBLC 或 sbix；不默认每项目输出所有格式。检查调色板/图层/paint 图、透明、裁切、缩放、浅深背景与普通轮廓回退，位图另检查 strike 尺寸、原点及失配 ppem。
- emoji 按序列检查 VS15/VS16、ZWJ、肤色等本项目声明范围；码点齐全仍可能序列错误。测试相关序列最终 glyph 数与真实颜色。没有生产的格式不写成已验证。
- `color` 回读必需表并编译，配合 OTS 和浏览器 Canvas 实际彩色像素。样本包含真正导出的 COLR v0/v1、从轮廓栅格化的 16/32 ppem sbix、Noto COLRv1 emoji 的 😀／👩‍💻／❤️；emoji 子集去掉 SVG 备选表，以确认测试的是 COLR 路径。
- 不把 COLR/sbix 的成功推定为 SVG 或 CBDT 的生产验收；这些格式按当前规范增加对应样本。位图放大可能像素化属于格式选择，需要在项目目标尺寸确认。

## 10. 等宽、代码、图标与专业符号

- 等宽任务逐一核对承诺占位，区分可见 ASCII 的一格宽、组合附标零宽、宽字符/emoji 的编辑器单元规则；检查 0/O、1/l/I、括号、标点和代码连字、光标/选择/对齐。不能对所有 Unicode 强制同 advance。
- `mono` 用例检查声明字符的固定宽度和实际代码总 advance；样本 Noto Mono 是有限 ASCII 合约。图标明确 PUA/Unicode/GSUB 的语义和屏幕阅读器文字替代，测试命名映射和替代图形，不能因 PUA 有轮廓就宣布可访问。
- 数学：检查真实 MATH 常数、italic correction、top accents、script placement、伸缩 variants/assembly；实际排分式、根式、积分/求和、上下标、伸缩括号和重音。`math` 样本用 STIX Two Math 与 HarfBuzz MATH API，Chrome 真实 MathML 另出 PDF。
- 音乐：使用 SMuFL 的 glyph 名/码位、bounding boxes、anchors、engraving defaults，并用真实排谱引擎。样本核对下载的 Bravura 字体/元数据，Verovio 用其**内置 Bravura 数据**排 MEI 乐谱；二者是分开的证据，不能宣称 Verovio 已载入下载的那个二进制。其他专业符号依据其行业规范新增样例和审阅。

## 11. 网页子集与体积

- 明确码点、脚本、特性、变体选择符与语言，保留 GSUB/GPOS/GDEF、复合字、附标和相关依赖。子集前考虑规范化/兼容分解；如泰文 sara am 塑形会用到分解后的字形，单纯保留输入码点可能漏字。
- 使用 FontTools subset，保存实际命令/参数与删除范围；`subset` 用例允许 GID 重编号，比较原版/子集塑形的簇、advance、offset 和实际轮廓。COLR paint/位图还需表和像素专项，不能只比较黑色 fallback。
- 回读每种网页容器、许可字段和字节；测加载、慢网/失败回退、font-display、布局位移和实际部署的 MIME/CORS、缓存失效及分语言 unicode-range。跨域和 CDN 必须使用真实配置测试，本机 `Access-Control-Allow-Origin:*` 不能成为线上验收。

## 12. 正式生产、安装与发行

- 使用与委托相符的 FontBakery profile。样本调用 `check-universal --skip-network --json ... -J 1`，保存原始 FAIL/WARN/SKIP 与解释；不改退出阈值把 FAIL 隐藏成成功。面向某个平台发行时再使用其 profile，不默认套用所有平台要求。
- 用 `python -m ots input output` 验证 TTF/CFF/可变/网页与声明彩色格式；保留原件，sanitized 输出仅作测试。OTS 接受不是审美、许可或应用兼容认证；负例必须确认截断字体被拒绝。
- 实际目标平台按[工程封装](engineering-packaging.md)执行安装→家族菜单与粗斜按钮→真实应用排版→PDF 字体嵌入与文本提取→新版本更新/缓存→卸载。每一步写清系统、应用版本、文件哈希和证据。过程注册、文件解析、浏览器载入、用户级安装是不同事实。
- macOS CoreText 可用[进程注册测试](../scripts/check_coretext.swift)单独检查载入与真实 CTLine glyph run；它不修改系统字体，不证明已经安装。Windows、Adobe、Office、手机或印刷是项目必需项时必须在对应环境实测；没有环境就保留待补，不拿模拟或另一个系统冒充。
- 安装更新实测时使用唯一测试家族，先保存当前状态，不能覆盖用户现有字体；测试后仅卸载本次测试成员。新字体即使文件字节已替换，应用/字体服务仍可能返回旧版本；优先使用系统安装器或在受控测试中原子替换，重新查询实际文件 URL、内部版本和家族成员，并重新导出样张。禁止为此清空全局字体缓存或结束用户应用而不保留其工作。

## 打包、版本与旧文件

- 按[交付计划示例](../assets/delivery-plan.example.json)列出字体、真实源、许可、试排和报告的路径/哈希，以及项目必需 gates；使用 `scripts/package_project.py /project/delivery.json /delivery/new.zip`。全部输入限定在该项目、拒绝符号链接与过期哈希，ZIP 后 CRC/逐字节回读。`release:true` 会拒绝尚未通过的必需关卡；审校包可保留 pending 并明确非正式发行。
- 源修改→重建→重跑受影响专项→刷新报告、预览、技术册和副本→回读 ZIP。报告必须绑定当前输入哈希；`check_specialties.py` 和 `check_source.py` 自动记录。外部工程以其当前构建身份为准，不用最终 TTX 冒充可重建源。
- 清理先列当前交付、源、许可、备份和其他项目依赖。按已有用户授权编写 `cleanup.json`（authorization、preserve、dependencies、candidates 的相对路径及 SHA-256），先运行 `scripts/retire_font_artifacts.py cleanup.json` 干跑；核对后可加 `--apply /project/new-recovery-folder`，只搬移列出的旧 TTF/OTF/WOFF/WOFF2/ZIP，保留恢复清单。未授权的电脑全盘清理不得扩大为这一步。
- 脚本是可恢复退役，不永久删除；用户要求进废纸篓时再通过系统操作移动已核对的退役文件夹并回读。源、许可、其他项目依赖与旧证据仍按[维护要求](engineering-packaging.md#版本维护源与旧文件)保护。清理样本只在隔离目录验证，不能顺带删除实际字体项目。
