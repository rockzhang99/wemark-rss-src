# 初始化与运行指南（INIT）

本文档说明如何初始化、配置、运行与部署 `wemark-rss`。适用于首次搭建与日常开发调试。

---

## 1. 环境要求

| 组件 | 版本要求 | 说明 |
|---|---|---|
| Python | ≥ 3.13.1 | 后端运行环境 |
| Node.js | ≥ 20.18.3 | 前端构建（npm / yarn） |
| Redis | 可选 | 配置/Token 缓存，提升性能 |
| MySQL / PostgreSQL | 可选 | 生产环境数据库（默认 SQLite） |
| Docker | 可选 | 容器化部署 |
| Git | 任意 | 版本管理 |

---

## 2. 获取代码

```bash
git clone https://github.com/wemark-rss/wemark-rss.git
cd wemark-rss
```

> 将 `wemark-rss/wemark-rss` 替换为你自己的仓库地址。

---

## 3. 后端初始化

### 3.1 安装依赖

```bash
pip install -r requirements.txt
```

依赖包含 FastAPI、uvicorn、SQLAlchemy、Playwright、Selenium、PyJWT、python-docx、reportlab、pymupdf 等。

> 若使用 Playwright，首次需安装浏览器内核：
> ```bash
> playwright install
> ```

### 3.2 准备配置文件

```bash
cp config.example.yaml config.yaml      # Linux / macOS
copy config.example.yaml config.yaml    # Windows
```

关键配置项（详见文件内注释）：

- `app_name` / `server.name`：应用与服务名（默认 `wemark-rss`）
- `db`：数据库连接串，默认 `sqlite:///./data/db.db`
- `redis.url`：缓存地址（留空则不启用 Redis）
- `port`：服务端口（默认 `8001`）
- `secret_key`：密钥，**生产环境务必修改为强随机值**
- `threads`：工作线程数（不建议超过 4）
- `enable_job`：是否启用定时任务
- `span_interval`：定时任务间隔（秒）

### 3.3 初始化并启动

首次运行需加 `-init True` 初始化数据库与管理员账号：

```bash
python main.py -job True -init True
```

- `-job True`：启动定时调度
- `-init True`：执行数据库初始化（建表、创建默认管理员）

启动成功后访问 `http://<你的IP>:8001/`。

默认管理员账号：`admin` / `admin@123`，请登录后立即修改密码。

---

## 4. 前端开发

前端源码位于 `web_ui/`：

```bash
cd web_ui
npm install        # 或 yarn install
npm run dev        # 开发模式，默认 http://localhost:3000
npm run build      # 生产构建，产物输出到 ../static/
npm run preview    # 预览构建产物
```

开发时修改 `web_ui/src/` 下的 Vue 组件即可热更新；生产部署需先 `npm run build`，后端会从 `static/` 提供页面。

> 若你修改了前端并重新构建，无需改动后端代码，重启服务即可生效。

---

## 5. Docker / Compose 部署

### 5.1 单容器（最简）

```bash
docker run -d \
  --name wemark-rss \
  -p 8001:8001 \
  -v ./data:/app/data \
  ghcr.io/wemark-rss/wemark-rss:latest
```

数据持久化在宿主 `./data` 目录。

### 5.2 完整编排（MySQL + Redis + 代理）

`compose/docker-compose.yaml` 提供包含 MySQL、Redis、sing-box 代理 sidecar 的完整栈：

```bash
cd compose
cp ../.env.example ../.env     # 按需填写环境变量
docker compose -f docker-compose.yaml up -d
```

- 服务容器名：`wemark-rss`，端口 `8001`
- 数据库名：`we_mp_rss`（历史命名，保持兼容）
- 通过 `/.env` 注入 `DB`、`REDIS_URL`、`PROXY_HTTP_URL` 等

其他编排文件：

- `compose/docker-compose.dev.yaml`：开发用（读取 `/.env`，便于本地调试）
- `compose/docker-compose-sqlite.yaml`：仅 SQLite，轻量部署

### 5.3 构建自有镜像

镜像名中的 `wemark-rss/wemark-rss` 为占位组织名。请改为你自己的 registry：

```bash
docker build -t your-org/wemark-rss:latest -f Dockerfile .
```

---

## 6. 环境变量速查

除 `config.yaml` 外，几乎所有配置均可用环境变量覆盖（变量名见 `config.example.yaml` 与 README 表格）。常用：

| 变量 | 作用 |
|---|---|
| `DB` | 数据库连接串 |
| `REDIS_URL` | Redis 地址 |
| `PORT` | 服务端口 |
| `SECRET_KEY` | 密钥 |
| `ENABLE_JOB` | 启用定时任务 |
| `SPAN_INTERVAL` | 定时间隔（秒） |
| `MAX_PAGE` | 最大抓取页数 |
| `RSS_BASE_URL` | RSS 域名 |
| `PROXY_HTTP_URL` | 代理地址（微信封 IP 场景） |

---

## 7. 常见问题（FAQ）

**Q：微信访问被封 / 抓取失败？**
A：数据中心 IP 常被微信限制。建议在 `compose` 中使用 `singbox` sidecar，仅在 `/.env` 配置单一 `PROXY_URL=` 入口，不要在多个文件中重复配置代理。

**Q：如何修改数据库？**
A：修改 `config.yaml` 的 `db`，或用环境变量 `DB` 覆盖。示例：
- SQLite：`sqlite:///./data/db.db`
- MySQL：`mysql+pymysql://user:pass@host/db?charset=utf8mb4`
- PostgreSQL：`postgresql://user:pass@host/db`

**Q：如何启用钉钉 / 飞书 / 企业微信通知？**
A：在 `config.yaml` 填写 `notice.dingding` / `notice.feishu` / `notice.wechat`，或用对应 `WEBHOOK` 环境变量。

**Q：默认账号密码是多少？**
A：管理员 `admin` / `admin@123`，首次启动后请修改。

**Q：定时任务不生效？**
A：确认 `ENABLE_JOB=True`，并在 UI「消息任务」中添加定时任务；间隔由 `SPAN_INTERVAL` 控制。

**Q：前端改了但页面没变？**
A：前端需 `npm run build` 后由后端 `static/` 提供；开发态可用 `npm run dev` 走 `:3000` 热更新。

**Q：如何开启 PDF / Markdown 导出？**
A：将 `EXPORT_PDF` / `EXPORT_MARKDOWN` 设为 `True`，并配置导出目录（默认 `./data/pdf`、`./data/markdown`）。

---

## 8. 目录与数据

- `data/`：运行时数据（数据库、缓存、导出文件、上传），**已被 `.gitignore` 忽略，请勿提交**
- `config.yaml` / `.env`：本地真实配置，**请勿提交**
- 安全细节参见 [SECURITY.md](./SECURITY.md)
