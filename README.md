# Hunter-Skill

尽情创造。

## 已收录

- [喵掌勺 · miao-zhang-shao](skills/miao-zhang-shao/SKILL.md)：黑白英短猫美食喜剧，从菜品策划、LibTV 视频制作到品牌封面。
- [产品手册分层排版 · product-manual-layout](skills/product-manual-layout/SKILL.md)：产品手册、操作手册、宣传册和产品目录的分层排版，支持按需交付 INDD／IDML、AI 与 PDF。
- [品牌 VI 手册 · brand-vi-manual](skills/brand-vi-manual/SKILL.md)：将定稿 Logo 与品牌简报扩展为 16:9 PPTX 商业 VI 手册，涵盖基础规范、应用设计与场景 Mockup。

## 使用

将 `skills/` 下所需 Skill 的整个文件夹放入你的 Skill 加载目录，保留其中的附带文件和目录。

### 喵掌勺

- 视频制作依赖可用的 LibTV 连接及相应模型权限；封面制作依赖图像生成工具。
- 完整封面流程还依赖单独安装的 `video-cover-design` Skill。本仓库原样保存本地源文件，其中指向该依赖的链接是作者本机绝对路径；在其他环境中使用时，需按实际安装位置解析。
- 裁切检查脚本需要 Python 3 和 Pillow。可在 `skills/miao-zhang-shao/` 目录运行 `python3 scripts/test_crop_cover.py` 检查裁切几何、像素保留和防覆盖行为。

### 产品手册分层排版

按交付格式准备 InDesign、Illustrator 或相应 PDF／矢量排版工具；需要生成视觉素材时，还需可用的 GPT Image 工具。具体制作和验收要求见 Skill 原文。

### 品牌 VI 手册

需要已定稿 Logo、品牌简报及可用的 Presentations Skill；需要生成场景或 Mockup 时，还需 imagegen Skill 和图像工具。默认交付本地 16:9 PPTX，具体要求见 Skill 原文。
