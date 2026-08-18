import os, json, io
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, "_ai_covers")
OLD = os.path.join(ROOT, "_covers_final")
MANI = os.path.join(ROOT, "scripts", "covers_manifest.json")

# 1) 收集 _ai_covers 里的 42 道
changed = {}  # (cat,name) -> png path
for cat in sorted(os.listdir(AI)):
    cdir = os.path.join(AI, cat)
    if not os.path.isdir(cdir):
        continue
    for name in sorted(os.listdir(cdir)):
        d = os.path.join(cdir, name)
        if not os.path.isdir(d):
            continue
        pngs = [f for f in os.listdir(d) if f.lower().endswith(".png")]
        if pngs:
            changed[(cat, name)] = os.path.join(d, pngs[0])

print(f"待并入 AI 封面: {len(changed)} 道")

# 2) 转成 cover.jpg 覆盖到 _covers_final
ok = 0
for (cat, name), png in changed.items():
    tdir = os.path.join(OLD, cat, name)
    os.makedirs(tdir, exist_ok=True)
    im = Image.open(png).convert("RGB")
    im.save(os.path.join(tdir, "cover.jpg"), "JPEG", quality=90)
    ok += 1
print(f"已写入 cover.jpg: {ok} 张")

# 3) 更新 manifest source -> aigc
data = json.load(open(MANI, encoding="utf-8"))
recs = data if isinstance(data, list) else data["recipes"]
cnt = 0
for it in recs:
    if (it.get("category"), it.get("name")) in changed:
        it["source"] = "aigc"
        cnt += 1
json.dump(recs, open(MANI, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"manifest 标记 aigc: {cnt} 条")

# 4) 校验覆盖率 + 来源分布
dist = {}
miss = 0
for it in recs:
    dist[it.get("source")] = dist.get(it.get("source"), 0) + 1
    cj = os.path.join(OLD, it["category"], it["name"], "cover.jpg")
    if not os.path.exists(cj):
        miss += 1
print("来源分布:", dist)
print("缺失 cover.jpg:", miss)
