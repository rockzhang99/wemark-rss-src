import sys
import asyncio

# Windows 需要使用 ProactorEventLoop 以支持 Playwright 子进程
# 必须在任何事件循环创建之前设置
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.openapi.models import OAuthFlowPassword
from fastapi.openapi.utils import get_openapi
import apis
import os
from core.config import cfg,VERSION,API_BASE

# 混合架构(改动036)：云端模式(deploy.role=cloud)不导入任何微信驱动相关路由/视图，
# 从物理上保证云端进程永远不会调用微信接口（数据中心 IP 安全）。
CLOUD = cfg.get("deploy.role", "agent") == "cloud"

# 与微信无关、云端/本地都需要的路由（核心管理功能）
from apis.user import router as user_router
from apis.res import router as res_router
from apis.agent import router as agent_router
# 认证路由已解耦 driver（微信扫码接口内惰性导入），云端也需导入用于登录/AK 管理
from apis.auth import router as auth_router
# 云端保留的管理路由：配置信息
from apis.config_management import router as config_router

# 仅本地 Agent 模式需要的路由（RSS/订阅/标签/工具/任务/级联/过滤/代理等，云端不需要）
from apis.rss import router as rss_router, feed_router
from apis.message_task import router as task_router
from apis.tags import router as tags_router
from apis.tools import router as tools_router
from apis.github_update import router as github_router
from apis.cascade import router as cascade_router
from apis.filter_rule import router as filter_rule_router
from apis.task_queue import router as task_queue_router
from apis.proxy import router as proxy_router

# views_router(含 /views/home 与解耦后的 mps/tags/articles) 云端与本地都需要(改动049),
# 无条件导入; 其余微信驱动相关路由仅本地 Agent 模式导入(云端排除, 避免 import driver)。
from views import router as views_router
if not CLOUD:
    from apis.article import router as article_router
    from apis.mps import router as wx_router
    from apis.sys_info import router as sys_info_router
    from apis.export import router as export_router
    from apis.env_exception import router as env_exception_router

# 云端公开首页（无需认证，游客可访问）
# 直接加载 views/home.py 模块文件，绕过 views/__init__.py（它会 import articles/tags/mps 等依赖 driver 的子模块）。
# views/home 的依赖 views.base 已解耦 driver（惰性导入），云端安全。
# 用 try/except 容错：即使 views/home.py 因部署裁剪缺失，后端也不应崩溃重启。
import importlib.util, os, logging
home_view_router = None
_home_path = os.path.join(os.path.dirname(__file__), "views", "home.py")
if os.path.exists(_home_path):
    try:
        _home_spec = importlib.util.spec_from_file_location("views.home", _home_path)
        _home_mod = importlib.util.module_from_spec(_home_spec)
        _home_spec.loader.exec_module(_home_mod)
        # 用 /views 前缀包装，保持与本地模式一致的 URL 路径 /views/home
        home_view_router = APIRouter(prefix="/views")
        home_view_router.include_router(_home_mod.router)
    except Exception as _home_err:
        logging.getLogger("uvicorn.error").warning(
            "公开首页 views/home 加载失败，已跳过（不影响其他功能）：%s", _home_err
        )
else:
    logging.getLogger("uvicorn.error").warning(
        "views/home.py 不存在，公开首页未启用（云端 cloud_strip 未保留该文件时属正常）"
    )
from starlette.middleware.base import BaseHTTPMiddleware

class AKMiddleware(BaseHTTPMiddleware):
    """Access Key 认证中间件"""
    async def dispatch(self, request: Request, call_next):
        # 提取 Authorization 头
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("AK-SK "):
            # 将AK/SK认证信息存储在 request state 中供后续使用
            request.state.ak_auth = auth_header
        response = await call_next(request)
        return response

app = FastAPI(
    title="WemarkRSS API",
    description="微信公众号RSS生成服务API文档",
    version="1.0.0",
    docs_url="/api/docs",  # 指定文档路径
    redoc_url="/api/redoc",  # 指定Redoc路径
    # 指定OpenAPI schema路径
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {
            "name": "认证",
            "description": "用户认证相关接口",
        }
    ],
    swagger_ui_parameters={
        "persistAuthorization": True,
        "withCredentials": True,
    }
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AK认证中间件
app.add_middleware(AKMiddleware)

@app.middleware("http")
async def add_custom_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Version"] = VERSION
    response.headers["X-Powered-By"] = "YoruAki"
    response.headers["GITHUB"] = "https://github.com/wemark-rss/wemark-rss"
    response.headers["Server"] = cfg.get("app_name", "WemarkRSS")
    return response
# 创建API路由分组
api_router = APIRouter(prefix=f"{API_BASE}")

# 部署模式接口（前端据此过滤菜单：云端只显示 AK/用户管理/配置信息）
@api_router.get("/deploy-info")
def get_deploy_info():
    """返回当前部署模式，前端据此决定显示哪些菜单项"""
    return {"role": "cloud" if CLOUD else "agent"}

# ===== 云端核心路由（始终注册）=====
# 用户管理、配置信息、Agent 上传接口(写库)、认证/AK 管理、公开首页(展示数据库)
api_router.include_router(user_router)
api_router.include_router(config_router)
api_router.include_router(agent_router)
api_router.include_router(auth_router)

# ===== 仅本地 Agent 模式的路由（云端排除）=====
if not CLOUD:
    # RSS/订阅/标签/工具/任务/级联/过滤/代理/异常统计等 Agent 本地功能
    api_router.include_router(task_router)
    api_router.include_router(tags_router)
    api_router.include_router(tools_router)
    api_router.include_router(github_router)
    api_router.include_router(cascade_router)
    api_router.include_router(filter_rule_router)
    api_router.include_router(task_queue_router)
    api_router.include_router(proxy_router)
    api_router.include_router(env_exception_router)
    # 微信驱动相关路由
    api_router.include_router(article_router)
    api_router.include_router(wx_router)
    api_router.include_router(sys_info_router)
    api_router.include_router(export_router)

resource_router = APIRouter(prefix="/static")
resource_router.include_router(res_router)

# RSS/Feed 路由：云端(对外提供订阅)与本地 Agent 都需要，故始终注册。
# 云端鉴权由 apis/rss.py 的 _rss_tenant_dep 负责(解析 AK-SK/Bearer, 按租户过滤)；
# 这些接口只读数据库、不触发云端抓取(云端无 driver)，在云端注册安全。
feeds_router = APIRouter()
feeds_router.include_router(rss_router)
feeds_router.include_router(feed_router)

# 注册路由分组
app.include_router(api_router)
app.include_router(resource_router)
app.include_router(feeds_router)
# /views/home 与 /views/mps|tags|articles 由 views_router 统一注册(改动049: 云端也注册)
app.include_router(views_router)

# 公开首页（无需认证，游客可访问）。
# 改动049: 云端现已解耦 driver 并保留 views/mps|tags|articles 模块,
# /views/home 与 /views/mps|tags|articles 均由上方无条件注册的 views_router 提供,
# 不再单独注册 home_view_router(避免 /views/home 重复路由)。下方 home_view_router 的
# importlib 加载逻辑保留作兜底, 但此处不再注册。

# 静态文件服务配置
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
app.mount("/static", StaticFiles(directory="static"), name="static")
from core.res.avatar import files_dir
app.mount("/files", StaticFiles(directory=files_dir), name="files")
# app.mount("/docs", StaticFiles(directory="./data/docs"), name="docs")
@app.get("/{path:path}",tags=['默认'],include_in_schema=False)
async def serve_vue_app(request: Request, path: str):
    """处理Vue应用路由"""
    # 排除API和静态文件路由
    if path.startswith(('api', 'assets', 'static')) or path in ['favicon.ico','vite.svg','logo.svg']:
        return None

    # 若 static/ 下存在该路径对应的真实文件(如 操作说明.html、images/*、favicon 等),
    # 直接作为静态文件返回, 不再回退到 SPA 入口(否则会返回空白的 Vue 壳, 改动045修复)
    _static_file = os.path.normpath(os.path.join("static", path))
    _static_root = os.path.abspath("static")
    if os.path.isfile(_static_file) and os.path.abspath(_static_file).startswith(_static_root + os.sep):
        return FileResponse(_static_file)

    # 返回Vue入口文件，并注入部署模式全局变量（前端同步读取，避免被 Vite code-splitting 打散）
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        # 在 <body> 或 <div id="app"> 前注入 window.__DEPLOY_ROLE__
        inject_script = f'<script>window.__DEPLOY_ROLE__="{ "cloud" if CLOUD else "agent" }"</script>'
        # 优先注入到 <div id="app"> 前（确保在 Vue mount 前执行）
        html_content = html_content.replace('<div id="app">', f'{inject_script}\n<div id="app">')
        return HTMLResponse(content=html_content, media_type="text/html")
    
    return {"error": "Not Found"}, 404

@app.get("/",tags=['默认'],include_in_schema=False)
async def serve_root(request: Request):
    """处理根路由"""
    return await serve_vue_app(request, "")