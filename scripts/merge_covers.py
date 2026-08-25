#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并真实封面(_gen_v2) 与 Pexels 缺口封面(_gen_pexels_gap) 为最终 360 套。

产出：
  _covers_final/<cat>/<name>/cover.jpg      合并后的最终封面
  scripts/covers_manifest.json                {category,name,src(相对路径),source(real|pexels)} 列表
  scripts/final_gallery.html                  最终画廊（按分类+菜名）
  scripts/covers_coverage.txt                 覆盖率报告
"""
import os, json, shutil
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
GEN_V2 = os.path.join(ROOT, "_gen_v2")
GEN_GAP = os.path.join(ROOT, "_gen_pexels_gap")
FINAL = os.path.join(ROOT, "_covers_final")
RECIPES = os.path.join(ROOT, "data", "recipes.json")
MANIFEST = os.path.join(SCRIPTS, "covers_manifest.json")
GALLERY = os.path.join(SCRIPTS, "final_gallery.html")
COVER_TXT = os.path.join(SCRIPTS, "covers_coverage.txt")

def real_dishes():
    d=json.load(open(RECIPES, encoding="utf-8"))
    out=[]
    for r in d["recipes"]:
        if r.get("type")=="tip": continue
        c=r.get("category",""); n=r.get("name","")
        if c and n: out.append((c,n))
    return out

def collect(base):
    cov={}
    if not os.path.isdir(base): return cov
    for cat in os.listdir(base):
        cp=os.path.join(base,cat)
        if not os.path.isdir(cp): continue
        for name in os.listdir(cp):
            p=os.path.join(cp,name,"cover.jpg")
            if os.path.exists(p): cov[(cat,name)]=p
    return cov

def main():
    dishes=real_dishes()
    real=collect(GEN_V2)
    gap=collect(GEN_GAP)
    os.makedirs(FINAL, exist_ok=True)

    manifest=[]; covered=0; missing=[]
    by_src=Counter(); by_cat=Counter()
    for (c,n) in dishes:
        src_path=None; source=None
        if (c,n) in real:
            src_path=real[(c,n)]; source="real"
        elif (c,n) in gap:
            src_path=gap[(c,n)]; source="pexels"
        if src_path:
            dst=os.path.join(FINAL,c,n); os.makedirs(dst,exist_ok=True)
            shutil.copyfile(src_path, os.path.join(dst,"cover.jpg"))
            manifest.append({"category":c,"name":n,"src":f"_covers_final/{c}/{n}/cover.jpg","source":source})
            covered+=1; by_src[source]+=1; by_cat[c]+=1
        else:
            missing.append((c,n))

    json.dump(manifest, open(MANIFEST,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    lines=[]
    lines.append(f"本地真实菜总数: {len(dishes)}")
    lines.append(f"已覆盖: {covered}  (real={by_src['real']}  pexels={by_src['pexels']})")
    lines.append(f"缺口: {len(missing)}")
    lines.append("")
    lines.append("按分类覆盖:")

    cat_total=Counter(c for c,_ in dishes)
    for c in sorted(cat_total):
        lines.append(f"  {c}: {by_cat[c]}/{cat_total[c]}")
    if missing:
        lines.append("")
        lines.append("未覆盖菜品:")
        for c,n in missing: lines.append(f"  - {c}/{n}")
    open(COVER_TXT,"w",encoding="utf-8").write("\n".join(lines))

    # gallery
    items=sorted(manifest, key=lambda x:(x["category"],x["name"]))
    h=[]
    h.append("<!doctype html><html lang='zh'><head><meta charset='utf-8'>")
    h.append(f"<title>HowToCook 最终封面画廊 (共 {covered} 张)</title>")
    h.append("<style>body{font-family:system-ui,'Microsoft YaHei',sans-serif;background:#f6f7f9;margin:0;padding:16px;}h1{font-size:18px;}.meta{color:#666;margin:8px 0 12px;}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px;}.card{background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);}.card.real{border:2px solid #3a9;}.card.pexels{border:2px solid #e8a;}.tag{font-size:9px;padding:1px 4px;border-radius:3px;color:#fff;}.tag.real{background:#3a9;}.tag.pexels{background:#e8a;}img{width:100%;height:90px;object-fit:cover;display:block;}.cap{font-size:11px;padding:3px 6px;color:#333;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}.cat{font-size:10px;color:#999;padding:0 6px 6px;}</style>")
    h.append("</head><body>")
    h.append(f"<h1>HowToCook 最终封面画廊</h1><div class='meta'>共 <b>{covered}</b> 张：<span class='tag real'>真实图 {by_src['real']}</span> 来自 HowToCookViewer 上游同源；<span class='tag pexels'>Pexels {by_src['pexels']}</span> 为英文精匹配补图。缺口 {len(missing)} 道。</div>")
    h.append("<div class='grid'>")
    for it in items:
        rel=f"../{it['src']}"
        cls=it["source"]
        h.append(f"<div class='card {cls}'><img src='{rel}' loading='lazy'><div class='cap'>{it['name']}</div><div class='cat'>{it['category']}</div></div>")
    h.append("</div></body></html>")
    open(GALLERY,"w",encoding="utf-8").write("\n".join(h))

    print("\n".join(lines))
    print(f"\nmanifest -> {MANIFEST}")
    print(f"gallery  -> {GALLERY}")

if __name__=="__main__":
    main()
