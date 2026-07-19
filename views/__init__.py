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

# 以下子路由依赖微信驱动（driver），云端 cloud_strip 会删除对应模块，用 try/except 容错
try:
    from .articles import router as articles_router
    from .tags import router as tags_router
    from .mps import router as mps_router
    from .article_detail import router as article_detail_router
    router.include_router(articles_router)
    router.include_router(article_detail_router)
    router.include_router(tags_router)
    router.include_router(mps_router)
except Exception:
    # 云端无 driver，跳过微信相关页面路由（首页 home 仍可正常使用）
    pass