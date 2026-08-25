import os, io, base64, html, json
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, "_ai_covers")
OLD = os.path.join(ROOT, "_covers_final")
MAXW = 480
QUALITY = 82

def enc(path):
    try:
        im = Image.open(path).convert("RGB")
        if im.width > MAXW:
            h = int(im.height * MAXW / im.width)
            im = im.resize((MAXW, h), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=QUALITY)
        b = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b}"
    except Exception as e:
        return None

# 旧图来源
src_map = {}
try:
    data = json.load(open(os.path.join(ROOT, "scripts", "covers_manifest.json"), encoding="utf-8"))
    recs = data.get("recipes", data) if isinstance(data, dict) else data
    for it in recs:
        src_map[(it.get("category"), it.get("name"))] = it.get("source", "?")
except Exception:
    pass

cards = []
for cat in sorted(os.listdir(AI)):
    cdir = os.path.join(AI, cat)
    if not os.path.isdir(cdir):
        continue
    for name in sorted(os.listdir(cdir)):
        d = os.path.join(cdir, name)
        if not os.path.isdir(d):
            continue
        pngs = [f for f in os.listdir(d) if f.lower().endswith(".png")]
        if not pngs:
            continue
        new_uri = enc(os.path.join(d, pngs[0]))
        old_jpg = os.path.join(OLD, cat, name, "cover.jpg")
        old_uri = enc(old_jpg) if os.path.exists(old_jpg) else None
        src = src_map.get((cat, name), "?")
        tagcls = "pexels" if src == "pexels" else ("real" if src == "real" else "ai")
        tagtxt = {"pexels": "PEXELS", "real": "真实图", "ai": "AI"}.get(src, src)
        tag = f"<span class='tag {tagcls}'>{tagtxt}</span>"
        old_img = f"<img loading='lazy' src='{old_uri}' onclick='zoom(this)'>" if old_uri else "<div class='empty'>无旧图</div>"
        new_img = f"<img loading='lazy' src='{new_uri}' onclick='zoom(this)'>" if new_uri else "<div class='empty'>生成失败</div>"
        cards.append(f"""<div class='card'><div class='ttl'>{html.escape(name)}{tag}</div>
<div class='cmp'>
<figure class='old'><figcaption>原图</figcaption>{old_img}</figure>
<figure class='new'><figcaption>AI 新图</figcaption>{new_img}</figure>
</div>
<div class='note'>{html.escape(cat)} / {html.escape(name)}</div>
</div>""")

html_doc = f"""<!doctype html><html lang='zh'><head><meta charset='utf-8'>
<title>AI 生成封面 · 旧图 vs 新图 对照</title>
<style>
body{{font-family:system-ui,'Microsoft YaHei',sans-serif;background:#0f1115;margin:0;padding:18px;color:#e8e8e8;}}
h1{{font-size:19px;margin:0 0 4px;}}
.meta{{color:#9aa0a6;margin-bottom:16px;font-size:13px;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px;}}
.card{{background:#1a1d23;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.4);}}
.ttl{{font-size:14px;padding:10px 12px 6px;font-weight:600;}}
.tag{{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;margin-left:6px;vertical-align:middle;}}
.tag.pexels{{background:#2b3a55;color:#9ec1ff;}}
.tag.real{{background:#234a2c;color:#9be8a0;}}
.tag.ai{{background:#4a2b40;color:#e8a0c8;}}
.cmp{{display:flex;}}
.cmp figure{{margin:0;flex:1;position:relative;border-top:1px solid #2a2e36;}}
.cmp figcaption{{position:absolute;top:6px;left:6px;font-size:10px;background:rgba(0,0,0,.6);padding:2px 6px;border-radius:5px;color:#fff;}}
.cmp img{{width:100%;height:200px;object-fit:cover;display:block;cursor:zoom-in;}}
.cmp .empty{{height:200px;display:flex;align-items:center;justify-content:center;color:#666;font-size:12px;}}
.cmp .old{{border-right:1px solid #2a2e36;}}
.note{{font-size:11px;color:#8a9099;padding:0 12px 10px;}}
.lightbox{{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;z-index:99;cursor:zoom-out;}}
.lightbox img{{max-width:92vw;max-height:92vh;border-radius:8px;}}
</style></head><body>
<h1>AI 生成封面 · 旧图 vs 新图 对照</h1>
<div class='meta'>共 {len(cards)} 道菜已用 AI 重新生成（图片已内嵌，无需联网）。左 = 原封面，右 = AI 新图。点击任意图可放大。</div>
<div class='grid'>
{''.join(cards)}
</div>
<div class='lightbox' id='lb' onclick="this.style.display='none'"><img id='lbimg' src=''></div>
<script>
function zoom(i){{document.getElementById('lbimg').src=i.src;document.getElementById('lb').style.display='flex';}}
</script>
</body></html>"""

out = os.path.join(ROOT, "ai_compare.html")
open(out, "w", encoding="utf-8").write(html_doc)
print("生成:", out, "卡片数:", len(cards), "大小:", round(os.path.getsize(out)/1024/1024, 2), "MB")
