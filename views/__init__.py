from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import os
import views.config as config
# 创建路由器
router = APIRouter(prefix="/views", tags=["网页预览"])

from .home import router as home_router

# 注册子路由
router.include_router(home_router)

# 以下子路由云端可用性不同: mps/tags/articles 已解耦 driver(改动049), 云端安全;
# article_detail 仍依赖 driver(云端 cloud_strip 已删除), 单独容错, 失败不影响其他。
import importlib, logging
def _safe_include(module_name):
    try:
        mod = importlib.import_module(f"views.{module_name}")
        router.include_router(mod.router)
    except Exception as _e:
        logging.getLogger("uvicorn.error").warning(
            "views 子路由 %s 未注册(云端裁剪/缺失): %s", module_name, _e
        )

_safe_include("mps")
_safe_include("tags")
_safe_include("articles")
_safe_include("article_detail")