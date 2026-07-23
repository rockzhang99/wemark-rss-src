#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""混合架构(改动036) 本地 Agent -> 云端 一次性补传工具。

上传器后台线程以较大 batch_size(默认50)上传时，个别批次可能因请求体过大被
nginx 返回 413(payload too large) 而整体失败。该批次文章未落到云端(云端按 id
幂等去重，且高水位 watermark 仅在上传成功后才推进)，于是出现"本地有、云端缺"
的残留文章。本脚本以较小 batch_size 触发一次 catch-up 补传。

- 基于高水位 watermark，只补传本地大于 watermark 的残留文章，可断点续传；
- 云端按文章 id 幂等去重(check_exist)，重复推送安全(added=0)；
- --force 可忽略 watermark 全量重推(适合怀疑 watermark 不准时兜底)；
- --batch 指定每批条数(默认5，明显小于触发 413 的阈值)。

用法(在工程根目录运行)：
  python tools/resync_cloud.py                 # 按高水位补传残留文章(默认 batch=5)
  python tools/resync_cloud.py --batch 5       # 显式指定每批条数
  python tools/resync_cloud.py --force         # 忽略高水位，全量重推
"""
import os
import sys
import argparse

# 允许在工程任意子目录以 `python tools/resync_cloud.py` 运行
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from core.uploader import CloudUploader


def main():
    ap = argparse.ArgumentParser(description="混合架构：本地->云端 一次性补传")
    ap.add_argument("--batch", type=int, default=5,
                    help="每批文章条数(默认5，避开 413)")
    ap.add_argument("--force", action="store_true",
                    help="忽略高水位 watermark，全量重推(云端按 id 去重，安全)")
    args = ap.parse_args()

    up = CloudUploader()
    up.init()
    if not up.enabled:
        print("[FAIL] upload.enabled 未开启，请先在 config.yaml 的 upload.* 配置 "
              "server/ak/sk 并设 enabled=true")
        return 1
    up.batch_size = args.batch

    if args.force:
        up._watermark = {}
        print("[INFO] --force：忽略高水位，将全量重推(云端按 id 去重，安全)")

    print(f"[INFO] server={up.server}  ak={up.ak[:4]}***  batch_size={up.batch_size}")
    # 一次性同步，不启动后台循环
    up._sync_feeds()
    up._sync_articles()
    print("[DONE] 补传完成。可本地跑 `python tools/verify_hybrid.py --deep` "
          "或云端 GET /feed/all.rss 验证文章已同步。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
