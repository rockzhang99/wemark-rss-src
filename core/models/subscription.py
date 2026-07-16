import uuid
from .base import Base, Column, String, Integer, DateTime
from datetime import datetime


class Subscription(Base):
    """用户订阅关系表（多用户数据隔离核心）

    公众号(Feed)作为全局目录存在，订阅关系通过本表按用户隔离。
    - 同一公众号可被多个用户订阅，各自独立启用/停用；
    - 文章(Article)挂在全局 Feed 上，订阅者共享同一份内容，避免重复抓取。
    """
    __tablename__ = 'subscriptions'
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)  # 对应用户 username
    feed_id = Column(String(255), nullable=False, index=True)  # 对应 feeds.id
    status = Column(Integer, default=1)  # 1=启用, 0=停用（用户维度的订阅开关）
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    from_attributes = True
