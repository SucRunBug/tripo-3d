# 开发环境安装与迁移

本项目用于 AI 制作游戏：Tripo 制作资产，Blender 检查与处理，国际版 Unity 接入玩法。本文介绍 Tripo Skill 安装与迁移、Blender CLI 配置；国际版 Unity Editor、Unity CLI 和 Pipeline 的大致步骤见 [README 的 Unity 配置](README.md#unity-cli)，该部分只参考官方文档，未本机测试。

需要 Python 3.10 或更高版本，以及能访问 Tripo 官方 API 的网络。生成、上传、查询、下载不依赖 Node、Blender 或 pip 库；真实渲染和引擎验收使用目标电脑已有的 3D 工具。以下 `python` 在 macOS/Linux 通常写作 `python3`，Windows 可使用 `py -3`。

## 安装

解压 `tripo-3d.zip`。在解压出的 `tripo-3d` 文件夹中打开终端：

```bash
python scripts/install.py
```

默认复制到当前用户的 Codex skills 目录，遵守已设置的 `CODEX_HOME`。已安装时不会覆盖旧目录。也可选择：

```bash
python scripts/install.py --target claude
python scripts/install.py --target agents
python scripts/install.py --dest "/path/to/custom/skills"
```

Claude/其他兼容 Agent 读取相同 `SKILL.md`；不要求 Codex 专用工具。安装后开启一个新会话，让应用重新发现 skill。在不支持该目录自动发现的应用里，直接让 Agent 读取解压目录中的 `SKILL.md`。

### 可选：一键配置 Blender CLI

本功能用于本地场景操作和真实渲染；不需要 Tripo 密钥。**本机测试平台为 macOS / Apple Silicon**，详见 [环境版本、完整命令和失败记录](references/blender-cli.md)。先装好 Blender、Python 3.10+ 和 Git，然后执行：

```bash
# 已安装 Skill，只配置 Blender CLI
python3 scripts/setup_blender.py

# 首次安装 Skill 并同时配置 Blender CLI（两条选一条）
python3 scripts/install.py --with-blender
```

默认运行环境保存在 `~/.local/share/tripo-3d/blender-cli/`，命令入口在 `~/.local/bin/cli-anything-blender`。自动使用独立 venv，不向系统 Python 装库，不覆盖其他工具的同名命令，不修改 shell 启动文件。按输出提示执行一次：

```bash
source "$HOME/.local/share/tripo-3d/blender-cli/activate.sh"
cli-anything-blender --help
blender --version
```

这会给当前终端添加命令路径。新终端按需重新 source；也可自行把这条 source 放进自己的 shell 配置。失败后根据打印的日志修复，再运行原命令；Skill 已复制成功但 CLI 配置失败时，使用 `setup_blender.py` 重试，避免重复安装 Skill。已有 Skill 不会被 `install.py` 覆盖。

```bash
# 无下载复检（创建新的测试场景并真实渲染）
python3 scripts/setup_blender.py --check

# 自定义路径；--blender 指向可执行文件，不是 .app 目录
python3 scripts/setup_blender.py --home "/path/with spaces/blender-cli" \
  --bin-dir "/path/to/bin" --blender "/Applications/Blender.app/Contents/MacOS/Blender"
```

自定义位置复检时需重复传入相同的 `--home`、`--bin-dir`，Blender 不在默认位置时也传 `--blender`。不要移动或删除安装环境，否则命令入口会失效。详细目录、卸载和平台限制见上面的专门说明。

## 获取 API Key

API Key 是让这个 skill 访问你 Tripo 账户的访问凭据。第一次使用时：

1. 打开 [Tripo 开发者控制台](https://platform.tripo3d.ai)，注册或登录账号。
2. 进入 **API Keys** 页面。
3. 点击 **Create Key**，按页面提示创建密钥；如需填写名称，可用 `codex-tripo` 便于识别。
4. 复制并妥善保存完整密钥。官方说明它只在创建时展示一次；如果未保存，可回到控制台创建新密钥。

上述入口与步骤来自 [Tripo 官方身份验证文档](https://developers.tripo3d.ai/en/docs/authentication)，核对日期 2026-09-17。界面更新时以控制台实际提示为准。

## 在本机配置并验证

在 **skill 文件夹**里打开自己的交互式终端（macOS 可使用“终端”App），依次运行：

```bash
python scripts/tripo.py doctor
python scripts/tripo.py configure
```

看到 `Tripo API key` 提示后粘贴密钥，再按回车。**输入时不显示字符或星号是正常的**。只粘贴密钥本身，不加 `Bearer`、引号或其他文字；不要把密钥发到聊天中。

`configure` 会向官方查询账户余额，验证成功后显示 `configured: true` 和保存位置。然后执行：

```bash
python scripts/tripo.py doctor --online
```

能正常返回账户余额且没有错误，表示密钥与账户连接验证成功。这两步都不会生成模型。`key_present: true` 只表示本机发现凭据，不能单独证明密钥有效；余额为 0 也可能验证成功，但生成前需在 API 控制台检查可用额度。具体计费和额度以当前账户为准。

如果由 Agent 提供命令，应使用当前安装位置的脚本绝对路径并加引号，让用户无需切换目录就能执行。

### 保存位置

`configure` 隐藏输入、向官方查询余额验证密钥，然后存入本机用户配置目录：

- macOS/Linux：`$XDG_CONFIG_HOME/tripo-3d/credentials.json`，未设置时为 `~/.config/tripo-3d/credentials.json`。
- Windows：`%LOCALAPPDATA%/Tripo3D/credentials.json`。

配置是本地明文文件，不是系统钥匙串；Unix 权限为 0600。它位于 skill 包和游戏项目之外，迁移包不包含此文件。共享电脑或不想落盘时，用环境变量 `TRIPO_API_KEY`；环境变量优先于本机配置。也可以不预配置，让单次命令在交互终端隐藏询问；该次输入不保存。

不要把真实密钥写进终端命令行、提示词文件、前端 `.env` 或提交记录。用 Agent 调用时，通过环境注入或由自己在交互终端执行 `configure`。删除上述配置文件即可移除持久密钥；无需修改 skill。

### 常见问题

| 遇到的情况 | 下一步 |
| --- | --- |
| 找不到 API Keys | 从上面的开发者控制台入口登录，并核对官方身份验证文档；不要在模型编辑页面里找密钥。 |
| 提示需要交互终端 | 在自己的终端 App 中执行 configure；Agent 的非交互命令面板无法完成隐藏输入。 |
| 输入时看不到字符 | 正常的隐藏输入行为；粘贴一次后按回车。 |
| 401 / 密钥无效 | 检查是否复制完整、是否已撤销，以及是否误加 Bearer 或引号；必要时创建新密钥并重新 configure。 |
| 403 / 无权限 | 在控制台核对账户和接口访问权限，按官方错误提示处理；不自动提交重试。 |
| configure 成功，但后续仍用旧密钥 | `TRIPO_API_KEY` 环境变量优先于保存的文件；在运行命令的同一环境中移除旧变量或更新环境注入后再验证。不要打印变量内容。 |
| 网络、TLS 或代理错误 | 检查本机网络与代理后重跑 doctor --online；不要关闭 TLS 校验。 |
| 余额不足 | 在 API 控制台检查额度及充值选项；由用户按实际需求决定是否充值。 |
| 账户连通，但 P2 生成提示模型不可用 | 当前 `P2-20260801` 标记为 Preview；核对官方模型参数和账户可用权限，必要时联系官方支持。余额查询不验证 P2 生成权限。 |

## 使用示例

新会话直接说：

> 使用 $tripo-3d，把这张参考图做成一个带 PBR 材质的 GLB 模型。先检查正面和背面外形，再按照我的要求细化。

> 使用 $tripo-3d，制作一个可控游戏角色，带 idle、walk、run、jump。沿用当前项目的控制器，导入后检查跳跃、手持道具和穿模。

> 使用 $tripo-3d，继续这个 jobs 文件夹中已提交的任务，不要重新生成。

执行 `python scripts/selftest.py` 可以离线检查脚本是否正常。`doctor --online` 只检查账户连通性，不生成模型。生成、绑骨、动画等费用按官方当前账户计费。

## 搬迁范围

只迁移 skill：复制完整 `tripo-3d/`，在新电脑配置新密钥。

继续已有任务：另外复制项目内的请求 JSON 和 `jobs/`，保留相对目录与 `job.json`；新密钥必须能访问原任务所在账户。只换电脑但没有任务记录时，先到官方账户核对任务，不能把所有阶段自动重跑。下载后的完整模型可以离线使用，不需要原账户密钥。
