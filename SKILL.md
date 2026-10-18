---
name: tripo-3d
description: 使用 Tripo 官方 API 从文字、单图或多视图生成和细化 3D 模型，完成可绑定检查、骨骼绑定、动画与格式导出；适用于 Tripo 建模、参考图还原及游戏资产接入，也支持换电脑后配置自己的 API 密钥。
---

# Tripo 3D 建模

把用户描述或参考图变成可检查、可下载、可用于目标项目的 3D 资产。基础工具只依赖 Python 3.10+ 标准库，直连 `https://openapi.tripo3d.ai`。技能路径从当前 `SKILL.md` 位置解析；工作文件放在用户项目，不能假设原电脑目录、游戏角色、前端框架或固定骨骼名。

## 开始

1. 首次使用或换电脑时读取 [INSTALL.md](INSTALL.md)，运行 `python scripts/tripo.py doctor`。已有 `TRIPO_API_KEY` 或本机配置时直接复用；缺少密钥时，按下面的首次配置引导帮助用户完成获取、配置和验证。
2. 从用户请求判断目标：静态道具、可动画角色、展示/AR、打印，或者已有模型细化。保留明确的风格、外形、输出格式和预算；只补充影响建模的缺失信息。用户已给参考图时优先使用参考图，不擅自换成文字猜测。
3. 读取 [references/api.md](references/api.md) 选择接口、准备请求 JSON。用 `submit --dry-run` 检查请求。实际调用前查余额，说明本轮对象、模型配置与提交阶段；用户已有的建模/绑定授权可继续使用，不额外设置批准关卡。制作 skill 或离线测试本身不需要创建收费模型。

## Blender CLI 配置与验证（可选）

用户要求安装或配置 Blender CLI，或本地渲染需要此工具时，读取 [Blender CLI 指南](references/blender-cli.md)，运行当前 skill 的 `scripts/setup_blender.py`。macOS 会自动探测 Blender.app，使用独立 venv 安装固定版本的 CLI-Anything，并在真实渲染出 PNG 后才报告成功。Blender 本体需预先安装；已有安装可用 `--check` 复检。此流程无需 Tripo 密钥，不产生 Tripo 费用。

**已验证平台：macOS / arm64；Linux 未实机验证，Windows 安装脚本暂不支持。** 不照抄旧教程参数：全局 `--project` 放子命令之前；`render execute` 只生成脚本，随后必须实际调用 Blender 并检查图片。记录失败日志及修复措施；受限 Agent 环境崩溃时，在允许 Blender 正常运行的本机终端复检，不把生成脚本当成渲染通过。

## 首次配置引导

当检查发现没有密钥，或用户问如何获取 API Key 时，在回复中直接给出以下指引，不只说“还缺 API Key”或仅丢一个 configure 命令：

1. 打开 [Tripo 开发者控制台](https://platform.tripo3d.ai)，注册或登录账号。
2. 进入 **API Keys** 页面，点击 **Create Key**，按页面提示创建并复制密钥。官方说明完整密钥只在创建时展示一次。
3. 给用户一条可直接执行的 `configure` 命令：根据当前 skill 的实际位置解析脚本绝对路径并正确引用，在用户自己的交互终端中执行。提示“粘贴时不显示字符是正常的，粘贴后按回车”；无需把密钥发送到聊天。
4. `configure` 查询账户余额并显示 `configured: true` 后才算保存成功。用户完成后运行 `doctor --online` 复核；只验证账户连接，不创建模型。余额不足和 P2 权限问题按 [INSTALL.md](INSTALL.md) 排查，不将“已写好模型配置”说成“已验证 P2 可生成”。

密钥获取与排错以 [INSTALL.md](INSTALL.md) 为详细说明真源。页面名称或位置不一致时核对其引用的官方文档，不猜按钮位置。等待用户配置时可以继续准备请求并 dry-run；不要索要明文密钥或用收费生成测试连接。

## 按请求选择流程

| 用户要做的事 | 工作方式 |
| --- | --- |
| 文字做道具/角色 | text-to-model；角色使用全身、中性 A/T 姿势、四肢分离描述 |
| 照片或角色参考图转模型 | image-to-model；同一对象、同一姿态的多视角用 multiview-to-model |
| 外形更像、模型更精细 | 先定位轮廓、比例、几何或材质问题，按 [references/quality.md](references/quality.md) 比对，再决定重生成或局部修正 |
| 让角色走、跑、跳 | 外形检查 → rig-check → rig → retarget；遵守任务 ID 的依赖关系 |
| 修改贴图、不改形状 | models/texture 或项目中的局部材质调整；不要仅为粗糙度问题重做整个角色 |
| 导出网页/游戏/AR/打印资产 | 按目标选 GLB、FBX、USDZ、STL/3MF；生成成功并不等于可打印或已适配引擎 |
| 将已有本地模型交给 Tripo | 上传 → models/import → 所需处理步骤 |
| 积木/体素风格 | 查当前官方支持；上游 stylize 已标为弃用，不调用第三方旧代理来替代 |

不要默认全部做完：静态道具不绑骨，只要求模型时不自动搭建游戏。动画和游戏接入读取 [references/game-integration.md](references/game-integration.md)。

## 提交与恢复

从 skill 所在目录调用脚本，或使用解析后的绝对脚本路径；请求和 `--job` 放用户工作目录。

```bash
python scripts/tripo.py submit --request /path/to/request.json --job /path/to/jobs/object-v1 --dry-run
python scripts/tripo.py submit --request /path/to/request.json --job /path/to/jobs/object-v1
python scripts/tripo.py wait --job /path/to/jobs/object-v1 --timeout 45
python scripts/tripo.py download --job /path/to/jobs/object-v1 --extract
```

- `submit` 只提交一个阶段，不自动生成、绑定、动画连续扣费。`job.json` 保存请求、任务 ID、状态和可用的余额/消费信息。
- `wait` 返回码 **3** 表示任务仍进行中；下次继续 `wait`，不要重新生成。返回码 1 需检查错误。默认每 5 秒查询，避免高频轮询。
- 同一个 job 只能对应同一请求。改参考图、模型配置或提示词时用新版本目录；保留旧资产供比对/回退。
- POST 超时、连接中断、服务端错误或进程退出可能已产生任务。脚本事先记录不确定状态，拒绝自动重提。用 `usage` 和官方控制台核对后，`recover --job ... --task-id ...` 接回已存在的任务；无法确认时停止依赖该结果的收费操作，说明缺失信息。
- 模型下载链接可能过期；再次 `download` 会刷新任务结果，不会创建模型。CDN 下载使用独立连接，绝不携带 API Bearer 密钥。
- API 模型版本、可用动作、价格会变化。具体参数示例是有日期的工作基线；遇到字段错误先核对官方接口页，不把重试或切换版本当作无成本操作。未经验证不要承诺免费额度、免费后处理或固定耗时。

## 验收与交付

1. 对 GLB 运行 `python scripts/inspect_glb.py model.glb --out audit.json`，记录网格、骨骼、动画、贴图及外部资源。该工具只做结构检查，不验证外形相似度或权重变形。
2. 用户关注外形时，渲染真实网格的正、侧、背面，和参考图按同一显示高度比对。优先检查轮廓、比例、服装和标志部件，再看材质。没有渲染就明确写未完成视觉验收，不能把源图或服务缩略图冒充模型实测。
3. 可控角色还要在目标引擎检查待机、行走、完整跳跃、技能、手持物和碰撞。可绑定≠动画自然，动画存在≠已经是可玩的角色。
4. 交付模型文件、相对路径资产清单、实际完成的阶段、外形差异及验证结论。只在任务提供消费字段或账户变化可归因时报告成本；并行账户活动使余额差不能精确代表单任务消费。

来源、采纳内容和有意修正的上游假设见 [references/sources.md](references/sources.md)。离线自检：`python scripts/selftest.py`，不联网、不需要密钥、不产生 Tripo 费用。
