# AI 制作游戏

用 Codex、Claude Code 等 AI Agent 串起 **Tripo 生成资产 → Blender 检查与处理 → Unity 开发游戏**，把游戏想法逐步做成可玩的原型。

本仓库整理这套流程所需的 Skill、工具配置和接入指南。目前包含 Tripo 3D 资产工具、已在 Mac 实测的 Blender CLI 一键配置，以及按官方文档整理的国际版 Unity / Unity CLI 配置步骤。仓库地址及已有 Skill 调用名继续使用 `tripo-3d`。

## 制作流程

| 阶段 | 工具与任务 | 当前提供的内容 |
| --- | --- | --- |
| 确定玩法 | 与 AI 说明核心操作、视角、规则和目标平台 | 先确定最小可玩范围，再制作需要的资产 |
| 制作资产 | Tripo 生成角色、道具和场景模型，完成绑定与动画 | Python 工具与 `tripo-3d` Skill |
| 检查资产 | Blender 检查外形、材质及真实渲染 | CLI 一键配置，macOS 已实测 |
| 开发游戏 | 国际版 Unity 接入模型、交互与玩法逻辑 | Unity CLI / Pipeline 配置指引，未本机测试 |
| 验收原型 | 检查走跑跳、碰撞、手持物与实际游玩 | 游戏接入与验收指南 |

先跑通一个角色、一种核心操作和一个小场景，再增加玩法。需要 Tripo 生成资产时配置自己的 API Key；Blender 和 Unity 环境按下面的步骤分别准备。

## 能做什么

- **生成模型**：文字、单张图片、标注 front/back/left/right 的多视图输入。
- **细化外形**：通过真实网格渲染与参考图比对，区分轮廓、比例、材质和蒙皮问题。
- **绑定与动画**：可绑定检查 → 骨骼绑定 → idle / walk / run / jump 等动作，检查各阶段任务依赖。
- **任务恢复**：保存任务 ID、请求和进度；网络中断后继续查询，避免重复提交收费任务。
- **资产交付**：下载模型与贴图、校验 GLB、检查 ZIP 路径，生成文件清单和 SHA-256。
- **游戏接入**：控制器、跳跃状态、手持物挂点、IK、蒙皮权重、角色与场景碰撞的实践指南。
- **开发环境配置**：Blender CLI 自动配置与国际版 Unity CLI / Pipeline 的配置说明。

## 快速开始：安装 Tripo 资产 Skill

Tripo 部分使用 **Python 3.10+ 标准库**，直连官方 API，无需安装 Python 第三方库。Blender CLI 与 Unity 有各自的安装依赖。

先到 [Tripo 开发者控制台](https://platform.tripo3d.ai) 注册或登录，进入 **API Keys → Create Key**，创建并复制密钥。完整密钥只在创建时显示一次。详细步骤见 [获取 API Key 与配置说明](INSTALL.md#获取-api-key)。

```bash
git clone https://github.com/SucRunBug/tripo-3d.git
cd tripo-3d
python scripts/install.py
python scripts/tripo.py configure
```

macOS/Linux 的 Python 命令通常是 `python3`；Windows 可使用 `py -3`。

`configure` 提示后粘贴密钥、按回车；输入不显示字符是正常的。显示 `configured: true` 表示验证并保存成功，再运行 `python scripts/tripo.py doctor --online` 复核账户连接，不会生成模型。具体位置和常见问题见 [安装说明](INSTALL.md)。不想落盘时，可通过环境变量 `TRIPO_API_KEY` 提供密钥。无需把密钥发到聊天中。

默认安装到 Codex 的 skills 目录；也支持：

```bash
python scripts/install.py --target claude
python scripts/install.py --target agents
```

安装后开启一个新会话：

> 使用 $tripo-3d，根据这张参考图生成一个带 PBR 材质的 GLB 模型，先检查正背面外形。

> 使用 $tripo-3d，为当前游戏制作可控角色，完成绑定和走跑跳动作，接入后检查跳跃、手持道具与碰撞。

只需要模型时不会默认搭建游戏；静态道具不会默认提交绑定和动画阶段。生成和后处理按 Tripo 官方当前账户计费。

## 一键配置 Blender CLI（可选）

已在 **macOS 15.7.4 / Apple Silicon arm64 / Blender 5.2.0 LTS / Python 3.14.7** 上完成安装及真实渲染验证。先安装 [Blender](https://www.blender.org/download/)，再在仓库目录运行：

```bash
# 单独配置 Blender CLI，已有 Tripo Skill 时用这条
python3 scripts/setup_blender.py

# 或在首次安装 Skill 时一起配置
python3 scripts/install.py --with-blender
```

自动识别 Mac 的 Blender.app、下载固定版本的 CLI-Anything、创建独立 Python 环境，验证建场景、材质、相机、灯光和真实 PNG 渲染后才发布命令入口。无需 Tripo API Key，不会创建收费模型。Blender 本体需事先安装。

```bash
source "$HOME/.local/share/tripo-3d/blender-cli/activate.sh"
cli-anything-blender --help
blender --version
```

支持自定义安装位置和复检；Linux 有安装分支但尚未实机验证，Windows 暂不支持此安装脚本。截图教程里的部分命令已与当前上游不同，详见 [Blender CLI 安装、实测与失败排查](references/blender-cli.md)。

<a id="unity-cli"></a>

## 配置 Unity CLI（国际版，未本机测试）

**以下按 Unity 官方文档整理，核对日期为 2026-10-18，未在本机安装或测试。** Unity CLI 目前处于实验阶段，命令以安装后的 `unity --help` 为准。[官方使用指南](https://docs.unity.com/en-us/unity-cli/use-unity-cli)

### 1. 安装国际版 Unity Editor

本项目使用 **Unity 国际版**。从 [Unity 国际版编辑器下载归档](https://unity.com/releases/editor/archive)选择版本，通过页面的 Unity Hub 安装入口安装 Editor 和目标平台模块。Mac 按芯片架构选择对应安装包。要使用下述 Pipeline，选择 **Unity 6.0 或更高版本**。[Pipeline 前置要求](https://docs.unity.com/en-us/unity-cli/unity-pipeline/unity-pipeline-package)

### 2. 安装 Unity CLI

macOS 需 14 或更高版本。在自己的终端执行官方安装命令：

```bash
curl -fsSL https://unity.com/install.sh | bash
unity --version
unity --help
```

如果找不到 `unity`，重新打开终端，或按安装提示将安装目录加入 PATH。Windows 和 Linux 的安装方式见[官方安装说明](https://docs.unity.com/en-us/unity-cli/use-unity-cli#install-the-unity-cli)。

### 3. 登录并检查编辑器

```bash
unity auth login
unity auth status
unity editors -i
unity doctor
```

先确认 CLI 能识别已安装的国际版 Editor。首次使用编辑器时，按编辑器或 Hub 的提示完成账户和许可配置。

### 4. 创建或打开项目

在准备存放游戏的目录执行；已有项目直接打开即可：

```bash
# 创建本地项目；--no-cloud 避免同时创建 Unity Cloud 项目
unity projects create MyGame --no-cloud
unity open ./MyGame

# 已有项目则使用自己的项目路径
# unity open "/path/to/MyGame"
```

### 5. 安装 Pipeline，让 AI 通过 CLI 操作编辑器

保持目标项目在 Unity Editor 中打开，进入该项目目录执行：

```bash
cd MyGame
unity pipeline install
# 回到编辑器，等待包安装与脚本编译完成，再执行：
unity pipeline list
unity command
```

按官方步骤检查 `Pipeline: Installed`，再通过 `unity command` 查看可用的编辑器命令。多个项目同时打开时，可用 `unity command --project-path="/path/to/MyGame"` 指定项目。[Pipeline 安装与连接指南](https://docs.unity.com/en-us/unity-cli/unity-pipeline/unity-pipeline-package)

完成后，把项目路径、核心玩法和验收要求交给 AI Agent，逐步接入模型、交互和玩法，并在编辑器中验证结果。本仓库的一键安装脚本目前只配置 Tripo Skill 和可选 Blender CLI，Unity 按上述步骤单独配置。

## 文档

| 文件 | 内容 |
| --- | --- |
| [SKILL.md](SKILL.md) | Agent 入口与工作流程 |
| [INSTALL.md](INSTALL.md) | 换电脑安装、密钥配置与已有任务迁移 |
| [官方 API 指南](references/api.md) | 请求 JSON、任务依赖、查询和恢复 |
| [外形与材质验收](references/quality.md) | 参考图准备、真实网格比对、精细化判断 |
| [游戏接入](references/game-integration.md) | 动画、控制器、IK、权重和碰撞 |
| [来源与取舍](references/sources.md) | 参考项目、官方文档和实践经验 |
| [Blender CLI](references/blender-cli.md) | 一键配置、macOS 实测、失败记录及修正命令 |
| [Unity CLI 配置](#unity-cli) | 国际版 Editor、CLI 登录与 Pipeline 接入；未本机测试 |

## 验证

```bash
python scripts/tripo.py doctor
python scripts/selftest.py
python scripts/test_setup_blender.py
python scripts/inspect_glb.py /path/to/model.glb --out audit.json
```

附带 22 项 Tripo 离线测试和 6 项 Blender 配置离线测试，无需密钥、不产生 Tripo 费用；另已用实际角色 GLB 和动画文件验证结构检查脚本。外形和动态变形仍需在 3D 查看器或目标引擎中实测；基础包不捆绑 Blender 或游戏引擎。

## 来源

参考 [meterlong/tripo-skills](https://github.com/meterlong/tripo-skills) 的需求路由、姿势建议与生成—绑定—动画流程，并结合实际双人游戏项目中的外形比对、材质修正、动画和碰撞经验重新编写。

Tripo 资产生成使用官方 API，没有采用上游第三方代理，也不承诺其免费额度。来源版本及具体取舍见 [sources.md](references/sources.md)。这是独立的 AI 制作游戏项目，与 Tripo、Blender、Unity 官方无隶属关系。
