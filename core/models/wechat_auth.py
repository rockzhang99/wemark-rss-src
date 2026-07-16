from .base import Base, Column, String, DateTime, Boolean, Text
from datetime import datetime


class UserWechatAuth(Base):
    """用户微信授权表（多用户隔离）

    每个用户各自扫码授权自己的微信账号，token/cookie 仅归属该用户，
    互不共享。抓取文章时按任务归属用户取用其授权（回退全局以兼容旧数据）。
    """
    __tablename__ = 'user_wechat_auth'

    user_id = Column(String(255), primary_key=True)  # 关联用户名
    token = Column(Text, default='')                 # 微信 token
    cookie = Column(Text, default='')                # 微信 cookie 字符串
    fingerprint = Column(Text, default='')           # 浏览器指纹
    expiry = Column(Text, default='')                # JSON: {expiry_time, remaining_seconds, expiry_timestamp}
    ext_data = Column(Text, default='')              # JSON: 公众号信息（名称/头像/粉丝数等）
    login = Column(Boolean, default=False)           # 是否已授权
    updated_at = Column(DateTime, default=datetime.now)
