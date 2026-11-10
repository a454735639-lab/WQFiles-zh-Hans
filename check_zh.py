#!/usr/bin/env python3
"""
汉化结果自检：在 CI 里作为构建前闸门，防止漏译或误伤逻辑串。

检查项：
  1. 源码里确实有大量中文字面量（证明汉化生效）
  2. 没有任何 isEqualToString/hasPrefix/hasSuffix/containsString 的右值是中文
     （中文比较条件 = 功能必然坏）
  3. 源码括号配对完整（防止替换切坏了语法）
  4. 备份清单/恢复日志的键名仍是英文

用法：python3 check_zh.py --src <源码目录>
退出码非 0 表示不合格，CI 会中断。
"""
import argparse, os, re, sys

COMPARE = re.compile(r'(isEqualToString|hasPrefix|hasSuffix|containsString|isEqual):@"([^"]*)"')
MANIFEST_KEYS = [
    '"Complete"', '"Parts"', '"PartHashes"', '"Sequence"', '"Created"',
    '"Reason"', '"Format"', '"BundleID"', '"State"', '"Safety"',
]


def has_cjk(s):
    return any('\u4e00' <= c <= '\u9fff' for c in s)


def balanced(text):
    depth = {'{': 0, '(': 0, '[': 0}
    pairs = {'}': '{', ')': '(', ']': '['}
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            j = text.find('\n', i)
            i = n if j < 0 else j + 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c in depth:
            depth[c] += 1
        elif c in pairs:
            depth[pairs[c]] -= 1
            if depth[pairs[c]] < 0:
                return False
        i += 1
    return all(v == 0 for v in depth.values()) and not in_str


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    args = ap.parse_args()

    files = sorted(f for f in os.listdir(args.src) if f.endswith('.m'))
    failures = []

    cjk_total = 0
    for f in files:
        text = open(os.path.join(args.src, f), encoding='utf-8').read()
        cjk_total += sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

        if not balanced(text):
            failures.append(f'{f}: 括号不配对，替换可能切坏了语法')

        for m in COMPARE.finditer(text):
            if has_cjk(m.group(2)):
                failures.append(f'{f}: 比较条件被译成中文 {m.group(2)!r}（功能会坏）')

        # 备份清单键必须还在
        if f == 'WQApps.m':
            for k in MANIFEST_KEYS:
                if k not in text:
                    failures.append(f'WQApps.m: 备份清单键 {k} 丢失')

    print(f'源码中文字符总数: {cjk_total}')
    if cjk_total < 2000:
        failures.append(f'中文太少（{cjk_total}），汉化可能没生效')

    if failures:
        print('\n不合格：')
        for x in failures:
            print('  -', x)
        return 1

    print('自检通过：汉化已生效，逻辑串与清单键均未被误伤')
    return 0


if __name__ == '__main__':
    sys.exit(main())
