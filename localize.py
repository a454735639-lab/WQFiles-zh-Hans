#!/usr/bin/env python3
"""
WQFiles 汉化工具（官方 v0.7 → 简体中文）

流程：
  1. 词法扫描源码，取出所有 @"..." 字面量（正确跳过普通字符串、注释、字符字面量）
  2. 合并编译器会拼接的相邻字面量（@"a" "b" → "ab"）
  3. 按 catalog 替换为中文，并校验格式符（%@/%lu/%.1f...）逐一一致
  4. 生成 zh-Hans.json 译文表，供审阅和后续版本复用

用法：
  python3 localize.py --src <源码目录> --catalog zh-Hans.json --check
  python3 localize.py --src <源码目录> --catalog zh-Hans.json --write
"""
import argparse, json, os, re, shutil, sys

FMT = re.compile(r'%(?:%|[-+ 0#]*\d*(?:\.\d+)?(?:hh|h|ll|l|q|L|z|j|t)?[@diouxXeEfgGaAcspnS])')


def _skip_string(text, i, n):
    """text[i] 是开引号；返回闭引号之后的下标。"""
    j = i + 1
    while j < n:
        c = text[j]
        if c == '\\':
            j += 2; continue
        if c == '"':
            return j + 1
        j += 1
    return n


def tokens(text):
    """返回 [(start, end, content, is_objc)]，按出现顺序。"""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            j = text.find('\n', i)
            i = n if j < 0 else j + 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "'":
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2; continue
                if text[j] == "'":
                    break
                j += 1
            i = j + 1
            continue
        if c == '"':
            e = _skip_string(text, i, n)
            out.append((i, e, text[i + 1:e - 1], False))
            i = e
            continue
        if c == '@' and i + 1 < n and text[i + 1] == '"':
            e = _skip_string(text, i + 1, n)
            out.append((i, e, text[i + 2:e - 1], True))
            i = e
            continue
        i += 1
    return out


def scan(text):
    """返回 [(start, end, merged_content)]，只保留 @"..." 并合并相邻拼接。"""
    toks = tokens(text)
    merged = []
    k = 0
    while k < len(toks):
        s, e, c, objc = toks[k]
        if not objc:
            k += 1
            continue
        cur_c, cur_e = c, e
        # 向后合并紧邻的普通字符串字面量（中间只允许空白）
        m = k + 1
        while m < len(toks):
            s2, e2, c2, objc2 = toks[m]
            if objc2:
                break
            if text[cur_e:s2].strip():
                break
            cur_c += c2
            cur_e = e2
            m += 1
        merged.append((s, cur_e, cur_c))
        k = m
    return merged


def fmts(s):
    return sorted(FMT.findall(s))


PLURAL = re.compile(r'(\w+(?:\.\w+)*) == 1 \? @"" : @"s"')


def drop_english_plurals(text):
    """中文没有单复数：把 `x == 1 ? @"" : @"s"` 的英文后缀去掉，
    同时把因此变多余的 %@ 从中文文案里删掉，避免「3 个容器s」或参数错位。"""
    text = PLURAL.sub('@""', text)

    def fix(m):
        fmt, args = m.group(1), m.group(2)
        # 删掉格式串里最后一个 %@（就是那个复数后缀占位符）
        idx = fmt.rfind('%@')
        if idx < 0:
            return m.group(0)
        fmt = fmt[:idx] + fmt[idx + 2:]
        return '@"' + fmt + '"' + args + ']'

    # 格式串 + 参数列表，参数列表以 `, @""` 结尾
    text = re.sub(r'@"((?:[^"\\]|\\.)*)"((?:[^\[\]]|\[[^\]]*\])*?),\s*@""\s*\]', fix, text)
    text = re.sub(r',\s*@""\s*\]', ']', text)
    return text


# 保持原样的字符串：URL、plist 魔数、日期格式、设备型号（Apple 官方名称）
KEEP = {
    'yyyy-MM-dd HH.mm.ss', 'yyyyMMdd-HHmmss', 'yyyyMMdd-HHmmss-SSS', 'en_US_POSIX',
    '<plist', '<!DOCTYPE plist', '\\uFFFD',
    'https://github.com/kolbicz', 'https://x.com/_kolbicz', 'https://x.com/forcequitOS',
    'wqfiles.io', 'de ad be ef', '0 KB',
}



# 参与逻辑比较的字符串（isEqualToString / hasPrefix / 目录名 / 状态值）。
# 翻译它们会破坏功能，永远保持原文。
LOGIC_LITERALS = {
    '.', '..', '/', '\\0', '.app', '.app/', '.csstore',
    'Active', 'Committed', 'Application',
    # 内部状态值：赋值与比较配对出现，译了容易错位
    'Path copied', 'File Backups', 'App Backups',
    # 文件系统里的真实目录名：Backups 是 ~/.../Backups 目录，译了找不到
    'Backups', 'AppBackups',
    '/Containers/', '/SystemGroup/', '/var/', '/mobile/Containers/Data/',
    '/private/var/mobile/Containers/Data/InternalDaemon',
    '/private/var/mobile/Containers/Shared/AppGroup',
    'com.apple.LaunchServices-',
}

# 备份清单 / 恢复日志里的 plist 键名，写进磁盘文件，绝对不能动
MANIFEST_KEYS = {
    'Complete', 'Parts', 'PartHashes', 'Sequence', 'Created', 'Reason', 'Format',
    'BundleID', 'Container', 'ContainerDevice', 'ContainerInode', 'State', 'Safety',
    'Backup', 'Verified', 'Name', 'Device', 'Inode', 'Target',
    'modifiedSeconds', 'modifiedNanoseconds', 'changedSeconds', 'changedNanoseconds',
    'size', 'path', 'bundleIdentifier', 'dataContainerURL', 'fullAt',
    # 写进备份清单的 reason 值：旧备份里存的是英文，译了新旧不一致
    'Before restore',
}

def needs_translation(s):
    """只翻译用户可见文案：排除路径、标识符、日志前缀、纯格式串。"""
    if not s.strip():
        return False
    if s in KEEP or s in LOGIC_LITERALS:
        return False
    if re.fullmatch(r'iPhone1[78],\d', s) or re.fullmatch(r'iPhone[ \d][A-Za-z0-9 ]*', s):
        return False
    if s.startswith('/') or s.startswith('com.apple.') or s.startswith('systemgroup.'):
        return False
    if re.fullmatch(r'[A-Za-z0-9._~@%\-/]+', s):
        return False
    if not re.search(r'[A-Za-z]{3,}', s):
        return False
    if re.fullmatch(r'[\s%@()\[\]·.,:;0-9xluifd\-+*/]*', s):
        return False
    if re.match(r'^(scan|names|grant|app scan|cache scan|enumerate|backup|copy|purge|measure|'
                r'label|delete|create|mkdir|rename|open|token|LaunchServices API|container manager|'
                r'reading|finding|getting|measuring|full|weekly|no saved|saved scan|remembered|'
                r'not loaded|refused|unknown app|too large|different volume|volume ids|failed the|'
                r'limited rows|with errors|no identifier|selected ==|uid |; )', s):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--catalog', required=True)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--backup-dir', default='.orig')
    ap.add_argument('--keep-plural', action='store_true',
                    help='保留英文复数后缀（默认删除，中文无复数）')
    args = ap.parse_args()

    cat = json.load(open(args.catalog, encoding='utf-8'))
    files = sorted(f for f in os.listdir(args.src) if f.endswith('.m'))

    problems, untranslated, stats = [], [], []
    for f in files:
        text = open(os.path.join(args.src, f), encoding='utf-8').read()
        lits = scan(text)
        hit = 0
        for s, e, c in lits:
            if c in cat:
                hit += 1
                if fmts(c) != fmts(cat[c]):
                    problems.append((f, c, cat[c], fmts(c), fmts(cat[c])))
            elif needs_translation(c):
                untranslated.append((f, c))
        stats.append((f, len(lits), hit))

    print(f'{"file":24} {"literals":>9} {"translated":>11}')
    for f, n, h in stats:
        print(f'{f:24} {n:9} {h:11}')

    if problems:
        print(f'\n[!] 格式符不一致 {len(problems)} 条：')
        for f, en, zh, a, b in problems:
            print(f'  {f}: {en!r}\n     -> {zh!r}  {a} != {b}')

    if untranslated:
        print(f'\n[!] 未翻译的界面文案 {len(untranslated)} 条：')
        for f, s in untranslated:
            print(f'  {f}: {s!r}')

    if args.write and not problems:
        bdir = os.path.join(args.src, args.backup_dir)
        if os.path.isdir(bdir):
            shutil.rmtree(bdir)
        os.makedirs(bdir)
        for f in files:
            path = os.path.join(args.src, f)
            shutil.copy2(path, os.path.join(bdir, f))
            text = open(path, encoding='utf-8').read()
            out, last = [], 0
            for s, e, c in scan(text):
                # 双重保护：译文表里即使有，逻辑串/清单键/路径也不替换
                if c not in cat or c in LOGIC_LITERALS or c in MANIFEST_KEYS or c in KEEP:
                    continue
                out.append(text[last:s])
                out.append('@"' + cat[c] + '"')
                last = e
            out.append(text[last:])
            text = ''.join(out)
            if not args.keep_plural:
                text = drop_english_plurals(text)
            open(path, 'w', encoding='utf-8').write(text)
            print(f'wrote {f}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
