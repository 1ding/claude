#!/usr/bin/env python3
"""
PPT 风格 HTML 布局烘焙工具

对 /convert-to-ppt-style-html 生成的 HTML 幻灯片执行精确布局：
1. 清除之前的 bake 结果（幂等）
2. 预调整：同类等高、背景扩 padding、grid 改列、列表加边框
3. 测量每个元素的实际渲染高度（Chrome headless）
4. 按 inter>intra 规则计算绝对定位坐标
5. 写死为 inline style

用法：
  python3 bake_ppt_layout.py <input.html> [output.html]

输出文件默认为原文件（原地覆盖）。
"""
import sys, os, time, json

# ── 参数 ──
INPUT = sys.argv[1] if len(sys.argv) > 1 else None
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else None
if not INPUT:
    print("用法: python3 bake_ppt_layout.py <input.html> [output.html]")
    sys.exit(1)
if not OUTPUT:
    OUTPUT = INPUT  # 原地覆盖
INPUT = os.path.abspath(INPUT)
OUTPUT = os.path.abspath(OUTPUT)

MAX_H = 349  # content-box 可用高度（px）

# ── 启动 Chrome ──
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1024,768')
opts.add_argument('--force-device-scale-factor=1')

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=opts
)
driver.get(f'file://{INPUT}')
time.sleep(1)

# ══════════════════════════════════════════════
# 第零步：清除之前的 bake（幂等）
# ══════════════════════════════════════════════
CLEAN_JS = r"""
(function(){
  document.querySelectorAll('.content-box').forEach(function(box) {
    box.style.removeProperty('position');
    var ch = box.children;
    for (var i = 0; i < ch.length; i++) {
      var c = ch[i];
      ['position','top','left','width','margin-top','margin-bottom',
       'padding-top','padding-bottom','line-height','grid-template-columns','gap'
      ].forEach(function(p){ c.style.removeProperty(p); });
      c.querySelectorAll('li').forEach(function(li){
        li.style.removeProperty('margin-bottom');
      });
      c.classList.remove('bordered');
      c.querySelectorAll('.bordered').forEach(function(el){ el.classList.remove('bordered'); });
      var cc = c.querySelector('.card-content');
      if (cc) cc.style.removeProperty('line-height');
    }
  });
})();
"""
driver.execute_script(CLEAN_JS)
time.sleep(0.3)
print("[bake] 清除旧结果")

# ══════════════════════════════════════════════
# 第一步：预调整（DOM 修改，测量前）
# ══════════════════════════════════════════════
PREADJUST_JS = r"""
(function(){
  var MAX = 349;

  function realHeight(box) {
    var ch = box.children, h = 0;
    for (var i = 0; i < ch.length; i++) {
      var s = getComputedStyle(ch[i]);
      h += ch[i].offsetHeight + (parseFloat(s.marginTop)||0) + (parseFloat(s.marginBottom)||0);
    }
    return h;
  }

  document.querySelectorAll('.content-box').forEach(function(box) {
    var gap = MAX - realHeight(box);
    var ch = box.children;

    /* ── R1: grid-4 单/双子元素页且留白大 → 改单列 ── */
    var g4 = box.querySelector(':scope > .grid-4');
    if (g4 && ch.length <= 2 && gap > 40) {
      g4.style.gridTemplateColumns = '1fr';
      g4.style.gap = '14px';
    }

    /* ── R2: 同类连续元素等高（短的加 padding） ── */
    ch = box.children;
    for (var i = 0; i < ch.length - 1; i++) {
      var a = ch[i], b = ch[i+1];
      if ((a.tagName + (a.classList[0]||'')) === (b.tagName + (b.classList[0]||''))) {
        var hA = a.offsetHeight, hB = b.offsetHeight;
        if (Math.abs(hA - hB) > 3) {
          var shorter = hA < hB ? a : b;
          var diff = Math.abs(hA - hB);
          var pt = parseFloat(getComputedStyle(shorter).paddingTop) || 0;
          var pb = parseFloat(getComputedStyle(shorter).paddingBottom) || 0;
          shorter.style.paddingTop = (pt + Math.ceil(diff/2)) + 'px';
          shorter.style.paddingBottom = (pb + Math.floor(diff/2)) + 'px';
        }
      }
    }

    gap = MAX - realHeight(box);
    if (gap < 10) return;

    /* ── R3: 背景元素优先扩 padding + line-height ── */
    var bgEls = box.querySelectorAll(':scope > .highlight-row, :scope > .card-key, :scope > .card');
    if (bgEls.length > 0) {
      var budget = gap * 0.6;
      var perEl = Math.min(budget / (bgEls.length * 2), 12);
      bgEls.forEach(function(el) {
        var pt = parseFloat(getComputedStyle(el).paddingTop) || 0;
        var pb = parseFloat(getComputedStyle(el).paddingBottom) || 0;
        el.style.paddingTop = (pt + perEl) + 'px';
        el.style.paddingBottom = (pb + perEl) + 'px';
        var target = el.querySelector('.card-content') || el;
        var lh = parseFloat(getComputedStyle(target).lineHeight) || 20;
        var fs = parseFloat(getComputedStyle(target).fontSize) || 13;
        var r = lh / fs;
        if (r < 2.0) target.style.lineHeight = Math.min(r + 0.15, 2.0).toFixed(2);
      });
    }

    gap = MAX - realHeight(box);
    if (gap < 10) return;

    /* ── R4: 列表加边框 ── */
    box.querySelectorAll(':scope > .list-items, :scope > ul').forEach(function(ul) {
      var lis = ul.querySelectorAll(':scope > li');
      if (lis.length >= 2 && gap > lis.length * 10) {
        ul.classList.add('bordered');
      }
    });
  });
})();
"""
driver.execute_script(PREADJUST_JS)
time.sleep(0.5)
print("[bake] 预调整完成")

# ══════════════════════════════════════════════
# 第二步：测量
# ══════════════════════════════════════════════
MEASURE_JS = """
var results = [];
document.querySelectorAll('.content-box').forEach(function(box, idx) {
    var children = [];
    var ch = box.children;
    for (var i = 0; i < ch.length; i++) {
        var c = ch[i];
        var s = getComputedStyle(c);
        var info = {
            tag: c.tagName, cls: c.className || '',
            h: c.offsetHeight,
            mt: parseFloat(s.marginTop) || 0,
            mb: parseFloat(s.marginBottom) || 0,
            lis: []
        };
        if (c.tagName === 'UL' || c.classList.contains('list-items')) {
            c.querySelectorAll(':scope > li').forEach(function(li) {
                var ls = getComputedStyle(li);
                info.lis.push({
                    h: li.offsetHeight,
                    mb: parseFloat(ls.marginBottom) || 0
                });
            });
        }
        children.push(info);
    }
    var realH = 0;
    for (var ri = 0; ri < ch.length; ri++) {
        var rs = getComputedStyle(ch[ri]);
        realH += ch[ri].offsetHeight + (parseFloat(rs.marginTop)||0) + (parseFloat(rs.marginBottom)||0);
    }
    results.push({ idx: idx, realH: realH, children: children });
});
return JSON.stringify(results);
"""
pages = json.loads(driver.execute_script(MEASURE_JS))
print(f"[bake] 测量完成: {len(pages)} 个内容页")

# ══════════════════════════════════════════════
# 第三步：计算绝对定位坐标
# ══════════════════════════════════════════════

def same_type(a, b):
    if a['tag'] != b['tag']:
        return False
    ca = a['cls'].split()[0] if a['cls'] else ''
    cb = b['cls'].split()[0] if b['cls'] else ''
    return ca == cb

def calc_page(page):
    ch = page['children']
    n = len(ch)
    if n == 0:
        return []

    heights = [c['h'] for c in ch]
    total = sum(heights)

    # 单子元素 → 垂直居中
    if n == 1:
        y = max(0, (MAX_H - heights[0]) / 2)
        pos = [{'y': round(y,1), 'h': heights[0], 'center': True}]
        if ch[0]['lis'] and len(ch[0]['lis']) > 1:
            li_h = sum(l['h'] for l in ch[0]['lis'])
            pos[0]['li_gap'] = round(max(2, (heights[0] - li_h) / (len(ch[0]['lis'])-1)), 1)
        return pos

    # 分类间距
    inter, intra = [], []
    for i in range(n-1):
        (intra if same_type(ch[i], ch[i+1]) else inter).append(i)

    li_intra = sum(max(0, len(c['lis'])-1) for c in ch)
    gap_space = max(0, MAX_H - total)

    # 权重分配 (inter:2, intra:1)
    tw = len(inter)*2 + (len(intra)+li_intra)*1
    if tw > 0:
        u = gap_space / tw
        ig = max(6, u * 2)
        ag = max(3, u * 1)
    else:
        ig = ag = gap_space / max(n-1, 1)

    if ig < ag:
        ig = ag + 2

    # 计算 Y
    pos = []
    y = 0
    for i in range(n):
        pos.append({'y': round(y,1), 'h': heights[i]})
        if i < n-1:
            y += heights[i] + (ig if i in inter else ag)

    # 微调：确保最后元素贴底
    bottom = pos[-1]['y'] + pos[-1]['h']
    if bottom > MAX_H + 2:
        # 压缩
        over = bottom - MAX_H
        total_gaps = bottom - total
        if total_gaps > 0:
            r = max(0.2, (total_gaps - over) / total_gaps)
            y = 0
            for i in range(n):
                pos[i]['y'] = round(y, 1)
                if i < n-1:
                    y += heights[i] + (ig if i in inter else ag) * r
    elif bottom < MAX_H - 3:
        # 扩展
        short = MAX_H - bottom
        total_gaps = bottom - total
        if total_gaps > 0:
            boost = 1 + short / total_gaps
            y = 0
            for i in range(n):
                pos[i]['y'] = round(y, 1)
                if i < n-1:
                    y += heights[i] + (ig if i in inter else ag) * boost

    # 列表 li 间距
    for i, c in enumerate(ch):
        if c['lis'] and len(c['lis']) > 1:
            li_h = sum(l['h'] for l in c['lis'])
            pos[i]['li_gap'] = round(max(2, (heights[i] - li_h) / (len(c['lis'])-1)), 1)

    return pos

all_pos = []
for page in pages:
    pos = calc_page(page)
    all_pos.append(pos)
    rh = page['realH']
    fill = (pos[-1]['y'] + pos[-1]['h']) / MAX_H * 100 if pos else 0
    tag = "OK" if 85 <= fill <= 102 else ("UNDER" if fill < 85 else "OVER")
    print(f"  P{page['idx']:2d}: {len(page['children'])}ch realH={rh:.0f} fill={fill:.0f}% [{tag}]")

# ══════════════════════════════════════════════
# 第四步：写回 HTML
# ══════════════════════════════════════════════
APPLY_JS = """
var positions = JSON.parse(arguments[0]);
var boxes = document.querySelectorAll('.content-box');
boxes.forEach(function(box, idx) {
    if (idx >= positions.length) return;
    var pos = positions[idx];
    var ch = box.children;
    for (var i = 0; i < ch.length && i < pos.length; i++) {
        var c = ch[i], p = pos[i];
        if (p.center) {
            c.style.marginTop = p.y + 'px';
            c.style.marginBottom = '0';
        } else {
            c.style.position = 'absolute';
            c.style.top = p.y + 'px';
            c.style.left = '0';
            c.style.width = '740px';
            c.style.marginTop = '0';
            c.style.marginBottom = '0';
        }
        if (p.li_gap !== undefined) {
            c.querySelectorAll(':scope > li').forEach(function(li, j, all) {
                li.style.marginBottom = (j < all.length - 1) ? p.li_gap + 'px' : '0';
            });
        }
    }
});
"""
driver.execute_script(APPLY_JS, json.dumps(all_pos))
time.sleep(0.3)

# ── 导出 ──
html = "<!DOCTYPE html>\n" + driver.execute_script("return document.documentElement.outerHTML;")
with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

kb = len(html.encode('utf-8')) / 1024
print(f"\n[bake] 输出: {OUTPUT}")
print(f"[bake] 大小: {kb:.0f} KB")

driver.quit()
