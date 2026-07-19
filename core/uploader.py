"""混合架构(改动036) 阶段2：本地 Agent -> 云端 上传器。

职责：
- 仅在本机以 agent 角色运行时启用（deploy.role != cloud）。
- 抓取文章落库后，增量把 Feed / Article 推送到阿里云纯 RSS 服务端。
- 云端不接触微信，只接收数据；鉴权复用现有 AK-SK 机制。
- 采用「本地高水位(watermark) + 周期性 catch-up」保证增量、可断点续传、可去重。
"""

import os
import json
import time
import threading
from typing import Optional, Dict, List

import requests

from core.config import cfg
from core.db import DB
from core.models.feed import Feed, FEATURED_MP_ID
from core.models.article import Article
from core.print import print_info, print_success, print_error, print_warning


class CloudUploader:
    def __init__(self):
        self.enabled = False
        self.server = ""
        self.ak = ""
        self.sk = ""
        self.batch_size = 50
        self.interval = 300
        self.timeout = 30
        self.max_retries = 3
        self._thread = None
        self._stop = False
        self._event = threading.Event()
        self._queue_lock = threading.Lock()
        self._lock = threading.Lock()
        # 即时队列：抓取回调入队，循环唤醒后立即推送
        self._pending_articles: Dict[str, List[dict]] = {}  # mp_id -> [article dict]
        self._pending_feeds: List[dict] = []
        # 高水位：每个公众号已上传的最大 publish_time，用于 catch-up 去重
        self._watermark: Dict[str, int] = {}
        self._state_path = os.path.join("data", "upload_state.json")

    # ------------------------------------------------------------------ #
    # 配置 & 状态
    # ------------------------------------------------------------------ #
    def init(self):
        upload_cfg = cfg.get("upload", {}) or {}
        self.enabled = bool(upload_cfg.get("enabled", False))
        self.server = (upload_cfg.get("server") or "").rstrip("/")
        self.ak = upload_cfg.get("ak") or ""
        self.sk = upload_cfg.get("sk") or ""
        self.batch_size = int(upload_cfg.get("batch_size", 50))
        self.interval = int(upload_cfg.get("interval", 300))
        self.timeout = int(upload_cfg.get("timeout", 30))
        self.max_retries = int(upload_cfg.get("max_retries", 3))
        self._load_state()
        if self.enabled and (not self.server or not self.ak or not self.sk):
            print_warning("[UPLOADER] upload.enabled=true 但缺少 server/ak/sk 配置，上传器已禁用")
            self.enabled = False

    def _load_state(self):
        try:
            if os.path.exists(self._state_path):
                with open(self._state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._watermark = data.get("watermark", {}) or {}
        except Exception as e:
            print_warning(f"[UPLOADER] 读取上传状态失败: {e}")
            self._watermark = {}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump({"watermark": self._watermark}, f, ensure_ascii=False)
        except Exception as e:
            print_warning(f"[UPLOADER] 写入上传状态失败: {e}")

    # ------------------------------------------------------------------ #
    # 对外入队接口（抓取回调调用）
    # ------------------------------------------------------------------ #
    def enqueue_article(self, mp_id: str, article: dict):
        if not self.enabled or not mp_id:
            return
        with self._queue_lock:
            self._pending_articles.setdefault(mp_id, []).append(article)
        self._event.set()

    def enqueue_feed(self, feed: dict):
        if not self.enabled:
            return
        with self._queue_lock:
            self._pending_feeds.append(feed)
        self._event.set()

    # ------------------------------------------------------------------ #
    # 生命周期
    # ------------------------------------------------------------------ #
    def start(self):
        if not self.enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print_success(f"[UPLOADER] 云端上传器已启动 -> {self.server} (间隔 {self.interval}s)")

    def stop(self):
        self._stop = True
        self._event.set()

    # ------------------------------------------------------------------ #
    # 主循环
    # ------------------------------------------------------------------ #
    def _loop(self):
        # 启动即做一次全量同步（feeds + 按高水位 articles），保证断点续传
        self._sync_feeds()
        self._sync_articles()
        while not self._stop:
            self._event.wait(timeout=self.interval)
            self._event.clear()
            if self._stop:
                break
            self._flush_queue()
            self._sync_feeds()
            self._sync_articles()

    def _flush_queue(self):
        with self._queue_lock:
            arts = self._pending_articles
            fds = self._pending_feeds
            self._pending_articles = {}
            self._pending_feeds = []
        for mp_id, items in arts.items():
            self._post_articles(mp_id, items)
        if fds:
            self._post_feeds(fds)

    # ------------------------------------------------------------------ #
    # Feed 同步（幂等 upsert，安全全量推送）
    # ------------------------------------------------------------------ #
    def _sync_feeds(self):
        try:
            session = DB.get_session()
            feeds = session.query(Feed).filter(
                Feed.status == 1,
                Feed.id != FEATURED_MP_ID,
            ).all()
            items = [{
                "id": f.id,
                "mp_name": f.mp_name or "",
                "mp_cover": f.mp_cover or "",
                "mp_intro": f.mp_intro or "",
                "status": f.status or 1,
                "faker_id": f.faker_id or "",
            } for f in feeds]
            session.close()
            if items:
                self._post_feeds(items)
        except Exception as e:
            print_error(f"[UPLOADER] 同步 Feed 列表失败: {e}")

    # ------------------------------------------------------------------ #
    # Article 同步（按高水位 catch-up）
    # ------------------------------------------------------------------ #
    def _sync_articles(self):
        try:
            session = DB.get_session()
            mps = session.query(Feed.id).filter(
                Feed.status == 1,
                Feed.id != FEATURED_MP_ID,
            ).all()
            session.close()
            for (mp_id,) in mps:
                self._sync_articles_for_mp(mp_id)
        except Exception as e:
            print_error(f"[UPLOADER] 同步文章失败: {e}")

    def _sync_articles_for_mp(self, mp_id: str):
        wm = self._watermark.get(mp_id, 0) or 0
        try:
            session = DB.get_session()
            q = session.query(Article).filter(Article.mp_id == mp_id)
            if wm:
                q = q.filter(Article.publish_time > wm)
            q = q.order_by(Article.publish_time.asc())
            rows = q.all()
            session.close()
            if not rows:
                return
            batch = []
            for a in rows:
                batch.append(a.to_dict())
                if len(batch) >= self.batch_size:
                    self._post_articles(mp_id, batch)
                    batch = []
            if batch:
                self._post_articles(mp_id, batch)
        except Exception as e:
            print_error(f"[UPLOADER] 同步文章失败(mp={mp_id}): {e}")

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #
    def _headers(self):
        return {
            "Authorization": f"AK-SK {self.ak}:{self.sk}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict) -> Optional[dict]:
        url = f"{self.server}{path}"
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, headers=self._headers(),
                                     timeout=self.timeout)
                if resp.status_code == 200:
                    return resp.json()
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                last_err = str(e)
            if attempt < self.max_retries:
                time.sleep(min(2 * attempt, 10))
        print_error(f"[UPLOADER] 上传失败 {path}: {last_err}")
        return None

    def _post_feeds(self, items: List[dict]):
        resp = self._post("/api/v1/wx/agent/feeds", {"feeds": items})
        if resp is not None:
            print_info(f"[UPLOADER] 上传 Feed {len(items)} 条 -> {resp.get('message')}")

    @staticmethod
    def _normalize_datetime(v):
        """把 to_dict() 产出的时间规范化为服务端 add_article 期望的格式。

        - to_dict() 的 created_at 是 ISO 字符串（如 2024-01-01T12:00:00），
          而服务端 add_article 用 datetime.strptime(v, '%Y-%m-%d %H:%M:%S') 解析，
          ISO 格式会抛 ValueError 被 except 吞掉 → 文章上传静默失败(added=0)。
        - 这里统一转成 '%Y-%m-%d %H:%M:%S'；None 直接返回让服务端补默认值。
        """
        if v is None:
            return None
        if isinstance(v, str):
            s = v.replace("T", " ", 1) if "T" in v else v
            s = s.split("+")[0].split(".")[0]  # 去掉时区/毫秒尾巴
            return s
        if hasattr(v, "strftime"):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        return v

    def _post_articles(self, mp_id: str, items: List[dict]):
        # 去掉 None 字段，避免云端 add_article 因空值报错；
        # 同时把 created_at 的 ISO 时间规范化为服务端可解析的格式。
        clean = []
        for it in items:
            norm = {k: v for k, v in it.items() if v is not None}
            if "created_at" in norm:
                norm["created_at"] = self._normalize_datetime(norm["created_at"])
            clean.append(norm)
        if not clean:
            return
        resp = self._post("/api/v1/wx/agent/articles", {"mp_id": mp_id, "articles": clean})
        if resp is not None:
            # 成功后推进高水位，保证 catch-up 去重与断点续传
            max_pt = self._watermark.get(mp_id, 0) or 0
            for it in items:
                pt = it.get("publish_time") or 0
                if pt > max_pt:
                    max_pt = pt
            with self._lock:
                self._watermark[mp_id] = max_pt
            self._save_state()
            print_info(
                f"[UPLOADER] 上传文章(mp={mp_id}) {len(clean)} 条, 云端新增 {resp.get('added')}"
            )


# 进程级单例
uploader = CloudUploader()
