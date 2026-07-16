__package__ = "driver"
from core.config import Config,cfg
# 确保data目录和wx.lic文件存在
import os
import json
from core.print import print_success, print_warning
from core.redis_client import redis_client

REDIS_TOKEN_PREFIX = "werss:token:"

lic_path="./data/wx.lic"
os.makedirs(os.path.dirname(lic_path), exist_ok=True)
if not os.path.exists(lic_path):
    with open(lic_path, "w") as f:
        f.write("{}")
wx_cfg = Config(lic_path)

def set_token(data:any,ext_data:any=None):

    """
    设置微信登录的Token和Cookie信息
    :param data: 包含Token和Cookie信息的字典
    """
    if data.get("token", "") == "":
        return

    token_data = {
        "token": data.get("token", ""),
        "cookie": data.get("cookies_str", ""),
        "fingerprint": data.get("fingerprint", ""),
        "expiry": data.get("expiry", {}),
    }
    if ext_data is not None:
        token_data["ext_data"] = ext_data

    # 优先存储到Redis，整体存储
    if redis_client.is_connected:
        try:
            _save_to_local(token_data)
            redis_client._client.set(REDIS_TOKEN_PREFIX + "data", json.dumps(token_data))
            print_success("Token已存储到Redis")
        except Exception as e:
            print_warning(f"Redis存储失败，回退到本地文件: {e}")
    else:
        _save_to_local(token_data)

    print_success(f"Token:{data.get('token')} \n到期时间:{data.get('expiry')['expiry_time']}\n")
    from jobs.notice import sys_notice

#     sys_notice(f"""WemarkRss授权成功
# - Token: {data.get("token")}
# - Expiry: {data.get("expiry")['expiry_time']}
# """, str(cfg.get("server.code_title","WemarkRss授权成功")))


def _save_to_local(token_data: dict):
    """保存到本地文件"""
    wx_cfg.set("token_data", token_data)
    wx_cfg.save_config()
    wx_cfg.reload()


def get(key:str,default:str="")->str:
    """从整体token_data中获取指定字段"""
    token_data = _get_token_data()
    if token_data is None:
        return default
    value = token_data.get(key, default)
    if isinstance(value, dict):
        return json.dumps(value)
    if value=="None":
        return ''
    return str(value) if value is not None else default


def _get_token_data() -> dict | None:
    """获取整体token_data"""
    # 优先从Redis获取
    if redis_client.is_connected:
        try:
            value = redis_client._client.get(REDIS_TOKEN_PREFIX + "data")
            if value is not None:
                return json.loads(value)
        except Exception as e:
            print_warning(f"Redis读取失败，回退到本地文件: {e}")
    # 回退到本地文件
    return wx_cfg.get("token_data", None)


# ===== 每用户各自授权（多用户隔离） =====

def set_token_for_user(user_id: str, data: dict, ext_data: dict = None):
    """将微信授权保存到指定用户（替换全局单 token 方案）"""
    if not user_id or not data or data.get("token", "") == "":
        return
    try:
        from core.db import DB
        from core.models.wechat_auth import UserWechatAuth
        from datetime import datetime
        import json

        session = DB.get_session()
        rec = session.query(UserWechatAuth).filter(UserWechatAuth.user_id == user_id).first()
        token_data = {
            "token": data.get("token", ""),
            "cookie": data.get("cookies_str", ""),
            "fingerprint": data.get("fingerprint", ""),
            "expiry": data.get("expiry", {}) or {},
        }
        if ext_data is not None:
            token_data["ext_data"] = ext_data

        expiry_json = json.dumps(token_data["expiry"], ensure_ascii=False) if token_data["expiry"] else ""
        ext_json = json.dumps(token_data.get("ext_data"), ensure_ascii=False) if token_data.get("ext_data") else ""

        if rec:
            rec.token = token_data["token"]
            rec.cookie = token_data["cookie"]
            rec.fingerprint = token_data["fingerprint"]
            rec.expiry = expiry_json
            rec.ext_data = ext_json
            rec.login = True
            rec.updated_at = datetime.now()
        else:
            rec = UserWechatAuth(
                user_id=user_id,
                token=token_data["token"],
                cookie=token_data["cookie"],
                fingerprint=token_data["fingerprint"],
                expiry=expiry_json,
                ext_data=ext_json,
                login=True,
                updated_at=datetime.now()
            )
            session.add(rec)
        session.commit()
    except Exception as e:
        print_warning(f"保存用户微信授权失败: {e}")


def get_user_wx_session(user_id: str) -> dict | None:
    """读取指定用户的微信授权会话"""
    if not user_id:
        return None
    try:
        from core.db import DB
        from core.models.wechat_auth import UserWechatAuth
        import json

        session = DB.get_session()
        rec = session.query(UserWechatAuth).filter(UserWechatAuth.user_id == user_id).first()
        if not rec or not rec.token:
            return None

        expiry = {}
        ext_data = None
        try:
            expiry = json.loads(rec.expiry) if rec.expiry else {}
        except Exception:
            pass
        try:
            ext_data = json.loads(rec.ext_data) if rec.ext_data else None
        except Exception:
            pass

        return {
            "token": rec.token,
            "cookie": rec.cookie,
            "fingerprint": rec.fingerprint,
            "expiry": expiry,
            "ext_data": ext_data,
        }
    except Exception as e:
        print_warning(f"读取用户微信授权失败: {e}")
        return None


def get_active_wx_session(prefer_user_id: str = None) -> dict | None:
    """获取微信会话：优先使用指定用户的授权，回退全局（兼容旧数据/未授权用户）"""
    if prefer_user_id:
        s = get_user_wx_session(prefer_user_id)
        if s and s.get("token"):
            return s
    return _get_token_data()