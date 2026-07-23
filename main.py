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
    # 打包后资源位于 sys._MEIPASS (_internal/), 运行时相对路径按此解析
    _base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))

    # === 运行日志落盘 (仅打包态) ===
    # 把 stdout/stderr 用 TeeStream 同时写控制台与 data/wemark.log, 避免日志只在控制台闪过
    try:
        os.makedirs('data', exist_ok=True)
        _log = os.path.abspath(os.path.join('data', 'wemark.log'))
        # 简单轮转: 超过 5MB 则备份为 wemark.log.1 (覆盖旧备份)
        if os.path.exists(_log) and os.path.getsize(_log) > 5 * 1024 * 1024:
            try:
                os.replace(_log, _log + '.1')
            except OSError:
                pass
        _logf = open(_log, 'a', encoding='utf-8', buffering=1)

        class _Tee:
            def __init__(self, con, f):
                self._con, self._f = con, f

            def write(self, d):
                self._con.write(d)
                try:
                    self._f.write(d)
                    self._f.flush()
                except Exception:
                    pass

            def flush(self):
                self._con.flush()
                try:
                    self._f.flush()
                except Exception:
                    pass

        sys.stdout = _Tee(sys.stdout, _logf)
        sys.stderr = _Tee(sys.stderr, _logf)
        print(f"[BOOT] 运行日志已重定向至 {_log}")
    except Exception as _e:
        print(f"[BOOT] 日志落盘初始化失败(忽略): {_e}")

    # 首次运行: 从模板生成 config.yaml (避免把开发机敏感配置打进安装包)
    if not os.path.exists('config.yaml'):
        _tmpl = os.path.join(_base, 'config.example.yaml')
        if os.path.exists(_tmpl):
            try:
                shutil.copy(_tmpl, 'config.yaml')
                print("[BOOT] 已从 config.example.yaml 生成 config.yaml")
            except Exception as e:
                print(f"[BOOT] 生成 config.yaml 失败: {e}")
        else:
            print("[BOOT] 未找到 config.example.yaml 模板")

    # 静态资源: 始终从 _internal 同步到 CWD(覆盖更新), 供 web.py 以相对路径挂载。
    # 注意: 不能用"仅缺失时解包"——已安装版本 CWD 里已有旧 static/, 重装新包若不覆盖,
    # 前端构建更新(如 App.vue 改动)不会生效(改动045修复)。
    _src_static = os.path.join(_base, 'static')
    if os.path.exists(_src_static):
        try:
            shutil.copytree(_src_static, 'static', dirs_exist_ok=True)
            print("[BOOT] 已同步静态资源 static/")
        except Exception as e:
            print(f"[BOOT] 同步 static 失败: {e}")

    # 自动补齐缺失的 Playwright 浏览器(自解决, 不再依赖 marker 跳过):
    # 微信 driver 默认用 webkit, PDF 工具默认用 chromium, 用户也可能在 config 切到 firefox,
    # 故首次/缺件时把三种浏览器都确保装好; 每次启动只检测真实缺失项, 缺哪个装哪个。
    #
    # 关键坑(改动043修正): frozen 态与 dev 态的浏览器查找目录【完全不同】, 检测必须与运行时一致,
    # 否则会误判"已齐备"而漏装:
    #   - frozen 态: Playwright 的 PyInstaller hook 让浏览器只在【包内】.local-browsers 查找
    #     (PLAYWRIGHT_BROWSERS_PATH=0 语义, 即 E:\WeMark-RSS\_internal\playwright\driver\package\.local-browsers),
    #     绝不查全局目录。故检测/安装都必须针对包内, 并在 install 前显式设 PLAYWRIGHT_BROWSERS_PATH=0。
    #   - dev 态: 浏览器在【全局】AppData/Local/ms-playwright, 保持默认(不设 env)即可。
    try:
        _frozen = getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')
        if _frozen:
            # 冻结态: 浏览器装到包内 .local-browsers, install 与运行走同一路径
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'
            import playwright as _pw_pkg
            _pw_dir = os.path.dirname(_pw_pkg.__file__)
            _browsers_path = os.path.join(_pw_dir, 'driver', 'package', '.local-browsers')
        else:
            # 开发态: 浏览器在全局目录, 保持默认(不设 PLAYWRIGHT_BROWSERS_PATH)
            import playwright as _pw_pkg
            _pw_dir = os.path.dirname(_pw_pkg.__file__)
            _browsers_path = (os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ms-playwright')
                              if os.name == 'nt'
                              else os.path.join(os.path.expanduser('~'), '.cache', 'ms-playwright'))

        def _browser_present(b: str) -> bool:
            return os.path.isdir(_browsers_path) and any(
                d.startswith(b + '-') for d in os.listdir(_browsers_path))

        _browsers = ['chromium', 'firefox', 'webkit']
        _missing = [b for b in _browsers if not _browser_present(b)]
        if _missing:
            os.makedirs('data', exist_ok=True)
            print(f"[BOOT] 自动补齐缺失的 Playwright 浏览器: {', '.join(_missing)} (仅需联网一次) ...")
            # 关键: 用 playwright.__main__.main() 触发安装。该函数内部执行
            # subprocess.run([node驱动, cli.js, *sys.argv[1:]]) —— 调的是 playwright
            # 自带的 node 驱动(不是本 exe), 天然无递归; 且 frozen 下不涉及 `-c`。
            # 注意: main() 按 sys.argv[1:] 拼命令, 故临时替换 argv 为 install <browser>。
            try:
                from playwright.__main__ import main as _pw_install
            except ImportError:
                from playwright.cli import main as _pw_install  # 兼容旧版 playwright
            _saved_argv = sys.argv
            _all_ok = True
            for _b in _missing:
                try:
                    sys.argv = ['playwright', 'install', _b]
                    _pw_install()
                except SystemExit:
                    pass  # playwright 安装完成时内部会 sys.exit(returncode), 忽略
                except Exception as _e:
                    print(f"[BOOT] 浏览器 {_b} 下载失败(可稍后手动执行 playwright install {_b}): {_e}")
                    _all_ok = False
            sys.argv = _saved_argv
            if _all_ok:
                # marker 仅作记录, 真正是否跳过由上面的缺失检测决定
                open(os.path.join('data', '.playwright_installed'), 'w').close()
            else:
                print("[BOOT] 部分浏览器下载失败, 下次启动将自动重试")
        else:
            print(f"[BOOT] Playwright 浏览器已齐备(chromium/firefox/webkit @ {_browsers_path}), 跳过下载")
    except Exception as e:
        print(f"[BOOT] Playwright 浏览器检测/安装异常(可稍后手动执行 playwright install): {e}")

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
