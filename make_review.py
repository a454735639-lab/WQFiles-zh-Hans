#!/usr/bin/env python3
"""
生成译文审校表：把 zh-Hans.json 按界面模块分组，标注源码位置。

用法：
  python3 make_review.py --en <官方源码目录> --catalog zh-Hans.json --out 译文审校表.md
"""
import argparse, json, os, sys

MODULE = {
    'main.m': '① 首页 / 文件浏览 / 备份管理',
    'WQApps.m': '② 应用数据（备份·恢复·清除）',
    'WQCache.m': '③ 缓存清理',
    'WQPlistEditor.m': '④ Plist 编辑器',
    'WQHexViewer.m': '⑤ 十六进制查看器',
    'WQUI.m': '⑥ 通用（设备信息、提示）',
    'WQSharing.m': '⑦ 分享 / 导出 ZIP',
    'WQAccess.m': '⑧ 底层访问（错误与安全提示）',
    'WQLaunchServices.m': '⑨ 系统应用名称表',
}
ORDER = list(MODULE.values())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from localize import scan


def cell(s, limit=130):
    s = s.replace('|', '\\|').replace('\n', '\\n')
    return s if len(s) <= limit else s[:limit - 1] + '…'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--en', required=True)
    ap.add_argument('--catalog', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    cat = json.load(open(args.catalog, encoding='utf-8'))
    rows = []
    for f in sorted(os.listdir(args.en)):
        if not f.endswith('.m'):
            continue
        text = open(os.path.join(args.en, f), encoding='utf-8').read()
        for s, e, c in scan(text):
            if c in cat:
                rows.append({
                    'file': f,
                    'line': text[:s].count('\n') + 1,
                    'en': c,
                    'zh': cat[c],
                    'mod': MODULE.get(f, '其他'),
                })

    out = ['# WQFiles 汉化译文审校表\n',
           f'共 **{len(rows)}** 条已翻译字符串（译文表 {len(cat)} 条，含未在本版本出现的条目）。\n',
           '按界面模块分组，`位置` 是官方源码中的行号，便于对照。\n',
           '| 模块 | 条数 |', '|---|---:|']
    for m in ORDER:
        n = sum(1 for r in rows if r['mod'] == m)
        if n:
            out.append(f'| {m} | {n} |')
    out.append('')

    for m in ORDER:
        sub = [r for r in rows if r['mod'] == m]
        if not sub:
            continue
        out.append(f'\n---\n\n## {m}\n')
        out.append(f'共 {len(sub)} 条。\n')
        out.append('| 位置 | 原文 | 译文 |')
        out.append('|---|---|---|')
        for r in sorted(sub, key=lambda x: (x['file'], x['line'])):
            out.append(f'| `{r["file"]}:{r["line"]}` | {cell(r["en"])} | {cell(r["zh"])} |')

    open(args.out, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(f'wrote {args.out}: {len(rows)} entries, {len(ORDER)} modules')


if __name__ == '__main__':
    main()
