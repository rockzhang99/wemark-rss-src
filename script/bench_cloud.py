#!/usr/bin/env python3
"""云端多租户压测脚本（改动036 阶段4 · 多租户压测）
用法：
  # 压测 RSS 读取（tenant 隔离下只看到自己数据）
  python script/bench_cloud.py --host https://rss.your-domain.com \
      --ak WKxxx --sk SKxxx --mode rss --concurrency 20 --requests 200

  # 压测 Agent 上传写入
  python script/bench_cloud.py --host https://rss.your-domain.com \
      --ak WKxxx --sk SKxxx --mode upload --concurrency 10 --requests 100

  # 多租户并发：传入多对 --ak/--sk，模拟不同租户同时访问
  python script/bench_cloud.py --host https://rss.your-domain.com \
      --ak WK1 --sk SK1 --ak WK2 --sk SK2 --mode rss --concurrency 40 --requests 400
"""
import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    print("需安装 requests: pip install requests")
    sys.exit(1)


def do_rss(host, ak, sk):
    url = f"{host}/rss"
    headers = {"Authorization": f"AK-SK {ak}:{sk}"}
    t0 = time.time()
    r = requests.get(url, headers=headers, timeout=10)
    return time.time() - t0, r.status_code


def do_upload(host, ak, sk, idx):
    url = f"{host}/api/v1/wx/agent/articles"
    headers = {"Authorization": f"AK-SK {ak}:{sk}", "Content-Type": "application/json"}
    mp = f"MP_BENCH_{ak[-6:]}"
    payload = {
        "mp_id": mp,
        "articles": [{
            "id": f"bench_{idx}_{ak[-6:]}",
            "title": f"bench {idx}",
            "url": "https://mp.weixin.qq.com/s/bench",
            "publish_time": int(time.time()),
            "content": "<p>bench</p>",
        }],
    }
    t0 = time.time()
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    return time.time() - t0, r.status_code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--ak", action="append", default=[])
    ap.add_argument("--sk", action="append", default=[])
    ap.add_argument("--mode", choices=["rss", "upload"], default="rss")
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--requests", type=int, default=200)
    args = ap.parse_args()

    if len(args.ak) != len(args.sk) or not args.ak:
        print("--ak 与 --sk 必须成对出现且至少一个")
        sys.exit(1)

    tasks = []
    for i in range(args.requests):
        ak = args.ak[i % len(args.ak)]
        sk = args.sk[i % len(args.sk)]
        tasks.append((ak, sk, i))

    latencies, codes = [], {}
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = []
        for ak, sk, idx in tasks:
            if args.mode == "rss":
                futures.append(ex.submit(do_rss, args.host, ak, sk))
            else:
                futures.append(ex.submit(do_upload, args.host, ak, sk, idx))
        for f in as_completed(futures):
            try:
                dt, code = f.result()
                latencies.append(dt)
                codes[code] = codes.get(code, 0) + 1
            except Exception:
                codes["ERR"] = codes.get("ERR", 0) + 1
    elapsed = time.time() - t_start

    print(f"模式={args.mode} 并发={args.concurrency} 总请求={args.requests} 耗时={elapsed:.2f}s")
    print(f"QPS={args.requests / elapsed:.1f}  状态码={codes}")
    if latencies:
        latencies.sort()
        p50 = statistics.median(latencies)
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        print(f"延迟(秒) p50={p50:.3f} p95={p95:.3f} p99={p99:.3f} max={max(latencies):.3f}")


if __name__ == "__main__":
    main()
