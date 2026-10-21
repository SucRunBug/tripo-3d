---
name: setup-blender-cli
description: 配置独立 Blender CLI 环境，完成真实图片渲染与失败排查；用户要求安装、配置或复检 Blender CLI 时使用，无需 Tripo 密钥。
---

# 配置 Blender CLI

仓库根目录为本文件所在目录的上两级；从根目录运行以下脚本，或使用绝对路径。

1. 检查操作系统、Python 3.10+、Git 和 Blender 本体。此脚本支持 macOS/Linux；历史实测仅覆盖 macOS arm64，Windows 不运行此脚本。
2. 已有受管理环境时，运行 `python3 scripts/setup_blender.py --check`；否则运行 `python3 scripts/setup_blender.py`。脚本会安装固定提交的 CLI-Anything 到独立 venv，并实际启动 Blender 渲染。不要仅为配置 CLI 执行整个 skill 安装器。
3. Blender 不在默认位置时加 `--blender "/absolute/path/to/Blender"`，指向可执行文件。自定义运行目录用 `--home`、命令目录用 `--bin-dir`，复检时传入相同参数。
4. 按脚本输出的实际路径激活环境；默认执行 `source "$HOME/.local/share/tripo-3d/blender-cli/activate.sh"`，检查 `cli-anything-blender --help` 和 `blender --version`。该激活只影响当前终端，不擅自改 shell 配置。
5. 以成功退出、生成新的有效 PNG、实际查看图片作为完成标准；交付版本、入口、图片与日志路径。只生成 Python 脚本不算渲染成功。

安装失败时读取 [配置与排错](../../references/blender-cli.md) 的相应章节；先修复具体错误，再重试。受限环境不能运行时保留日志并报告未完成，不把历史实测当作本轮结果。配置无需读取 Tripo API、角色制作或 Unity 文档。
