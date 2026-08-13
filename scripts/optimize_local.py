#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后处理：对 download_images.py 下载的真实图片做体积裁剪，以满足微信主包 2MB 限制。
- 每道菜只保留第一张图作为头图（其余移到包外 _img_backup 备份，不进小程序包）
- 头图狠压（质量 45、长边 <= 500px），总体积控制在 ~1.4MB
- 刷新 scripts/images-manifest.json（仅含头图），供 build-recipes.js 合并
"""
import os
import json
import shutil
from PIL import Image
from io import BytesIO

ASSETS = r"D:/tmp/HowToCook/cookbook-miniprogram/miniprogram/assets/recipes"
BACKUP = r"D:/tmp/HowToCook/cookbook-miniprogram/_img_backup"
MANIFEST = r"D:/tmp/HowToCook/cookbook-miniprogram/scripts/images-manifest.json"
QUALITY = 28
MAX_EDGE = 340
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")

os.makedirs(BACKUP, exist_ok=True)
manifest = {}

for cat in sorted(os.listdir(ASSETS)):
    catp = os.path.join(ASSETS, cat)
    if not os.path.isdir(catp):
        continue
    for name in sorted(os.listdir(catp)):
        dishp = os.path.join(catp, name)
        if not os.path.isdir(dishp):
            continue
        imgs = sorted([f for f in os.listdir(dishp) if f.lower().endswith(IMG_EXT)])
        if not imgs:
            continue
        keep = imgs[0]
        # 其余图移出包（备份，可恢复）
        for extra in imgs[1:]:
            try:
                shutil.move(
                    os.path.join(dishp, extra),
                    os.path.join(BACKUP, "%s__%s__%s" % (cat, name, extra)),
                )
            except Exception as e:
                print("移动失败", cat, name, extra, e)
        # 狠压保留的头图
        p = os.path.join(dishp, keep)
        try:
            im = Image.open(p)
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
            im.save(buf, "JPEG", quality=QUALITY, optimize=True, progressive=True)
            with open(p, "wb") as f:
                f.write(buf.getvalue())
        except Exception as e:
            print("压缩失败", p, e)
        manifest["%s/%s" % (cat, name)] = [
            "assets/recipes/%s/%s/%s" % (cat, name, keep)
        ]

with open(MANIFEST, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

total = 0
for root, _, files in os.walk(ASSETS):
    for fn in files:
        total += os.path.getsize(os.path.join(root, fn))

print("保留头图数: %d  菜品数: %d" % (sum(len(v) for v in manifest.values()), len(manifest)))
print("assets 总体积: %.2f MB (%.0f KB)" % (total / 1024 / 1024, total / 1024))
print("注：被移出的多余图在 _img_backup/（不计入小程序包）")
