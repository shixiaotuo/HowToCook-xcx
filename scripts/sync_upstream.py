#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 通用上游同步：对每道真菜，从已下载的上游 markdown（_upstream/<id>.md）解析四类字段，
# 与本地 recipes.json 对比，做完整性修复：
#   1) summary  —— 补全被截断的结尾（本地是上游前缀时替换）
#   2) steps    —— 全量重建：## 子标题 / > 说明 / Sn 分段编号（与源一致）
#   3) ingredientDetails —— 仅当本地为空时从上游 计算/必备原料 生成（避免覆盖已有正确数据）
#   4) additional —— 从上游 附加内容 补齐，markdown 链接转裸 URL，去掉页脚
# 同步小程序端 + 云函数端两份 recipes.json。
import os, re, io, json, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, '..', '..'))
MP_DATA = os.path.join(ROOT, 'cookbook-miniprogram', 'data', 'recipes.json')
CF_DATA = os.path.join(ROOT, 'cookbook-miniprogram', 'cloudfunctions', 'getRecipes', 'data', 'recipes.json')
UP_DIR = os.path.join(ROOT, '_upstream')

SKIP_SUBTITLES = {'工具', '原料'}

def read(path):
    with io.open(path, encoding='utf-8') as f:
        return f.read()

def load_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)

def parse_sections(md):
    secs = {}
    cur = None
    for ln in md.splitlines():
        m = re.match(r'^##\s+(.*)$', ln)
        if m:
            cur = m.group(1).strip()
            secs.setdefault(cur, [])
        elif cur is not None:
            secs[cur].append(ln)
    return secs

def parse_intro(md):
    paras = []
    buf = []
    in_intro = False
    for ln in md.splitlines():
        s = ln.strip()
        if s.startswith('# '):
            in_intro = True
            continue
        if s.startswith('预估烹饪难度') or s.startswith('预估卡路里'):
            break
        if in_intro:
            if not s:
                if buf:
                    paras.append(' '.join(buf).strip())
                    buf = []
                continue
            buf.append(s)
    if buf:
        paras.append(' '.join(buf).strip())
    return '\n'.join(p for p in paras if p)

def parse_steps(md):
    secs = parse_sections(md)
    op = secs.get('操作')
    if not op:
        return []
    steps = []
    skip = False
    for ln in op:
        s = ln.strip()
        if not s:
            continue
        if s.startswith('### '):
            title = s[4:].strip()
            if title in SKIP_SUBTITLES:
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
        m = re.match(r'^(\d+)\.\s+(.*)$', s, re.S)
        if m:
            steps.append('S' + m.group(1) + ' ' + m.group(2).strip())
            continue
        steps.append('> ' + s)
    return steps

def parse_additional(md):
    secs = parse_sections(md)
    add = secs.get('附加内容')
    if not add:
        return []
    out = []
    for ln in add:
        s = ln.strip()
        if not s:
            continue
        # 图片 markdown（![alt](./x.jpg) 等）在纯文本区无意义的，直接跳过
        if re.search(r'!\[[^\]]*\]\([^)]*\)', s):
            continue
        if '如果您遵循本指南' in s or 'Issue' in s or 'Pull request' in s or 'pull request' in s:
            continue
        s = re.sub(r'^[-*]\s+', '', s).strip()
        if not s:
            continue
        s = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1 \2', s)
        out.append(s)
    return out

def parse_ingredient_details(md):
    secs = parse_sections(md)
    items = []
    calc = secs.get('计算', [])
    for ln in calc:
        s = ln.strip()
        if not s:
            continue
        if s.startswith('|') and '---' not in s:
            cells = [c.strip() for c in s.strip('|').split('|')]
            if len(cells) >= 2:
                items.append('：'.join(cells) if cells[0] else '｜'.join(cells[1:]))
            continue
        if re.match(r'^[-*]\s+', s) or re.match(r'^\d+\.\s+', s):
            items.append(re.sub(r'^([-*]|\d+\.)\s+', '', s).strip())
            continue
        if re.search(r'(份数|克|g\b|ml|个|只|瓣|适量|少许|汤匙|茶匙|杯|斤|kg|mL|KG)', s, re.I):
            items.append(s)
    base = secs.get('必备原料和工具', [])
    for ln in base:
        s = ln.strip()
        if not s or re.match(r'^###\s', s):
            continue
        s = re.sub(r'^[-*]\s+', '', s).strip()
        if re.search(r'(\d+\s*(g|克|ml|mL|个|只|瓣|适量|少许|汤匙|茶匙|杯|斤|kg|KG)|份数)', s, re.I):
            items.append(s)
    seen, uniq = set(), []
    for x in items:
        if x not in seen:
            seen.add(x); uniq.append(x)
    return uniq

def norm(s):
    return re.sub(r'\s+', '', s or '')

def sync_recipe(rec, dry):
    rid = rec.get('id') or rec.get('name', '')
    fp = os.path.join(UP_DIR, rid + '.md')
    if not os.path.exists(fp):
        return None
    md = read(fp)
    changes = []

    up_intro = parse_intro(md)
    local_sum = rec.get('summary', '')
    if up_intro and local_sum:
        if norm(local_sum) != norm(up_intro) and norm(up_intro).startswith(norm(local_sum)):
            changes.append('summary(截断补全)')
            if not dry:
                rec['summary'] = up_intro
    elif up_intro and not local_sum:
        changes.append('summary(缺失)')
        if not dry:
            rec['summary'] = up_intro

    up_steps = parse_steps(md)
    if up_steps:
        local_steps = rec.get('steps', [])
        if local_steps != up_steps:
            changes.append('steps(%d→%d)' % (len(local_steps), len(up_steps)))
            if not dry:
                rec['steps'] = up_steps

    if not rec.get('ingredientDetails'):
        up_ing = parse_ingredient_details(md)
        if up_ing:
            changes.append('ingredientDetails(+%d)' % len(up_ing))
            if not dry:
                rec['ingredientDetails'] = up_ing

    up_add = parse_additional(md)
    local_add = rec.get('additional') or []
    if local_add:
        # 本地已有附加内容（如人工精修版），保护不被原始上游覆盖
        pass
    elif up_add:
        changes.append('additional(+%d)' % len(up_add))
        if not dry:
            rec['additional'] = up_add

    return changes

def main():
    dry = '--write' not in sys.argv
    for fp in (MP_DATA, CF_DATA):
        data = load_json(fp)
        total = 0
        fixed = 0
        report = {}
        cat = {}
        for r in data['recipes']:
            if r.get('type') == 'tip':
                continue
            ch = sync_recipe(r, dry)
            total += 1
            if ch:
                fixed += 1
                report[r.get('name', '?')] = ch
                for c in ch:
                    k = c.split('(')[0]
                    cat[k] = cat.get(k, 0) + 1
        if not dry:
            with io.open(fp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        print('=== %s ===' % os.path.relpath(fp, ROOT))
        print('  扫描真菜: %d | 有改动: %d' % (total, fixed))
        print('  分类统计:', cat)
        if dry:
            print('  [DRY-RUN] 改动样例（前 25）:')
            for name, ch in list(report.items())[:25]:
                print('    - %s: %s' % (name, ', '.join(ch)))
    if dry:
        print('\n*** 这是 DRY-RUN，未写入。确认无误后加 --write 执行。***')

if __name__ == '__main__':
    main()
