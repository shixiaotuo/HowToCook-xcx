#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""方案A：用 HowToCookViewer 真实家常菜图全量替换 Pexels 封面。

封面图可靠来源 = 索引/LoadMore 卡片的 card-img-top；
中文菜名+分类 = 详情页上游路径 dishes/<cat>/<name>.md（解码）。
两者以 Detail/<id> 为键关联，再匹配本地 recipes.json 下载。

阶段：cards(卡片封面) -> join(关联菜名) -> download(下载转jpg)
"""
import os, sys, re, json, html as htmllib, subprocess, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
GEN_V2 = os.path.join(ROOT, "_gen_v2")
BASE = "https://howtocook.aiursoft.com"
RECIPES = os.path.join(ROOT, "data", "recipes.json")
CARDS_JSON = os.path.join(SCRIPTS, "viewer_cards.json")
DIAG_JSON = os.path.join(SCRIPTS, "_diag.json")
MAP_JSON = os.path.join(SCRIPTS, "viewer_map.json")
LOG = os.path.join(SCRIPTS, "_run.log")
WORKERS = 10

RE_CARD = re.compile(r'<a href="/Recipes/Detail/(\d+)"[^>]*>(.*?)</a>', re.S)
RE_IMG = re.compile(r'<img[^>]*src="([^"]*)"')
RE_COVER = re.compile(r'/download/recipe-images/([a-f0-9]+\.[a-zA-Z0-9]+)')

def log(*a):
    line = " ".join(str(x) for x in a)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)

def curl_text(url, max_time=30, retries=4):
    return subprocess.run(
        ["curl","-s","-L","--max-time",str(max_time),"--retry",str(retries),
         "--retry-delay","2","--retry-all-errors","-A","Mozilla/5.0",url],
        capture_output=True, text=True).stdout or ""

def curl_bytes(url, dst, max_time=45, retries=5):
    return subprocess.run(
        ["curl","-s","-L","--max-time",str(max_time),"--retry",str(retries),
         "--retry-delay","2","--retry-all-errors","-A","Mozilla/5.0","-o",dst,url]).returncode == 0

def parse_cards_from_html(h):
    out = {}
    for m in RE_CARD.finditer(h):
        did = int(m.group(1))
        inner = m.group(2)
        im = RE_IMG.search(inner)
        uuid = None
        if im:
            cm = RE_COVER.search(im.group(1))
            if cm:
                uuid = cm.group(1)
        out[did] = uuid
    return out

def stage_cards():
    if os.path.exists(LOG):
        os.remove(LOG)
    cards = {}
    h = curl_text(BASE + "/Recipes/Index")
    cards.update(parse_cards_from_html(h))
    log("[cards] index page cards:", len(cards))
    page = 2
    while True:
        try:
            body = curl_text(f"{BASE}/Recipes/LoadMore?page={page}")
            new = parse_cards_from_html(body)
            cards.update(new)
            log(f"[cards] page={page} new={len(new)} total={len(cards)}")
            if not new:
                log("[cards] no new cards, stop.")
                break
        except Exception as e:
            log(f"[cards] page={page} ERROR: {e}")
            log(traceback.format_exc())
            break
        page += 1
        time.sleep(0.3)
        if page > 60:
            log("[cards] safety stop at page 60")
            break
    withcov = sum(1 for v in cards.values() if v)
    json.dump({str(k): v for k, v in cards.items()}, open(CARDS_JSON,"w"), ensure_ascii=False, indent=1)
    log(f"[cards] done. {len(cards)} cards, {withcov} with cover -> {CARDS_JSON}")

def stage_join():
    cards = {int(k): v for k, v in json.load(open(CARDS_JSON)).items()}
    diag = json.load(open(DIAG_JSON, encoding="utf-8"))
    data = json.load(open(RECIPES, encoding="utf-8"))
    local = {}
    for r in data["recipes"]:
        if r.get("type") == "tip": continue
        c = r.get("category",""); n = r.get("name","")
        if c and n: local[(c,n)] = True
    # name -> category (assume unique names; build map)
    name2cat = {}
    for (c,n) in local:
        name2cat.setdefault(n, c)
    vmap = {}
    for did, uuid in cards.items():
        d = diag.get(str(did))
        if not d or not d.get("name"):
            continue
        name = d["name"]
        cat = name2cat.get(name)
        if cat is None:
            continue
        if not uuid:
            continue
        key = f"{cat}/{name}"
        vmap[key] = {"id": did, "uuid_ext": uuid, "matched": True}
    json.dump(vmap, open(MAP_JSON,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[join] local={len(local)} cards_with_name={sum(1 for d in diag.values() if d.get('name'))}")
    log(f"[join] wrote {len(vmap)} entries -> {MAP_JSON}")

def stage_download():
    vmap = json.load(open(MAP_JSON, encoding="utf-8"))
    data = json.load(open(RECIPES, encoding="utf-8"))
    local = set()
    for r in data["recipes"]:
        if r.get("type")=="tip": continue
        c=r.get("category",""); n=r.get("name","")
        if c and n: local.add((c,n))
    keys = list(vmap.keys())
    ok=0; fail=[]
    def do_one(key):
        v=vmap[key]; cat,name=key.split("/",1)
        dstdir=os.path.join(GEN_V2,cat,name); os.makedirs(dstdir,exist_ok=True)
        dst=os.path.join(dstdir,"cover.jpg")
        url=f"{BASE}/download/recipe-images/{v['uuid_ext']}?w=600"
        tmp=dst+".tmp"
        if not curl_bytes(url,tmp):
            return key,False,"dl_fail"
        try:
            im=Image.open(tmp); im.load()
            if im.mode in ("RGBA","P"): im=im.convert("RGB")
            if im.size[0]<20 or im.size[1]<20: raise ValueError("too small")
            im.save(dst,"JPEG",quality=88); os.remove(tmp)
            return key,True,""
        except Exception as e:
            try: os.remove(tmp)
            except Exception: pass
            return key,False,str(e)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs={ex.submit(do_one,k):k for k in keys}
        done=0
        for f in as_completed(futs):
            key,good,err=f.result(); done+=1
            if good: ok+=1
            else: fail.append((key,err))
            if done%50==0: log(f"[dl] {done}/{len(keys)} ok={ok} fail={len(fail)}")
    covered=set()
    for key in keys:
        cat,name=key.split("/",1)
        if os.path.exists(os.path.join(GEN_V2,cat,name,"cover.jpg")):
            covered.add((cat,name))
    missing=[f"{c}/{n}" for (c,n) in local if (c,n) not in covered]
    log("\n=== COVERAGE ===")
    log(f"local real dishes : {len(local)}")
    log(f"covers downloaded : {len(covered)}")
    log(f"missing           : {len(missing)}")
    for m in missing: log("  MISSING:", m)
    lines=["# 方案A：HowToCookViewer 仍未覆盖的菜（共 %d 道）"%len(missing),"",
           "本地有、但 Viewer（索引卡片）未提供封面的菜，需 AI 生成或手动补图：",""]
    for m in missing: lines.append(f"- [ ] {m}")
    open(os.path.join(SCRIPTS,"viewer_missing.md"),"w",encoding="utf-8").write("\n".join(lines))
    log("wrote viewer_missing.md")

if __name__=="__main__":
    try:
        stage=sys.argv[1] if len(sys.argv)>1 else "cards"
        {"cards":stage_cards,"join":stage_join,"download":stage_download}[stage]()
    except Exception:
        log("FATAL:", traceback.format_exc())
