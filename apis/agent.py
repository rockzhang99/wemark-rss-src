from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List
from core.auth import get_current_user_or_ak
from core.db import DB
from core.models.feed import Feed
from core.print import print_info, print_error

router = APIRouter(prefix="/agent", tags=["Agent"])


def _resolve_tenant(current_user: dict) -> str:
    """由认证用户解析租户标识（云端多租户隔离依据）。"""
    return current_user.get("user_id") or current_user.get("username") or "default"


class FeedItem(BaseModel):
    id: str
    mp_name: str = ""
    mp_cover: str = ""
    mp_intro: str = ""
    status: int = 1
    faker_id: str = ""


class FeedsUpload(BaseModel):
    feeds: List[FeedItem] = Field(default_factory=list)


class ArticlesUpload(BaseModel):
    mp_id: str
    articles: List[dict] = Field(default_factory=list)


@router.post("/feeds")
async def upload_feeds(
    payload: FeedsUpload,
    current_user: dict = Depends(get_current_user_or_ak),
):
    """本地 Agent 上传公众号目录（Feed）到云端，按租户落库。"""
    tenant_id = _resolve_tenant(current_user)
    session = DB.get_session()
    try:
        for f in payload.feeds:
            existing = session.query(Feed).filter(Feed.id == f.id).first()
            if existing:
                existing.mp_name = f.mp_name
                existing.mp_cover = f.mp_cover
                existing.mp_intro = f.mp_intro
                existing.status = f.status
                existing.faker_id = f.faker_id
                existing.tenant_id = tenant_id
            else:
                session.add(Feed(
                    id=f.id, mp_name=f.mp_name, mp_cover=f.mp_cover,
                    mp_intro=f.mp_intro, status=f.status, faker_id=f.faker_id,
                    tenant_id=tenant_id,
                ))
        session.commit()
        return {"code": 0, "message": "ok", "count": len(payload.feeds)}
    except Exception as e:
        session.rollback()
        print_error(f"上传 Feed 失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        session.close()


@router.post("/articles")
async def upload_articles(
    payload: ArticlesUpload,
    current_user: dict = Depends(get_current_user_or_ak),
):
    """本地 Agent 上传文章到云端，按租户落库（复用 DB.add_article 幂等去重）。"""
    tenant_id = _resolve_tenant(current_user)
    added = 0
    for art in payload.articles:
        data = dict(art)
        data["mp_id"] = payload.mp_id
        data["tenant_id"] = tenant_id
        try:
            if DB.add_article(data, check_exist=True):
                added += 1
        except Exception as e:
            print_error(f"上传文章失败(mp_id={payload.mp_id}): {e}")
    return {"code": 0, "message": "ok", "received": len(payload.articles), "added": added}
