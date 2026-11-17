# 猎人字体设计 · Hunter Font Design

把一句风格要求，逐步变成可审校、可试排、可导出的字体。这套 Skill 来自 Hunter Block 字体的真实设计与反复修订。

**核心顺序：确认需求与风格 → A/B/C 三张概念参考图 → 用户选定 → 设计原则 → 同尺度网格样字 → 分组扩展字符 → 整套光学审校 → 工程验收、试排与技术字样册 → 字体封装 → 按需制作展示海报。**

## 一键安装

需先安装 Node.js 22.20 或以上版本（包含 `npx`），在终端执行：

```bash
npx -y skills@latest add Kevin-ho616/Hunter-Skill --skill hunter-font-design -g -y
```

该命令全局安装本 Skill，并跳过交互确认。安装后，在助手中调用 `$hunter-font-design`；字体制作所需的其他工具与依赖按下文准备。安装环境与参数见 [Skills CLI 官方说明](https://github.com/vercel-labs/skills#install-a-skill)。

## 内容

- [SKILL.md](SKILL.md)：执行流程与验收要求。
- [覆盖范围与按需专项](references/coverage-and-specialties.md)：识别家族、正文屏显、文字/竖排、可变/彩色、专业符号及网页子集等任务，逐项进入可执行的专项构建、验证与审阅。
- [专项生产、工具与验证](references/specialist-workflows.md)：12 类专项的设计动作、实际工具、固定来源样本、完整复现命令、正式发行门禁与维护。
- [设计规则模板](assets/design-rules-template.md)：三案与选择记录，以及字高、笔画、字宽、转角、内白、开口、间距与光学例外。
- [参考测量与项目参数](references/measurement-and-targets.md)：有参考时先校准测量，用 [参数示例](assets/font-targets.example.json) 记录项目自己的目标、容差、字符范围与塑形样例。
- [审字经验](references/design-review.md)：共享部件、跨字符风格统一和常见修订误区。
- [字距专项审校](references/spacing-and-kerning.md)：成稿时默认检查小写局部留白、大小写边界、窄字与下伸部、标点数字、附标替代字、上下文及适用的混排场景；按当前字形和目标字号决定收紧、放宽或保持，并记录结果。
- [工程与封装](references/engineering-packaging.md)：命名、编码、字偶、真实 TTF/OTF、WOFF2/WOFF 与验证边界。
- [版权与许可](references/copyright-and-license.md)：填写版权方与授权资料，在构建源写入，并逐字重、逐格式回读检查；开源底字保留原版权和许可，修改者署名另行追加。
- [试排工具](references/proof-tool.md)：离线输入文字、调整排版、查看同尺度网格。
- [通用验收与技术字样册](references/automated-checks-and-book.md)：检查真实字体，生成同版本的字符表、字号阶梯、字偶对照与 PDF。
- [中文衍生字库](references/cjk-derived.md)：选择开源骨架定制路线时，核对来源许可、汉字结构、约定覆盖与中文试排。
- [宣传展示](references/promotion-posters.md)：技术样张、应用海报、实际字面行距、透明 Logo 与字体参与构图。

Skill 是提供给 AI 编程助手的工作方法和工具，不是一个按下按钮便自动完成全部字体设计的程序。它不绑定专用付费 API；字体轮廓制作、构建和图片生成由所用助手的实际能力与环境承担。

## 在 Codex 中使用

可使用上方命令安装；也可手动下载本仓库，将整个 `hunter-font-design` 文件夹放入 Codex 当前配置的 Skill 加载目录，保留 `assets`、`scripts`、`references`、`agents`。在助手可识别 Skill 后调用：

```text
使用 $hunter-font-design，帮我设计一套用于海报标题的英文字体。
希望厚重、简约，字形略高但不要过窄。
确认需求与风格后，先用同一组样字生成 A/B/C 三张概念参考图。
等我直观比较并选定方向后，再做设计原则和真实网格控制字。
需要大写、小写、数字和常用标点，最终交付 TTF/OTF 和离线试排工具。
```

根据自己的项目替换风格、字符范围与交付要求。不同客户端的 Skill 加载方式以其配置为准。

三案以 A/B/C 效果图展示，在已确认的风格内使用相同样字、相近字高和简洁背景，比较字形比例、曲率与端头等差异。用户选定一案或明确组合某些特征后，再开始完整制作。初步效果是概念图，不能当作可安装字体；所选方向仍需经过真实轮廓和控制字验证。已有认可母版的续做、局部修字或追加海报不重新选样；明确要求跳过或授权代选时按该指示继续。

## 单独使用离线试排工具

浏览器打开 [assets/proof-tool/index.html](assets/proof-tool/index.html)，点击“载入字体”，选择自己的 TTF、OTF、WOFF 或 WOFF2。字体和输入文字在本机处理；无须启动服务器。浏览器仍需支持相应字体格式。

支持字号、行距、字间距、段距、宽度、对齐、字偶与标准连字开关，以及基线、大写线、小写线、字面框和边距。网格与参数只改变显示，不修改字体轮廓。通过文件选择临时导入的字体尚未解析完整字符映射，缺字可能由系统回退；不能把显示成功当成字符覆盖证明。

## 生成附带字体的校样包

在本 Skill 目录中，使用已有环境，或建立项目虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install fonttools brotli
.venv/bin/python scripts/create_proof.py /path/to/YourFont.ttf /path/to/new-proof
```

两个路径请替换成实际位置。输出目录必须尚不存在，避免覆盖审校证据。脚本复制原字体，读取版本、字高、字符映射和度量，生成可离线打开的试排包；不会安装、上传或改写字体。

可选浏览器回归检查需要 Node.js、可解析的 `playwright` 包及已安装的 Google Chrome：

```bash
node scripts/check_proof.cjs /path/to/new-proof
```

检查脚本验证字体加载/下载字节、主要交互、缺字提示、网格度量、固定控制区域、窄屏布局与离线行为。请优先使用已有依赖；未运行自动化时，按 [试排工具说明](references/proof-tool.md) 手动检查。

## 测量、工程验收与自动技术字样册

最新版同时包含 `measure_reference.py`、`check_font.py`、`create_font_book.py` 与 `render_font_book.cjs`。按项目自己的 `font-targets.json` 使用，字体、验收报告、试排与字样册保留一致的版本和文件哈希；陈旧报告不能用于新字体。

依赖按实际用途准备：fontTools 为基础，塑形检查用 uharfbuzz，WOFF2 用 brotli，图片测量用 Pillow；PDF 导出另需 Playwright 与可用 Chromium／Chrome。完整命令、检查范围和 PASS/FAIL/INFO/SKIP 含义见 [工具说明](references/automated-checks-and-book.md)。这些工具不会替代整套光学审校，也不会自动把技术册当作宣传海报。

## 范围与许可

目前已验证的制作经验以拉丁展示字体为主，另有中文开源骨架定制的专项流程。逐字原创中文、其他复杂文字塑形、可变字体和彩色字体仍需要额外的专门设计与验证。网格规则不是机械等宽要求；光学校正要结合具体风格和目标字号判断。

**本目录内 Skill 文本、模板及工具代码以 [MIT License](LICENSE) 开源。** 这一授权只适用于本目录，不改变仓库内其他 Skill 的授权。试排模板附有猎人品牌图像与公众号二维码；这些品牌素材不因工具代码开源而自动获得其他用途或再分发许可，其他项目应按自身品牌替换。本目录不包含 Hunter Block 字体文件或第三方字库；字体、海报及第三方资产的授权另按实际来源确认。依赖软件各自遵循原许可。

字体能被解析、浏览器能显示、进程内注册成功、系统安装完成和目标软件兼容是不同的验收结果。正式发布自己的字体前，请按实际目标完成检查并明确字体授权。

## 专项工具与实际字体测试

使用 [requirements-specialties.txt](requirements-specialties.txt) 在独立 Python 3.12 环境准备 Fontmake、FontTools、HarfBuzz、PathOps、ttfautohint、FontBakery、OTS、FreeType 和 Verovio。按[专项参考](references/specialist-workflows.md)下载固定哈希的公开 OFL 字体及许可，构建可编辑 UFO/Designspace/Glyphs 样本，再运行塑形/家族/多轴/彩色/公式/排谱/子集/源依赖检查及真实浏览器渲染。字体二进制按需下载，不随 Skill 源包提交。

交付用 [delivery-plan.example.json](assets/delivery-plan.example.json) 登记范围与证据，`package_project.py` 检查哈希、必需关卡和 ZIP；`retire_font_artifacts.py` 对已有授权内的旧字体/ZIP 先干跑、再可恢复搬移。来源许可和其他项目依赖必须保护。工具测试通过不代表人已经认可所有字形，也不代表所有系统、应用、语言和格式都已测试。
