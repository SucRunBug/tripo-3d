---
name: tripo-assets
description: 使用 Tripo 官方接口生成模型、绑定动画并检查游戏资产交付；用于文字/参考图建模、细化、绑定、动画、下载和恢复已有任务。
---

# Tripo 3D 建模

把用户描述或参考图变成可检查、可下载、可用于目标项目的 3D 资产。基础工具只依赖 Python 3.10+ 标准库，直连 `https://openapi.tripo3d.ai`。仓库根目录是当前 `SKILL.md` 所在目录的上两级；所有 `scripts/` 命令从仓库根目录执行，或解析为绝对路径；工作文件放在用户项目，不能假设原电脑目录、游戏角色、前端框架或固定骨骼名。

## 开始

1. 运行 `python scripts/tripo.py doctor`。缺少凭据或连接失败时，仅加载 [连接 Tripo](../connect-tripo/SKILL.md)。
2. 从用户请求判断目标：静态道具、可动画角色、展示/AR、打印，或者已有模型细化。保留明确的风格、外形、输出格式和预算；只补充影响建模的缺失信息。用户已给参考图时优先使用参考图，不擅自换成文字猜测。
3. 读取 [references/api.md](../../references/api.md) 选择接口、准备请求 JSON。用 `submit --dry-run` 检查请求。实际调用前查余额，说明本轮对象、模型配置与提交阶段；用户已有的建模/绑定授权可继续使用，不额外设置批准关卡。制作 skill 或离线测试本身不需要创建收费模型。

## 按请求选择流程

| 用户要做的事 | 工作方式 |
| --- | --- |
| 文字做道具/角色 | text-to-model；角色使用全身、中性 A/T 姿势、四肢分离描述 |
| 照片或角色参考图转模型 | image-to-model；同一对象、同一姿态的多视角用 multiview-to-model |
| 外形更像、模型更精细 | 先定位轮廓、比例、几何或材质问题，按 [references/quality.md](../../references/quality.md) 比对，再决定重生成或局部修正 |
| 让角色走、跑、跳 | 外形检查 → rig-check → rig → retarget；遵守任务 ID 的依赖关系 |
| 修改贴图、不改形状 | models/texture 或项目中的局部材质调整；不要仅为粗糙度问题重做整个角色 |
| 导出网页/游戏/AR/打印资产 | 按目标选 GLB、FBX、USDZ、STL/3MF；生成成功并不等于可打印或已适配引擎 |
| 将已有本地模型交给 Tripo | 上传 → models/import → 所需处理步骤 |
| 积木/体素风格 | 查当前官方支持；上游 stylize 已标为弃用，不调用第三方旧代理来替代 |

不要默认全部做完：静态道具不绑骨，只要求模型时不自动搭建游戏。动画和游戏接入读取 [references/game-integration.md](../../references/game-integration.md)。

## 提交与恢复

从仓库根目录调用脚本，或使用解析后的绝对脚本路径；请求和 `--job` 放用户工作目录。

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

离线自检：`python scripts/selftest.py`，不联网、不需要密钥、不产生 Tripo 费用。
