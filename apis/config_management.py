import os
import shutil
import yaml
from fastapi import APIRouter, Depends, HTTPException,Body,Path,Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from core.models.config_management import ConfigManagement
from core.db  import DB
from core.auth import get_current_user_or_ak, require_permissions
from .base import  success_response, error_response
from core.config import cfg
from core.yaml_db.store_config import ConfigManager
router = APIRouter(prefix="/configs", tags=["配置管理"])


@router.get("",summary="获取配置项列表")
def list_configs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """获取配置项列表（读取 config_management 数据库表，与编辑/删除操作同源）"""
    db = DB.get_session()
    try:
        total = db.query(ConfigManagement).count()
        # 如果表为空，自动从 config.yaml 同步一次，避免页面空白
        if total == 0:
            try:
                ConfigManager().store_config_to_db()
                total = db.query(ConfigManagement).count()
            except Exception as e:
                return error_response(code=500, message=f"从 config.yaml 同步配置失败: {e}")
        configs = db.query(ConfigManagement).offset(offset).limit(limit).all()
        return success_response(data={
            "list": [_config_to_dict(c) for c in configs],
            "page": {
                    "limit": limit,
                    "offset": offset
                },
                "total": total
        })
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.post("/sync", summary="从 config.yaml 同步配置到数据库")
def sync_configs(
    current_user: dict = Depends(require_permissions("admin"))
):
    """手动将当前 config.yaml 全量同步到 config_management 表（仅 admin）"""
    try:
        ConfigManager().store_config_to_db()
        return success_response(message="配置已同步到数据库")
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.get("/{config_key}", summary="获取单个配置项详情")
def get_config(
    config_key: str,
    current_user: dict = Depends(get_current_user_or_ak)
):
    db=DB.get_session()
    """获取单个配置项详情"""
    try:
        config = db.query(ConfigManagement).filter(ConfigManagement.config_key == config_key).first()
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        return success_response(data=_config_to_dict(config))
    except Exception as e:
        return error_response(code=500, message=str(e))

class ConfigManagementCreate(BaseModel):
    config_key: str
    config_value: str
    description: Optional[str] = None

@router.post("", summary="创建配置项")
def create_config(
    config_data: ConfigManagementCreate = Body(...),
    current_user: dict = Depends(require_permissions("admin"))
):
    db=DB.get_session()
    """创建配置项"""
    try:
        # 检查config_key是否已存在
        existing_config = db.query(ConfigManagement).filter(ConfigManagement.config_key == config_data.config_key).first()
        if existing_config:
            raise HTTPException(status_code=400, detail="Config with this key already exists")
        
        db_config = ConfigManagement(
            config_key=config_data.config_key,
            config_value=config_data.config_value,
            description=config_data.description
        )
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        _sync_yaml_from_db()
        return success_response(data=_config_to_dict(db_config), message="配置已创建并写回 config.yaml（重启服务后生效）")
    except Exception as e:
        db.rollback()
        return error_response(code=500, message=str(e))

@router.put("/{config_key}", summary="更新配置项")
def update_config(
    config_key: str=Path(...,min_length=1),
    config_data: ConfigManagementCreate = Body(...),
    current_user: dict = Depends(require_permissions("admin"))
):
    db=DB.get_session()
    """更新配置项"""
    try:
        db_config = db.query(ConfigManagement).filter(ConfigManagement.config_key == config_key).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        if config_data.config_value is not None:
            db_config.config_value = config_data.config_value
        if config_data.description is not None:
            db_config.description = config_data.description
        
        db.commit()
        db.refresh(db_config)
        _sync_yaml_from_db()
        return success_response(data=_config_to_dict(db_config), message="配置已更新并写回 config.yaml（重启服务后生效）")
    except Exception as e:
        db.rollback()
        return error_response(code=500, message=str(e))

@router.delete("/{config_key}",summary="删除配置项")
def delete_config(
    config_key: str,
    current_user: dict = Depends(require_permissions("admin"))
):
    db=DB.get_session()
    """删除配置项"""
    try:
        db_config = db.query(ConfigManagement).filter(ConfigManagement.config_key == config_key).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        db.delete(db_config)
        db.commit()
        _sync_yaml_from_db()
        return success_response(message="Config deleted successfully")
    except Exception as e:
        db.rollback()
        return error_response(code=500, message=str(e))


def _config_to_dict(config: ConfigManagement) -> dict:
    """将 ORM 对象转为纯字典，避免 SQLAlchemy 对象直接序列化的问题"""
    return {
        "config_key": config.config_key,
        "config_value": config.config_value,
        "description": config.description,
    }


def _sync_yaml_from_db():
    """将 config_management 表写回 config.yaml（先备份为 config.yaml.backup），使前台编辑真正生效。
    注意：标准 SQLAlchemy 的 ConfigManagement 无 .query 属性，故此处自行查询并写回，不依赖 generate_config_from_db。
    """
    try:
        import logging
        from core.yaml_db.store_config import ConfigManager
        db = DB.get_session()
        items = db.query(ConfigManagement).all()
        flat = {item.config_key: item.config_value for item in items}
        manager = ConfigManager()
        nested = manager._convert_to_nested_dict(flat)
        config_path = cfg.config_path or "config.yaml"
        backup_path = config_path + ".backup"
        if os.path.exists(config_path):
            shutil.copy2(config_path, backup_path)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(nested, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        logging.getLogger("ConfigManagement").error(f"写回 config.yaml 失败: {e}")
