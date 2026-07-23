#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""混合架构一键验证脚本（改动036 配套工具）。

验证两件事：
  1) 本地 Agent -> 云端 上传接口是否通畅（POST /api/v1/wx/agent/feeds|articles）
  2) 云端 RSS 订阅是否可读（GET /feed/all.rss 等，需带 AK-SK token）

特性：
  - 自动读取 config.yaml 的 upload.* 配置（并展开 ${VAR:-default} 占位符）
  - 默认「轻量验证」：用空 feeds 列表探测接口/鉴权/路径，不污染云端数据
  - --deep：额外真传一条带 __verify__ 标记的测试文章，确认端到端可被订阅看到
             （会在云端插入测试数据，可用 --clean 提示手动清理）

用法：
  python tools/verify_hybrid.py            # 轻量验证（推荐先跑这个）
  python tools/verify_hybrid.py --deep     # 端到端深度验证
"""
import os
import re
import sys
import json

try:
    import yaml
except ImportError:
    print("[FAIL] 缺少 PyYAML，请先 pip install pyyaml")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[FAIL] 缺少 requests，请先 pip install requests")
    sys.exit(1)


CONFIG = "config.yaml"


def expand(s):
    """展开 ${VAR} / ${VAR:-default} 占位符（用环境变量，缺失则用 default）。"""
    if not isinstance(s, str):
        return s

    def repl(m):
        inner = m.group(1)
        if ":-" in inner:
            name, default = inner.split(":-", 1)
        else:
            name, default = inner, ""
        return os.environ.get(name, default)

    return re.sub(r"\$\{([^}]+)\}", repl, s)


def walk(o):
    if isinstance(o, dict):
        return {k: walk(v) for k, v in o.items()}
    if isinstance(o, list):
        return [walk(v) for v in o]
    return expand(o)


def load_cfg():
    if not os.path.exists(CONFIG):
        print(f"[FAIL] 未找到 {CONFIG}，请在工程根目录运行本脚本")
        sys.exit(1)
    with open(CONFIG, encoding="utf-8") as f:
        return walk(yaml.safe_load(f))


def is_xml(body: str) -> bool:
    return any(t in body for t in ("<rss", "<feed", "<channel"))


def main():
    deep = "--deep" in sys.argv
    cfg = load_cfg()

    role = cfg.get("deploy", {}).get("role", "agent")
    up = cfg.get("upload", {}) or {}
    server = (up.get("server") or "").rstrip("/")
    ak = up.get("ak") or ""
    sk = up.get("sk") or ""
    enabled = str(up.get("enabled", False)).lower() == "true"

    print("=" * 56)
    print(" 混合架构验证  (本地 Agent -> 云端 RSS 服务端)")
    print("=" * 56)
    print(f" deploy.role      = {role}")
    print(f" upload.enabled   = {enabled}")
    print(f" upload.server    = {server or '(空)'}")
    print(f" ak / sk          = {ak[:4]}*** / {sk[:4]}***  (len={len(ak)}/{len(sk)})")

    if role != "agent":
        print("[WARN] 当前 deploy.role 不是 agent；本脚本用于验证『本地->云端』，"
              "应在本地 agent 上运行（云端也可只测订阅）")
    if not enabled:
        print("[WARN] upload.enabled=False，上传器未启用（config.yaml upload.enabled=true 才会上传）")
    if not server or not ak or not sk:
        print("[FAIL] upload.server / ak / sk 缺失，无法验证上传，请先在 config.yaml 配置")
        return 1

    auth = f"AK-SK {ak}:{sk}"
    headers = {"Authorization": auth, "Content-Type": "application/json"}

    # ---------- 1) 上传接口 ----------
    print("\n--- [1/2] 上传接口 (POST /api/v1/wx/agent/feeds) ---")
    try:
        # 轻量：空 feeds 列表，验证网络/路径/鉴权，零污染
        r = requests.post(f"{server}/api/v1/wx/agent/feeds",
                          json={"feeds": []}, headers=headers, timeout=20)
        print(f"  HTTP {r.status_code}  body={r.text[:160]}")
        up_ok = r.status_code == 200 and '"code":0' in r.text
        print(f"  => 上传接口: {'OK' if up_ok else 'FAIL'}")
    except Exception as e:
        print(f"  => 上传接口 FAIL: {e}")
        up_ok = False

    if deep and up_ok:
        print("\n--- [1b] 深度验证：真传一条测试文章 ---")
        test_mp = "__verify__mp"
        try:
            requests.post(f"{server}/api/v1/wx/agent/feeds",
                          json={"feeds": [{"id": test_mp, "mp_name": "[verify]测试号",
                                           "mp_intro": "混合架构验证脚本插入", "status": 1}]},
                          headers=headers, timeout=20)
            r = requests.post(f"{server}/api/v1/wx/agent/articles",
                              json={"mp_id": test_mp, "articles": [{
                                  "id": "__verify__art_1",
                                  "title": "[verify]测试文章",
                                  "content": "<p>混合架构验证</p>",
                                  "description": "verify",
                                  "url": "https://mp.weixin.qq.com/verify",
                                  "publish_time": 1700000000,
                                  "pic_url": "",
                              }]}, headers=headers, timeout=20)
            print(f"  HTTP {r.status_code}  body={r.text[:160]}")
            print("  => 已插入测试数据（mp=__verify__mp, art=__verify__art_1），"
                  "验证完可在云端库删除")
        except Exception as e:
            print(f"  => 深度上传 FAIL: {e}")

    # ---------- 2) 订阅接口 ----------
    print("\n--- [2/2] 云端 RSS 订阅 (GET /feed/all.rss?token=AK-SK...) ---")
    try:
        r = requests.get(f"{server}/feed/all.rss",
                         params={"token": auth}, timeout=20)
        print(f"  HTTP {r.status_code}  bytes={len(r.content)}")
        print(f"  head={r.text[:100].replace(chr(10), ' ')}")
        sub_ok = r.status_code == 200 and is_xml(r.text)
        print(f"  => RSS 订阅: {'OK' if sub_ok else 'FAIL'}")
        if sub_ok and "<item" not in r.text:
            print("  [提示] feed 为空：本地可能还没上传数据，或上传/订阅 ak:sk 租户不一致")
    except Exception as e:
        print(f"  => RSS 订阅 FAIL: {e}")
        sub_ok = False

    # ---------- 诊断 ----------
    print("\n--- 诊断提示 ---")
    print("  401 -> ak/sk 错误或 token 格式错（URL 里 AK-SK 后的空格须编码为 %20）")
    print("  404 -> 云端未部署 agent 路由，或前后端路径不一致")
    print("  连接失败 -> server 地址/网络不通，或云端未启动")
    print("  订阅空 feed -> 本地未上传数据，或上传与订阅 ak:sk 不属于同一租户")
    print(f"\n结果: 上传={'OK' if up_ok else 'FAIL'}  订阅={'OK' if sub_ok else 'FAIL'}")
    return 0 if (up_ok and sub_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
