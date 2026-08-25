#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Aiursoft HowToCookViewer 全量抓取 360 道真实家常菜封面（方案 A：替换 Pexels）。

站点 https://howtocook.aiursoft.com 是 HowToCook 上游（Unlicense）的 CDN 重新托管，
封面为真实成品/步骤图，零误匹配、覆盖全。

数据流：
  enum    : 抓 /Recipes/Index + /Recipes/LoadMore?page=N 枚举全部 Detail/<id>（看 X-Has-More 头）
  parse   : 逐个 Detail 页解析 封面UUID 与 上游路径 dishes/<cat>/<实体编码中文名>/...md
  download: 下载 ?w=600 封面，Pillow 转 RGB jpg 存 _gen_v2/<cat>/<name>/cover.jpg

输出：
  scripts/viewer_ids.json   枚举到的 Detail id 列表
  scripts/viewer_map.json   { "<cat>/<name>": {id, uuid_ext, matched} }
  _gen_v2/<cat>/<name>/cover.jpg
"""
import os, sys, re, json, html as htmllib, subprocess, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
GEN_V2 = os.path.join(ROOT, "_gen_v2")
BASE = "https://howtocook.aiursoft.com"
RECIPES = os.path.join(ROOT, "data", "recipes.json")
IDS_JSON = os.path.join(SCRIPTS, "viewer_ids.json")
MAP_JSON = os.path.join(SCRIPTS, "viewer_map.json")

WORKERS = 12

def curl_text(url, max_time=30, retries=4):
    p = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(max_time),
         "--retry", str(retries), "--retry-delay", "2", "--retry-all-errors",
         "-A", "Mozilla/5.0", url],
        capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else ""

def curl_bytes(url, dst, max_time=45, retries=5):
    rc = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(max_time),
         "--retry", str(retries), "--retry-delay", "2", "--retry-all-errors",
         "-A", "Mozilla/5.0", "-o", dst, url]).returncode
    return rc == 0

def curl_headers_and_text(url, hdrfile, max_time=30, retries=4):
    rc = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(max_time),
         "--retry", str(retries), "--retry-delay", "2", "--retry-all-errors",
         "-A", "Mozilla/5.0", "-D", hdrfile, url],
        capture_output=True, text=True)
    return rc == 0, rc

# ---------- stage: enum ----------
def stage_enum():
    ids = []
    # first page
    h = curl_text(BASE + "/Recipes/Index")
    ids += re.findall(r'href="(/Recipes/Detail/(\d+))"', h)
    ids = [int(m) for _, m in re.findall(r'href="(/Recipes/Detail/(\d+))"', h)]
    seen = set(ids)
    page = 2
    while True:
        hdr = os.path.join(SCRIPTS, "_lm_hdr.txt")
        ok, _ = curl_headers_and_text(f"{BASE}/Recipes/LoadMore?page={page}", hdr)
        body = curl_text(f"{BASE}/Recipes/LoadMore?page={page}")
        has_more = "true"
        try:
            hh = open(hdr, encoding="utf-8", errors="replace").read()
            m = re.search(r'(?im)^X-Has-More:\s*(\w+)', hh)
            if m:
                has_more = m.group(1).lower()
        except Exception:
            pass
        new = [int(m) for _, m in re.findall(r'href="(/Recipes/Detail/(\d+))"', body)]
        added = 0
        for i in new:
            if i not in seen:
                seen.add(i); ids.append(i); added += 1
        print(f"[enum] page={page} new={added} total={len(ids)} X-Has-More={has_more}")
        if has_more != "true" or not new:
            break
        page += 1
        time.sleep(0.3)
    json.dump(sorted(set(ids)), open(IDS_JSON, "w"), ensure_ascii=False, indent=1)
    print(f"[enum] done. {len(ids)} detail ids -> {IDS_JSON}")

# ---------- stage: parse ----------
RE_COVER = re.compile(r'/download/recipe-images/([a-f0-9]+\.[a-zA-Z0-9]+)')
RE_UP = re.compile(r'dishes/([a-z_]+)/((?:&#x[0-9A-Fa-f]+;)+)/')

def parse_detail(did):
    h = curl_text(f"{BASE}/Recipes/Detail/{did}")
    if not h:
        return did, None
    covers = RE_COVER.findall(h)
    uuid_ext = covers[0] if covers else None
    m = RE_UP.search(h)
    cat, name = None, None
    if m:
        cat = m.group(1)
        enc = m.group(2)
        try:
            name = htmllib.unescape(enc)
        except Exception:
            name = enc
    return did, {"cat": cat, "name": name, "uuid_ext": uuid_ext}

def stage_parse():
    ids = json.load(open(IDS_JSON))
    vmap = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(parse_detail, d): d for d in ids}
        done = 0
        for f in as_completed(futs):
            did, info = f.result()
            done += 1
            if info and info["name"] and info["uuid_ext"]:
                key = f"{info['cat']}/{info['name']}"
                vmap[key] = {"id": did, "uuid_ext": info["uuid_ext"], "matched": False}
            if done % 50 == 0:
                print(f"[parse] {done}/{len(ids)}")
    json.dump(vmap, open(MAP_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[parse] done. {len(vmap)} recipes with cover+name -> {MAP_JSON}")
    # sample
    for k in list(vmap.keys())[:8]:
        print("   ", k, "->", vmap[k]["uuid_ext"])

# ---------- stage: download + match ----------
def stage_download():
    vmap = json.load(open(MAP_JSON, encoding="utf-8"))
    # local recipes
    data = json.load(open(RECIPES, encoding="utf-8"))
    local = {}
    for r in data["recipes"]:
        if r.get("type") == "tip":
            continue
        cat = r.get("category", "")
        name = r.get("name", "")
        if cat and name:
            local[(cat, name)] = True
    print(f"[dl] local real dishes = {len(local)} ; viewer recipes = {len(vmap)}")

    matched_keys = []
    for key, v in vmap.items():
        cat, name = key.split("/", 1)
        if (cat, name) in local:
            v["matched"] = True
            matched_keys.append(key)

    print(f"[dl] matched to local = {len(matched_keys)}")

    ok = 0
    fail = []
    def do_one(key):
        v = vmap[key]
        cat, name = key.split("/", 1)
        dstdir = os.path.join(GEN_V2, cat, name)
        os.makedirs(dstdir, exist_ok=True)
        dst = os.path.join(dstdir, "cover.jpg")
        url = f"{BASE}/download/recipe-images/{v['uuid_ext']}?w=600"
        tmp = dst + ".tmp"
        if not curl_bytes(url, tmp):
            return key, False, "download_fail"
        try:
            im = Image.open(tmp)
            im.load()
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            if im.size[0] < 20 or im.size[1] < 20:
                raise ValueError("too small")
            im.save(dst, "JPEG", quality=88)
            os.remove(tmp)
            return key, True, ""
        except Exception as e:
            try: os.remove(tmp)
            except Exception: pass
            return key, False, str(e)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(do_one, k): k for k in matched_keys}
        done = 0
        for f in as_completed(futs):
            key, good, err = f.result()
            done += 1
            if good:
                ok += 1
            else:
                fail.append((key, err))
            if done % 50 == 0:
                print(f"[dl] {done}/{len(matched_keys)} ok={ok} fail={len(fail)}")

    # save updated map
    json.dump(vmap, open(MAP_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # coverage report
    covered = set()
    for key in matched_keys:
        cat, name = key.split("/", 1)
        p = os.path.join(GEN_V2, cat, name, "cover.jpg")
        if os.path.exists(p):
            covered.add((cat, name))
    missing = [f"{c}/{n}" for (c, n) in local if (c, n) not in covered]
    print(f"\n=== COVERAGE ===")
    print(f"local real dishes : {len(local)}")
    print(f"covers downloaded : {len(covered)}")
    print(f"missing           : {len(missing)}")
    if missing:
        print("MISSING LIST:")
        for m in missing:
            print("  -", m)
    # write missing report
    lines = ["# 方案A：HowToCookViewer 仍未覆盖的菜（共 %d 道）" % len(missing), "",
             "以下是本地有、但 Viewer 未提供封面的菜，需 AI 生成或手动补图：", ""]
    for m in missing:
        lines.append(f"- [ ] {m}")
    open(os.path.join(SCRIPTS, "viewer_missing.md"), "w", encoding="utf-8").write("\n".join(lines))

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "enum"
    if stage == "enum":
        stage_enum()
    elif stage == "parse":
        stage_parse()
    elif stage == "download":
        stage_download()
    else:
        print("usage: fetch_viewer_covers.py [enum|parse|download]")
