#!/usr/bin/env python3
"""Convert PPT content markdown to HTML slides per TW-FMT-PPT-02 spec."""

import re
import sys
from pathlib import Path


def parse_markdown(text):
    """Parse PPT content markdown into structured pages."""
    pages = []
    current_section = ""
    lines = text.strip().split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        # Skip empty lines and revision record
        if not stripped:
            i += 1
            continue

        if stripped.startswith('## 修订记录'):
            break  # Stop processing at revision record

        if stripped.startswith('# ') and not stripped.startswith('## '):
            # Title page (#)
            title = stripped[2:]
            items = []
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('#'):
                    break
                if s.startswith('- '):
                    items.append(s[2:])
                i += 1
            pages.append({'type': 'title', 'title': title, 'items': items})
            continue

        elif stripped.startswith('## '):
            # Section page (##)
            current_section = stripped[3:]
            pages.append({'type': 'section', 'title': current_section})
            i += 1
            continue

        elif stripped.startswith('### '):
            # Content page (###)
            page_title = stripped[4:]
            items = []
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('#'):
                    break
                if s.startswith('- '):
                    items.append(s[2:])
                i += 1
            if items:  # Only add if there are items
                pages.append({
                    'type': 'content',
                    'section': current_section,
                    'title': page_title,
                    'items': items
                })
            continue

        i += 1

    return pages


def process_text(text):
    """Convert markdown text to HTML with annotation styling."""
    has_key = '[KEY]' in text
    # Remove annotation tags
    text = re.sub(r'\s*\[(KEY|DATA|CHART:\w+|LAYOUT:\w+)\]', '', text)

    if has_key:
        # First bold in KEY items gets highlight
        text = re.sub(
            r'\*\*(.+?)\*\*',
            lambda m: f'<strong class="highlight">{m.group(1)}</strong>',
            text, count=1
        )
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    else:
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    return text


def shorten_section(section):
    """Shorten section name for breadcrumb."""
    s = re.sub(r'^第\S+章\s*', '', section)
    return s


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
  background: #e5e7eb;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
.ppt-container {
  width: 800px; height: 450px; margin: 20px auto;
  position: relative; background: #ffffff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.ppt-content { width: 100%; height: 100%; position: relative; background: #ffffff; }

/* Title bar */
.title-bar {
  position: absolute; top: 30px; left: 30px; width: 740px; height: 25px;
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid #e2e8f0;
}
.breadcrumb-title {
  font-size: 14px; font-weight: 600; color: #1e293b;
  display: flex; align-items: center; gap: 6px;
}
.breadcrumb-title .level-1 { color: #6366f1; }
.breadcrumb-title .level-2 { color: #334155; }
.breadcrumb-title .separator { color: #94a3b8; font-weight: 400; }
.company-logo { font-size: 12px; font-weight: 600; color: #6366f1; letter-spacing: 1px; }

/* Footer */
.ppt-footer {
  position: absolute; bottom: 5px; left: 30px; right: 30px; height: 20px;
  display: flex; justify-content: space-between; align-items: center;
  font-size: 10px; font-weight: 100; color: #94a3b8;
}

/* Content area */
.content-box {
  position: absolute; top: 66px; left: 30px; width: 740px; max-height: 349px;
}

/* List styles */
.list-items { list-style: none; padding: 0; margin: 0; }
.list-items li {
  display: flex; align-items: flex-start; margin-bottom: 10px;
  font-size: 13px; color: #334155; line-height: 1.6;
}
.list-items li:last-child { margin-bottom: 0; }
.list-dot {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  background: #6366f1; margin-right: 10px; margin-top: 8px; flex-shrink: 0;
}

/* Compact mode for 7-8 items */
.compact .list-items li { margin-bottom: 6px; font-size: 12px; line-height: 1.5; }
.compact .list-dot { margin-top: 6px; }

/* Dense mode for 9+ items */
.dense .list-items li { margin-bottom: 4px; font-size: 11px; line-height: 1.4; }
.dense .list-dot { margin-top: 5px; }

/* Highlight */
.highlight {
  background: #eff6ff; padding: 2px 6px; border-radius: 3px;
  font-weight: 600; color: #6366f1;
}

/* Title page */
.layout-title .ppt-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.layout-title .ppt-content::before {
  content: ''; position: absolute; width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  border-radius: 50%; top: -100px; right: -100px;
}
.layout-title .ppt-content::after {
  content: ''; position: absolute; width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
  border-radius: 50%; bottom: -80px; left: -80px;
}
.title-main {
  position: absolute; top: 155px; left: 50%; transform: translateX(-50%);
  font-size: 26px; font-weight: 700; color: #ffffff; text-align: center;
  text-shadow: 0 2px 8px rgba(0,0,0,0.2); letter-spacing: 0.5px; z-index: 1; width: 700px;
}
.title-subtitle {
  position: absolute; top: 210px; left: 50%; transform: translateX(-50%);
  font-size: 14px; font-weight: 400; color: rgba(255,255,255,0.9);
  text-align: center; z-index: 1; width: 600px;
}
.title-date {
  position: absolute; top: 245px; left: 50%; transform: translateX(-50%);
  font-size: 12px; font-weight: 400; color: rgba(255,255,255,0.7);
  text-align: center; z-index: 1;
}
.title-author {
  position: absolute; bottom: 50px; left: 50%; transform: translateX(-50%);
  font-size: 8px; color: rgba(255,255,255,0.7); text-align: center; z-index: 1;
}

/* Section page */
.layout-section .ppt-content {
  background: linear-gradient(135deg, #818cf8 0%, #a78bfa 100%);
}
.section-title {
  position: absolute; top: 180px; left: 50%; transform: translateX(-50%);
  font-size: 22px; font-weight: 700; color: #ffffff; text-align: center;
  text-shadow: 0 2px 6px rgba(0,0,0,0.15); letter-spacing: 0.5px; z-index: 1; width: 700px;
}
"""

SCRIPT = """
<script>
document.addEventListener('keydown', function(e) {
  if (e.key === 'ArrowDown' || e.key === 'PageDown') {
    window.scrollBy({ top: 470, behavior: 'smooth' });
    e.preventDefault();
  } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
    window.scrollBy({ top: -470, behavior: 'smooth' });
    e.preventDefault();
  }
});
</script>
"""


def gen_title(page, num):
    subtitle = ""
    timerange = ""
    date_info = ""
    for item in page.get('items', []):
        clean = re.sub(r'\*\*.*?\*\*[：:]?\s*', '', item).strip()
        if '副标题' in item:
            subtitle = clean
        elif '时间范围' in item:
            timerange = clean
        elif '日期' in item:
            date_info = clean

    return f'''<!-- Page {num}: 封面页 -->
<div class="ppt-container layout-title">
  <div class="ppt-content">
    <div class="title-main">{page['title']}</div>
    <div class="title-subtitle">{subtitle}</div>
    <div class="title-date">{timerange} · {date_info}</div>
  </div>
</div>
'''


def gen_section(page, num):
    return f'''<!-- Page {num}: 章节页 - {page['title']} -->
<div class="ppt-container layout-section">
  <div class="ppt-content">
    <div class="section-title">{page['title']}</div>
  </div>
</div>
'''


def gen_content(page, num):
    items = page['items']
    n = len(items)
    section = shorten_section(page['section'])
    title = page['title']

    # Density class
    if n <= 6:
        density = ''
        fs, lh, mb = 13, 1.6, 10
    elif n <= 8:
        density = ' compact'
        fs, lh, mb = 12, 1.5, 6
    else:
        density = ' dense'
        fs, lh, mb = 11, 1.4, 4

    # Estimate height
    avg_lines = 1.5
    item_h = round(fs * lh * avg_lines + mb)
    total_h = n * item_h - mb
    height_ok = "OK" if total_h <= 349 else "WARN"

    # Build list items
    lis = []
    for item in items:
        processed = process_text(item)
        lis.append(f'        <li><span class="list-dot"></span>{processed}</li>')
    items_html = '\n'.join(lis)

    return f'''<!-- Page {num}: {section} › {title} -->
<div class="ppt-container layout-content{density}">
  <div class="ppt-content">
    <div class="title-bar">
      <div class="breadcrumb-title">
        <span class="level-1">{section}</span>
        <span class="separator">›</span>
        <span class="level-2">{title}</span>
      </div>
      <div class="company-logo">TENWARD</div>
    </div>
    <div class="content-box">
      <!-- Height: {n} items × ~{item_h}px = ~{total_h}px ≤ 349px [{height_ok}] -->
      <ul class="list-items">
{items_html}
      </ul>
    </div>
  </div>
  <div class="ppt-footer">
    <span>上海天帷智慧数字技术有限公司 / www.tenward.com</span>
    <span>第 {num} 页</span>
  </div>
</div>
'''


def convert(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    pages = parse_markdown(text)

    parts = [f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=800">
<title>科技风险评级提升计划</title>
<style>{CSS}</style>
</head>
<body>
''']

    num = 1
    for page in pages:
        if page['type'] == 'title':
            parts.append(gen_title(page, num))
        elif page['type'] == 'section':
            parts.append(gen_section(page, num))
        elif page['type'] == 'content':
            parts.append(gen_content(page, num))
        num += 1

    parts.append(SCRIPT)
    parts.append('</body>\n</html>\n')

    html = '\n'.join(parts)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # Stats
    tc = sum(1 for p in pages if p['type'] == 'title')
    sc = sum(1 for p in pages if p['type'] == 'section')
    cc = sum(1 for p in pages if p['type'] == 'content')
    print(f"Total: {len(pages)} pages (Title: {tc}, Section: {sc}, Content: {cc})")
    print(f"File: {output_path} ({len(html):,} bytes, {len(html)//1024} KB)")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 md_to_ppt_html.py input.md [output.html]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.rsplit('.', 1)[0] + '.html'
    convert(inp, out)
