#!/usr/bin/env python3
"""
汉化后处理：处理「同一字符串在显示处要译、在比较处不能译」的情况。

localize.py 按字符串内容做替换，所以像 @"Backups" 这种既被用作
目录名比较、又被用作界面标题的串，只能整体保留英文。这个脚本
按**调用上下文**精确替换那些纯显示位置。

在 localize.py --write 之后运行，可重复执行（幂等）。

用法：python3 postlocalize.py --src <源码目录>
"""
import argparse, os, sys

# (文件, 原文片段, 替换后片段)
RULES = [
    # 首页「工具」里的两个入口标题（只用于 initWithPath:title:，不影响目录名比较）
    ('main.m',
     'initWithPath:wq_backup_root() title:@"Backups"',
     'initWithPath:wq_backup_root() title:@"备份"'),
    ('main.m',
     'initWithPath:wq_app_backup_root() title:@"App Backups"',
     'initWithPath:wq_app_backup_root() title:@"应用备份"'),
    # 备份目录在文件列表里的显示标签（左边是比较条件，右边是 label，只改 label）
    ('main.m',
     'if ([name isEqualToString:@"Backups"]) item.label = @"File Backups";',
     'if ([name isEqualToString:@"Backups"]) item.label = @"备份";'),
    ('main.m',
     'if ([name isEqualToString:@"AppBackups"]) item.label = @"App Backups";',
     'if ([name isEqualToString:@"AppBackups"]) item.label = @"应用备份";'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    args = ap.parse_args()

    changed = 0
    for fname, old, new in RULES:
        path = os.path.join(args.src, fname)
        if not os.path.exists(path):
            print(f'[skip] {fname} 不存在')
            continue
        text = open(path, encoding='utf-8').read()
        if new in text:
            print(f'[ok]   {fname}: 已应用')
            continue
        if old not in text:
            print(f'[miss] {fname}: 未找到 {old[:60]!r}')
            continue
        open(path, 'w', encoding='utf-8').write(text.replace(old, new))
        changed += 1
        print(f'[fix]  {fname}: {old[:50]}… -> {new[:50]}…')

    print(f'完成，修改 {changed} 处')
    return 0


if __name__ == '__main__':
    sys.exit(main())
