#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Anduin2017/HowToCook 上游 Markdown 解析某道菜的「操作」段，
生成带前缀约定的 steps 数组，供小程序详情页分层渲染：
  - "## 标题"      -> 步骤区子标题（不编号）
  - "> 说明文字"   -> 提示/说明（不编号）
  - "Sn 文本"      -> 操作步骤，"n" 为上游原始分段编号（保留，不重排）
  - 其余纯文本     -> 操作步骤（由页面自动连续编号，兼容旧数据）

用法：
  python parse_upstream_steps.py <rid> [--write]
  rid 例：dessert/戚风蛋糕
  --write 时把解析结果写回 data/recipes.json 与 cloudfunctions/.../data/recipes.json
"""
import sys, os, re, io, json, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MP_DATA = os.path.join(ROOT, 'data', 'recipes.json')
CF_DATA = os.path.join(ROOT, 'cloudfunctions', 'getRecipes', 'data', 'recipes.json')

SKIP_TITLES = {'工具', '原料'}  # 这些子段的内容本地已用 ingredients 呈现，steps 不重复

def load_recipes(path):
    return json.load(io.open(path, encoding='utf-8'))

def fetch_md(source):
    m = re.search(r'dishes/([^/]+)/([^/?#]+)', source)
    cat, enc = m.group(1), m.group(2)
    # 先试 文件夹/<enc>.md 结构
    for path in (
        f'https://raw.githubusercontent.com/Anduin2017/HowToCook/master/dishes/{cat}/{enc}/{enc}.md',
        f'https://raw.githubusercontent.com/Anduin2017/HowToCook/master/dishes/{cat}/{enc}.md',
    ):
        try:
            req = urllib.request.Request(path, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode('utf-8')
        except Exception:
            continue
    raise RuntimeError('上游 Markdown 抓取失败: ' + source)

def parse_operation(md):
    lines = md.splitlines()
    # 取 ## 操作 段
    seg, cap = [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith('## '):
            cap = (s == '## 操作')
            continue
        if cap and s:
            seg.append(ln)
    steps, skip = [], False
    for ln in seg:
        s = ln.strip()
        if not s:
            continue
        if s.startswith('### '):
            title = s[4:].strip()
            if title in SKIP_TITLES:
                skip = True
            else:
                skip = False
                steps.append('## ' + title)
            continue
        if skip:
            continue
        if s.startswith('> '):
            steps.append('> ' + s[2:].strip())
            continue
        if re.match(r'^[-*]\s+', s):
            steps.append('> ' + re.sub(r'^[-*]\s+', '', s).strip())
            continue
        if re.match(r'^\d+\.\s+', s):
            m = re.match(r'^(\d+)\.\s+(.*)$', s, re.S)
            steps.append('S' + m.group(1) + ' ' + m.group(2).strip())
            continue
        steps.append('> ' + s)  # 其它说明性文字
    return steps

def main():
    if len(sys.argv) < 2:
        print('用法: python parse_upstream_steps.py <rid> [--write]')
        sys.exit(1)
    rid = sys.argv[1]
    do_write = '--write' in sys.argv
    recs = load_recipes(MP_DATA)['recipes']
    rec = next((r for r in recs if (r.get('id') or '') == rid), None)
    if not rec:
        print('未找到:', rid)
        sys.exit(1)
    md = fetch_md(rec.get('source', ''))
    steps = parse_operation(md)
    print(f'解析 {rid} -> steps 条数: {len(steps)}')
    for i, s in enumerate(steps):
        print(f'  {i+1:2d}. {s[:60]}')
    if do_write:
        # 写回两份
        for fp in (MP_DATA, CF_DATA):
            d = load_recipes(fp)
            for r in d['recipes']:
                if (r.get('id') or '') == rid:
                    r['steps'] = steps
                    break
            io.open(fp, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
            print('已写回:', os.path.relpath(fp, ROOT))

if __name__ == '__main__':
    main()
