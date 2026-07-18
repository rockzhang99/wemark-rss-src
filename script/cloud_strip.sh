#!/usr/bin/env bash
# 云端手动部署裁剪脚本（与 Dockerfiles/cloud/Dockerfile 的删除逻辑一致）
# 用法：在云端机器拉取代码后，于仓库根目录执行  bash script/cloud_strip.sh
# 作用：物理删除微信驱动 / 本地管理 UI 代码，使最终运行目录不含任何微信依赖。
#
# 重要：不要删除 tools/ 和 public/ ！
#   - tools/ 是通用工具（HTML 清洗、DB 修复、纯 Python 实现的 Redis 服务端等），
#     不含任何微信驱动，但 core/db.py、apis/article.py、apis/filter_rule.py 等云端
#     运行时模块都 import 它，删除会导致云端启动即崩溃。
#   - public/ 是 legacy 页面模板，web 路由可能引用，保留无害。
set -e

echo "[cloud-strip] 开始裁剪微信驱动相关代码 ..."
rm -rf core/wx core/article_content.py
rm -f  jobs/mps.py jobs/article.py jobs/failauth.py jobs/fetch_no_article.py
rm -rf driver views web_ui doc2pdf qtserver
echo "[cloud-strip] 删除完成（已保留 tools/ 与 public/，云端运行时依赖它们）。"

echo "[cloud-strip] 校验：以下模块应全部显示 MISSING（云端不应存在）"
python - <<'PY'
import importlib.util
for m in ("driver", "core.wx", "core.article_content"):
    spec = importlib.util.find_spec(m)
    print("  MISSING" if spec is None else "  STILL PRESENT !!!", m)
PY
echo "[cloud-strip] 裁剪脚本结束。"
