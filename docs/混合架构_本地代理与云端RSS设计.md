# 混合架构设计：本地代理（住宅 IP）+ 云端纯 RSS 服务

> 关联改动：改动 035（放弃云部署、改 PyInstaller 本地安装包）→ 改动 036（在 035 基础上改为「本地轻量代理 + 阿里云纯 RSS 服务端」混合架构，部署模式 A：多租户 SaaS）。
> 日期：2026-07-17

## 1. 目标与核心判断

- **只让「面向微信的那一段」跑在住宅 IP**，其余（存储、RSS 输出、通知）放阿里云数据中心 IP。
- 阿里云那台机器**永远不直接调微信接口** → 微信从来看不到这个数据中心 IP → 不会被封。这是本架构安全性的唯一前提，必须靠「云端构建不打包微信驱动代码」从物理上保证。
- 云端前端**只提供 RSS 服务**（XML/JSON/Atom），不提供订阅管理 UI；管理 UI 留在本地代理的 localhost。

## 2. 组件职责切分

### 2.1 本地代理 Agent（PyInstaller 打包，跑在客户住宅机）

| 职责 | 说明 |
|---|---|
| 微信授权 | 扫码授权、token/cookie 获取与刷新（仅本地，凭证**绝不**上传云端） |
| 文章抓取 | Playwright + `driver/` + `core/wx/` 抓文章与正文（仅本地） |
| 定时调度 | `jobs/mps.py` 本地 cron，按 owner 用本人授权抓取 |
| 管理 UI | 现有 Vue 前端跑在 localhost，客户本地配置订阅/标签/消息任务 |
| 上传器 Uploader | 抓取后把新文章 + Feed 元数据增量推送到云端（HTTPS + Agent AK） |
| 本地库 | SQLite 缓存/状态，作为上传前的本地真源 |

Agent 构建**包含** `driver/`、`core/wx/`、`web_ui/static`（管理 UI）、上传器；**不含**云端 RSS 路由（可选，Agent 也可本地顺带提供 RSS，但本设计以云端为唯一 RSS 出口）。

### 2.2 云端 Server（阿里云，数据中心 IP，纯 RSS 服务）

| 职责 | 说明 |
|---|---|
| 接收上传 | `POST /agent/articles`、`POST /agent/feeds`，用 Agent AK 鉴权并按租户落库 |
| 存储 | `Feed` + `Article` 表，多租户隔离（见第 4 节） |
| RSS 输出 | `/rss/...`、`/feed/...` 只读，按租户过滤，token 保护 |
| 健康检查 | `/healthz` 等运维端点 |
| **禁止事项** | 不 import `driver/`、`core/wx/`；不提供微信授权；不提供管理 UI |

云端构建**排除** `driver/`、`core/wx/`、`playwright`、`web_ui/static`（管理 UI），**不含** Chromium 下载逻辑 → 体积小、无微信调用能力。

## 3. Agent ↔ Cloud 通信协议

复用现有 AccessKey（AK/SK）机制（`core/auth.py` 的 `get_current_user_or_ak`），每个客户在云端拥有一个 AK，Agent 配置里持有该 AK 作为「上传凭证」。

### 3.1 上传 Feed（公众号目录）
`POST /api/v1/wx/agent/feeds`
```json
{ "feeds": [ { "id": "MP_WXS_xxx", "mp_name": "...", "mp_intro": "...", "mp_cover": "..." } ] }
```
云端 upsert `Feed`，并打上 `tenant_id`。

### 3.2 上传文章（批量，增量）
`POST /api/v1/wx/agent/articles`
```json
{ "mp_id": "MP_WXS_xxx",
  "articles": [ { "id": "...", "title": "...", "content": "...", "url": "...", "publish_time": 123456, ... } ] }
```
- 文章体直接复用 `Article.to_dict()` 的字段（`core/models/article.py`），云端用 `DB.add_article(article_data)` upsert（已带 `check_exist` 去重，按 `url` 或 `id`）。
- 云端在写入前**强制覆盖/补写 `tenant_id`**（取自 AK 对应的用户），防止 Agent 伪造跨租户数据。
- 增量策略：Agent 维护本地高水位（如 `max(publish_time)` 或 `is_uploaded` 标记），每次抓取后只上传新增/变更；云端幂等去重，重复上传无害。

### 3.3 鉴权与通道安全
- 请求头 `Authorization: AK-SK <ak>:<sk_sign>`（沿用现有中间件 `AKMiddleware`）。
- 必须 HTTPS；云端不开放 HTTP 明文上传。
- 云端从 AK 解析出 `owner`（租户），所有写入强制打 `tenant_id`。

## 4. 多租户隔离（模式 A 的关键工作）

现有 `articles`/`feeds` 表是全局的（无租户字段），RSS 端点 `apis/rss.py` 的 `get_current_user` 依赖已被注释掉、对外敞开。SaaS 必须补上隔离，复用改动 021 给 `tags`/`message_tasks` 加 `owner` 的范式：

1. `core/models/feed.py` 的 `Feed` 增加 `tenant_id`（String(255), 索引）。
2. `core/models/article.py` 的 `Article` 增加 `tenant_id`（String(255), 索引）。
3. `core/db.py` 增加 `ensure_tenant_columns()`，随 `Db.init()` 调用（`ALTER TABLE ... ADD COLUMN tenant_id`，历史数据回填为首个/默认租户）。
4. 上传接口写入时打 `tenant_id`。
5. `apis/rss.py` **重新启用** `get_current_user` 鉴权，所有查询追加 `filter(tenant_id == current_user_tenant)`，RSS token 与租户绑定，杜绝跨客户泄漏。
6. 云端管理 UI 不存在，所以租户隔离只需在「上传写入」与「RSS 读取」两处保证；管理侧的订阅/标签隔离由本地 Agent 各自负责。

> 简化备选：若不想动 `Feed`/`Article` 模型，可采用「DB-per-tenant」（云端按 AK 路由到独立 SQLite/Shema）。但统一加 `tenant_id` 与现有 `owner` 范式一致、改动最小，推荐首选。

## 5. 「立即刷新」与调度如何不污染云端

- 客户在本地管理 UI 点「刷新」→ 本地 Agent 直接用本地微信驱动抓取 → 抓完上传云端。**云端全程不参与微信调用**，符合「数据中心 IP 安全」前提。
- 定时任务只在 Agent 本地跑（`jobs/mps.py` 按 owner 取本地授权），云端无 scheduler。

## 6. 部署与构建变更

- `config.yaml` 新增：
  - `deploy.role: agent | cloud`（单进程双形态，或拆两个入口）。
  - Agent 侧：`upload.enabled: true`、`upload.server: https://your-cloud.com`、`upload.ak`/`upload.sk`。
  - Cloud 侧：`wechat.enabled: false`、`rss` 正常、`db` 指向共享多租户库。
- 构建脚本（在 改动 035 的 `build/` 基础上拆两份）：
  - `build/pyinstaller_agent.spec`：含 `driver/`、`core/wx/`、管理 UI、上传器、Chromium 外置下载（即现有 spec 基本不变）。
  - `build/pyinstaller_cloud.spec`（或云端直接 `python main.py` + Docker，无需 PyInstaller）：**exclude** `driver`、`core.wx`、`playwright`、`selenium`、`psycopg2`、`pymysql`、`web_ui/static` 管理 UI；仅保留 RSS/Feed 路由 + 上传 API + DB。
- **运行时守卫**：云端启动时若检测到 `driver` 被 import，立即 `raise` 并退出，作为第二道防线，确保云端永不具微信调用能力。

## 7. 风险与注意点

- **多租户隔离是最大工作量**：必须同时锁死「上传写入打 tenant_id」与「RSS 读取按 tenant_id 过滤」，任一边漏了都会跨客户泄漏。
- **内容图片不走云端**：文章 `content` 里的图片是 `mmbiz.qpic.cn` 等微信 CDN 直链，RSS 阅读器直接拉微信 CDN，云端 IP 不接触微信，安全。
- **Agent 离线 = RSS 停滞**：文章实时性依赖 Agent 在线抓取并上传；Agent 关机期间 RSS 不更新（与纯本地方案一致）。
- **带宽**：上传整篇 HTML 正文，单篇几十 KB~几百 KB，正常公众号量级可接受；可按需只上传 `description` 摘要、正文按需拉取以省带宽（后续优化）。
- **RSS token 必须租户绑定**：现有 `apis/rss.py` 鉴权被注释，上线前务必恢复并按 tenant 过滤，否则等于公开全库。

## 8. 落地顺序（建议分阶段）

1. **阶段 1（协议 + 云端骨架）**：云端加 `tenant_id` 列、上传 API、RSS 按租户过滤、`deploy.role=cloud` 开关、运行时守卫。先用 curl 模拟 Agent 上传验证。
2. **阶段 2（Agent 上传器）**：Agent 抓取后增量上传；本地高水位去重；配置 `upload.*`。
3. **阶段 3（构建拆分）**：`pyinstaller_cloud.spec` / Docker；确认云端镜像不含微信驱动、无 Chromium 下载。
4. **阶段 4（联调 + 安全复核）**：多租户隔离压测、HTTPS、AK 轮换、RSS token 租户绑定复核。

> 本文件为设计文档，尚未改动业务代码。按阶段 1 起可开始落地。
