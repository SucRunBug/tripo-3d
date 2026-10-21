---
name: tripo-3d
description: AI 制作游戏的选择入口；用于连接 Tripo、配置 Blender CLI 或 Unity CLI，以及转交 Tripo 资产任务。
---

# 选择任务

用户已明确目标时直接进入对应 skill；未明确时只问：连接 Tripo，还是配置 CLI（Blender / Unity）？

| 目标 | 只读取对应文件 |
| --- | --- |
| 连接 Tripo、获取密钥、验证账户 | [connect-tripo](skills/connect-tripo/SKILL.md) |
| 配置或复检 Blender CLI | [setup-blender-cli](skills/setup-blender-cli/SKILL.md) |
| 配置 Unity CLI / Pipeline | [setup-unity-cli](skills/setup-unity-cli/SKILL.md) |
| 生成、细化、绑定或下载 Tripo 模型，恢复任务 | [tripo-assets](skills/tripo-assets/SKILL.md) |

只加载当前任务的 skill；需要排错或具体参数时再读取其引用资料。不预读全部子 skill、README、安装说明或历史测试记录。多个目标按需逐项完成，不默认安装全部工具。所有路径相对于本文件；保留整个仓库目录结构。
