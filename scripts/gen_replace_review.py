# -*- coding: utf-8 -*-
"""生成 replace_review.html：42 道需替换菜的 旧图 vs 新候选 左右对照。
默认勾选"替换"，用户取消=保留旧图。导出选择清单供 apply_replace.py 使用。
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
cands = json.load(open(os.path.join(BASE, "flagged_candidates.json"), encoding="utf-8"))

CAT_CN = {
    "aquatic": "水产", "meat_dish": "荤菜", "vegetable_dish": "素菜",
    "soup": "汤羹", "staple": "主食", "breakfast": "早餐",
    "semi_finished": "速食", "drink": "饮品", "condiment": "调味",
    "dessert": "甜点", "tip": "小贴士",
}
for c in cands:
    c["cat_cn"] = CAT_CN.get(c["category"], c["category"])
    c["old_rel"] = f"_covers_final/{c['category']}/{c['name']}/cover.jpg"

data_json = json.dumps(cands, ensure_ascii=False)

html = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>封面替换复核 · 旧图 vs 新候选</title>
<style>
 :root{--bg:#f5f6f8;--panel:#fff;--line:#e6e8ec;--txt:#1f2329;--sub:#8a9099;--red:#e54545;--redbg:#fff1f0;--green:#16a34a;--blue:#2563eb;}
 *{box-sizing:border-box}
 body{font-family:-apple-system,"Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--txt);margin:0;}
 header{position:sticky;top:0;z-index:20;background:var(--panel);border-bottom:1px solid var(--line);padding:10px 14px;}
 h1{font-size:16px;margin:0 0 8px;}
 .bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
 .btn{font-size:13px;padding:6px 12px;border:1px solid var(--line);border-radius:7px;background:var(--panel);cursor:pointer;}
 .btn:hover{background:#eef1f5;}
 .btn.primary{background:var(--blue);border-color:var(--blue);color:#fff;}
 .btn.primary:hover{filter:brightness(1.05);}
 .stat{margin-left:auto;font-size:13px;color:var(--sub);}
 .stat b{color:var(--txt);}
 main{padding:12px 14px 60px;}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px;}
 .card.keep{border-color:var(--green);}
 .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}
 .nm{font-size:13px;font-weight:600;}
 .tag{font-size:11px;color:var(--sub);}
 .cmp{display:grid;grid-template-columns:1fr 1fr;gap:6px;}
 .cell{background:#eef1f5;border-radius:6px;overflow:hidden;}
 .cell .lab{font-size:11px;padding:2px 6px;background:#e3e7ed;color:var(--sub);}
 .cell img{width:100%;height:130px;object-fit:cover;display:block;cursor:zoom-in;}
 .newcell img{cursor:zoom-in;}
 .alt{font-size:11px;color:var(--sub);margin:6px 2px 4px;line-height:1.4;max-height:42px;overflow:hidden;}
 .foot{display:flex;align-items:center;gap:6px;margin-top:4px;}
 .foot input{width:16px;height:16px;}
 .foot label{font-size:13px;cursor:pointer;}
 .card.keep .foot label{color:var(--green);}
 .lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.86);z-index:50;align-items:center;justify-content:center;}
 .lb.show{display:flex;}
 .lb img{max-width:92vw;max-height:86vh;border-radius:8px;}
 .lb .x{position:absolute;top:16px;right:22px;color:#fff;font-size:30px;cursor:pointer;}
</style></head><body>
<header>
 <h1>封面替换复核 · 旧图 vs 新候选（共 <span id="n">0</span> 道）</h1>
 <div class="bar">
   <button class="btn" id="all">全选替换</button>
   <button class="btn" id="none">全部保留</button>
   <button class="btn primary" id="exp">导出选择</button>
   <span class="stat">将替换 <b id="nRep" style="color:var(--blue)">0</b> · 保留旧图 <b id="nKeep" style="color:var(--green)">0</b></span>
 </div>
</header>
<main><div class="grid" id="grid"></div></main>
<div class="lb" id="lb"><div class="x" id="lbx">×</div><img id="lbImg" src=""></div>
<script>
const DATA=__DATA__;
const LS="replace_flags_v1";
const flags=new Set(JSON.parse(localStorage.getItem(LS)||"[]"));
function enc(p){return "../"+p.split("/").map(encodeURIComponent).join("/");}
const grid=document.getElementById("grid");
function render(){
 let rep=0,keep=0; grid.innerHTML="";
 DATA.forEach((d,i)=>{
  const replace=flags.has(i); replace?rep++:keep++;
  const card=document.createElement("div");
  card.className="card"+(replace?"":" keep");
  card.innerHTML=`
   <div class="hd"><span class="nm">${d.name}</span><span class="tag">${d.cat_cn} · ${d.source_old==='real'?'原真实图':'原PEXELS'}</span></div>
   <div class="cmp">
     <div class="cell"><div class="lab">旧图（当前）</div><img loading="lazy" src="${enc(d.old_rel)}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%221%22 height=%221%22/%3E';this.alt='旧图缺失'"></div>
     <div class="cell newcell"><div class="lab">新候选（score ${d.score}）</div><img loading="lazy" src="${d.new_url}" onerror="this.alt='新图加载失败'"></div>
   </div>
   <div class="alt" title="${d.new_alt}">${d.new_alt||'（无描述）'}</div>
   <div class="foot"><input type="checkbox" id="c${i}" ${replace?"checked":""}><label for="c${i}">替换为新图</label></div>`;
  card.querySelector("#c"+i).addEventListener("change",e=>{ e.target.checked?flags.add(i):flags.delete(i); save(); render(); });
  card.querySelectorAll("img").forEach(im=>im.addEventListener("click",()=>openLb(im.src)));
  grid.appendChild(card);
 });
 document.getElementById("n").textContent=DATA.length;
 document.getElementById("nRep").textContent=rep;
 document.getElementById("nKeep").textContent=keep;
}
function save(){localStorage.setItem(LS,JSON.stringify([...flags]));}
document.getElementById("all").onclick=()=>{DATA.forEach((_,i)=>flags.add(i));save();render();};
document.getElementById("none").onclick=()=>{flags.clear();save();render();};
document.getElementById("exp").onclick=()=>{
 const list=DATA.filter((_,i)=>flags.has(i)).map(d=>({category:d.category,name:d.name,pexels_id:d.pexels_id,new_url:d.new_url,new_alt:d.new_alt}));
 if(!list.length){alert("没有勾选要替换的项");return;}
 const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(list,null,2)],{type:"application/json"}));a.download="replace_choices.json";a.click();
 const t=list.map(d=>`${d.category}/${d.name}\t${d.pexels_id}`).join("\n");
 const b=document.createElement("a");b.href=URL.createObjectURL(new Blob([t],{type:"text/plain"}));b.download="replace_choices.txt";b.click();
 alert(`将替换 ${list.length} 道，已导出选择清单`);
};
function openLb(src){document.getElementById("lbImg").src=src;document.getElementById("lb").classList.add("show");}
document.getElementById("lbx").onclick=()=>document.getElementById("lb").classList.remove("show");
document.getElementById("lb").onclick=e=>{if(e.target.id==="lb")document.getElementById("lb").classList.remove("show");};
render();
</script></body></html>
"""
html = html.replace("__DATA__", data_json)
out = os.path.join(BASE, "replace_review.html")
open(out, "w", encoding="utf-8").write(html)
print("written:", out, "size:", len(html), "items:", len(cands))
