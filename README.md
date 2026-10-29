# Hunter-Skill

个人 Skill 存储与版本管理。

## 已收录

- [喵掌勺 · miao-zhang-shao](skills/miao-zhang-shao/SKILL.md)：黑白英短猫美食喜剧，从菜品策划、LibTV 视频制作到品牌封面。

## 使用

将 `skills/miao-zhang-shao/` 整个文件夹放入你的 Skill 加载目录，保留其中的 `references/`、`assets/`、`scripts/` 和 `agents/`。

- 视频制作依赖可用的 LibTV 连接及相应模型权限；封面制作依赖图像生成工具。
- 完整封面流程还依赖单独安装的 `video-cover-design` Skill。本仓库原样保存本地源文件，其中指向该依赖的链接是作者本机绝对路径；在其他环境中使用时，需按实际安装位置解析。
- 裁切检查脚本需要 Python 3 和 Pillow。可在 `skills/miao-zhang-shao/` 目录运行 `python3 scripts/test_crop_cover.py` 检查裁切几何、像素保留和防覆盖行为。
