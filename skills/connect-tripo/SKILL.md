---
name: connect-tripo
description: 配置 Tripo API 密钥并验证账户连接，排查凭据与网络问题；用户要求连接 Tripo、获取 API Key、换电脑或处理认证失败时使用。
---

# 连接 Tripo

仓库根目录为本文件所在目录的上两级。以下命令从根目录执行；给用户的命令应转换为带引号的脚本绝对路径。只配置 Tripo，不安装 Blender 或 Unity。

1. 检查 Python 3.10+，运行 `python3 scripts/tripo.py doctor`。Windows 可使用 `py -3`。
2. 已发现凭据时直接运行 `python3 scripts/tripo.py doctor --online`，不要要求重复配置或打印凭据。
3. 缺少凭据时，引导用户打开 [Tripo 开发者控制台](https://platform.tripo3d.ai)，进入 API Keys → Create Key，复制密钥；页面变化时核对[官方认证文档](https://developers.tripo3d.ai/en/docs/authentication)。
4. 让用户在自己的交互终端运行 `python3 scripts/tripo.py configure`。提示粘贴时不显示字符，按回车提交；不在聊天、命令参数或仓库保存密钥。
5. `configure` 返回 `configured: true` 后，运行 `doctor --online` 验证。报告实际连接结果，不用收费生成验证连接，也不将余额查询成功说成模型权限已验证。

`TRIPO_API_KEY` 优先于本机凭据文件。保存位置、401/403、代理错误、P2 权限及任务迁移仅在需要时读取 [认证与排错](references/authentication.md)。

用户还要求生成资产时，连接完成后读取 [资产制作](../tripo-assets/SKILL.md)；仅要求连接则到此结束。
