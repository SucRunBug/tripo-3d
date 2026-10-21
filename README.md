# AI 制作游戏

连接 Tripo、配置 Blender CLI 或国际版 Unity CLI。让 Agent 读取 [SKILL.md](SKILL.md)，按目标只加载对应 skill。

| 任务 | Skill |
| --- | --- |
| Tripo 密钥配置与账户验证 | [connect-tripo](skills/connect-tripo/SKILL.md) |
| Blender CLI 安装与真实渲染验证 | [setup-blender-cli](skills/setup-blender-cli/SKILL.md) |
| Unity CLI 与 Pipeline 配置 | [setup-unity-cli](skills/setup-unity-cli/SKILL.md) |
| Tripo 建模、绑定、动画与任务恢复 | [tripo-assets](skills/tripo-assets/SKILL.md) |

## 安装

```bash
git clone https://github.com/SucRunBug/tripo-3d.git
cd tripo-3d
python3 scripts/install.py
```

开启新会话，使用 `$tripo-3d` 并说明目标。安装器复制整个包，顶层入口通过相对路径读取子 skill，不依赖 Agent 自动发现嵌套目录。子目录共享根目录脚本，不要单独复制。支持 Claude Code 和自定义目录，见 [安装与迁移](INSTALL.md)。

Blender 历史实测覆盖 macOS arm64，Linux 未实机验证，Windows 不支持现有配置脚本；Unity 配置按官方文档整理，未本机实测。Tripo 连接验证不会生成模型，资产生成和后处理按官方账户计费。

## 离线检查

```bash
python3 scripts/selftest.py
python3 scripts/test_setup_blender.py
```

来源与技术取舍按需见 [sources.md](references/sources.md)。本项目与 Tripo、Blender、Unity 官方无隶属关系。
