# 活软件参考宿主与在线演示

| 内容 | 位置 | 怎么跑 |
|---|---|---|
| 参考宿主（真实 `lp` 命令，写证据、看板、部署回执） | `server.py`、`static/`、`grow.sh` | `python3 examples/living_app/server.py`，打开 http://127.0.0.1:8765/ |
| 网站在线演示（浏览器内 SQLite） | `web/` → `docs/demo/index.html` | 改完 `web/`、`static/a2ui.js`、`surfaces/` 或 `ddl/` 后运行 `python3 examples/living_app/build_site.py` |
| 可选的模型通道 | `functions/api/agent.js`（仓库根目录） | 部署在 Cloudflare Pages，见下文 |

## 在线演示怎么回答问题

1. 先查固定页（已生长出来的固化结构）。
2. 再找预置的次抛展示面；问题被覆盖不到 60% 就不硬套。
3. 接入了模型时，交给模型：模型只输出展示面 JSON（查询 + 组件）。页面按 `web/surface-rules.js` 校验——与 `lp surface validate` 同一套规则，外加不允许递归查询、不读敏感字段——通过后才在浏览器的 SQLite 里执行，数字由数据库计算。
4. 都不行就如实说明。

## 接入模型（不绑定具体模型）

`functions/api/agent.js` 调用任何兼容 OpenAI Chat Completions 的接口。在 Cloudflare Pages 项目的 **Settings → Variables and Secrets** 里配置：

| 变量 | 说明 |
|---|---|
| `LP_MODEL_BASE_URL` | 接口地址，例如 `https://api.example.com/v1`（会请求 `<地址>/chat/completions`） |
| `LP_MODEL_NAME` | 模型名 |
| `LP_MODEL_API_KEY` | 密钥，设为 Secret；只在服务端使用，不会下发给页面 |
| `LP_MODEL_JSON_MODE` | 可选，设为 `1` 时请求 `response_format: json_object`（接口支持时再开） |
| `LP_RATE_PER_HOUR` / `LP_RATE_PER_DAY` | 可选，每个 IP 每小时、全站每天的次数上限，默认 20 / 300 |

另外在 **Settings → Bindings** 绑定一个 D1 数据库，变量名 `LP_LIMITS`，用于限流计数（函数会自动建表 `lp_rate`，每次请求用一条 upsert 原子加一，并发不会丢计数）。没有绑定、或计数存储出错时函数一律拒绝调用（公开页面不应该在没有限流的情况下暴露付费密钥）；只在私有环境临时测试时可以设 `LP_ALLOW_NO_RATE_LIMIT=1`。

限流是第一道闸；**花费的硬上限请同时在模型服务商那边设置**（每月预算或额度），两道一起才稳。

三项模型变量都配好后，页面侧栏会显示「模型：已接入」；缺任何一项都退回预置展示面。
