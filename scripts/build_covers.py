#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上游 HowToCook 图 + Pexels 图 混合构建 360 封面。
- 上游图从 media.githubusercontent.com (Git LFS 真文件) 下载，Pillow 转 jpg 存 _gen_up
- 合并优先级: 上游成品.jpg > Pexels ok > 上游步骤图(仅替 Pexels low/fail) > 留空
- 输出 final_covers.json + final_missing.md
"""
import os, sys, json, time, subprocess, urllib.parse
from PIL import Image
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
GEN = os.path.join(ROOT, "_gen")          # Pexels 图
GEN_UP = os.path.join(ROOT, "_gen_up")    # 上游图
MEDIA = "https://media.githubusercontent.com/media/Anduin2017/HowToCook/master/"
RECIPES = os.path.join(ROOT, "data", "recipes.json")
UP_CP = {}  # (cat,name) -> bool 是否上游成品图

def safe_remove(p):
    try:
        if os.path.exists(p):
            os.remove(p)
    except OSError:
        pass  # 沙箱 safe-delete 拦截时忽略

def valid_image(path):
    if not os.path.exists(path):
        return False
    try:
        im = Image.open(path)
        im.load()
        return im.size[0] > 20 and im.size[1] > 20
    except Exception:
        return False

def load_dishes():
    d = json.load(open(RECIPES, encoding="utf-8"))
    out, seen = [], set()
    for r in d["recipes"]:
        if r.get("type") == "tip":
            continue
        rid = r.get("id") or r.get("name")
        if rid in seen:
            continue
        seen.add(rid)
        out.append((r.get("category", ""), r.get("name", "")))
    return out

def download_upstream():
    m = json.load(open(os.path.join(SCRIPTS, "upstream_map.json"), encoding="utf-8"))
    ok, fail = 0, []
    for it in m["matched"]:
        cat, name, src = it["cat"], it["name"], it["src"]
        url = MEDIA + urllib.parse.quote(src, safe="/")
        dstdir = os.path.join(GEN_UP, cat, name)
        os.makedirs(dstdir, exist_ok=True)
        dst = os.path.join(dstdir, "cover.jpg")
        rc = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "45", "--retry", "5",
             "--retry-delay", "3", "--retry-all-errors", "-o", dst, url]
        ).returncode
        if rc != 0:
            fail.append(src + f" (rc={rc})")
            safe_remove(dst)
            continue
        try:
            im = Image.open(dst)
            im.load()
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            if im.size[0] < 20 or im.size[1] < 20:
                raise ValueError("image too small")
            im.save(dst, "JPEG", quality=88)
            ok += 1
        except Exception as e:
            fail.append(src + f" ({e})")
            safe_remove(dst)
        time.sleep(0.25)
    print(f"[upstream] downloaded ok={ok} fail={len(fail)}")
    for f in fail[:20]:
        print("   FAIL", f)
    return ok, fail

def main():
    print("== 1) 下载上游图 ==")
    download_upstream()

    print("== 2) 读取 Pexels 报告 ==")
    rep = json.load(open(os.path.join(SCRIPTS, "pexels_report.json"), encoding="utf-8"))
    px = {}
    for d in rep["details"]:
        p = os.path.join(GEN, d["cat"], d["name"], "cover.jpg")
        px[(d["cat"], d["name"])] = {
            "status": d["status"], "alt": d.get("alt", ""),
            "valid": valid_image(p)}

    print("== 3) 混合合并 ==")
    dishes = load_dishes()
    final, missing = [], []
    for cat, name in dishes:
        up_path = os.path.join(GEN_UP, cat, name, "cover.jpg")
        up_ok = valid_image(up_path)
        p = px.get((cat, name), {})
        px_status = p.get("status")
        px_ok = p.get("valid", False)

        if up_ok and (UP_CP.get((cat, name)) or px_status != "ok"):
            decide = "upstream"
        elif px_status == "ok" and px_ok:
            decide = "pexels"
        elif up_ok:
            decide = "upstream"
        elif px_status in ("low", "fail") and px_ok:
            decide = "pexels"  # 留着 Pexels 图（虽 low）
        else:
            decide = None

        if decide == "upstream":
            final.append({"cat": cat, "name": name, "source": "upstream",
                          "local": up_path, "up_chengpin": UP_CP.get((cat, name), False)})
        elif decide == "pexels":
            final.append({"cat": cat, "name": name, "source": "pexels",
                          "local": os.path.join(GEN, cat, name, "cover.jpg"),
                          "up_chengpin": False})
        else:
            missing.append({"cat": cat, "name": name,
                            "reason": "上游无有效图 & Pexels 无有效图"})

    json.dump({"dishes": final},
              open(os.path.join(SCRIPTS, "final_covers.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"[final] 有封面 {len(final)} 道, 缺 {len(missing)} 道")
    print("   来源分布:", dict(Counter(d["source"] for d in final)))
    print("   其中上游成品图:", sum(1 for d in final if d.get("up_chengpin")))

    lines = ["# 最终仍缺封面的菜（需 AI 生成或手动补图）", "",
             f"> 共 {len(missing)} 道。其余 {len(final)} 道已混合并存盘。", ""]
    for mm in missing:
        lines.append(f"- [ ] **{mm['name']}** （{mm['cat']}）— {mm['reason']}")
    open(os.path.join(SCRIPTS, "final_missing.md"), "w", encoding="utf-8").write("\n".join(lines))
    print("   已写 scripts/final_missing.md")

if __name__ == "__main__":
    m = json.load(open(os.path.join(os.path.dirname(__file__), "upstream_map.json"), encoding="utf-8"))
    for it in m["matched"]:
        UP_CP[(it["cat"], it["name"])] = ("成品" in it["src"])
    main()
