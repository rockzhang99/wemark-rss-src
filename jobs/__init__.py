# 混合架构(改动036) 阶段3：云端镜像不含微信驱动(driver/core.wx)，
# 导入 jobs 包时若 mps 因缺少 driver 而失败，静默跳过（不影响云端 RSS/上传 API）。
try:
    from jobs.mps import *  # noqa: F401,F403
except Exception:
    pass