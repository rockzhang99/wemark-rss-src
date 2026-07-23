from core.models.user import User
from core.models.article import Article
from core.models.config_management import ConfigManagement
from core.models.feed import Feed
from core.models.message_task import MessageTask
from core.models.cascade_node import CascadeNode, CascadeSyncLog
from core.models.cascade_task_allocation import CascadeTaskAllocation
from core.models.filter_rule import FilterRule
from core.db import Db,DB
from core.config import cfg
from core.auth import pwd_context
import time
import os
from core.print import print_info, print_error
def init_user(_db: Db):
    try:
      # 注意: 绝不能用系统自带的 USERNAME 环境变量取默认管理员账号!
      # Windows 默认存在 USERNAME=Administrator, 若用 os.getenv("USERNAME","admin")
      # 会取到 Administrator 而非 admin, 导致登录 admin/admin@123 失败(改动042修复)。
      # 改用带命名空间前缀 WEMARK_ADMIN_USER / WEMARK_ADMIN_PASS, 默认 admin / admin@123。
      username = os.getenv("WEMARK_ADMIN_USER", "admin")
      password = os.getenv("WEMARK_ADMIN_PASS", os.getenv("PASSWORD", "admin@123"))
      session=_db.get_session()
      
      # 检查用户是否已存在
      existing_user = session.query(User).filter(User.username == username).first()
      
      if existing_user:
          # 用户已存在，更新为管理员权限
          existing_user.role = 'admin'
          existing_user.is_active = True
          session.commit()
          print_info(f"用户已存在，已更新为管理员权限：{username}")
      else:
          # 用户不存在，创建新用户
          import uuid
          session.add(User(
              id=0,
              username=username,
              password_hash=pwd_context.hash(password),
              role='admin',
              is_active=True,
          ))
          session.commit()
          print_info(f"初始化用户成功,请使用以下凭据登录：{username}")
    except Exception as e:
        # print_error(f"Init error: {str(e)}")
        pass
def migrate_user_roles(_db: Db):
    """角色体系重构（2026-07-16）：将历史普通用户(user)统一迁移为普通管理员(editor)。"""
    try:
        session = _db.get_session()
        updated = session.query(User).filter(User.role == 'user').update(
            {User.role: 'editor'}, synchronize_session=False
        )
        session.commit()
        if updated:
            print_info(f"角色迁移完成：{updated} 个普通用户已升级为普通管理员(editor)")
    except Exception:
        pass

def sync_models():
     # 同步模型到表结构
         from data_sync import DatabaseSynchronizer
         DB.create_tables()
         time.sleep(3)
         # 打包(frozen)态下源码目录 core/models 不可扫描, 且建表已由 DB.create_tables() 完成,
         # 故跳过 DatabaseSynchronizer(否则报找不到 core/models 路径); 开发态保留原行为
         import sys
         if not getattr(sys, 'frozen', False):
             synchronizer = DatabaseSynchronizer(db_url=cfg.get("db",""))
             synchronizer.sync()
         print_info("模型同步完成")

     

 
def init():
    sync_models()
    init_user(DB)
    migrate_user_roles(DB)
    # 将 config.yaml 同步到 config_management 表，确保配置信息页有数据可管理
    try:
        from core.yaml_db.store_config import ConfigManager
        manager = ConfigManager()
        manager.store_config_to_db()
    except Exception as e:
        print_error(f"同步配置到数据库失败: {e}")

if __name__ == '__main__':
    init()