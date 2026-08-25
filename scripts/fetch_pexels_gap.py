#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 Viewer 缺口菜（194 道），用【英文菜名】重抓 Pexels 并精匹配（解决中文直搜误匹配）。

阶段：
  translate : 用 mymemory 免费 API 把缺口菜名译英文，加 MANUAL 手工词典覆盖译错项，缓存 gap_translations.json
  scrape     : 英文查询搜 Pexels，做相关性校验（剔除非食物图，优先匹配菜名/主料词），滚动限流 190/h
  download   : 下载最佳封面到 _gen_pexels_gap/<cat>/<name>/cover.jpg

PEXELS_KEY 经环境变量传入（不落盘）。
"""
import os, sys, re, json, time, html as htmllib, subprocess, collections
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
GEN_GAP = os.path.join(ROOT, "_gen_pexels_gap")
MISSING_MD = os.path.join(SCRIPTS, "viewer_missing.md")
TRANS_JSON = os.path.join(SCRIPTS, "gap_translations.json")
REPORT_JSON = os.path.join(SCRIPTS, "pexels_gap_report.json")
LOG = os.path.join(SCRIPTS, "_run_gap.log")
WORKERS = 6
PX_KEY = os.environ.get("PEXELS_KEY", "")

FOOD = {"food","dish","meal","plate","cook","cooked","cuisine","recipe","restaurant",
        "bowl","chinese","asia","meat","chicken","beef","pork","lamb","fish","seafood",
        "shrimp","crab","lobster","squid","octopus","soup","noodle","noodles","rice","egg",
        "vegetable","veggie","tofu","dumpling","bun","bread","dessert","cake","fruit","salad",
        "curry","fried","roast","roasted","steam","steamed","grill","broth","sauce","spicy",
        "sichuan","hotpot","snack","breakfast","sandwich","pancake","porridge","pie","cookie",
        "drink","beverage","tea","juice","coffee","milk","smoothie","cocktail","wine","beer",
        "potato","corn","mushroom","bean","beans","pasta","noodles","cheese","congee","wonton",
        "dumplings","pancakes","pastry","salad","pork","prawns","pepper","onion","garlic","tomato"}

NONFOOD = {"ant","ants","insect","bug","landscape","mountain","ocean","sea","beach",
           "river","lake","person","woman","man","model","portrait","forest","tree","building",
           "city","car","dog","cat","flower","abstract","sky","cloud","sunset","road","street",
           "computer","phone","text","word","hand","foot","baby","child","group","team","gollum",
           "bomber","plasma","frostbite","sheepskin","shangzhi","chocard","anesthetic","laurel",
           "cinnamon","moss","surface","scratch","souffle","risotto","yakinari","spirulina",
           "blossom","pig","killing","fired","powder"}

CAT_EN = {"meat_dish":"chinese meat dish","aquatic":"seafood dish","vegetable_dish":"vegetable dish",
          "soup":"chinese soup","staple":"chinese noodles rice","breakfast":"chinese breakfast",
          "dessert":"chinese dessert","drink":"chinese drink","condiment":"chinese sauce",
          "semi-finished":"prepared food"}

# 手工修正：覆盖 mymemory 译错、会导致误匹配的菜名
MANUAL = {
    "蚂蚁上树": "glass noodles pork",
    "螺蛳粉": "luosifen rice noodles",
    "咕噜肉": "sweet and sour pork",
    "炒茄子": "stir fried eggplant",
    "凉拌油麦菜": "blanched leafy greens salad",
    "手抓饼": "scallion pancake",
    "葱油桂鱼": "steamed fish scallion oil",
    "小米辣炒肉": "stir fried pork chili",
    "生汆丸子汤": "pork meatball soup",
    "印度焖饭": "indian biryani",
    "鲜肉烧卖": "shaomai dumpling",
    "皮蛋豆腐": "preserved egg tofu",
    "速冻馄饨": "frozen wonton",
    "韩国麻药鸡蛋": "korean marinated eggs",
    "咖喱炒蟹": "curry crab",
    "陕北熬豆角": "braised green beans",
    "枝竹羊腩煲": "tofu skin lamb hot pot",
    "老干妈拌面": "noodles chili sauce",
    "蛋煎糍粑": "fried glutinous rice cake",
    "油酥": "crispy pastry",
    "小酥肉": "crispy fried pork",
    "豆角焖面": "braised noodles green beans",
    "桂圆红枣粥": "longan red date congee",
    "速冻汤圆": "frozen glutinous rice balls",
    "鸡蛋花": "egg drop soup",
    "太阳蛋": "sunny side up egg",
    "血浆鸭": "braised duck",
    "带把肘子": "pork knuckle",
    "杀猪菜": "northeastern pork stew",
    "牛油火锅底料": "hot pot soup base",
    "糖醋里脊": "sweet and sour pork",
    "蒸卤面": "steamed braised noodles",
    "印度烤饼": "naan bread",
    "香干肉丝": "shredded pork dried tofu",
    "蒜苔炒肉末": "stir fried pork garlic scapes",
    "凉拌金针菇": "cold enoki mushroom",
    "腐乳肉": "pork fermented tofu",
    "炒馍": "stir fried flatbread",
    "肉蟹煲": "crab clay pot",
    "杨枝甘露": "mango sago pomelo",
    "冰粉": "ice jelly dessert",
    "糖醋汁": "sweet and sour sauce",
    "水煮鱼": "sichuan boiled fish",
    "水煮肉片": "sichuan boiled pork",
    "番茄红酱": "tomato sauce",
    "黄瓜皮蛋汤": "cucumber preserved egg soup",
    "酸辣蕨根粉": "fermented fern noodles",
    "雷椒皮蛋": "pepper preserved egg",
    "简易版炒糖色": "caramel sauce",
    "金钱蛋": "fried egg coins",
    "可乐桶": "cola bucket cocktail",
    "B52轰炸机": "b52 cocktail",
    "虎皮肘子": "pork elbow",
    "利提巧卡": "liti chocard",
    "商芝肉": "shangzhi pork",
}

def log(*a):
    line=" ".join(str(x) for x in a)
    try:
        with open(LOG,"a",encoding="utf-8") as f: f.write(line+"\n")
    except Exception: pass
    print(line, flush=True)

def curl_text(url, max_time=30, retries=5, headers=None):
    cmd=["curl","-s","-L","--max-time",str(max_time),
        "--retry",str(retries),"--retry-delay","2","--retry-all-errors","-A","Mozilla/5.0"]
    for h in (headers or []):
        cmd += ["-H", h]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout or ""

def curl_bytes(url, dst, max_time=45, retries=6):
    return subprocess.run(["curl","-s","-L","--max-time",str(max_time),
        "--retry",str(retries),"--retry-delay","2","--retry-all-errors","-A","Mozilla/5.0","-o",dst,url]).returncode == 0

# ----- Pexels rolling rate limiter (190 / hour) -----
_REQ = collections.deque()
def _rate_limit(max_per_hour=190):
    while _REQ and time.time()-_REQ[0] > 3600: _REQ.popleft()
    if len(_REQ) >= max_per_hour:
        wait = 3600 - (time.time()-_REQ[0]) + 1
        if wait > 0:
            log(f"[rate] sleeping {wait:.0f}s to stay under {max_per_hour}/hr")
            time.sleep(wait)
    _REQ.append(time.time())

def load_gap():
    out=[]
    for line in open(MISSING_MD, encoding="utf-8"):
        line=line.strip()
        if line.startswith("- [ ]"):
            s=line[5:].strip()
            if "/" in s:
                c,n=s.split("/",1); out.append((c,n))
    return out

# ---------- translate ----------
def translate_mymemory(text):
    u=f"https://api.mymemory.translated.net/get?q={quote(text)}&langpair=zh|en"
    for _ in range(4):
        js=curl_text(u)
        try:
            d=json.loads(js)
            t=d["responseData"]["translatedText"]
            if t: return t
        except Exception:
            pass
        time.sleep(1)
    return text

def stage_translate():
    if os.path.exists(LOG): os.remove(LOG)
    gap=load_gap()
    cache={}
    if os.path.exists(TRANS_JSON):
        try: cache=json.load(open(TRANS_JSON,encoding="utf-8"))
        except Exception: cache={}
    done=0
    for (c,n) in gap:
        if n in MANUAL:
            cache[n]=MANUAL[n]; continue
        if n in cache: continue
        tr=translate_mymemory(n).strip().strip(":").strip()
        cache[n]=tr; done+=1
        time.sleep(0.3)
        if done%30==0: log(f"[tr] mymemory {done}/{len(gap)}")
    json.dump(cache, open(TRANS_JSON,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[tr] done. {len(cache)} translations (manual={len(MANUAL)}) -> {TRANS_JSON}")

# ---------- scrape ----------
def query_words(en):
    sw={"a","the","of","with","and","or","scrambled","fried","braised","steamed","boiled",
        "stir","chinese","dish","food","recipe","style","home","made","simple","easy","chocard",
        "shangzhi","surface","fired","powder"}
    return [w for w in re.findall(r"[a-z]+", en.lower()) if len(w)>2 and w not in sw]

def search_pexels(q):
    _rate_limit()
    url=f"https://api.pexels.com/v1/search?query={quote(q)}&per_page=15&page=1"
    js=curl_text(url, retries=5, max_time=30, headers=[f"Authorization: {PX_KEY}"])
    try:
        d=json.loads(js)
        return d.get("photos",[])
    except Exception:
        return []

def score_photo(photo, qwords):
    alt=(photo.get("alt") or "").lower()
    words=set(re.findall(r"[a-z]+", alt))
    score=0
    for w in qwords:
        if w in words: score+=2
    if any(f in words for f in FOOD): score+=1
    if any(nf in words for nf in NONFOOD): score=-1000
    return score

def pick_best(photos, qwords):
    best=None; best_s=-1000
    for p in photos:
        s=score_photo(p, qwords)
        if s>best_s:
            best_s=s; best=p
    if best_s>0 and best:
        return best, best_s
    return None, best_s

def stage_scrape():
    gap=load_gap()
    trans=json.load(open(TRANS_JSON,encoding="utf-8"))
    report=[]; ok=0; fail=0; retry=[]
    for (c,n) in gap:
        en=trans.get(n, n)
        q=re.sub(r"[^a-zA-Z0-9 ]"," ",en).strip()
        qwords=query_words(en)
        photos=search_pexels(q)
        best,s=pick_best(photos, qwords)
        used_q=q
        if best is None and qwords:
            # try key ingredient word only
            q2=" ".join(qwords[:3])
            photos2=search_pexels(q2)
            best,s=pick_best(photos2, qwords); used_q=q2
        if best is None:
            # last: first food-ish photo from primary results (no extra API call)
            for p in photos:
                a=(p.get("alt") or "").lower()
                if any(f in a for f in FOOD) and not any(nf in a for nf in NONFOOD):
                    best,s=p,1; used_q=q; break
        if best is None:
            fail+=1
            report.append({"cat":c,"name":n,"status":"fail","en":en,"score":s})
            log(f"[scrape] FAIL {n} (en={en})")
        else:
            ok+=1
            report.append({"cat":c,"name":n,"status":"ok","en":en,"score":s,"query":used_q,
                           "id":best.get("id"),
                           "src":best["src"]["large"] or best["src"]["large2x"],
                           "alt":best.get("alt","")})
        if (ok+fail)%30==0: log(f"[scrape] {ok+fail}/{len(gap)} ok={ok} fail={fail}")
    json.dump(report, open(REPORT_JSON,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[scrape] done. ok={ok} fail={fail} -> {REPORT_JSON}")

def stage_download():
    rep=json.load(open(REPORT_JSON,encoding="utf-8"))
    ok=0; fail=[]
    def do_one(r):
        c=r["cat"]; n=r["name"]
        dstdir=os.path.join(GEN_GAP,c,n); os.makedirs(dstdir,exist_ok=True)
        dst=os.path.join(dstdir,"cover.jpg")
        if not curl_bytes(r["src"], dst):
            return r["name"],False,"dl_fail"
        try:
            im=Image.open(dst); im.load()
            if im.mode in ("RGBA","P"): im=im.convert("RGB")
            if im.size[0]<20 or im.size[1]<20: raise ValueError("too small")
            im.save(dst,"JPEG",quality=88)
            return r["name"],True,""
        except Exception as e:
            try: os.remove(dst)
            except Exception: pass
            return r["name"],False,str(e)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs={ex.submit(do_one,r):r for r in rep if r["status"]=="ok"}
        done=0
        for f in as_completed(futs):
            nm,good,err=f.result(); done+=1
            if good: ok+=1
            else: fail.append((nm,err))
            if done%30==0: log(f"[dl] {done}/{len(futs)} ok={ok} fail={len(fail)}")
    log(f"[dl] downloaded ok={ok} fail={len(fail)}")
    for nm,err in fail: log("  DLFAIL",nm,err)

if __name__=="__main__":
    stage=sys.argv[1] if len(sys.argv)>1 else "translate"
    try:
        {"translate":stage_translate,"scrape":stage_scrape,"download":stage_download}[stage]()
    except Exception:
        import traceback; log("FATAL:",traceback.format_exc())
