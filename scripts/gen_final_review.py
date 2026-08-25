# -*- coding: utf-8 -*-
"""生成最终 360 封面勾选复核页 final_review.html。
数据来自 covers_manifest.json（{category,name,src,source}）。
功能：缩略图网格 + 勾选"需要修正" + 分类/来源/状态筛选 + 搜索 + 全选反选
      + 导出勾选清单(JSON/txt) + 导入恢复 + localStorage 自动保存 + 点图放大。
"""
import json, os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
man = json.load(open(os.path.join(base, "scripts", "covers_manifest.json"), encoding="utf-8"))

# 分类中文名映射
CAT_CN = {
    "aquatic": "水产", "meat_dish": "荤菜", "vegetable_dish": "素菜",
    "soup": "汤羹", "staple": "主食", "breakfast": "早餐",
    "semi_finished": "速食", "drink": "饮品", "condiment": "调味",
    "dessert": "甜点", "tip": "小贴士",
}
for m in man:
    m["cat_cn"] = CAT_CN.get(m["category"], m["category"])

data_json = json.dumps(man, ensure_ascii=False)

html = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>封面复核 · 勾选需要修正的图片</title>
<style>
  :root{
    --bg:#f5f6f8; --panel:#fff; --line:#e6e8ec; --txt:#1f2329; --sub:#8a9099;
    --red:#e54545; --redbg:#fff1f0; --green:#16a34a; --blue:#2563eb; --chip:#eef1f5;
  }
  *{box-sizing:border-box}
  body{font-family:-apple-system,"Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--txt);margin:0;padding:0;}
  header{position:sticky;top:0;z-index:20;background:var(--panel);border-bottom:1px solid var(--line);padding:10px 14px;}
  h1{font-size:16px;margin:0 0 8px;}
  .bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
  .bar input,.bar select{font-size:13px;padding:6px 8px;border:1px solid var(--line);border-radius:7px;background:#fff;color:var(--txt);}
  .bar input[type=search]{min-width:160px;}
  .btn{font-size:13px;padding:6px 12px;border:1px solid var(--line);border-radius:7px;background:var(--panel);color:var(--txt);cursor:pointer;}
  .btn:hover{background:var(--chip);}
  .btn.primary{background:var(--blue);border-color:var(--blue);color:#fff;}
  .btn.primary:hover{filter:brightness(1.05);}
  .btn.danger{background:var(--red);border-color:var(--red);color:#fff;}
  .btn.danger:hover{filter:brightness(1.05);}
  .stat{font-size:13px;color:var(--sub);margin-left:auto;}
  .stat b{color:var(--txt);}
  main{padding:12px 14px 60px;}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:10px;}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;position:relative;cursor:pointer;transition:border-color .12s;}
  .card:hover{border-color:#c4ccd6;}
  .card.flag{border-color:var(--red);box-shadow:0 0 0 2px var(--redbg) inset;}
  .card .img{width:100%;height:96px;background:#eef1f5;display:flex;align-items:center;justify-content:center;overflow:hidden;}
  .card .img img{width:100%;height:100%;object-fit:cover;display:block;}
  .card .cap{padding:5px 7px 6px;}
  .card .nm{font-size:12px;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .card .meta{display:flex;justify-content:space-between;align-items:center;margin-top:3px;font-size:11px;color:var(--sub);}
  .badge{font-size:10px;padding:1px 6px;border-radius:20px;}
  .badge.real{background:#e7f7ee;color:var(--green);}
  .badge.pexels{background:#eef2ff;color:var(--blue);}
  .chk{position:absolute;top:6px;right:6px;width:22px;height:22px;border-radius:6px;background:rgba(255,255,255,.92);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font-size:14px;color:var(--red);}
  .card.flag .chk{background:var(--red);color:#fff;border-color:var(--red);}
  .empty{color:var(--sub);text-align:center;padding:40px;font-size:14px;}
  /* lightbox */
  .lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.86);z-index:50;align-items:center;justify-content:center;flex-direction:column;}
  .lb.show{display:flex;}
  .lb img{max-width:90vw;max-height:80vh;border-radius:8px;}
  .lb .lbcap{color:#fff;margin-top:12px;font-size:14px;}
  .lb .lbclose{position:absolute;top:16px;right:20px;color:#fff;font-size:28px;cursor:pointer;}
  .lb .lbbadge{position:absolute;top:18px;left:20px;color:#fff;font-size:12px;opacity:.8;}
</style>
</head>
<body>
<header>
  <h1>封面复核 · 勾选需要修正的图片</h1>
  <div class="bar">
    <input type="search" id="q" placeholder="搜索菜名…">
    <select id="fcat"><option value="">全部分类</option></select>
    <select id="fsrc">
      <option value="">全部来源</option>
      <option value="real">真实图(166)</option>
      <option value="pexels">PEXELS补图(194)</option>
    </select>
    <select id="fstat">
      <option value="">全部状态</option>
      <option value="flag">仅看·需修正</option>
      <option value="ok">仅看·正常</option>
    </select>
    <button class="btn" id="selAll">全选当前</button>
    <button class="btn" id="selNone">清空当前</button>
    <button class="btn primary" id="exp">导出勾选</button>
    <button class="btn" id="imp">导入恢复</button>
    <input type="file" id="impFile" accept="application/json" style="display:none">
    <span class="stat">共 <b id="nTotal">0</b> · 已标需修正 <b id="nFlag" style="color:var(--red)">0</b></span>
  </div>
</header>
<main>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">没有匹配的图片</div>
</main>
<div class="lb" id="lb">
  <div class="lbbadge" id="lbBadge"></div>
  <div class="lbclose" id="lbClose">×</div>
  <img id="lbImg" src="">
  <div class="lbcap" id="lbCap"></div>
</div>
<script>
const DATA = __DATA__;
const LS_KEY = "cover_review_flags_v1";
const flags = new Set(JSON.parse(localStorage.getItem(LS_KEY) || "[]"));
function save(){ localStorage.setItem(LS_KEY, JSON.stringify([...flags])); }
function enc(p){ return "../" + p.split("/").map(encodeURIComponent).join("/"); }

// 分类下拉
const cats = [...new Set(DATA.map(d=>d.category))];
const catCn = Object.fromEntries(DATA.map(d=>[d.category,d.cat_cn]));
cats.forEach(c=>{ const o=document.createElement("option"); o.value=c; o.textContent=(catCn[c]||c)+" ("+DATA.filter(d=>d.category===c).length+")"; fcat.appendChild(o); });

const grid=document.getElementById("grid");
const empty=document.getElementById("empty");
function render(){
  const q=document.getElementById("q").value.trim().toLowerCase();
  const fc=document.getElementById("fcat").value;
  const fs=document.getElementById("fsrc").value;
  const fst=document.getElementById("fstat").value;
  grid.innerHTML="";
  let shown=0, flagShown=0;
  DATA.forEach((d,i)=>{
    if(fc && d.category!==fc) return;
    if(fs && d.source!==fs) return;
    if(q && !d.name.toLowerCase().includes(q) && !d.category.includes(q)) return;
    const isFlag=flags.has(i);
    if(fst==="flag" && !isFlag) return;
    if(fst==="ok" && isFlag) return;
    shown++; if(isFlag) flagShown++;
    const card=document.createElement("div");
    card.className="card"+(isFlag?" flag":"");
    card.dataset.i=i;
    card.innerHTML=`
      <div class="img"><img loading="lazy" src="${enc(d.src)}" onerror="this.parentNode.innerHTML='<span style=color:#999;font-size:12px>图缺失</span>'"></div>
      <div class="chk">${isFlag?"✓":""}</div>
      <div class="cap">
        <div class="nm" title="${d.name}">${d.name}</div>
        <div class="meta"><span>${d.cat_cn}</span><span class="badge ${d.source}">${d.source==="real"?"真实图":"PEXELS"}</span></div>
      </div>`;
    card.addEventListener("click",(e)=>{ if(e.target.closest(".chk")) return; toggle(i); });
    card.querySelector(".chk").addEventListener("click",(e)=>{ e.stopPropagation(); toggle(i); });
    card.querySelector(".img").addEventListener("click",(e)=>{ e.stopPropagation(); openLb(d); });
    grid.appendChild(card);
  });
  empty.style.display = shown? "none":"block";
  document.getElementById("nTotal").textContent=shown;
  document.getElementById("nFlag").textContent=flagShown;
}
function toggle(i){
  if(flags.has(i)) flags.delete(i); else flags.add(i);
  save(); render();
}
// 批量选择
document.getElementById("selAll").onclick=()=>{ applyToVisible(true); };
document.getElementById("selNone").onclick=()=>{ applyToVisible(false); };
function applyToVisible(on){
  const q=document.getElementById("q").value.trim().toLowerCase();
  const fc=document.getElementById("fcat").value, fs=document.getElementById("fsrc").value, fst=document.getElementById("fstat").value;
  DATA.forEach((d,i)=>{
    if(fc && d.category!==fc) return;
    if(fs && d.source!==fs) return;
    if(q && !d.name.toLowerCase().includes(q)) return;
    if(fst==="flag"){ if(!flags.has(i)) return; } // 仅看已标时全选无意义
    if(fst==="ok" && flags.has(i)) return;
    if(on) flags.add(i); else flags.delete(i);
  });
  save(); render();
}
// 导出
document.getElementById("exp").onclick=()=>{
  const list=DATA.filter((d,i)=>flags.has(i)).map(d=>({category:d.category,name:d.name,source:d.source}));
  if(!list.length){ alert("还没有勾选任何图片"); return; }
  const blob=new Blob([JSON.stringify(list,null,2)],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download="cover_fix_list.json"; a.click();
  const txt=list.map(d=>`${d.category}/${d.name}\t${d.source}`).join("\n");
  const b2=document.createElement("a"); b2.href=URL.createObjectURL(new Blob([txt],{type:"text/plain"})); b2.download="cover_fix_list.txt"; b2.click();
  alert(`已导出 ${list.length} 条需修正清单（JSON + TXT）`);
};
// 导入
document.getElementById("imp").onclick=()=>document.getElementById("impFile").click();
document.getElementById("impFile").onchange=(e)=>{
  const f=e.target.files[0]; if(!f) return;
  const r=new FileReader(); r.onload=()=>{
    try{ const arr=JSON.parse(r.result); flags.clear();
      arr.forEach(x=>{ const i=DATA.findIndex(d=>d.category===x.category&&d.name===x.name); if(i>=0) flags.add(i); });
      save(); render(); alert(`已恢复 ${flags.size} 条勾选`);
    }catch(err){ alert("解析失败："+err.message); }
  }; r.readAsText(f);
};
// lightbox
function openLb(d){ document.getElementById("lbImg").src=enc(d.src); document.getElementById("lbCap").textContent=d.name+" · "+d.cat_cn+" · "+(d.source==="real"?"真实图":"PEXELS补图"); document.getElementById("lb").classList.add("show"); }
document.getElementById("lbClose").onclick=()=>document.getElementById("lb").classList.remove("show");
document.getElementById("lb").onclick=(e)=>{ if(e.target.id==="lb") document.getElementById("lb").classList.remove("show"); };
document.addEventListener("keydown",e=>{ if(e.key==="Escape") document.getElementById("lb").classList.remove("show"); });
// 事件
["q","fcat","fsrc","fstat"].forEach(id=>document.getElementById(id).addEventListener("input",render));
render();
</script>
</body>
</html>
"""

html = html.replace("__DATA__", data_json)
out = os.path.join(base, "scripts", "final_review.html")
open(out, "w", encoding="utf-8").write(html)
print("written:", out, "size:", len(html), "items:", len(man))
