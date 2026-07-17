#!/usr/bin/env bash
# 云端手动部署裁剪脚本（与 Dockerfiles/cloud/Dockerfile 的删除逻辑一致）
# 用法：在云端机器拉取代码后，于仓库根目录执行  bash script/cloud_strip.sh
# 作用：物理删除微信驱动 / 本地管理 UI 代码，使最终运行目录不含任何微信依赖。
set -e

echo "[cloud-strip] 开始裁剪微信驱动相关代码 ..."
rm -rf core/wx core/article_content.py
rm -f  jobs/mps.py jobs/article.py jobs/failauth.py jobs/fetch_no_article.py
rm -rf driver views web_ui doc2pdf qtserver tools public
echo "[cloud-strip] 删除完成。"

echo "[cloud-strip] 校验：以下模块应全部显示 MISSING（云端不应存在）"
python - <<'PY'
import importlib.util
for m in ("driver", "core.wx", "core.article_content"):
    spec = importlib.util.find_spec(m)
    print("  MISSING" if spec is None else "  STILL PRESENT !!!", m)
PY
echo "[cloud-strip] 裁剪脚本结束。"
