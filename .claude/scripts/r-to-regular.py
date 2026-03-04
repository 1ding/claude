#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R 版本转常规版本号
用法: python3 r-to-regular.py <源文件路径> [新版本号]

- 从文件名解析当前版本号，自动 +0.01；或使用指定版本号
- 将修订记录表中所有 R.xx 行合并为一行常规版本号行
- 写入同目录下新文件，打印新文件路径到 stdout
- 若源文件已是常规版本（无 _R 修订号），直接输出源文件路径并退出（code 0）
"""

import re
import sys
import os
from datetime import datetime

def next_version(current: str) -> str:
    """v0.03 → v0.04，v0.99 → v1.00"""
    m = re.match(r'v(\d+)\.(\d+)', current)
    if not m:
        raise ValueError(f"无法解析版本号: {current}")
    major, minor = int(m.group(1)), int(m.group(2))
    minor += 1
    if minor >= 100:
        major += 1
        minor = 0
    return f"v{major}.{minor:02d}"

def main():
    if len(sys.argv) < 2:
        print("用法: python3 r-to-regular.py <源文件路径> [新版本号]", file=sys.stderr)
        sys.exit(1)

    src_path = sys.argv[1]
    forced_version = sys.argv[2] if len(sys.argv) >= 3 else None

    if not os.path.isfile(src_path):
        print(f"错误: 文件不存在: {src_path}", file=sys.stderr)
        sys.exit(1)

    src_name = os.path.basename(src_path)
    src_dir  = os.path.dirname(src_path)

    # 解析文件名格式: {前缀}_v{版本}_R{修订号}@{时间戳}.md
    # 或常规版本:     {前缀}_v{版本}@{时间戳}.md
    r_pattern = re.match(r'^(.+?)_(v\d+\.\d+)_R(\d+)@(\d{12})\.md$', src_name)
    if not r_pattern:
        # 已是常规版本，直接返回源路径
        print(src_path)
        sys.exit(0)

    doc_prefix   = r_pattern.group(1)   # 如 07-BC详细设计-BC35...
    cur_version  = r_pattern.group(2)   # 如 v0.03

    new_version = forced_version if forced_version else next_version(cur_version)

    # 验证版本号格式
    if not re.match(r'^v\d+\.\d{2}$', new_version):
        print(f"错误: 版本号格式不符合 vX.YY: {new_version}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    new_name = f"{doc_prefix}_{new_version}@{timestamp}.md"
    dst_path = os.path.join(src_dir, new_name)

    # 读取源文件
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 找到连续的 R.xx 行并合并
    r_block_pattern = re.compile(r'(\| R\.\d+\s+\|.*\n)+')
    m = r_block_pattern.search(content)
    if not m:
        print(f"错误: 未在修订记录表中找到 R.xx 行", file=sys.stderr)
        sys.exit(1)

    # 提取各 R 行的修订内容
    r_entries = re.findall(r'\| R\.(\d+)\s+\| [\d-]+ \| (.+?) \| \S+\s+\|', m.group())
    if not r_entries:
        print(f"错误: R.xx 行格式解析失败", file=sys.stderr)
        sys.exit(1)

    merged_summary = "；".join(s.strip() for _, s in r_entries)
    today = datetime.now().strftime("%Y-%m-%d")
    merged_line = f"| {new_version}  | {today} | {merged_summary} | AI     |\n"

    # 检查行宽（版本管理规范要求 ≤200 显示宽度；中文字符占 2，英文字符占 1）
    display_width = sum(2 if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf'
                        or '\uf900' <= c <= '\ufaff' or '\uff00' <= c <= '\uffef'
                        else 1 for c in merged_line.rstrip('\n'))
    if display_width > 200:
        print(f"  [警告] 合并后修订记录行显示宽度 {display_width} > 200，建议手动精简修订内容描述", file=sys.stderr)

    new_content = content[:m.start()] + merged_line + content[m.end():]

    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    size_kb = len(new_content.encode("utf-8")) / 1024
    print(f"[r-to-regular] {src_name}", file=sys.stderr)
    print(f"  → {new_name}  ({size_kb:.1f} KB)", file=sys.stderr)
    print(f"  合并 {len(r_entries)} 条 R 记录为 {new_version}", file=sys.stderr)

    # stdout 只输出新文件路径（供调用方捕获）
    print(dst_path)

if __name__ == "__main__":
    main()
