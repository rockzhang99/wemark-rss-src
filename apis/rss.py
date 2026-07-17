from fastapi import APIRouter, Depends, Query, HTTPException, Request,Response
from fastapi import status
from fastapi.responses import Response
from core.db import DB
from core.rss import RSS
from core.models.feed import Feed
import json
from .base import success_response, error_response
from core.auth import (get_current_user, get_current_user_or_ak, authenticate_ak,
                       get_user, get_effective_permissions, SECRET_KEY, ALGORITHM)
import jwt
from core.config import cfg
from apis.base import format_search_kw
from core.print import print_error,print_success
from typing import Optional


async def _rss_tenant_dep(request: Request) -> Optional[str]:
    """解析 RSS 访问者租户(改动036 多租户隔离)。
    - 非云端模式(本地 Agent)：返回 None，保持原有开放访问、不过滤（向后兼容）。
    - 云端模式：必须携带认证（Authorization 头 或 ?token= 查询参数，供 RSS 阅读器订阅）；
      超级管理员(admin)返回 None 看全部，其余按租户过滤。
    """
    if cfg.get("deploy.role", "agent") != "cloud":
        return None

    # 解析凭证：优先 Authorization 头，其次 ?token= 查询参数（阅读器常把 token 放 URL）
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        q = request.query_params.get("token")
        if q:
            auth_header = q if q.startswith(("AK-SK ", "Bearer ")) else f"Bearer {q}"

    current_user = None
    if auth_header.startswith("AK-SK "):
        cred = auth_header[6:].strip()
        if ":" in cred:
            ak, sk = cred.split(":", 1)
            current_user = authenticate_ak(ak, sk)
    elif auth_header.startswith("Bearer "):
        try:
            payload = jwt.decode(auth_header[7:].strip(), SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username:
                u = get_user(username)
                if u:
                    current_user = {
                        "username": u.username,
                        "role": u.role,
                        "permissions": get_effective_permissions(u),
                        "original_user": u,
                    }
        except Exception:
            current_user = None

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response(code=40101, message="未授权的RSS访问"),
        )
    if current_user.get("role") == "admin":
        return None
    return current_user.get("user_id") or current_user.get("username")


def clamp_rss_limit(limit: int) -> int:
    """Clamp RSS item count to configured bounds to avoid oversized feeds."""
    default_page_size = int(cfg.get("rss.page_size", 30) or 30)
    max_items = int(cfg.get("rss.max_items", default_page_size) or default_page_size)
    if max_items < 1:
        max_items = default_page_size if default_page_size > 0 else 30
    return min(limit, max_items)
def verify_rss_access(current_user: dict = Depends(get_current_user)):
    """
    RSS访问认证方法
    :param current_user: 当前用户信息
    :return: 认证通过返回用户信息，否则抛出HTTP异常
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response(
                code=40101,
                message="未授权的RSS访问"
            )
        )
    return current_user

router = APIRouter(prefix="/rss",tags=["Rss"])
feed_router = APIRouter(prefix="/feed",tags=["Feed"])

@router.get("/{feed_id}/api", summary="获取特定RSS源详情")
async def get_rss_source(
    feed_id: str,
    request: Request,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: Optional[str] = Depends(_rss_tenant_dep),
):
    return await get_mp_articles_source(request=request,feed_id=feed_id, limit=limit,offset=offset, is_update=True, tenant_id=tenant_id)





@router.get("/fresh", summary="更新并获取RSS订阅列表")
async def update_rss_feeds( 
    request: Request,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: Optional[str] = Depends(_rss_tenant_dep),
):
    return await get_rss_feeds(request=request, limit=limit,offset=offset, is_update=True, tenant_id=tenant_id)

@router.get("", summary="获取RSS订阅列表")
async def get_rss_feeds(
    request: Request,
    limit: int = Query(10, ge=1, le=30),
    offset: int = Query(0, ge=0),
    is_update:bool=False,
    tenant_id: Optional[str] = Depends(_rss_tenant_dep),
):
    limit = clamp_rss_limit(limit)
    rss=RSS(name=f'all_{limit}_{offset}')
    rss_xml=rss.get_cache()
    if rss_xml is not None  and is_update==False:
         return Response(
            content=rss_xml,
            media_type="application/xml"
        )
    session = DB.get_session()
    try:
        total = session.query(Feed).count()
        feeds_q = session.query(Feed).order_by(Feed.created_at.desc())
        if tenant_id is not None:
            feeds_q = feeds_q.filter(Feed.tenant_id == tenant_id)
        feeds = feeds_q.limit(limit).offset(offset).all()
        rss_domain=cfg.get("rss.base_url",request.base_url)
        # 转换为RSS格式数据
        from datetime import datetime, timezone, timedelta
        # assume CST (UTC+8) for naive timestamps
        cst = timezone(timedelta(hours=8))
        rss_list = [{
            "id": str(feed.id),
            "title": feed.mp_name,
            "link":  f"{rss_domain}rss/{feed.id}",
            "description": feed.mp_intro,
            "image": feed.mp_cover,
            "updated": (feed.created_at if getattr(feed.created_at, 'tzinfo', None) is not None else feed.created_at.replace(tzinfo=cst)).isoformat()
        } for feed in feeds]
        
        # 生成RSS XML
        rss_xml = rss.generate_rss(rss_list, title="WemarkRSS订阅",link=rss_domain)
        
        return Response(
            content=rss_xml,
            media_type="application/xml"
        )
    except Exception as e:
        print(f"获取RSS订阅列表错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=error_response(
                code=50001,
                message="获取RSS订阅列表失败"
            )
        )

@router.get("/content/{content_id}", summary="获取缓存的文章内容")
async def get_rss_feed(
    content_id: str,
    request: Request,
    tenant_id: Optional[str] = Depends(_rss_tenant_dep),
):
    # 云端模式：校验租户隔离，防止跨租户读取文章正文（改动036 阶段4 安全加固）
    if cfg.get("deploy.role", "agent") == "cloud" and tenant_id is not None:
        session = DB.get_session()
        try:
            from core.models.article import Article
            art = session.query(Article).filter(Article.id == content_id).first()
            if art is None or art.tenant_id != tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_response(code=40402, message="文章内容未找到"),
                )
        finally:
            session.close()

    rss = RSS()
    content = rss.get_cached_content(content_id)
      
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response(
                code=40402,
                message="文章内容未找到"
            )
        )
    title=content['title']
    html='''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <title>{title}</title>
        </head>
    <body>
    <center>
    <h1 style="text-align:center;">{title}</h1>
    <div class="author">来源:{source}</div>
    <div class="author">发布时间:{publish_time}</div>
    <div class="copyright">
        <p>
        本文章仅用于学习和交流目的，不代表本网站观点和立场，如涉及版权问题，请及时联系我们删除。
        </p>
    </div>
    <div id=content>{text}</div>
    </center>
    </body>
    </html>
    '''
    text=rss.add_logo_prefix_to_urls(content['content'])
    html=html.format(title=title,text=text,source=content['mp_name'],publish_time=content['publish_time'])
    return Response(
            content=html,
            media_type="text/html"
        )
def UpdateArticle(art:dict):
            return DB.add_article(art)


@router.api_route("/{feed_id}/fresh", summary="更新并获取公众号文章RSS")
async def update_rss_feeds( 
    request: Request,
    feed_id: str,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: Optional[str] = Depends(_rss_tenant_dep),
    # current_user: dict = Depends(get_current_user)
):
        #如果需要放开授权，请只允许内网访问，防止 被利用攻击 放开授权办法，注释上面current_user: dict = Depends(get_current_user)

        # from core.models.feed import Feed
        # mp = DB.session.query(Feed).filter(Feed.id == feed_id).first()
        # from core.wx import WxGather
        # wx=WxGather().Model()
        # wx.get_Articles(mp.faker_id,Mps_id=mp.id,CallBack=UpdateArticle)
        # result=wx.articles

        return await get_mp_articles_source(request=request,feed_id=feed_id, limit=limit,offset=offset, is_update=True, tenant_id=tenant_id)



@router.get("/{feed_id}", summary="获取公众号文章")
async def get_mp_articles_source(
    request: Request,
    feed_id: str=None,
    tag_id:str=None,
    ext:str="xml",
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    kw:str="",
    is_update:bool=True,
    content_type:str=Query(None,alias="ctype"),
    template:str=None,
    tenant_id: Optional[str] = None,
    # current_user: dict = Depends(get_current_user)
):
    limit = clamp_rss_limit(limit)
    rss=RSS(name=f'{tag_id}_{feed_id}_{limit}_{offset}',ext=ext)
    rss.set_content_type(content_type)
    rss_xml = rss.get_cache()
    if rss_xml is not None and is_update==False:
         return Response(
            content=rss_xml,
            media_type=rss.get_type()
        )
    session = DB.get_session()
    try:
        from core.models.article import Article
        from core.models.tags import Tags
        # 查询公众号信息
        feed = session.query(Feed)
        query=session.query(Feed, Article).join(Article, Feed.id == Article.mp_id)
        if tenant_id is not None:
            query = query.filter(Article.tenant_id == tenant_id)
        rss_domain = str(cfg.get("rss.base_url", str(request.base_url))).rstrip("/") + "/"
        if tag_id is not None:
            feed_link = f"{rss_domain}feed/tag/{tag_id}.{ext}"
        elif kw != "":
            target_feed_id = feed_id or "all"
            feed_link = f"{rss_domain}feed/search/{kw}/{target_feed_id}.{ext}"
        else:
            target_feed_id = feed_id or "all"
            feed_link = f"{rss_domain}feed/{target_feed_id}.{ext}"
        if feed_id not in ["all",None]:
            feed_q = feed.filter(Feed.id == feed_id)
            if tenant_id is not None:
                feed_q = feed_q.filter(Feed.tenant_id == tenant_id)
            feed=feed_q.first()
            query=query.filter(Article.mp_id==feed_id)
        else:
            feed=Feed()
            feed.mp_name=cfg.get("rss.title","WemarkRss") or "WemarkRss"
            feed.mp_intro=cfg.get("rss.description") or "WemarkRss高效订阅我的公众号"
            feed.mp_cover=cfg.get("rss.cover") or f"{rss_domain}static/logo.svg"
            #如果传入了tag_id就加载tag对应的订阅信息
            if tag_id is not None:
                tags_q = session.query(Tags).filter(Tags.id == tag_id)
                if tenant_id is not None:
                    tags_q = tags_q.filter(Tags.owner == tenant_id)
                tags=tags_q.first()
                if tags:
                    mps_ids = [str(mp['id']) for mp in json.loads(tags.mps_id)] if tags.mps_id else []
                    query=query.filter(Feed.id.in_(mps_ids))
                    feed.mp_name = tags.name
                    feed.mp_intro = tags.intro
                    feed.mp_cover = f'{rss_domain}{tags.cover}'

        
        if not feed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response(
                    code=40401,
                    message="公众号不存在"
                )
            )
      
        # 查询文章列表
        total = query.count()
        # articles = query.order_by(Article.publish_time.desc()).limit(limit).offset(offset).all()
        if kw!="":
            query=query.filter(format_search_kw(kw))
        articles =query.order_by(Article.publish_time.desc()).limit(limit).offset(offset).all()
        # 转换为RSS格式数据
        from datetime import datetime, timezone, timedelta
        cst = timezone(timedelta(hours=8))
        rss_list = [{
            "id": str(article.id),
            "title": article.title or "",
            "link":  f"{rss_domain}/views/article/{article.id}" if cfg.get("rss.local",False) else article.url,
            "description": article.description if article.description != "" else article.title or "",
            "content": article.content or "",
            "image": article.pic_url or "",
            "mp_name":_feed.mp_name or "",
            "updated": datetime.fromtimestamp(article.publish_time, tz=cst),
            "feed": {
                    "id":_feed.id,
                    "name":_feed.mp_name,
                    "cover":_feed.mp_cover,
                    "intro":_feed.mp_intro
            }
        } for _feed,article in articles]
        

        # 缓存文章内容
        for _feed,article in articles:
            content_data = {
                "id": article.id,
                "title": article.title,
                "content": article.content,
                "publish_time": article.publish_time,
                "mp_id": article.mp_id,
                "pic_url": article.pic_url,
                "mp_name": _feed.mp_name
            }
            rss.cache_content(article.id, content_data)
        # 生成RSS XML
        rss_xml = rss.generate(rss_list,ext=ext, title=f"{feed.mp_name}",link=feed_link,description=feed.mp_intro,image_url=feed.mp_cover,template=template)
        
        return Response(
            content=rss_xml,
            media_type=rss.get_type()
        )
    except Exception as e:
        print_error(f"获取RSS错误:{e}")
        # raise
        return Response(
             content=rss_xml,
             media_type=rss.get_type()
        )
    


@feed_router.get("/{feed_id}.{ext}", summary="获取公众号文章源")
async def rss(
    request: Request,
    feed_id: str,
    ext: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    kw:str="",
    content_type:str=Query(None,alias="ctype"),
    is_update:bool=True,
    tenant_id: Optional[str] = Depends(_rss_tenant_dep),
):
    return await get_mp_articles_source(request=request,feed_id=feed_id, limit=limit,offset=offset, is_update=is_update,ext=ext,kw=kw,content_type=content_type, tenant_id=tenant_id)


@feed_router.get("/search/{kw}/{feed_id}.{ext}", summary="获取公众号文章源")
async def rss(
    request: Request,
    feed_id: str,
    ext: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    kw:str="",
    content_type:str=Query(None,alias="ctype"),
    is_update:bool=True,
    tenant_id: Optional[str] = Depends(_rss_tenant_dep),
):
    return await get_mp_articles_source(request=request,feed_id=feed_id, limit=limit,offset=offset, is_update=is_update,ext=ext,kw=kw,content_type=content_type, tenant_id=tenant_id)
@feed_router.get("/tag/{tag_id}.{ext}", summary="获取公众号文章源")
async def rss(
    request: Request,
    tag_id:str="",
    feed_id: str=None,
    ext: str="jmd",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    kw:str="",
    content_type:str=Query(None,alias="ctype"),
    is_update:bool=True,
    tenant_id: Optional[str] = Depends(_rss_tenant_dep),
):
    return await get_mp_articles_source(request=request,feed_id=feed_id, tag_id=tag_id,limit=limit,offset=offset, is_update=is_update,ext=ext,kw=kw,content_type=content_type, tenant_id=tenant_id)


