# 官方 API 与可执行请求

核对日期：2026-09-09。官方文档：https://developers.tripo3d.ai/zh/docs 。基地址 `https://openapi.tripo3d.ai`；身份验证只用于该 origin 的 API。不要混用第三方 `/api/generate`、旧 `/v2/openapi/task` 的 `type` schema 和这里的 v3 schema。

脚本请求文件只有 `endpoint` 和 `payload`。下面每段 JSON 保存为自己的请求文件，再调用 `submit --request ... --job ...`。路径由 Agent 根据当前 workspace 解析，示例名称不是已有文件。

## 读取与上传

```bash
python scripts/tripo.py balance
python scripts/tripo.py usage
python scripts/tripo.py upload --file ./front.png --record ./uploads/front.json
python scripts/tripo.py status --task-id TASK_ID
```

上传使用官方 `POST /v3/files` multipart 字段 `file`，返回 `file_token`。单图 `input` 和多视图每个 view 的值使用返回的 token，不是上传记录文件路径。脚本按 SHA-256 复用上传；更换图片须换记录文件。旧 token 失效时用新的上传记录重新上传，不能把不同图片拼入一个已有模型任务。

辅助脚本接收 PNG/JPEG ≤20 MiB、模型 ≤60 MiB。官方 multipart 模型上限当前为 150 MB；大文件建议 `POST /v3/files/presign` → 对返回的预签名 URL 执行 PUT → 使用 `file_token`。PUT 不带 API Authorization。这个大文件流程没有内置在脚本中，按官方 files-presign 页执行；不要降低 TLS 校验来绕过网络问题。

## 文字生成

```json
{
  "endpoint": "/v3/generation/text-to-model",
  "payload": {
    "prompt": "One full-body handmade wooden explorer doll, neutral A-pose, arms away from torso, feet fully visible. Blue wool jacket, brown cloth trousers, matte carved wood face. One character, no weapon, no pedestal, no environment.",
    "model": "v3.1-20260211",
    "face_limit": 30000,
    "texture": true,
    "pbr": true,
    "texture_quality": "detailed"
  }
}
```

提示词上限按本项目使用的 1024 字符保守检查。描述只补充用户未明确的建模细节；用户要复杂动态姿势的雕塑时，不应强行改成游戏角色 A-pose。

## 单图、多图

单图字段是 `input`：

```json
{
  "endpoint": "/v3/generation/image-to-model",
  "payload": {"input": "FILE_TOKEN", "model": "v3.1-20260211", "face_limit": 30000, "texture": true, "pbr": true, "texture_quality": "detailed"}
}
```

多图推荐显式 view-key，不把一张拼图当四个角度：

```json
{
  "endpoint": "/v3/generation/multiview-to-model",
  "payload": {
    "inputs": [{"front": "FRONT_FILE_TOKEN"}, {"back": "BACK_FILE_TOKEN"}],
    "model": "v3.1-20260211",
    "face_limit": 80000,
    "geometry_quality": "detailed",
    "texture": true,
    "pbr": true,
    "texture_quality": "detailed"
  }
}
```

可加 `left`、`right`；使用主体自身的左右视图，检查照片实际方向，不靠文件排序猜测。只有一张好图时走单图即可。也可按需求额外生成 image-to-multiview，再用 `inputs:[{"task_id":"MULTIVIEW_TASK_ID"}]`，但生成的侧背面是推断，不是用户提供的真实证据，会新增任务费用。

`v3.1-20260211` 是本项目验证过的 H 系列基线，不承诺永远最新。官方还列出 P1/P2 系列，侧重低面数/拓扑；它们的面数范围、geometry_quality、quad 等支持与 H 系列不同。换模型先核对参数页，不直接把 H 系列 payload 套过去。80000 面是精细角色示例，不是所有设备或道具的默认要求。

## 绑定与动画依赖

每一步提交后 `wait` 到 success。假设原模型任务 ID 为 `MODEL_TASK_ID`。

rig-check.json：

```json
{"endpoint":"/v3/animations/rig-check","payload":{"input":"MODEL_TASK_ID"}}
```

检查 job 的 `result.output.riggable === true` 和推荐 `rig_type`。检查本身也是异步任务，不把创建响应当检查结果。输出没有模型可下载是正常现象。

rig.json（以下适用于双足人形）：

```json
{"endpoint":"/v3/animations/rig","payload":{"input":"MODEL_TASK_ID","model":"v1.0-20240301","rig_type":"biped","spec":"tripo","out_format":"glb"}}
```

```bash
python scripts/tripo.py submit --request rig.json --job jobs/rig --source-job jobs/rig-check
python scripts/tripo.py wait --job jobs/rig
```

`rig.input` 仍是模型任务 ID，不能用检查任务 ID。Unity/Unreal 工作流可按实际导入器选择 `spec:mixamo`；非人形按 rig-check 和当前官方版本支持选择，不能套用双足骨架。

animations.json：

```json
{
  "endpoint":"/v3/animations/retarget",
  "payload": {
    "input":"RIG_TASK_ID",
    "animations":["preset:biped:idle","preset:biped:walk","preset:biped:run","preset:biped:jump"],
    "out_format":"glb",
    "bake_animation":true,
    "export_with_geometry":true,
    "animate_in_place":true
  }
}
```

```bash
python scripts/tripo.py submit --request animations.json --job jobs/animations --source-job jobs/rig
python scripts/tripo.py wait --job jobs/animations
python scripts/tripo.py download --job jobs/animations --extract
```

`retarget.input` 必须是成功的绑定任务 ID。这里的 biped 预设来自本项目实际成功调用；官方也展示 `preset:idle`/`preset:walk` 等别名，使用其他骨架或动作前查询当前预设清单。`animation` 与 `animations` 互斥。检查返回文件实际包含哪些 clips，不能因为任务 success 就假定所有动作都生成了。

## 修改、导入、转换

```json
{"endpoint":"/v3/models/texture","payload":{"input":"MODEL_TASK_ID","texture_quality":"detailed","texture_prompt":{"text":"matte knitted fabric, visible woven fibres, preserve the existing color layout"}}}
```

```json
{"endpoint":"/v3/models/import","payload":{"input":"UPLOADED_MODEL_FILE_TOKEN"}}
```

```json
{"endpoint":"/v3/models/convert","payload":{"input":"MODEL_OR_RIG_TASK_ID","format":"FBX","texture_size":2048,"with_animation":true}}
```

导出格式按官方枚举选择，如 `GLTF`、`FBX`、`OBJ`、`STL`、`USDZ`、`3MF`。GLB 是网页常用交付；`GLTF` 转换可能返回 `.gltf`、`.glb` 或资源包，按实际文件判断，不只改后缀。`mesh/decimate` 在脚本 allowlist 中，但参数应查当前官方页面后构造；不要把装饰性细化自动转成减面。

## 状态、成本、下载

- 查询：`GET /v3/tasks/{task_id}`。读取 `data.status`、`progress`、`output`、`credits_consumed`，字段不存在时标为未知。
- `wait` 默认最多约 45 秒查询窗口，超时保存状态、退出 3；网络请求还有独立超时。Agent 用可让出控制的命令执行，并继续报告有意义进展。
- 收费 POST 不自动重试。收到 5xx、408、连接中断或异常成功响应后，该 job 保持 unknown。`usage` 与控制台确认匹配对象/时间/参数后，`recover --job jobs/model --task-id EXISTING_ID`；recover 是用户/Agent 完成核对后的手动关联，并不自动证明任务归属语义一致。
- 已有失败任务不自动换目录重做。判断失败原因，调整具体输入，在原有授权/预算内重试；授权或必要信息缺失时再询问。
- 下载刷新结果中的签名 URL，保存原始文件及 `assets.json` 的相对路径、字节数、SHA-256。ZIP 校验路径再解包。重复解包遇到已有目录会停下，避免覆盖人工修改的资产；原始文件下载与解包目录不要混作工作副本。
- `.gltf/.obj` 等若引用外部贴图或 buffer，需从完整 ZIP/关联资源中一起交付。检查缺失资源；单个主文件不一定自包含。
- 账户 `balance`/`frozen` 与任务 credits 的单位按当前官方文档。并发消费/冻结会影响余额，不能直接把余额差宣称为单模型准确费用。
