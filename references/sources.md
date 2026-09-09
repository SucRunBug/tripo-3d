# 来源与取舍

## 官方接口基准

- 文档入口：https://developers.tripo3d.ai/zh/docs
- 文字：https://developers.tripo3d.ai/zh/docs/generation-text-to-model/standard
- 单图：https://developers.tripo3d.ai/zh/docs/generation-image-to-model/standard
- 多视图：https://developers.tripo3d.ai/zh/docs/generation-multiview-to-model/standard
- 上传：https://developers.tripo3d.ai/zh/docs/files
- 检查/绑定/动画：同站 `animations-rig-check`、`animations-rig`、`animations-retarget`
- 贴图/转换/导入：同站 `models-texture`、`models-convert`、`models-import`

2026-09-09 检查了官方网页公开发布的接口说明和示例。主脚本中的 H3.1、多视图 front/back、biped 绑定与四个动作，另有该游戏项目 2026-09-08 的成功任务经验。没有为制作 skill 重新创建付费 Tripo 任务；离线测试和真实本地 GLB 检查不能代替未来账户上的 API 可用性验证。

## 参考项目

https://github.com/meterlong/tripo-skills

查看版本：`ce707a6af60e4ad7804aa1ca355cfeb1171837f4`，2026-09-09。该版本只有 `SKILL.md`，未发现许可证文件。本包以其流程思路为参考，重新编写说明和客户端，没有随包复制上游文件或代理实现。

| 上游内容 | 本 skill 的处理 |
| --- | --- |
| 把自然语言需求映射到生成/贴图/绑定/动画/转换 | 保留这种路由，按用户实际交付范围选步骤 |
| 为动画角色准备 A/T-pose | 保留；不强加到静态动态姿势雕塑 |
| 生成 → 检查 → 绑定 → 动画 | 保留，并用 source-job 校验父任务与 riggable |
| 根据打印、网页、AR 用途选格式 | 保留，补充外部资源和实际验收要求 |
| 轮询 task_id 后下载 | 加入可恢复状态、提交锁和不确定 POST 防重复提交 |
| 第三方 workers.dev 代理 | 不采用；只向官方 API 发送密钥 |
| “10 次免费”“后处理总是免费” | 不继承；费用按官方当前账户与任务结果确认 |
| 默认 v3.0 与固定生成秒数 | 不固化为最新/保证；采用已验证基线，并提示核对当前支持 |
| “只有人形可绑定” | 修正为按当前 rig-check 和官方版本支持，存在非人形类型 |
| LEGO/voxel stylize | 官方当前文档标为 deprecated，按需核对而非保证可用 |
| “production-ready” 的广泛承诺 | 用真实网格外形、蒙皮、性能和引擎测试来证明就绪程度 |

## 本项目经验的提炼

- 中性正背面参考优先于纯文字猜角色；动作图与建模视图分开。
- 小图可以指导比例，不能承诺原作微小纹理的精确恢复。
- 角色轮廓错误、PBR 材质过亮、蒙皮权重错误是不同问题，分别解决。
- 使用实际 GLB 正交渲染比对；游戏中的控制、跳跃、技能与碰撞需要独立验收。
- 动画资产可去重，但前提是骨架与节点映射一致，不能把特定模型的硬编码修正变成通用规则。
- 保留阶段文件和任务 ID；下载和恢复不重复生成；API 密钥不进入前端和迁移包。
