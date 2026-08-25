# -*- coding: utf-8 -*-
"""针对 cover_fix_list.txt 里的 42 道菜，用更精准的英文检索词重新从 Pexels 抓候选封面。
不立即下载，只收集最佳候选的 CDN URL，供 replace_review 页左右对照确认。
用法：PEXELS_KEY=xxx python refetch_flagged.py
"""
import os, re, json, sys, time, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
LIST = r"E:/DOWN/cover_fix_list.txt"
OUT = os.path.join(BASE, "flagged_candidates.json")

PEXELS_KEY = os.environ.get("PEXELS_KEY", "")
if not PEXELS_KEY:
    print("ERROR: 需要 PEXELS_KEY 环境变量", file=sys.stderr); sys.exit(1)

# 42 道的人工优化英文检索词（比自动翻译更精准，针对之前误匹配/不贴切）
MANUAL = {
    "响油鳝丝": "stir fried eel shreds chinese",
    "微波葱姜黑鳕鱼": "black cod scallion ginger",
    "水煮鱼": "sichuan spicy boiled fish",
    "清蒸生蚝": "steamed oysters",
    "红烧鱼头": "braised fish head chinese",
    "红烧鲤鱼": "braised carp chinese",
    "肉蟹煲": "crab claypot seafood",
    "微波炉荷包蛋": "poached egg",
    "手抓饼": "scallion pancake chinese",
    "桂圆红枣粥": "red date longan congee",
    "葱油": "scallion oil sauce",
    "蒜香酱油": "garlic soy dipping sauce",
    "蔗糖糖浆": "sugar syrup",
    "红柚蛋糕": "grapefruit cake",
    "芋泥雪媚娘": "taro mochi dessert",
    "可乐桶": "cola cocktail punch",
    "乡村啤酒鸭": "beer braised duck",
    "冬瓜酿肉": "stuffed winter melon pork",
    "冷吃兔": "spicy rabbit sichuan",
    "可乐鸡翅": "cola chicken wings",
    "台式卤肉饭": "taiwanese braised pork rice",
    "商芝肉": "braised pork belly chinese",
    "姜葱捞鸡": "ginger scallion poached chicken",
    "田螺酿": "stuffed snails chinese",
    "虎皮肘子": "braised pork knuckle",
    "凉皮": "liangpi cold noodle",
    "炒馍": "stir fried flatbread",
    "热干面": "wuhan hot dry noodles",
    "蒸卤面": "braised noodles chinese",
    "酸辣蕨根粉": "spicy glass noodles",
    "醪糟小汤圆": "sweet rice balls soup",
    "凉拌油麦菜": "lettuce salad chinese",
    "印度葫芦丸子": "lauki kofta bottle gourd",
    "芹菜拌茶树菇": "celery mushroom stir fry",
    "茄子炖土豆": "eggplant potato stew",
    "蒲烧茄子": "grilled eggplant",
    "蚝油生菜": "lettuce oyster sauce",
    "西红柿炒鸡蛋": "tomato scrambled eggs",
    "酸辣土豆丝": "shredded potato stir fry",
    "陕北熬豆角": "braised green beans",
    "雷椒皮蛋": "century egg chili",
    "鸡蛋火腿炒黄瓜": "cucumber egg ham stir fry",
}

GENERIC = {"chinese", "dish", "food", "recipe", "sauce", "the", "a", "with", "and"}

def query_words(en):
    return [w for w in re.findall(r"[a-z]+", en.lower()) if len(w) >= 3 and w not in GENERIC]

def curl_text(url, max_time=30, retries=5):
    return subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(max_time), "--retry", str(retries),
         "--retry-delay", "2", "--retry-all-errors", "-A", "Mozilla/5.0",
         "-H", f"Authorization: {PEXELS_KEY}", url],
        capture_output=True, text=True).stdout or ""

def search_pexels(query, per_page=40):
    import urllib.parse as up
    q = re.sub(r"[^a-zA-Z0-9 ]", " ", query).strip()
    url = f"https://api.pexels.com/v1/search?query={up.quote(q)}&per_page={per_page}&page=1"
    js = curl_text(url)
    try:
        return json.loads(js).get("photos", [])
    except Exception:
        return []

def requests_quote(q):
    import urllib.parse as up
    return up.quote(q)

def score_photo(ph, qwords):
    alt = (ph.get("alt") or "").lower()
    if not alt:
        alt = (ph.get("url") or "")
    s = 0
    for w in qwords:
        if w in alt:
            s += 2 if len(w) >= 5 else 1
    # 惩罚明显非食物的词（风景/人像/动物）
    bad = ["landscape", "portrait", "woman", "man", "child", "dog", "cat", "beach", "mountain", "forest"]
    if any(b in alt for b in bad):
        s -= 3
    return s

def pick_best(photos, qwords):
    best, bs = None, -999
    for ph in photos:
        sc = score_photo(ph, qwords)
        # 轻微偏好高点赞（质量）
        sc += min(ph.get("likes", 0) // 200, 3)
        if sc > bs:
            bs, best = sc, ph
    return best, bs

def main():
    items = []
    with open(LIST, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "\t" not in line:
                continue
            cat_name, source = line.split("\t")
            cat, name = cat_name.split("/", 1)
            items.append((cat, name, source))
    print(f"读取 {len(items)} 道需替换")
    out = []
    for i, (cat, name, source) in enumerate(items, 1):
        en = MANUAL.get(name)
        if not en:
            print(f"  [{i}/{len(items)}] {name}: 无人工词，跳过", file=sys.stderr); continue
        qw = query_words(en)
        photos = search_pexels(en, per_page=40)
        best, sc = pick_best(photos, qw)
        if best:
            out.append({
                "category": cat, "name": name, "source_old": source,
                "query": en, "score": sc, "pexels_id": best["id"],
                "new_url": best["src"].get("large2x") or best["src"].get("large"),
                "new_alt": best.get("alt", ""),
                "old_src": f"_covers_final/{cat}/{name}/cover.jpg",
            })
            print(f"  [{i}/{len(items)}] {name:10} q={en:32} cand={len(photos):2} score={sc} alt={best.get('alt','')[:50]!r}")
        else:
            print(f"  [{i}/{len(items)}] {name}: 0 结果（词={en}）", file=sys.stderr)
        time.sleep(2.2)  # 限速，避 Pexels 200/hr
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n完成：{len(out)} 道拿到候选，写入 {OUT}")

if __name__ == "__main__":
    main()
