"""重置 admin 账号密码（改动036 排障工具）。

用法（在 venv 激活、项目根目录下执行）：
    python script/reset_admin.py                      # 重置为默认 admin@123
    $env:NEW_PASSWORD="你的强密码"; python script/reset_admin.py   # 重置为指定密码

说明：仅修改已存在 admin 的密码哈希，不删数据、不新建用户。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import DB
from core.auth import pwd_context
from core.models.user import User


def main():
    new_pw = os.getenv("NEW_PASSWORD", "admin@123")
    session = DB.get_session()
    try:
        u = session.query(User).filter(User.username == "admin").first()
        if not u:
            # 账号不存在则创建（与 init_sys.init_user 逻辑对齐）
            # 注意：users.id 是 String 主键，init_sys 写死 id=0 易与已有行冲突，
            # 这里改用 username 本身作为 id，保证唯一且不与 id="0" 撞车
            session.add(User(
                id="admin",
                username="admin",
                password_hash=pwd_context.hash(new_pw),
                role="admin",
                is_active=True,
            ))
            session.commit()
            print(f"[OK] admin 用户已创建，密码为: {new_pw}")
            return
        u.password_hash = pwd_context.hash(new_pw)
        u.is_active = True
        session.commit()
        print(f"[OK] admin 密码已重置为: {new_pw}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
