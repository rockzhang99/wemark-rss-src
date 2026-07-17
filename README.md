# WeMark-RSS（wemark-rss）

> 微信公众号文章抓取 · 下载 · 导出 · RSS 一站式解决方案

`wemark-rss` 是一个用于**订阅与管理微信公众号内容**的工具，能够自动抓取公众号文章、生成 RSS 订阅源，并提供完善的 Web 管理后台。

- 后端：Python 3.13 + FastAPI
- 前端：Vue 3 + Vite + Arco Design / Ant Design Vue
- 数据库：SQLite（默认）/ MySQL / PostgreSQL
- 部署：Docker / Docker Compose

---

## 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
  - [方式一：Docker 一键运行](#方式一docker-一键运行)
  - [方式二：源码运行（开发/调试）](#方式二源码运行开发调试)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [默认账号](#默认账号)
- [文档导航](#文档导航)
- [致谢与许可](#致谢与许可)

---

## 功能特性

- 微信公众号内容抓取与解析
- RSS 订阅源生成（支持全文 / 摘要、CDATA、分页、自定义标题/描述/封面）
- 用户友好的 Web 管理界面（13 种主题）
- 定时自动更新内容（可配置抓取间隔、最大页数）
- 多种数据库支持（默认 SQLite，可选 MySQL / PostgreSQL）
- 多种抓取方式 + 多种 RSS 客户端支持
- 授权过期提醒、自定义通知渠道（钉钉 / 企业微信 / 飞书 / 自定义 WebHook）
- 导出 `md / docx / pdf / json` 格式
- API 接口与 WebHook 调用（支持 Access Key 认证 `AK-SK`）
- HTML 内容过滤规则（全局规则 + 公众号专属规则，按 ID / Class / CSS 选择器 / 属性 / 正则过滤）
- 级联系统（Cascade）：父子节点架构，智能任务分发，横向扩展采集能力
- 环境异常统计、Headers / Cookies 认证、配置缓存（Redis / Memcached / 内存）

---

## 系统架构

项目采用前后端分离架构：

```
┌─────────────┐      HTTP/JSON       ┌──────────────────┐
│  Web 前端    │ ───────────────────▶ │  FastAPI 后端     │
│ (Vue3+Vite) │ ◀─────────────────── │  (main.py/web.py)│
└─────────────┘                      └──────────────────┘
                                            │
                              ┌─────────────┼──────────────┐
                              ▼             ▼              ▼
                         core/(抓取/调度)  apis/(接口)   driver/(微信/浏览器)
                              │
                              ▼
                        DB(SQLite/MySQL) + Redis(缓存) + data/(数据)
```

- 后端入口：`main.py` 启动 FastAPI（`web.py` 定义）
- 核心逻辑：`core/`，HTTP 接口：`apis/`，页面处理：`views/`，定时任务：`jobs/`，微信/浏览器驱动：`driver/`
- 前端源码：`web_ui/src/`，构建产物由 `static/` 提供
- 部署编排：`compose/`、`Dockerfiles/`

---

## 快速开始

### 方式一：Docker 一键运行

```bash
docker run -d \
  --name wemark-rss \
  -p 8001:8001 \
  -v ./data:/app/data \
  ghcr.io/wemark-rss/wemark-rss:latest
```

启动后访问 `http://<你的IP>:8001/` 即可进入管理界面。

> 镜像地址中的 `wemark-rss/wemark-rss` 为占位组织名，请替换为你自己的 GitHub Container Registry / Docker Hub 组织。详见 [INIT.md](./INIT.md)。

使用 Docker Compose（含 MySQL + Redis + 代理 sidecar）：

```bash
cd compose
cp ../.env.example ../.env   # 按需修改
docker compose -f docker-compose.yaml up -d
```

### 方式二：源码运行（开发/调试）

1. 安装后端依赖（Python ≥ 3.13.1）：

# 2. 建虚拟环境
python -m venv venv

# 3. 激活（PowerShell）
.\venv\Scripts\Activate.ps1

```bash
pip install -r requirements.txt
```

2. 准备配置：

```bash
cp config.example.yaml config.yaml
# Windows:  copy config.example.yaml config.yaml
```

3. 启动后端（首次运行加 `-init True` 初始化数据库与管理员）：

```bash
.\venv\Scripts\Activate.ps1
python main.py -job True -init True
```

4. 前端开发（Node ≥ 20.18.3）：

```bash
cd web_ui
npm install      # 或 yarn install
npm run dev      # 开发服务器 http://localhost:3000
npm run build    # 生产构建，产物写入 static/
```

访问 `http://<你的IP>:8001/` 使用后台；前端热更新走 `:3000`。

---

## 配置说明

所有配置集中在 `config.yaml`（由 `config.example.yaml` 复制而来），也可通过环境变量覆盖。常用项：

| 配置 / 环境变量 | 默认值 | 说明 |
|---|---|---|
| `APP_NAME` | `wemark-rss` | 应用名称 |
| `SERVER_NAME` | `wemark-rss` | 服务名称 |
| `WEB_NAME` | `WemarkRSS微信公众号订阅助手` | 前端显示名 |
| `DB` | `sqlite:///./data/db.db` | 数据库连接串 |
| `PORT` | `8001` | API 端口 |
| `SECRET_KEY` | `wemark-rss` | 密钥（生产务必修改） |
| `ENABLE_JOB` | `True` | 是否启用定时任务 |
| `SPAN_INTERVAL` | `10` | 定时任务间隔（秒） |
| `MAX_PAGE` | `5` | 最大抓取页数 |
| `THREADS` | `1` | 最大线程数 |
| `RSS_BASE_URL` | 空 | RSS 域名 |
| `RSS_FULL_CONTEXT` | `True` | 是否显示全文 |
| `RSS_PAGE_SIZE` | `30` | RSS 分页大小 |
| `TOKEN_EXPIRE_MINUTES` | `4320` | 登录会话时长（分钟） |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 缓存（可选） |
| `EXPORT_PDF` / `EXPORT_MARKDOWN` | `False` | 导出开关 |

完整变量表见 `config.example.yaml` 注释与 [INIT.md](./INIT.md)。

---

## 项目结构

```
wemark-rss/
├── main.py              # 后端启动入口
├── web.py               # FastAPI 应用定义
├── config.example.yaml  # 配置模板
├── requirements.txt     # Python 依赖
├── apis/                # HTTP 接口层
├── core/                # 核心逻辑（抓取、调度、通知、配置等）
├── views/               # 页面/模板处理
├── jobs/                # 定时任务
├── driver/              # 微信 / 浏览器驱动（Playwright/Selenium）
├── schemas/             # 数据模型
├── tools/ script/       # 工具脚本
├── migrations/          # 数据库迁移
├── web_ui/              # 前端源码（Vue3 + Vite）
├── static/              # 前端构建产物（由 web_ui 构建生成）
├── public/templates/    # 传统页面 HTML 模板
├── compose/ Dockerfiles/# 部署编排与镜像
├── docs/                # 补充文档
├── qtserver/            # MQTT 辅助服务（Node）
└── data/                # 运行时数据（git 忽略）
```

---

## 默认账号

首次以 `-init True` 启动后会初始化管理员：

- 账号：`admin`
- 密码：`admin@123`

请登录后立即修改密码。

---

## 文档导航

- [INIT.md](./INIT.md) —— 详细的初始化、配置、运行与部署指南（含 Docker / 源码 / 常见问题）
- [RULES.md](./RULES.md) —— 二次开发规范（目录约定、命名、配置、API、提交与重命名影响范围）
- [AGENTS.md](./AGENTS.md) —— 仓库协作与 Agent 工作指南
- [CONTRIBUTING.md](./CONTRIBUTING.md) —— 贡献指南
- [SECURITY.md](./SECURITY.md) —— 安全与配置注意事项
- `docs/` —— 各功能专项文档（AK 认证、级联系统、WebUI 快速上手等）

---

## 致谢与许可

本项目基于 [rachelos/we-mp-rss](https://github.com/rachelos/we-mp-rss) 重命名派生，原项目采用 MIT 许可。
感谢原作者的开源贡献以及所有贡献者（cyChaos、子健MeLift、晨阳 等）。

- 许可协议：**MIT**（见 [LICENSE](./LICENSE)）
- 原项目赞助与致谢信息保留于文档与 `docs/` 中。

> 注意：派生后已将全部 `we-mp-rss` 标识重命名为 `wemark-rss` / `WeMark-RSS`，但作者署名（如 `rachelos@qq.com`）与 `SAFE_LIC_KEY` 默认值 `RACHELOS` 等配置值予以保留，属正常署名与历史配置，不影响使用。
