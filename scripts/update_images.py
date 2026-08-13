#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键更新脚本：从 GitHub 拉取 HowToCook 菜谱封面图并打包进小程序主包。

为什么需要它：
  HowToCook 仓库的 Git LFS 额度已超额，git clone / git lfs pull 都拉不到真实图片
  （本地只会得到 130 字节的 LFS 指针文件）。本脚本改用「github.com raw 直链」通道，
  该通道走普通文件分发、不查 LFS 额度，可稳定拿到真实图片。

做什么：
  1. 扫描本地仓库的 markdown，解析每道菜的封面图引用（文件型 / 文件夹型都覆盖）
  2. 用 raw 直链下载每张封面（自动装 Pillow；失败自动降级通道）
  3. 压缩到微信主包 2MB 限制内（>1.85MB 自动再压一轮）
  4. 写入 miniprogram/assets/recipes/<分类>/<菜名>/cover.jpg
  5. 生成 images-manifest.json，并尝试重算 recipes.json

用法（Windows 一键见 update_images.bat）：
  python update_images.py [本地仓库dishes目录]
  例：python update_images.py "D:/tmp/111/HowToCook/dishes"
  不传参则自动探测几个常见位置，最后回退到默认路径。
"""
import os
import sys
import re
import json
import time
import shutil
import subprocess
from io import BytesIO
from urllib.parse import quote
from urllib.request import Request, urlopen

# ------------------------- 路径配置 -------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_ROOT = os.path.join(PROJECT_ROOT, "miniprogram", "assets", "recipes")
MANIFEST = os.path.join(SCRIPT_DIR, "images-manifest.json")
BUILD_JS = os.path.join(SCRIPT_DIR, "build-recipes.js")

REPO_OWNER = "Anduin2017"
REPO_NAME = "HowToCook"
BRANCH = "master"

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
SKIP_CATS = {"template"}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; cookbook-updater/1.0)"}
MAX_EDGE = 380
QUALITY_HI = 45
QUALITY_LO = 22
BUDGET_BYTES = 1.85 * 1024 * 1024   # 主包安全线
MAX_WORKERS = 6

# 掩护图优先匹配的关键字（命中其一就用它当封面）
COVER_HINTS = ("成品", "封面", "final", "cover", "主图", "完成")

# ------------------------- Pillow 自动安装 -------------------------
def safe_rmtree(p):
    """逐文件/逐目录删除，避免依赖系统回收站（沙箱/锁定文件场景更稳）"""
    if not os.path.isdir(p):
        return
    for root, dirs, files in os.walk(p, topdown=False):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
            except OSError:
                pass
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
    try:
        os.rmdir(p)
    except OSError:
        pass

def ensure_pillow():
    try:
        from PIL import Image
        return Image
    except ImportError:
        print("[*] 未检测到 Pillow，尝试自动安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
            from PIL import Image
            print("[*] Pillow 安装成功。")
            return Image
        except Exception as e:
            print("[!] Pillow 安装失败：%s" % e)
            print("[!] 将不进行压缩，直接保存原图（体积可能超 2MB，请留意微信上传限制）。")
            return None

# ------------------------- 仓库探测 -------------------------
def detect_repo_dishes():
    candidates = [
        r"D:/tmp/111/HowToCook/dishes",
        r"D:/tmp/HowToCook/HowToCook-master/dishes",
        r"D:/tmp/HowToCook/HowToCook/dishes",
        os.path.join(PROJECT_ROOT, "..", "HowToCook-master", "dishes"),
        os.path.join(PROJECT_ROOT, "..", "HowToCook", "dishes"),
    ]
    if len(sys.argv) > 1:
        p = sys.argv[1]
        if os.path.isdir(p):
            return os.path.abspath(p)
        print("[!] 参数指定的目录不存在：%s" % p)
    for c in candidates:
        if os.path.isdir(c):
            return os.path.abspath(c)
    return None

# ------------------------- 解析菜谱与图片引用 -------------------------
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")

def list_recipes(dishes_root):
    """返回 [(cat, name, md_abs_path, repo_root)]"""
    repo_root = os.path.dirname(dishes_root)
    recipes = []
    for cat in sorted(os.listdir(dishes_root)):
        if cat in SKIP_CATS:
            continue
        catp = os.path.join(dishes_root, cat)
        if not os.path.isdir(catp):
            continue
        for item in sorted(os.listdir(catp)):
            if item == "README.md":
                continue
            full = os.path.join(catp, item)
            if item.endswith(".md") and os.path.isfile(full):
                # 文件型菜谱：dishes/<cat>/<name>.md
                name = item[:-3]
                recipes.append((cat, name, full, repo_root))
            elif os.path.isdir(full):
                # 文件夹型菜谱：dishes/<cat>/<name>/<name>.md
                md = os.path.join(full, item + ".md")
                if os.path.isfile(md):
                    recipes.append((cat, name := item, md, repo_root))
    return recipes

def pick_cover(refs):
    """refs: [(repo_rel_path, basename)] -> 选一张作为封面"""
    if not refs:
        return None
    for hint in COVER_HINTS:
        for rel, base in refs:
            if hint in base.lower():
                return rel
    return refs[0][0]

def collect_image_refs(md_path, repo_root):
    """解析 markdown 图片引用，返回 [(repo相对路径, 文件名)]"""
    try:
        text = open(md_path, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        return []
    md_dir = os.path.dirname(md_path)
    out = []
    for m in IMG_RE.finditer(text):
        ref = m.group(1).strip()
        if ref.startswith("http://") or ref.startswith("https://"):
            continue  # 外链图跳过（不稳定）
        if "?" in ref:
            ref = ref.split("?", 1)[0]
        if not ref.lower().endswith(IMG_EXT):
            continue
        if ref.startswith("./") or ref.startswith("../") or ref.startswith("/"):
            ref = ref.lstrip("./")
            abs_p = os.path.normpath(os.path.join(md_dir, ref))
        else:
            abs_p = os.path.normpath(os.path.join(md_dir, ref))
        if not abs_p.startswith(repo_root):
            continue
        rel = os.path.relpath(abs_p, repo_root).replace("\\", "/")
        out.append((rel, os.path.basename(abs_p)))
    return out

# ------------------------- 下载 -------------------------
def build_url(repo_rel):
    segs = [quote(s) for s in repo_rel.split("/")]
    return "https://github.com/%s/%s/raw/%s/%s" % (REPO_OWNER, REPO_NAME, BRANCH, "/".join(segs))

def build_url_raw(repo_rel):
    segs = [quote(s) for s in repo_rel.split("/")]
    return "https://raw.githubusercontent.com/%s/%s/%s/%s" % (REPO_OWNER, REPO_NAME, BRANCH, "/".join(segs))

def download_bytes(repo_rel):
    """尝试 github.com raw，失败回退 raw.githubusercontent.com；返回 bytes 或 None"""
    for url in (build_url(repo_rel), build_url_raw(repo_rel)):
        for attempt in range(3):
            try:
                req = Request(url, headers=HEADERS)
                with urlopen(req, timeout=40) as resp:
                    data = resp.read()
                if len(data) < 600:
                    raise Exception("内容过小(%d字节)，疑似非真实图片" % len(data))
                return data
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.2 * (2 ** attempt))
    return None

def compress(Image, data, quality):
    try:
        im = Image.open(BytesIO(data))
        if im.mode in ("RGBA", "P", "LA"):
            im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > MAX_EDGE:
            if w >= h:
                nw, nh = MAX_EDGE, int(h * MAX_EDGE / w)
            else:
                nh, nw = MAX_EDGE, int(w * MAX_EDGE / h)
            im = im.resize((nw, nh))
        buf = BytesIO()
        im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        return buf.getvalue()
    except Exception:
        return data

# ------------------------- 主流程 -------------------------
def main():
    Image = ensure_pillow()
    dishes_root = detect_repo_dishes()
    if not dishes_root:
        print("[!] 找不到本地仓库 dishes 目录。请传参：python update_images.py <dishes目录>")
        sys.exit(1)
    print("[*] 仓库 dishes 目录：%s" % dishes_root)

    recipes = list_recipes(dishes_root)
    print("[*] 扫描到菜谱 %d 道" % len(recipes))

    # 清空旧输出
    if os.path.isdir(OUT_ROOT):
        safe_rmtree(OUT_ROOT)
    os.makedirs(OUT_ROOT, exist_ok=True)
    tmp_root = os.path.join(SCRIPT_DIR, "_img_tmp")
    if os.path.isdir(tmp_root):
        safe_rmtree(tmp_root)
    os.makedirs(tmp_root, exist_ok=True)

    manifest = {}
    ok = 0
    fail = []
    # 计划：每道菜下载一张封面
    plan = []
    for cat, name, md_path, repo_root in recipes:
        refs = collect_image_refs(md_path, repo_root)
        cover = pick_cover(refs)
        if cover:
            plan.append((cat, name, cover))

    print("[*] 需要下载封面的菜：%d 道" % len(plan))
    total = len(plan)
    done = 0
    for cat, name, rel in plan:
        data = download_bytes(rel)
        done += 1
        if not data:
            fail.append((cat, name, rel))
            if done % 20 == 0 or done == total:
                print("进度 %d/%d  成功 %d  失败 %d" % (done, total, ok, len(fail)))
            continue
        # 暂存原始字节到 tmp
        tdir = os.path.join(tmp_root, cat, name)
        os.makedirs(tdir, exist_ok=True)
        tpath = os.path.join(tdir, "raw.bin")
        with open(tpath, "wb") as f:
            f.write(data)
        ok += 1
        if done % 20 == 0 or done == total:
            print("进度 %d/%d  成功 %d  失败 %d" % (done, total, ok, len(fail)))

    # 压缩并写出（按预算自适应）
    def emit(quality):
        if os.path.isdir(OUT_ROOT):
            safe_rmtree(OUT_ROOT)
        os.makedirs(OUT_ROOT, exist_ok=True)
        man = {}
        for cat, name, rel in plan:
            tpath = os.path.join(tmp_root, cat, name, "raw.bin")
            if not os.path.isfile(tpath):
                continue
            raw = open(tpath, "rb").read()
            out = compress(Image, raw, quality) if Image else raw
            odir = os.path.join(OUT_ROOT, cat, name)
            os.makedirs(odir, exist_ok=True)
            opath = os.path.join(odir, "cover.jpg")
            with open(opath, "wb") as f:
                f.write(out)
            man["%s/%s" % (cat, name)] = ["assets/recipes/%s/%s/cover.jpg" % (cat, name)]
        return man

    manifest = emit(QUALITY_HI)
    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT_ROOT) for f in fs)
    if size > BUDGET_BYTES and Image:
        print("[*] 体积 %.2fMB 超预算，自动用更低画质再压一轮..." % (size / 1024 / 1024))
        manifest = emit(QUALITY_LO)
        size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT_ROOT) for f in fs)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    safe_rmtree(tmp_root)

    print("\n=== 完成 ===")
    print("封面下载成功：%d  失败：%d" % (ok, len(fail)))
    print("写入菜谱数：%d" % len(manifest))
    print("assets 总体积：%.2f MB" % (size / 1024 / 1024))
    print("manifest：%s" % MANIFEST)
    if fail:
        print("\n失败明细（前15条，多为该菜谱无图或图已失效）：")
        for cat, name, rel in fail[:15]:
            print("  %s/%s  (%s)" % (cat, name, rel))
        if len(fail) > 15:
            print("  ...共 %d 条" % len(fail))
    if size > 2 * 1024 * 1024:
        print("\n[!] 警告：体积已超过 2MB 主包上限，微信上传会失败。请减少封面或改用云存储方案。")

    # 尝试重算 recipes.json
    node = shutil.which("node")
    if node and os.path.isfile(BUILD_JS):
        print("\n[*] 正在重算 recipes.json ...")
        try:
            subprocess.check_call([node, BUILD_JS, dishes_root], cwd=PROJECT_ROOT)
            print("[*] recipes.json 已更新。")
        except Exception as e:
            print("[!] 重算失败：%s" % e)
            print("    请手动运行：node scripts/build-recipes.js \"%s\"" % dishes_root)
    else:
        print("\n[*] 未检测到 node，跳过 recipes.json 重算。")
        print("    请手动运行：node scripts/build-recipes.js \"%s\"" % dishes_root)

if __name__ == "__main__":
    main()
