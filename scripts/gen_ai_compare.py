import os, json

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
proj = base
flagged = json.load(open(os.path.join(proj, "scripts/flagged_candidates.json"), encoding="utf-8"))
names = sorted({(x["category"], x["name"], x.get("source", "pexels")) for x in flagged})
# include the test dish 西红柿炒鸡蛋 (real->ai)
names.append(("vegetable_dish", "西红柿炒鸡蛋", "real"))
names = sorted(set(names))

cards = []
missing = []
for (cat, name, src) in names:
    old_p = os.path.join(proj, "_covers_final", cat, name, "cover.jpg")
    new_dir = os.path.join(proj, "_ai_covers", cat, name)
    new_files = [f for f in os.listdir(new_dir)] if os.path.isdir(new_dir) else []
    if not os.path.exists(old_p):
        missing.append(("old", cat, name))
    if not new_files:
        missing.append(("new", cat, name))
    rel_old = f"../../_covers_final/{cat}/{name}/cover.jpg" if os.path.exists(old_p) else ""
    rel_new = f"../../_ai_covers/{cat}/{name}/{new_files[0]}" if new_files else ""
    cards.append((cat, name, src, rel_old, rel_new))

html = []
html.append("<!doctype html><html lang='zh'><head><meta charset='utf-8'>")
html.append("<title>AI 生成封面 · 旧图 vs 新图 对照</title>")
html.append("""<style>
body{font-family:system-ui,'Microsoft YaHei',sans-serif;background:#0f1115;margin:0;padding:18px;color:#e8e8e8;}
h1{font-size:19px;margin:0 0 4px;}
.meta{color:#9aa0a6;margin-bottom:16px;font-size:13px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px;}
.card{background:#1a1d23;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.4);}
.ttl{font-size:14px;padding:10px 12px 6px;font-weight:600;}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;margin-left:6px;vertical-align:middle;}
.tag.pexels{background:#2b3a55;color:#9ec1ff;}
.tag.real{background:#234a2c;color:#9be8a0;}
.cmp{display:flex;}
.cmp figure{margin:0;flex:1;position:relative;border-top:1px solid #2a2e36;}
.cmp figcaption{position:absolute;top:6px;left:6px;font-size:10px;background:rgba(0,0,0,.6);padding:2px 6px;border-radius:5px;color:#fff;}
.cmp img{width:100%;height:170px;object-fit:cover;display:block;cursor:zoom-in;}
.cmp .old{border-right:1px solid #2a2e36;}
.note{font-size:11px;color:#8a9099;padding:0 12px 10px;}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;z-index:99;cursor:zoom-out;}
.lightbox img{max-width:92vw;max-height:92vh;border-radius:8px;}
</style></head><body>""")
html.append("<h1>AI 生成封面 · 旧图 vs 新图 对照</h1>")
html.append(f"<div class='meta'>共 {len(cards)} 道菜已用 AI 重新生成。左 = 原封面（真实图/PEXELS），右 = AI 生成新封面。点击任意图可放大。</div>")
html.append("<div class='grid'>")
for cat, name, src, rel_old, rel_new in cards:
    new_src = rel_new or "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E"
    old_src = rel_old or "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E"
    tagcls = "real" if src == "real" else "pexels"
    tagtxt = "真实图" if src == "real" else "PEXELS"
    html.append(f"<div class='card'><div class='ttl'>{name}<span class='tag {tagcls}'>{tagtxt}</span></div>")
    html.append("<div class='cmp'>")
    html.append(f"<figure class='old'><figcaption>原图</figcaption><img loading='lazy' src='{old_src}' onclick='zoom(this)'></figure>")
    html.append(f"<figure class='new'><figcaption>AI 新图</figcaption><img loading='lazy' src='{new_src}' onclick='zoom(this)'></figure>")
    html.append("</div>")
    html.append(f"<div class='note'>{cat} / {name}</div>")
    html.append("</div>")
html.append("</div>")
html.append("""<div class='lightbox' id='lb' onclick='this.style.display=\"none\"'><img id='lbimg' src=''></div>
<script>function zoom(img){document.getElementById('lbimg').src=img.src;document.getElementById('lb').style.display='flex';}</script>
</body></html>""")
open(os.path.join(proj, "scripts/ai_compare.html"), "w", encoding="utf-8").write("\n".join(html))
print("comparison page written:", len(cards), "cards, missing:", missing)
