# 安装与迁移

需要 Python 3.10+。在仓库根目录执行 `python3 scripts/install.py`，默认安装到 Codex skills 目录，遵守 `CODEX_HOME`。Windows 可用 `py -3`。

```bash
python3 scripts/install.py --target claude
python3 scripts/install.py --target agents
python3 scripts/install.py --dest "/path/to/skills"
```

以上方式任选一种。安装器保留整个目录结构，不覆盖已有安装。更新时先比较差异、备份本地修改，再替换完整目录；不要单独复制子 skill。开启新会话使用 `$tripo-3d`；不支持自动发现的 Agent 直接读取顶层 `SKILL.md`。

- 连接账户：读取 [连接 Tripo](skills/connect-tripo/SKILL.md)。
- 配置 Blender：读取 [Blender CLI](skills/setup-blender-cli/SKILL.md)。兼容旧的 `--with-blender` 安装参数；仅配置 CLI 时使用专门 skill。
- 配置 Unity：读取 [Unity CLI](skills/setup-unity-cli/SKILL.md)。

换电脑时迁移整个包；凭据不包含在包内，需在新电脑重新配置。继续已有 Tripo 任务还需迁移项目请求和 jobs 记录，避免重复收费提交。
