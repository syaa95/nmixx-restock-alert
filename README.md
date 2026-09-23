# NMIXX 补货提醒

监控 [Strange Muse (Strange Ver.) Vinyl](https://nmixxshopus.com/products/strange-muse-strange-ver-vinyl)。云端任务每 5 分钟检查一次，每轮检查 12 次后自动启动下一轮；保留 GitHub 定时触发作为补充。任务交接可能有延迟，不能保证抢到库存。

## 配置

在 Settings → Secrets and variables → Actions 中添加 Repository secrets：

| 名称 | 内容 |
| --- | --- |
| `GMAIL_USER` | 发件 Gmail 地址 |
| `GMAIL_APP_PASSWORD` | Google 应用专用密码，不是登录密码 |
| `ALERT_TO` | 收件邮箱 |

应用专用密码要求 Google 账号启用两步验证，且并非所有账号都支持。仅在 Google 官方账号页面创建，直接粘贴到 GitHub Secrets，不要写入代码或聊天。

Actions → NMIXX restock alert → Run workflow：

- `bootstrap`：启动连续监控，完成一次检查后自动创建下一轮。
- `watch`：每 5 分钟检查，12 次后自动续跑。
- `inspect`：只验证库存接口，不发邮件，不更新状态。
- `test-email`：发送明确标记的测试邮件，不更新库存状态。
- `check`：正式检查。首次运行发送启用通知；首次已可购买则直接发送库存提醒。

定时任务使用 `watch`，连续模式内部使用 `check`。如果 Secrets 未配置，任务会失败，监控尚不可用。配置后手动运行 `bootstrap` 并确认邮件实际进入收件箱。

## 行为与维护

- 使用 Shopify 产品 JSON 中的布尔库存字段，校验目标商品及规格；接口故障不会当作售罄。
- 持续有货只通知一次；观察到再次售罄后补货会重新提醒。两次检查之间发生的短暂变化可能漏掉。
- 邮件服务器接受通知后保存库存状态。邮件发送与 Git 提交不是原子操作，极少数提交失败场景可能导致下一次重复提醒。
- `stock-state.json` 保存库存与最近成功检查日期，每天及状态变更时提交；不保存邮箱或凭据。
- 在 Actions 查看每次运行及摘要；建议启用 GitHub 自带的失败通知。长时间未收到邮件本身不能证明任务健康。
- 公开仓库定时任务在 60 天无活动后可能被 GitHub 停用；请定期检查 Actions，必要时重新启用。
- 停止：先 Actions → 工作流菜单 → Disable workflow，再取消所有运行中或排队的任务（Cancel workflow）。只禁用调度不会停止已运行的轮询。撤销邮件访问：删除 Google 应用专用密码。
- 商品页面注明仅限美国销售。提醒不保证能下单或配送到你的地址。

自动续跑通过当前仓库的临时 GITHUB_TOKEN（actions: write）调用 workflow_dispatch，不需要额外个人令牌。页面可能显示“Manually run by github-actions”，这是机器人自动触发，不是人工点击。并发限制确保最多一轮正在运行。

本项目仅依赖 Python 标准库。公开日志不打印邮箱或密码，不接受 pull_request 触发，不向第三方 Action 传递邮件 Secrets。

参考：[GitHub 定时任务](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)、[Shopify Product API](https://shopify.dev/docs/api/ajax/reference/product)、[Google 应用专用密码](https://support.google.com/accounts/answer/185833)。
