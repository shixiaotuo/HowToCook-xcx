# -*- coding: utf-8 -*-
# 补齐 8 道菜缺失的 ingredientDetails（用量计算），从上游 Anduin2017/HowToCook 解析而来。
# 精准替换：以 "id":"<rid>" 为锚点，只替换其后的第一个 "ingredientDetails":[]，避免误改 18 条 kitchen_tips。
import io, json

FILES = [
    r'D:/tmp/HowToCook/cookbook-miniprogram/data/recipes.json',
    r'D:/tmp/HowToCook/cookbook-miniprogram/cloudfunctions/getRecipes/data/recipes.json',
]

FILL = {
    'dessert/戚风蛋糕': [
        "基准：每份 = 1 个鸡蛋（约 50g）",
        "鸡蛋：1 份 1 个｜6 寸 3 个｜8 寸 5 个",
        "白糖：1 份 16g｜6 寸 50g｜8 寸 80g",
        "食用油：1 份 8g｜6 寸 25g｜8 寸 40g（可换黄油）",
        "牛奶：1 份 10g｜6 寸 30g｜8 寸 50g（可换水）",
        "低筋面粉：1 份 17g｜6 寸 50g｜8 寸 90g",
        "柠檬汁或白醋：少许（可选）",
    ],
    'dessert/无厨师机蜂蜜面包': [
        "高筋面粉 400g",
        "牛奶 200g",
        "酵母 4g",
        "鸡蛋 1个",
        "白砂糖 70g",
        "盐 2g",
        "黄油 30g",
        "蜂蜜 20g",
        "水 20g",
        "芝麻 适量（可选，洒顶部）",
    ],
    'dessert/烤箱版巴斯克芝士蛋糕': [
        "奶油奶酪 212g",
        "白砂糖 60g",
        "鸡蛋 2个",
        "鸡蛋黄 1个",
        "淡奶油 120g",
        "低筋面粉 10g",
        "巧克力 38g（可选，巧克力味）",
    ],
    'dessert/龟苓膏': [
        "龟苓膏粉 25克",
        "冷水 120毫升",
        "开水 500毫升",
        "白砂糖 100克",
    ],
    'drink/酒酿醪糟': [
        "糯米 800g（圆糯米）",
        "安琪甜酒曲 8g",
        "清水 720g（蒸饭）+ 600g（发酵）",
    ],
    'meat_dish/桂林十八酿': [
        "容器（任选）：青椒、苦瓜、茄子、田螺、豆腐、香菇、南瓜花等",
        "馅料（任选）：猪肉馅（肥瘦3:7）、虾滑馅、鱼肉馅、混合馅",
        "组合：18 种容器 × 4 种馅料 ≈ 72 种",
    ],
    'meat_dish/鱼香肉丝': [
        "里脊肉 200g",
        "胡萝卜 100g",
        "青椒 100g",
        "木耳（干） 5g",
        "生抽 10ml",
        "料酒 5ml",
        "蛋清 1个",
        "淀粉 10g",
        "醋 15ml",
        "白糖 10g",
        "盐 5g",
        "姜 20g",
        "葱 20g",
        "蒜 2瓣",
        "豆瓣酱 15g",
    ],
    'staple/微波炉腊肠煲仔饭': [
        "米 200ml",
        "腊肠 1根",
        "鸡蛋 1个",
        "红萝卜 1个",
        "盐 适量",
        "油 15ml",
        "生抽 10ml",
        "香葱 1颗",
    ],
}

ANCHOR_EMPTY = '"ingredientDetails":[]'

def apply_file(fp):
    txt = io.open(fp, 'r', encoding='utf-8').read()
    replaced = 0
    for rid, arr in FILL.items():
        id_anchor = '"id":"%s"' % rid
        i = txt.find(id_anchor)
        if i < 0:
            print('  [WARN] 未找到 id:', rid)
            continue
        j = txt.find(ANCHOR_EMPTY, i)
        if j < 0:
            print('  [WARN] %s 没有空 ingredientDetails（可能已填）' % rid)
            continue
        new_seg = '"ingredientDetails":' + json.dumps(arr, ensure_ascii=False)
        txt = txt[:j] + new_seg + txt[j + len(ANCHOR_EMPTY):]
        replaced += 1
    io.open(fp, 'w', encoding='utf-8').write(txt)
    return replaced

for fp in FILES:
    print('FILE:', fp.split('HowToCook')[-1])
    n = apply_file(fp)
    print('  替换条数:', n)

# 校验两份 JSON 合法 + 结果
for fp in FILES:
    data = json.load(io.open(fp, encoding='utf-8'))
    recs = data['recipes']
    real = [r for r in recs if r.get('category') != 'kitchen_tips']
    still_empty = [r.get('id') for r in real if not (r.get('ingredientDetails') or [])]
    print('校验', fp.split('HowToCook')[-1], '| 真菜空 ingredientDetails:', len(still_empty), still_empty)
print('DONE')
