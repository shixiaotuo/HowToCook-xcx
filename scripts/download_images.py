#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 GitHub 下载 HowToCook 菜谱的真实图片（本地仓库之前是 LFS 指针，全部失效），
压缩后打包进小程序主包 miniprogram/assets/recipes/<cat>/<name>/，
并生成 scripts/images-manifest.json 供 build-recipes.js 合并到 recipes.json。

下载通道：https://github.com/Anduin2017/HowToCook/raw/master/dishes/<cat>/<name>/<img>
（github.com raw 会自动把 LFS 指针解析为真实图片并重定向到 media.githubusercontent.com）
"""
import os
import sys
import json
import time
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from urllib.parse import quote
from urllib.request import Request, urlopen

from PIL import Image

REPO_DISHES = r"D:/tmp/HowToCook/HowToCook-master/dishes"
OUT_ROOT = r"D:/tmp/HowToCook/cookbook-miniprogram/miniprogram/assets/recipes"
MANIFEST = r"D:/tmp/HowToCook/cookbook-miniprogram/scripts/images-manifest.json"
BASE_URL = "https://github.com/Anduin2017/HowToCook/raw/master/dishes"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; cookbook-builder/1.0)"}
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
CATS_SKIP = {"template"}
MAX_WORKERS = 5
MAX_EDGE = 1000      # 长边最大像素
JPEG_QUALITY = 78

# 收集所有 (cat, name, img) 任务：图片都在  dishes/<cat>/<name>/  子目录里
def collect_tasks():
    tasks = []
    for cat in sorted(os.listdir(REPO_DISHES)):
        if cat in CATS_SKIP:
            continue
        catp = os.path.join(REPO_DISHES, cat)
        if not os.path.isdir(catp):
            continue
        for name in sorted(os.listdir(catp)):
            dishp = os.path.join(catp, name)
            if not os.path.isdir(dishp):
                continue  # 文件型菜（<cat>/<name>.md）在本仓库无独立图片目录，跳过
            for img in sorted(os.listdir(dishp)):
                if img.lower().endswith(IMG_EXT) and not img.lower().startswith("readme"):
                    tasks.append((cat, name, img))
    return tasks

def download_one(task):
    cat, name, img = task
    seg = [quote(p) for p in [cat, name, img]]
    url = BASE_URL + "/" + "/".join(seg)
    out_dir = os.path.join(OUT_ROOT, cat, name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, img)
    last_err = ""
    for attempt in range(4):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=40) as resp:
                data = resp.read()
            if len(data) < 600:  # 小于 600 字节基本是 LFS 指针/错误页，视为失败
                raise Exception("下载内容过小(%d字节)，疑似非真实图片" % len(data))
            # 压缩：统一转 JPEG（菜谱照片无透明通道需求），超长边则缩放
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
                # 原图是 png 也转 jpg 以省体积
                im.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
                out_data = buf.getvalue()
            except Exception:
                out_data = data  # 解码失败则保留原始字节
            with open(out_path, "wb") as f:
                f.write(out_data)
            return (task, True, len(out_data), "")
        except Exception as e:
            last_err = str(e)
            if attempt < 3:
                time.sleep(1.5 * (2 ** attempt))
    return (task, False, 0, last_err)

def main():
    tasks = collect_tasks()
    print("待下载图片任务数: %d" % len(tasks))
    ok, fail = 0, 0
    failed = []
    manifest = {}
    # 先清空旧输出目录，避免混入旧的 LFS 指针
    if os.path.isdir(OUT_ROOT):
        shutil.rmtree(OUT_ROOT)
    os.makedirs(OUT_ROOT, exist_ok=True)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(download_one, t) for t in tasks]
        done = 0
        for fut in as_completed(futs):
            task, success, size, err = fut.result()
            cat, name, img = task
            done += 1
            if success:
                ok += 1
                manifest.setdefault("%s/%s" % (cat, name), []).append(
                    "assets/recipes/%s/%s/%s" % (cat, name, img)
                )
            else:
                fail += 1
                failed.append((task, err))
            if done % 25 == 0 or done == len(tasks):
                print("进度 %d/%d  成功 %d  失败 %d" % (done, len(tasks), ok, fail))

    # manifest 排序图片，保证头图顺序稳定
    for k in manifest:
        manifest[k] = sorted(manifest[k])

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\n=== 完成 ===")
    print("成功: %d  失败: %d" % (ok, fail))
    print("manifest 写入: %s (菜品数 %d)" % (MANIFEST, len(manifest)))
    if failed:
        print("\n失败明细(前20条):")
        for (cat, name, img), err in failed[:20]:
            print("  %s/%s/%s -> %s" % (cat, name, img, err))
        print("...共 %d 条失败" % len(failed))

if __name__ == "__main__":
    main()
