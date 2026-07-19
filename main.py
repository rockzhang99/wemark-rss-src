import sys
import os
import shutil
import asyncio

# Windows 需要使用 ProactorEventLoop 以支持 Playwright 子进程
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ===== 打包(frozen)模式引导 =====
# 仅在 PyInstaller 等打包后的可执行文件中生效, 开发态(python main.py)不受影响
if getattr(sys, 'frozen', False):
    # 切换到 exe 所在目录, 保证相对路径 config.yaml / static / data 解析正确
    os.chdir(os.path.dirname(sys.executable))

    # 首次运行: 从模板生成 config.yaml (避免把开发机敏感配置打进安装包)
    if not os.path.exists('config.yaml') and os.path.exists('config.example.yaml'):
        try:
            shutil.copy('config.example.yaml', 'config.yaml')
            print("[BOOT] 已从 config.example.yaml 生成 config.yaml")
        except Exception as e:
            print(f"[BOOT] 生成 config.yaml 失败: {e}")

    # 首次运行: 自动安装 Playwright 浏览器(若缺失), 安装包本身不含浏览器以保持小巧
    _marker = os.path.join('data', '.playwright_installed')
    if not os.path.exists(_marker):
        try:
            os.makedirs('data', exist_ok=True)
            print("[BOOT] 首次启动: 自动下载 Playwright Chromium (仅需联网一次) ...")
            import subprocess
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                           check=False)
            open(_marker, 'w').close()
        except Exception as e:
            print(f"[BOOT] Playwright 浏览器自动安装失败(可稍后手动执行): {e}")

from core.config import cfg

# 混合架构(改动036)：云端模式禁止打包/导入微信驱动
# 注意：driver 的所有运行期 import 均已被 `if ROLE != "cloud"` 守卫，
# 仅目录存在不会触发微信直连。此处仅做存在性告警，不再致命终止进程，
# 以便完整仓库也能在云端启动。
ROLE = cfg.get("deploy.role", "agent")
if ROLE == "cloud":
    try:
        import driver  # noqa: F401
        print(
            "[WARN] 云端部署检测到 driver/ 目录存在，但云端运行路径不会导入/执行微信驱动代码。"
            "若担心数据中心 IP 直连微信被封禁，建议使用排除 driver 的云端构建/入口。"
        )
    except ImportError:
        print("[BOOT] 云端模式：已确认不包含微信驱动代码")

if cfg.get("redis.server.enabled", False):
        from tools.redis_server import run_redis_server
        run_redis_server(config_path="config.yaml")
import uvicorn
from core.print import print_warning, print_info, print_success
import threading
if ROLE != "cloud":
    from driver.auth import start_auth_service
import os

if __name__ == '__main__':
    print("环境变量:")
    for k,v in os.environ.items():
        print(f"{k}={v}")
    if str(cfg.args.init).lower() in ("true","1","yes","y"):
        import init_sys as init
        init.init()
    if ROLE != "cloud":
        start_auth_service()
    # 启动级联同步服务（如果配置为子节点）
    cascade_service_started = False
    if cfg.get("cascade.enabled", False) and cfg.get("cascade.node_type") == "child":
        try:
            from jobs.cascade_sync import cascade_sync_service
            from jobs.cascade_task_dispatcher import start_child_task_worker
            import asyncio
            
            cascade_sync_service.initialize()
            if cascade_sync_service.sync_enabled:
                # 在后台线程启动同步服务
                def run_sync():
                    asyncio.run(cascade_sync_service.start_periodic_sync())
                
                sync_thread = threading.Thread(target=run_sync, daemon=True)
                sync_thread.start()
                
                # 启动子节点任务拉取器
                poll_interval = cfg.get("cascade.task_poll_interval", 30)
                
                def run_task_worker():
                    asyncio.run(start_child_task_worker(poll_interval=poll_interval))
                
                task_worker_thread = threading.Thread(target=run_task_worker, daemon=True)
                task_worker_thread.start()
                
                cascade_service_started = True
                print_success(f"级联同步服务已启动，任务拉取间隔: {poll_interval}秒")
        except Exception as e:
            print_warning(f"启动级联同步服务失败: {str(e)}")
    else:
        print_info("级联模式未启用或当前节点为父节点")
    
    if not cascade_service_started and ROLE != "cloud":
        print_info("启动网关定时调度服务")
        import asyncio
        from jobs.cascade_task_dispatcher import cascade_schedule_service
        cascade_schedule_service.start()

    if ROLE != "cloud" and str(cfg.args.job).lower() in ("true","1","yes","y") and cfg.get("server.enable_job",False):
        from jobs import start_job
        threading.Thread(target=start_job,daemon=False).start()
        print_success("已开启定时任务")
    else:
        print_warning("未开启定时任务")
    
    if ROLE != "cloud" and cfg.get("gather.content_auto_check",False):
        from jobs import start_fix_article
        start_fix_article()
        print_success("已开启自动修正文章任务")
    else:
        print_warning("未开启自动修正文章任务")
    
    # 启动文章统计定时刷新任务
    if ROLE != "cloud" and cfg.get("server.article_stats_refresh_enabled", False):  # 默认关闭
        from jobs.mps import start_article_stats_refresh
        start_article_stats_refresh()
    else:
        print_warning("文章统计定时刷新任务未启用")
    
    # 混合架构(改动036) 阶段2：本地 Agent 云端上传器（仅 agent 模式）
    if ROLE != "cloud":
        try:
            from core.uploader import uploader
            uploader.init()
            uploader.start()
        except Exception as e:
            print_warning(f"启动云端上传器失败: {e}")
    
    print("启动服务器")
    AutoReload=cfg.get("server.auto_reload",False)
    thread=cfg.get("server.threads",1)
    reload_dirs = ["apis", "core", "driver", "jobs", "schemas", "tools", "views", "web_ui"]
    
    # Windows 上禁用 reload 模式，因为会导致事件循环问题
    if sys.platform == 'win32' and AutoReload:
        print_warning("Windows 平台上禁用 reload 模式以确保 Playwright 正常工作")
        AutoReload = False
    
    # Windows 上使用自定义配置确保 ProactorEventLoop
    if sys.platform == 'win32':
        # 使用 uvicorn 的 Config 和 Server 类来控制事件循环
        config = uvicorn.Config(
            "web:app",
            host="0.0.0.0",
            port=int(cfg.get("port", 8001)),
            reload=False,
            reload_dirs=reload_dirs,
            reload_excludes=['static', 'data', 'node_modules', '*.pnpm*'],
            workers=thread,
        )
        server = uvicorn.Server(config)
        
        # 确保使用 ProactorEventLoop
        if not isinstance(asyncio.get_event_loop(), asyncio.ProactorEventLoop):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        asyncio.run(server.serve())
    else:
        uvicorn.run("web:app", host="0.0.0.0", port=int(cfg.get("port",8001)),
                reload=AutoReload,
                reload_dirs=reload_dirs,
                reload_excludes=['static','data','node_modules','*.pnpm*'],
                workers=thread,
                )
    pass
