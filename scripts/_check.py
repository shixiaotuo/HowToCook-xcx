import json
f = 'D:/tmp/HowToCook/cookbook-miniprogram/cloudfunctions/getRecipes/data/recipes.json'
d = json.load(open(f, encoding='utf-8'))
sf = [r for r in d['recipes'] if r.get('category') == 'semi-finished']
cats = [c for c in d['categories'] if c['key'] == 'semi-finished']
with open('D:/tmp/HowToCook/cookbook-miniprogram/scripts/_check_out.txt', 'w', encoding='utf-8') as o:
    o.write('semi-finished 菜数: %d\n' % len(sf))
    o.write('categoryName 示例: %s\n' % (sf[0]['categoryName'] if sf else None))
    o.write('categories 显示名: %s\n' % (cats[0]['name'] if cats else None))
    o.write('总条数: %d\n' % d['total'])
