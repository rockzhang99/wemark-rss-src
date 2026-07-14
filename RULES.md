# 二次开发规范（RULES）

本文件约定 `wemark-rss` 二次开发时的目录、命名、配置、API、提交与重命名影响范围，确保协作一致、可维护。

---

## 1. 重命名影响范围（重要）

本项目由 `we-mp-rss` 派生并重命名为 `wemark-rss`。二次开发时请注意：

- **项目标识**：`we-mp-rss` 已全部替换为 `wemark-rss`；`We-MP-RSS` 替换为 `WeMark-RSS`；镜像/仓库路径 `rachelos/we-mp-rss` 替换为 `wemark-rss/wemark-rss`（占位组织名，部署前请改为你自己的组织）。
- **保留项（不要随意改动）**：
  - 作者署名邮箱 `rachelos@qq.com`（致谢/打赏联系）
  - 配置项 `SAFE_LIC_KEY` 默认值 `RACHELOS`（授权加密 KEY，属历史配置值）
  - 数据库名 `we_mp_rss`（Compose 中 MySQL 库名，保持兼容，非项目标识）
- **新增代码/配置时**：统一使用 `wemark-rss` / `WeMark` 命名，不要再引入 `we-mp-rss`。

---

## 2. 目录与模块约定

| 目录 | 职责 |
|---|---|
| `main.py` / `web.py` | 启动入口 / FastAPI 应用 |
| `core/` | 核心逻辑（抓取、调度、通知、配置、缓存等），按功能分子目录（如 `core/notice/`、`core/lax/`） |
| `apis/` | HTTP 接口层（仅供接口，不含页面） |
| `views/` | 页面 / 模板处理 |
| `jobs/` | 定时任务 |
| `driver/` | 微信 / 浏览器驱动（Playwright / Selenium） |
| `schemas/` | 数据模型 / 校验 |
| `tools/` `script/` | 工具与运维脚本 |
| `migrations/` | 数据库迁移 |
| `web_ui/src/` | 前端源码（Vue3） |
| `static/` | 前端构建产物（由 `web_ui` 构建生成，**不要手改**） |
| `public/templates/` | 传统页面 HTML 模板 |
| `compose/` `Dockerfiles/` | 部署编排与镜像 |
| `docs/` | 补充文档 |
| `qtserver/` | MQTT 辅助服务（Node） |

> 新增文档放 `docs/`，新增工具脚本放 `tools/` 或 `script/`。

---

## 3. 命名规范

- **Python**：4 空格缩进；模块 / 函数用 `snake_case`；类用 `PascalCase`。
- **前端（Vue）**：视图组件用 `PascalCase` 文件名（如 `AccessKeyManagement.vue`）；组合式函数 / API 封装用 `camelCase` 或小写（如 `auth.ts`、`messageTask.ts`）。
- **避免大规模重构**：仓库无强制格式化配置，保持与周边代码风格一致；整理 import、避免宽泛重构。
- **配置项命名**：新增配置使用 `snake_case`，并在 `config.example.yaml` 中补充注释与环境变量映射。

---

## 4. 配置与密钥

- 禁止提交 `config.yaml`、`.env`、Token、Cookie、`data/` 下数据。
- 所有机密从 `config.example.yaml` 与 `.env.example` 起步，真实密钥仅存于本地配置。
- 修改鉴权、WebHook、Access Key 流程前，先阅读 `SECURITY.md`。
- 生产环境务必修改 `SECRET_KEY` 等默认值。

---

## 5. API 规范

- 接口集中在 `apis/`，路由前缀一般为 `/api/`。
- 支持 Access Key 认证：`Authorization: AK-SK {access_key}:{secret_key}`。
- 新增接口请补充到对应 `apis/` 模块，并在 `docs/` 或 README 中记录。
- 保持向后兼容；破坏性变更需在 PR 中说明并附迁移说明。

---

## 6. 测试与本地验证

- 后端测试较少，多贴近代码（如 `core/lax/test_template_parser.py`），运行：
  ```bash
  cd core/lax && python -m unittest test_template_parser.py
  ```
- 改动 API / 抓取 / 调度代码后，至少启动 `python main.py` 做一次冒烟测试，验证受影响 UI 或接口。
- 前端改动至少通过 `npm run build`。

---

## 7. 提交与分支规范

- 采用 Angular 风格提交，例如：
  - `feat: 新增 RSS 分页大小配置`
  - `fix: 处理过期的微信 Cookie`
  - `docs: 补充 INIT 部署说明`
- Commit body 用 `-` 开头的行，避免空行。
- 每个提交保持逻辑单一；适当添加注释提升可读性。
- 开新功能前创建独立工作分支（如 `feature/xxx`、`fix/xxx`）。
- 推送 / 提 PR 前，先 `fetch` 上游并合并最新 `main`，解决冲突后再提交。
- PR 需包含：问题简述、关键改动、相关 Issue、配置 / 迁移说明、UI 改动截图。

---

## 8. 部署约定

- 开发用 Compose 读取 `/.env`：`docker compose -f compose/docker-compose.dev.yaml up -d --force-recreate`。
- 不要在 compose 文件中硬编码凭据或代理；代理统一通过 `/.env` 的单个 `PROXY_URL=` 入口。
- 微信封数据中心 IP 时，优先使用 `singbox` sidecar。
- 构建镜像前将 `wemark-rss/wemark-rss` 改为你自己的 registry 组织名。

---

## 9. 安全红线

- 不提交密钥、Cookie、用户数据。
- 修改鉴权 / WebHook / Access Key 前阅读 `SECURITY.md`。
- 对外暴露服务时启用强 `SECRET_KEY`，限制通知 WebHook 权限。
