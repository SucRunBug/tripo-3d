---
name: setup-unity-cli
description: 配置国际版 Unity CLI 与 Pipeline，验证目标编辑器连接；用户要求配置 Unity CLI、安装 Pipeline 或排查编辑器连接时使用。
---

# 配置 Unity CLI

只配置用户需要的国际版 Unity 环境；无需 Tripo 密钥或 Blender。以下流程基于官方文档，未在本机实测；执行时以已安装版本的 `--help` 为准。

1. 检查 `unity --version`、`unity --help` 和操作系统。已安装可用则复用。macOS 需要 14+；Windows/Linux 的兼容条件和安装命令按[官方指南](https://docs.unity.com/en-us/unity-cli/use-unity-cli)核对。
2. 缺少 CLI 时，macOS/Linux 使用官方安装命令 `curl -fsSL https://unity.com/install.sh | bash`。随后重新打开终端或按输出调整 PATH，再检查版本。不要混用不同包管理器重复安装。
3. 运行 `unity auth login`，由用户完成登录；随后运行 `unity auth status`、`unity editors -i`、`unity doctor`。没有 Editor 时按[国际版下载归档](https://unity.com/releases/editor/archive)通过 Hub 安装所需版本与平台模块，完成账户和许可配置。既有项目遵循其 Editor 版本，不擅自升级；Pipeline 要求 Unity 6.0+。
4. 已有项目使用 `unity open "/path/to/MyGame"`。仅在用户需要新项目时运行 `unity projects create MyGame --no-cloud`，再打开；不自动创建 Cloud 项目。
5. 用户需要 CLI 控制 Editor 时，在目标项目目录运行 `unity pipeline install`，保持该项目在 Editor 中打开，等待包安装及编译完成，再运行 `unity pipeline list`。
6. 确认目标项目显示 `Pipeline: Installed`，运行 `unity command --project-path="/path/to/MyGame"` 查看可用编辑器命令。CLI 安装成功不代表编辑器已连接。

登录失败检查账户状态；找不到 Editor 检查安装路径；Pipeline 未连接先核对项目路径、编辑器运行状态与编译错误，不反复重装。多项目必须明确目标路径。仅要求 CLI 安装时，无需新建项目或安装 Pipeline。

交付实际版本、项目路径和验证结果，分别报告 CLI、账户、Editor、Pipeline 的完成状态；未执行的步骤标为未验证。Pipeline 步骤见[官方连接指南](https://docs.unity.com/en-us/unity-cli/unity-pipeline/unity-pipeline-package)。
