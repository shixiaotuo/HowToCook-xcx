#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_pexels.py — 用 Pexels 官方 API 为 360 道食谱批量抓取封面图（免费图库，省 AI credits）。

用法:
  python scripts/fetch_pexels.py                 # 全量 360 道，后台跑
  python scripts/fetch_pexels.py --limit 5       # 先试 5 道验证
  PEXELS_KEY=xxxx python scripts/fetch_pexels.py  # 用环境变量传 key

说明:
  - 读两份 recipes.json，提取 360 道真菜（type!='tip'）。
  - 调 Pexels Search API（中文 query），从 15 张候选里挑「相关性打分最高」的一张，
    下载 large2x 直链到 _gen/<cat>/<name>/cover.jpg。
  - 传输层用 curl 子进程（urllib 经本沙箱代理链路会间歇性返回伪造 401，curl 稳定）。
  - 免费档 200 req/h，默认每请求 sleep 19s；遇 429 指数退避；其他非 200 长退避重试。
  - 匹配度判定：alt 描述命中「具体食材词」才算匹配（ok）；只命中泛词（food/dish…）记为 low（不确定）；
    搜不到/下载失败记为 fail（留空待手动）。
  - 凭据仅来自参数/env，绝不写入任何文件。
  - 报告 scripts/pexels_report.json 记录每道菜的 score / alt / status，供事后筛清单。
"""
import os
import sys
import json
import time
import argparse
import subprocess
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GEN_DIR = os.path.abspath(os.path.join(ROOT, "..", "_gen"))  # D:/tmp/HowToCook/_gen
DATA_FILES = [
    os.path.join(ROOT, "data", "recipes.json"),
    os.path.join(ROOT, "cloudfunctions", "getRecipes", "data", "recipes.json"),
]
API = "https://api.pexels.com/v1/search"

# 具体食材/烹饪词：命中即视为「有相关度」。权重高（5）。
SPECIFIC_EN = {
    "shrimp", "prawn", "crab", "crayfish", "crawfish", "lobster", "fish", "eel",
    "cod", "salmon", "tuna", "squid", "octopus", "clam", "oyster", "mussel",
    "beef", "pork", "chicken", "duck", "lamb", "meat", "bacon", "sausage",
    "tofu", "egg", "vegetable", "mushroom", "potato", "tomato", "onion",
    "pepper", "chili", "carrot", "broccoli", "cabbage", "spinach", "corn",
    "rice", "noodle", "pasta", "curry", "soup", "dumpling", "bun", "bread",
    "salad", "sushi", "pizza", "steak", "burger", "sauce", "garlic", "ginger",
    "bean", "lentil", "cheese", "chicken wing", "rib", "wing",
}
# 泛词：仅命中这些算弱相关（1）。
GENERIC_EN = {
    "food", "dish", "meal", "plate", "bowl", "cuisine", "delicious", "cooked",
    "recipe", "photography", "tasty", "fresh", "healthy", "gourmet", "restaurant",
}
# 中文词：alt 偶尔含中文，命中按具体食材计（3）。
CN_FOOD_WORDS = {
    "虾", "蟹", "鱼", "鳝", "牛肉", "猪肉", "鸡肉", "鸭", "羊肉", "肉", "菜",
    "饭", "面", "汤", "豆腐", "蛋", "咖喱", "小龙虾", "寿司", "沙拉", "包",
    "饺", "炒", "煎", "炸", "蒸", "烤", "煮",
}
SPEC_THRESHOLD = 5  # 命中任一具体食材(+5)即视为 ok；低于此归 low。


def relevance(query, alt):
    alt_l = (alt or "").lower()
    score = 0
    matched = []
    if query and query.lower() in alt_l:
        score += 10
        matched.append("query")
    for w in CN_FOOD_WORDS:
        if w in (alt or ""):
            score += 3
            matched.append(w)
    for w in SPECIFIC_EN:
        if w in alt_l:
            score += 5
            matched.append(w)
    for w in GENERIC_EN:
        if w in alt_l:
            score += 1
            matched.append(w)
    return score, matched


def _curl(args, timeout):
    # 让 curl 自己重试所有瞬错(含 TLS rc=35 / 429)，比 Python 层短退避更稳。
    base = ["curl", "-s", "--max-time", str(timeout),
            "--retry", "6", "--retry-delay", "5", "--retry-all-errors"]
    cmd = base + args
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 120)
        return r.returncode, r.stdout
    except subprocess.TimeoutExpired:
        return 124, b""


def search(key, query, per_page=15):
    url = API + "?" + urllib.parse.urlencode(
        {"query": query, "per_page": per_page, "locale": "zh-CN"})
    hdr = ["-H", "Authorization: " + key]
    for attempt in range(2):
        rc, out = _curl(["-f"] + hdr + [url], 20)
        if rc == 0:
            try:
                return json.loads(out)
            except Exception:
                pass
        print(f"    curl rc={rc}, retry {attempt + 1}/4", file=sys.stderr)
        time.sleep(5 + 5 * attempt)
    return None


def download(url, dest):
    for attempt in range(2):
        rc, _ = _curl(["-f", "-o", dest, url], 30)
        if rc == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0:
            return os.path.getsize(dest)
        print(f"    download rc={rc}, retry {attempt + 1}/4", file=sys.stderr)
        time.sleep(5 + 5 * attempt)
    return 0


def load_dishes():
    dishes = []
    seen = set()
    for p in DATA_FILES:
        d = json.load(open(p, encoding="utf-8"))
        for r in d["recipes"]:
            if r.get("type") == "tip":
                continue
            rid = r.get("id") or r.get("name")
            if rid in seen:
                continue
            seen.add(rid)
            dishes.append({"id": rid, "category": r.get("category", ""), "name": r.get("name", "")})
    return dishes


def wait_for_network(key, max_wait_min=40, probe="test"):
    """出口网络偶发 TLS 故障（代理握手断开，连 github 也 000）。
    开跑前先探测 Pexels 连通性，不通则每 60s 重试，直到恢复再继续。"""
    deadline = time.time() + max_wait_min * 60
    attempt = 0
    while True:
        attempt += 1
        res = search(key, probe, per_page=1)
        if res is not None:
            print(f"[net] reachable after {attempt} probe(s), start fetching", file=sys.stderr)
            return True
        if time.time() >= deadline:
            print(f"[net] STILL DOWN after {max_wait_min}min, giving up", file=sys.stderr)
            return False
        wait = 60
        print(f"[net] down, probe {attempt} failed; retry in {wait}s", file=sys.stderr)
        time.sleep(wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("PEXELS_KEY"))
    ap.add_argument("--limit", type=int, default=0, help="debug: only first N dishes")
    ap.add_argument("--sleep", type=float, default=19.0, help="seconds between requests (free tier 200/h)")
    ap.add_argument("--per-page", type=int, default=15)
    ap.add_argument("--max-wait-min", type=int, default=40, help="wait up to N min for network to recover before abort")
    args = ap.parse_args()
    if not args.key:
        print("ERROR: need PEXELS_KEY (env or --key)", file=sys.stderr)
        sys.exit(2)
    if not wait_for_network(args.key, args.max_wait_min):
        sys.exit(3)
    dishes = load_dishes()
    if args.limit:
        dishes = dishes[: args.limit]
    print(f"total dishes: {len(dishes)}")

    ok, low, fail = [], [], []
    details = []
    for i, d in enumerate(dishes):
        q = d["name"]
        print(f"[{i + 1}/{len(dishes)}] {q}", file=sys.stderr)
        res = search(args.key, q, args.per_page)
        if not res or not res.get("photos"):
            fail.append(d["id"])
            details.append({"id": d["id"], "name": q, "cat": d["category"],
                            "score": 0, "alt": "", "status": "fail"})
            print("   no result", file=sys.stderr)
            time.sleep(args.sleep)
            continue
        best_photo, best_score, best_matched = None, -1, []
        for photo in res["photos"]:
            s, m = relevance(q, photo.get("alt", ""))
            if s > best_score:
                best_score, best_photo, best_matched = s, photo, m
        if best_photo is None or best_score <= 0:
            fail.append(d["id"])
            details.append({"id": d["id"], "name": q, "cat": d["category"],
                            "score": best_score, "alt": "", "status": "fail"})
            print(f"   no relevant (score {best_score})", file=sys.stderr)
            time.sleep(args.sleep)
            continue
        status = "ok" if best_score >= SPEC_THRESHOLD else "low"
        alt_text = best_photo.get("alt", "")
        print(f"   alt={alt_text[:50]!r} score={best_score} matched={best_matched} -> {status}",
              file=sys.stderr)
        src = best_photo["src"].get("large2x") or best_photo["src"].get("large")
        dstdir = os.path.join(GEN_DIR, d["category"], d["name"])
        os.makedirs(dstdir, exist_ok=True)
        dst = os.path.join(dstdir, "cover.jpg")
        sz = download(src, dst)
        rec = {"id": d["id"], "name": q, "cat": d["category"],
               "score": best_score, "alt": alt_text, "status": status}
        if sz:
            (ok if status == "ok" else low).append(d["id"])
            rec["bytes"] = sz
            print(f"   saved {sz} bytes", file=sys.stderr)
        else:
            fail.append(d["id"])
            rec["status"] = "fail"
            print("   download failed", file=sys.stderr)
        details.append(rec)
        time.sleep(args.sleep)

    rep = {"total": len(dishes), "ok": ok, "low": low, "fail": fail, "details": details}
    with open(os.path.join(ROOT, "scripts", "pexels_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f"\nDONE ok={len(ok)} low={len(low)} fail={len(fail)} total={len(dishes)}")


if __name__ == "__main__":
    main()
