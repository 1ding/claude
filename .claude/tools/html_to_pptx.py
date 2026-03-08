#!/usr/bin/env python3
"""HTML Slides → PPTX Converter v3 — Navy-Gold Design System.

Base script for ppt-slides-theme.html template.
Handles all known components; unknown components can be handled by
registering custom renderers via register_renderer() before calling convert().

Usage:
    # Direct: handles known components only
    python html_to_pptx.py input.html output.pptx

    # Extended: AI generates a wrapper script that imports this module,
    # registers custom renderers, then calls convert()
"""

import sys, re, html as html_module
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ── Constants ──
SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5
PX_TO_IN = SLIDE_W_IN / 1280  # 0.01041666...
PX_TO_PT = 0.75  # CSS px to PPT pt

COLORS = {
    'navy':         RGBColor(0x0A, 0x16, 0x28),
    'navy_mid':     RGBColor(0x13, 0x22, 0x40),
    'navy_light':   RGBColor(0x1A, 0x30, 0x58),
    'gold':         RGBColor(0xC9, 0xA8, 0x4C),
    'gold_light':   RGBColor(0xE8, 0xCC, 0x6A),
    'white':        RGBColor(0xF0, 0xEC, 0xE4),
    'text_muted':   RGBColor(0x8A, 0x9B, 0xB5),
    'accent_blue':  RGBColor(0x3B, 0x7D, 0xD8),
    'accent_red':   RGBColor(0xD9, 0x4F, 0x4F),
    'accent_green': RGBColor(0x3A, 0xAD, 0x6B),
    'accent_teal':  RGBColor(0x2B, 0xA8, 0xA8),
    'accent_orange':RGBColor(0xE0, 0x8A, 0x3C),
}
# CSS var name → color key
VAR_MAP = {
    '--navy': 'navy', '--navy-mid': 'navy_mid', '--navy-light': 'navy_light',
    '--gold': 'gold', '--gold-light': 'gold_light', '--white': 'white',
    '--text-muted': 'text_muted', '--accent-blue': 'accent_blue',
    '--accent-red': 'accent_red', '--accent-green': 'accent_green',
    '--accent-teal': 'accent_teal', '--accent-orange': 'accent_orange',
}
FONT_T = 'Noto Serif SC'
FONT_B = 'Noto Sans SC'

HEAT_FG = {
    'h-attack': COLORS['accent_red'], 'h-break': COLORS['gold'],
    'h-deep': COLORS['accent_teal'], 'h-base': COLORS['accent_blue'],
    'h-mature': COLORS['accent_green'], 'h-lead': RGBColor(0x6C,0xE8,0x9A),
    'h-tbd': COLORS['accent_orange'],
}
HEAT_BG = {
    'h-attack': RGBColor(0x2E,0x15,0x15), 'h-break': RGBColor(0x2A,0x24,0x14),
    'h-deep': RGBColor(0x12,0x24,0x28), 'h-base': RGBColor(0x12,0x1C,0x30),
    'h-mature': RGBColor(0x12,0x24,0x1C), 'h-lead': RGBColor(0x14,0x28,0x1E),
    'h-tbd': RGBColor(0x28,0x1E,0x12),
}
HEAT_BOLD = {'h-attack','h-break','h-lead'}
TAG_COLORS = {
    'tag-done':   (RGBColor(0x14,0x28,0x1E), COLORS['accent_green']),
    'tag-attack': (RGBColor(0x2E,0x15,0x15), COLORS['accent_red']),
    'tag-base':   (RGBColor(0x12,0x1C,0x30), COLORS['accent_blue']),
    'tag-tbd':    (RGBColor(0x28,0x1E,0x12), COLORS['accent_orange']),
    'tag-break':  (RGBColor(0x2A,0x24,0x14), COLORS['gold_light']),
    'tag-deep':   (RGBColor(0x12,0x24,0x28), COLORS['accent_teal']),
}

# CSS line-height → PPT line_spacing (as proportion)
# e.g. line-height:1.65 → 1.65
DEFAULT_LINE_SPACING = 1.65

# ── Utility ──
def px(v):
    return Inches(v * PX_TO_IN)

def css_px(s):
    if not s: return 0
    m = re.search(r'([-\d.]+)\s*px', str(s))
    return float(m.group(1)) if m else 0

def css_pt(css_px_val):
    """Convert CSS px to PPT Pt."""
    return Pt(css_px_val * PX_TO_PT)

def sty(el):
    """Parse inline style to dict."""
    d = {}
    for p in el.get('style', '').split(';'):
        p = p.strip()
        if ':' in p:
            k, v = p.split(':', 1)
            d[k.strip()] = v.strip()
    return d

def coords(el):
    s = sty(el)
    return (css_px(s.get('left','0')), css_px(s.get('top','0')),
            css_px(s.get('width','0')), css_px(s.get('height','0')))

def hcls(el, c):
    cls = el.get('class', [])
    if isinstance(cls, str): cls = cls.split()
    return c in cls

def find_cls(el, prefix):
    for c in (el.get('class') or []):
        if c.startswith(prefix): return c
    return None

def txt(el):
    if el is None: return ''
    return html_module.unescape(el.get_text(separator='', strip=True))

def parse_c(s):
    """Parse color from CSS value."""
    if not s: return None
    m = re.search(r'var\((--[\w-]+)\)', s)
    if m:
        k = VAR_MAP.get(m.group(1))
        return COLORS.get(k) if k else None
    m = re.search(r'#([0-9a-fA-F]{6})', s)
    if m:
        h = m.group(1)
        return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))
    return None

def parse_fs(s):
    """Parse font-size from CSS, return Pt."""
    if not s: return None
    m = re.search(r'([\d.]+)px', s)
    if m: return Pt(float(m.group(1)) * PX_TO_PT)
    return None

def parse_lh(s):
    """Parse line-height from CSS, return float."""
    if not s: return None
    m = re.search(r'([\d.]+)', s)
    if m: return float(m.group(1))
    return None

def parse_fw(s):
    """Parse font-weight, return (bold, weight_int)."""
    if not s: return False, 400
    if 'bold' in s: return True, 700
    m = re.search(r'(\d+)', s)
    if m:
        w = int(m.group(1))
        return w >= 700, w
    return False, 400

# ── Shape helpers ──
def set_bg(slide, color):
    f = slide.background.fill; f.solid(); f.fore_color.rgb = color

def set_bg_gradient(slide, stops):
    """Set gradient background. stops = [(pos, RGBColor), ...]"""
    bg = slide.background
    fill = bg.fill
    fill.gradient()
    fill.gradient_stops.clear()
    # We need to use XML manipulation for gradient angle
    gs_xml = fill._fill
    # Set angle to 135 degrees (in 60000ths of a degree)
    lin = gs_xml.find(qn('a:lin'))
    if lin is None:
        lin = gs_xml.makeelement(qn('a:lin'), {'ang': '8100000', 'scaled': '1'})
        gs_xml.append(lin)
    else:
        lin.set('ang', '8100000')

    for pos, color in stops:
        gs = fill.gradient_stops.add_stop()
        gs.position = pos
        gs.color.rgb = color

def add_tb(slide, l, t, w, h):
    return slide.shapes.add_textbox(px(l), px(t), px(w), px(h))

def set_tf(tf):
    tf.word_wrap = True
    from pptx.enum.text import MSO_AUTO_SIZE
    tf.auto_size = MSO_AUTO_SIZE.NONE

def add_run(p, text, font=FONT_B, size=Pt(10), color=COLORS['white'], bold=False):
    r = p.add_run()
    r.text = text
    r.font.name = font
    r.font.size = size
    r.font.color.rgb = color
    r.font.bold = bold
    return r

def set_para_spacing(p, line_height=None, space_before=None, space_after=None):
    """Set paragraph spacing."""
    if line_height:
        p.line_spacing = line_height
    if space_before is not None:
        p.space_before = space_before
    if space_after is not None:
        p.space_after = space_after

def set_bullet(p, char='•', color=None, size=None, indent_level=0):
    """Set PPT native bullet on a paragraph.

    Args:
        p: paragraph object
        char: bullet character (default '•')
        color: RGBColor for bullet (default gold)
        size: bullet font size in Pt
        indent_level: indentation level (0-based)
    """
    if color is None:
        color = COLORS['gold']
    pPr = p._p.get_or_add_pPr()
    # Set indent: level * 457200 EMU (= 0.5 inch)
    pPr.set('lvl', str(indent_level))
    # Hanging indent: marL = left margin, indent = negative hanging
    mar_l = 228600 + indent_level * 457200  # 0.25 inch base + level offset
    indent = -171450  # -0.1875 inch hanging
    pPr.set('marL', str(mar_l))
    pPr.set('indent', str(indent))
    # Remove any existing bullet settings
    for tag in ['a:buNone', 'a:buChar', 'a:buAutoNum', 'a:buFont', 'a:buSzPct', 'a:buClr']:
        existing = pPr.find(qn(tag))
        if existing is not None:
            pPr.remove(existing)
    # Set bullet color
    buClr = pPr.makeelement(qn('a:buClr'), {})
    srgb = buClr.makeelement(qn('a:srgbClr'), {
        'val': str(color)
    })
    buClr.append(srgb)
    pPr.append(buClr)
    # Set bullet font
    if size:
        buSzPct = pPr.makeelement(qn('a:buSzPts'), {'val': str(int(size.pt * 100))})
        pPr.append(buSzPct)
    buFont = pPr.makeelement(qn('a:buFont'), {'typeface': 'Arial', 'charset': '0'})
    pPr.append(buFont)
    # Set bullet character
    buChar = pPr.makeelement(qn('a:buChar'), {'char': char})
    pPr.append(buChar)

def add_rrect(slide, l, t, w, h, fill=None, border=None, bw=Pt(0.5), radius=0.04):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px(l), px(t), px(w), px(h))
    if fill:
        shape.fill.solid(); shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if border:
        shape.line.color.rgb = border; shape.line.width = bw
    else:
        shape.line.fill.background()
    try: shape.adjustments[0] = radius
    except: pass
    return shape

def add_rect(slide, l, t, w, h, fill):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, px(l), px(t), px(w), px(h))
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    return shape

def set_cell_border(cell, bot_color=None, bot_w='6350'):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    for side in ['lnL','lnR','lnT']:
        ln = tcPr.find(qn(f'a:{side}'))
        if ln is None:
            ln = tcPr.makeelement(qn(f'a:{side}'), {}); tcPr.append(ln)
        ln.set('w', '0')
        for ch in list(ln): ln.remove(ch)
        ln.append(ln.makeelement(qn('a:noFill'), {}))
    if bot_color:
        lnB = tcPr.find(qn('a:lnB'))
        if lnB is None:
            lnB = tcPr.makeelement(qn('a:lnB'), {}); tcPr.append(lnB)
        lnB.set('w', str(bot_w))
        for ch in list(lnB): lnB.remove(ch)
        sf = lnB.makeelement(qn('a:solidFill'), {})
        rgb_s = f'{bot_color[0]:02X}{bot_color[1]:02X}{bot_color[2]:02X}' if hasattr(bot_color,'__getitem__') else str(bot_color).replace('#','')
        sf.append(sf.makeelement(qn('a:srgbClr'), {'val': rgb_s}))
        lnB.append(sf)

# ── Rich text renderer ──
def render_rich(para, el, color=COLORS['white'], size=Pt(10), font=FONT_B,
                bc=COLORS['gold_light'], lh=None):
    """Render element children as runs, preserving bold/color/spans."""
    if lh: set_para_spacing(para, line_height=lh)
    for child in el.children:
        if isinstance(child, NavigableString):
            t = str(child)
            if t.strip():
                add_run(para, t, font, size, color)
        elif isinstance(child, Tag):
            if child.name in ('strong','b'):
                s = sty(child)
                c = parse_c(s.get('color','')) or bc
                add_run(para, txt(child), font, size, c, bold=True)
            elif child.name == 'span':
                s = sty(child)
                c = parse_c(s.get('color','')) or color
                fs = parse_fs(s.get('font-size','')) or size
                is_b, _ = parse_fw(s.get('font-weight',''))
                if child.find('strong') or child.find('br'):
                    render_rich(para, child, c, fs, font, bc)
                else:
                    add_run(para, txt(child), font, fs, c, bold=is_b)
            elif child.name == 'br':
                add_run(para, '\n', font, size, color)

# ── Component Renderers ──

def render_cover(slide, el):
    """Cover page with solid background."""
    set_bg(slide, COLORS['navy'])

    ct = el.find(class_='cover-content')
    if not ct: return

    badge = ct.find(class_='cover-badge')
    title = ct.find(class_='cover-title')
    sub = ct.find(class_='cover-sub')
    ver = ct.find(class_='cover-version')

    # Badge: 13px, letter-spacing 6px
    if badge:
        bw = 320
        bs = add_rrect(slide, (1280-bw)//2, 215, bw, 34,
                       border=COLORS['gold'], bw=Pt(0.75), radius=0.02)
        bs.fill.background()
        tf = bs.text_frame; set_tf(tf)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        add_run(tf.paragraphs[0], txt(badge), FONT_B, css_pt(13), COLORS['gold'])

    # Title: 44px Serif, weight 900, line-height 1.35
    if title:
        tb = add_tb(slide, 190, 270, 900, 130)
        tf = tb.text_frame; set_tf(tf)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        set_para_spacing(p, line_height=1.35)
        for child in title.children:
            if isinstance(child, NavigableString):
                t = str(child).strip()
                if t: add_run(tf.paragraphs[-1], t, FONT_T, css_pt(44), COLORS['white'], bold=True)
            elif isinstance(child, Tag):
                if child.name == 'br':
                    np = tf.add_paragraph()
                    np.alignment = PP_ALIGN.CENTER
                    set_para_spacing(np, line_height=1.35)
                elif child.name == 'span':
                    add_run(tf.paragraphs[-1], txt(child), FONT_T, css_pt(44), COLORS['gold'], bold=True)

    # Gold line: 80x2
    add_rect(slide, 600, 415, 80, 2, COLORS['gold'])

    # Subtitle: 22px, weight 300, letter-spacing 8px
    if sub:
        tb = add_tb(slide, 190, 440, 900, 40)
        tf = tb.text_frame; set_tf(tf)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        add_run(tf.paragraphs[0], txt(sub), FONT_B, css_pt(22), COLORS['text_muted'])

    # Version: 13px
    if ver:
        tb = add_tb(slide, 190, 490, 900, 40)
        tf = tb.text_frame; set_tf(tf)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        s = sty(ver)
        fs = parse_fs(s.get('font-size','')) or css_pt(13)
        add_run(tf.paragraphs[0], txt(ver), FONT_B, fs, COLORS['text_muted'])

def render_header(slide, el):
    if not el: return
    ch = el.find(class_='slide-chapter')
    ti = el.find(class_='slide-title')
    tb = add_tb(slide, 56, 32, 1168, 60)
    tf = tb.text_frame; set_tf(tf)
    p = tf.paragraphs[0]
    # chapter: 12px, bold 700, gold, letter-spacing 4px
    if ch: add_run(p, txt(ch), FONT_B, css_pt(12), COLORS['gold'], bold=True)
    if ti:
        p2 = tf.add_paragraph()
        p2.space_before = Pt(4)
        # title: 30px Serif, bold 700
        add_run(p2, txt(ti), FONT_T, css_pt(30), COLORS['white'], bold=True)

def render_footer(slide, el):
    if not el: return
    spans = el.find_all('span', recursive=False)
    doc = txt(spans[0]) if spans else ''
    pn_el = el.find(class_='page-num')
    pn = txt(pn_el) if pn_el else ''
    # footer text: 11px
    tb = add_tb(slide, 56, 688, 1100, 24)
    tf = tb.text_frame; set_tf(tf)
    add_run(tf.paragraphs[0], doc, FONT_B, css_pt(11), COLORS['text_muted'])
    if pn:
        tb2 = add_tb(slide, 1100, 688, 124, 24)
        tf2 = tb2.text_frame; set_tf(tf2)
        tf2.paragraphs[0].alignment = PP_ALIGN.RIGHT
        # page-num: 13px Serif, bold 700
        add_run(tf2.paragraphs[0], pn, FONT_T, css_pt(13), COLORS['gold'], bold=True)

def render_table(slide, el, bx=0, by=0):
    lx, ty, w, _ = coords(el)
    ax, ay = bx+lx, by+ty
    if w==0: w=1168

    thead = el.find('thead')
    tbody_el = el.find('tbody')
    if not thead or not tbody_el: return

    ths = thead.find('tr').find_all('th')
    rows = tbody_el.find_all('tr')
    nc = len(ths); nr = len(rows)+1

    # Column widths
    col_w = []
    ts = 0
    for th in ths:
        cw = css_px(sty(th).get('width','0'))
        col_w.append(cw); ts += cw
    unsp = [i for i,cw in enumerate(col_w) if cw==0]
    if unsp:
        r = w-ts; p = r/len(unsp)
        for i in unsp: col_w[i] = p

    # Row height: th=9px font → ~26px row; td=12.5px → ~28px row
    # CSS: th padding 9px 12px, td padding 8px 12px
    th_row_h = 32  # 9+9+14 (font line)
    td_row_h = 28  # 8+8+12
    total_h = th_row_h + td_row_h * len(rows)

    tshape = slide.shapes.add_table(nr, nc, px(ax), px(ay), px(w), px(total_h))
    tbl = tshape.table
    for i, cw in enumerate(col_w): tbl.columns[i].width = px(cw)
    tbl.rows[0].height = px(th_row_h)
    for i in range(1, nr): tbl.rows[i].height = px(td_row_h)

    # Clear style
    tpr = tbl._tbl.find(qn('a:tblPr'))
    if tpr is not None: tpr.attrib.clear()

    # Header: 11.5px font, bold 700, gold
    for j, th in enumerate(ths):
        cell = tbl.cell(0,j); cell.text = ''
        cell.fill.solid(); cell.fill.fore_color.rgb = COLORS['navy_mid']
        p = cell.text_frame.paragraphs[0]
        set_para_spacing(p, line_height=1.3)
        add_run(p, txt(th), FONT_B, css_pt(11.5), COLORS['gold'], bold=True)
        set_cell_border(cell, COLORS['gold'], '19050')  # 2px = 25400 EMU, 1.5px ≈ 19050
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left=Pt(8); cell.margin_right=Pt(6)
        cell.margin_top=Pt(6); cell.margin_bottom=Pt(6)

    # Data: 12.5px font, weight 300, line-height 1.5
    for i, tr in enumerate(rows):
        tds = tr.find_all('td')
        for j, td in enumerate(tds):
            if j>=nc: break
            cell = tbl.cell(i+1,j); cell.text = ''
            cell.fill.solid(); cell.fill.fore_color.rgb = COLORS['navy']

            hc = find_cls(td, 'h-')
            if hc and hc in HEAT_BG: cell.fill.fore_color.rgb = HEAT_BG[hc]

            p = cell.text_frame.paragraphs[0]
            set_para_spacing(p, line_height=1.5)

            tag_el = td.find(class_='status-tag')
            if tag_el:
                tc2 = find_cls(tag_el, 'tag-')
                tc = TAG_COLORS.get(tc2, (None, COLORS['white']))[1] if tc2 else COLORS['white']
                add_run(p, txt(tag_el), FONT_B, css_pt(11), tc, bold=True)
            else:
                s = sty(td)
                td_c = parse_c(s.get('color','')) or COLORS['white']
                td_b, _ = parse_fw(s.get('font-weight',''))
                if hc and hc in HEAT_FG:
                    td_c = HEAT_FG[hc]
                    td_b = hc in HEAT_BOLD
                add_run(p, txt(td), FONT_B, css_pt(12.5), td_c, bold=td_b)

            set_cell_border(cell, RGBColor(0x1A,0x20,0x30), '6350')
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left=Pt(8); cell.margin_right=Pt(6)
            cell.margin_top=Pt(5); cell.margin_bottom=Pt(5)

def render_col_card(slide, el, bx=0, by=0):
    lx, ty, w, h = coords(el)
    ax, ay = bx+lx, by+ty
    if w==0: w=376
    if h==0: h=200

    # Card: bg navy_mid, border 1px rgba(201,168,76,0.12), radius 10px
    # border color approximation: rgba(c9a84c, 0.12) on navy ≈ #1a2640
    add_rrect(slide, ax, ay, w, h, fill=COLORS['navy_mid'],
              border=RGBColor(0x1E,0x2C,0x48), bw=Pt(0.75), radius=0.06)

    # Gold top bar: 3px, gradient gold→transparent (use solid gold)
    bar_color = COLORS['gold']
    cb = el.find(class_='card-bar')
    if cb:
        bs = sty(cb)
        bc = parse_c(bs.get('background',''))
        if bc: bar_color = bc
    add_rect(slide, ax, ay, w, 3, bar_color)

    # Content: padding 22px
    cx, cy, cw = ax+22, ay+22, w-44
    h3 = el.find('h3')
    yo = cy

    if h3:
        tb = add_tb(slide, cx, yo, cw, 30)
        tf = tb.text_frame; set_tf(tf)
        p = tf.paragraphs[0]
        s = sty(h3)
        # h3: 16px Serif, bold 700, gold_light, margin-bottom 10px
        h3s = parse_fs(s.get('font-size','')) or css_pt(16)
        h3c = parse_c(s.get('color','')) or COLORS['gold_light']
        render_rich(p, h3, h3c, h3s, FONT_T, COLORS['gold_light'])
        yo += 32

    # Remaining: p, ul
    rest = [c for c in el.children if isinstance(c,Tag) and c!=h3 and not hcls(c,'card-bar')]
    if rest:
        tb = add_tb(slide, cx, yo, cw, h-(yo-ay)-12)
        tf = tb.text_frame; set_tf(tf)
        first = True
        for child in rest:
            if child.name == 'p':
                p = tf.paragraphs[0] if first else tf.add_paragraph()
                first = False
                s = sty(child)
                fs = parse_fs(s.get('font-size','')) or css_pt(13)
                c = parse_c(s.get('color','')) or COLORS['text_muted']
                lh = parse_lh(s.get('line-height','')) or 1.65
                mb = s.get('margin-bottom','')
                sa = Pt(0)
                if mb:
                    m = re.search(r'(\d+)', mb)
                    if m: sa = Pt(int(m.group(1)) * PX_TO_PT)
                set_para_spacing(p, line_height=lh, space_after=sa)
                render_rich(p, child, c, fs, FONT_B, COLORS['gold_light'])
            elif child.name == 'ul':
                for li in child.find_all('li', recursive=False):
                    p = tf.paragraphs[0] if first else tf.add_paragraph()
                    first = False
                    # card-list li: 12px, line-height 1.55, margin-bottom 6px
                    # bullet-list li: 14px, line-height 1.65, margin-bottom 10px
                    is_card_list = hcls(child, 'card-list')
                    li_fs = css_pt(12) if is_card_list else css_pt(14)
                    li_lh = 1.55 if is_card_list else 1.65
                    li_mb = Pt(4) if is_card_list else Pt(6)
                    li_c = COLORS['text_muted'] if is_card_list else COLORS['white']
                    set_para_spacing(p, line_height=li_lh, space_after=li_mb)
                    set_bullet(p, '•', COLORS['gold'], li_fs)
                    render_rich(p, li, li_c, li_fs, FONT_B, COLORS['gold_light'])

def render_emphasis_box(slide, el, bx=0, by=0):
    lx, ty, w, h = coords(el)
    ax, ay = bx+lx, by+ty
    if w==0: w=1168
    if h==0: h=80

    # emphasis-box: bg gradient 135deg rgba(c9a84c, 0.08) → rgba(c9a84c, 0.03)
    # On navy #0a1628, rgba(c9a84c, 0.08) ≈ #141e30, rgba(c9a84c, 0.03) ≈ #0e192a
    # border-left: 3px solid gold, border-radius: 0 8px 8px 0
    add_rrect(slide, ax, ay, w, h, fill=RGBColor(0x11, 0x1C, 0x2D),
              border=RGBColor(0x18, 0x24, 0x38), bw=Pt(0.3), radius=0.04)
    # Gold left bar
    add_rect(slide, ax, ay, 3, h, COLORS['gold'])

    ps = el.find_all('p')
    tb = add_tb(slide, ax+20, ay+8, w-36, h-16)
    tf = tb.text_frame; set_tf(tf)
    first = True
    for p_el in ps:
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        s = sty(p_el)
        # p: 14px, line-height 1.65
        fs = parse_fs(s.get('font-size','')) or css_pt(14)
        c = parse_c(s.get('color','')) or COLORS['white']
        lh = parse_lh(s.get('line-height','')) or 1.65
        mb = s.get('margin-bottom','')
        sa = Pt(4)
        if mb:
            m = re.search(r'(\d+)', mb)
            if m: sa = Pt(int(m.group(1)) * PX_TO_PT)
        set_para_spacing(para, line_height=lh, space_after=sa)
        render_rich(para, p_el, c, fs, FONT_B, COLORS['gold_light'])

def render_section_label(slide, el, bx=0, by=0):
    lx, ty, w, _ = coords(el)
    ax, ay = bx+lx, by+ty
    if w==0: w=600

    yb = el.find(class_='year-badge')
    yt = el.find(class_='year-theme')
    if yb:
        # year-badge: bg gold, text navy, Serif 16px, bold 900, radius 4px
        yb_s = sty(yb)
        yb_fs = parse_fs(yb_s.get('font-size','')) or css_pt(16)
        bw2 = 60
        bs = add_rrect(slide, ax, ay, bw2, 24, fill=COLORS['gold'], bw=Pt(0), radius=0.03)
        bs.line.fill.background()
        tf = bs.text_frame; set_tf(tf)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        add_run(tf.paragraphs[0], txt(yb), FONT_T, yb_fs, COLORS['navy'], bold=True)
        if yt:
            yt_s = sty(yt)
            yt_fs = parse_fs(yt_s.get('font-size','')) or css_pt(16)
            tb = add_tb(slide, ax+bw2+8, ay, w-bw2-8, 24)
            tf2 = tb.text_frame; set_tf(tf2)
            add_run(tf2.paragraphs[0], txt(yt), FONT_B, yt_fs, COLORS['gold_light'])
    else:
        # section-label: 12px, bold 700, gold, letter-spacing 3px
        tb = add_tb(slide, ax, ay, w, 22)
        tf = tb.text_frame; set_tf(tf)
        add_run(tf.paragraphs[0], txt(el), FONT_B, css_pt(12), COLORS['gold'], bold=True)

def render_flow_box(slide, el, bx=0, by=0):
    lx, ty, w, h = coords(el)
    ax, ay = bx+lx, by+ty
    # flow-box: bg navy_mid, border 1px gold, radius 8px, 13px text
    shape = add_rrect(slide, ax, ay, w, h, fill=COLORS['navy_mid'],
                      border=COLORS['gold'], bw=Pt(0.75), radius=0.06)
    tf = shape.text_frame; set_tf(tf)
    for p in tf.paragraphs: p.clear()
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    render_rich(tf.paragraphs[0], el, COLORS['gold_light'], css_pt(13), FONT_B, COLORS['gold'])

def render_flow_arrow(slide, el, bx=0, by=0):
    lx, ty, w, h = coords(el)
    ax, ay = bx+lx, by+ty
    tb = add_tb(slide, ax, ay, w, h)
    tf = tb.text_frame; set_tf(tf)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    # flow-arrow: 20px
    add_run(tf.paragraphs[0], '▶', FONT_B, css_pt(20), COLORS['gold'])

def render_toc_item(slide, el, bx=0, by=0):
    lx, ty, w, h = coords(el)
    ax, ay = bx+lx, by+ty
    if h==0: h=44
    add_rrect(slide, ax, ay, w, h, fill=COLORS['navy_mid'],
              border=RGBColor(0x1E,0x2C,0x48), bw=Pt(0.5), radius=0.05)
    tb = add_tb(slide, ax+16, ay+6, w-32, h-12)
    tf = tb.text_frame; set_tf(tf)
    p = tf.paragraphs[0]
    num = el.find(class_='toc-num')
    text = el.find(class_='toc-text')
    # toc-num: 14px Serif, bold 900, gold
    if num: add_run(p, txt(num)+'   ', FONT_T, css_pt(14), COLORS['gold'], bold=True)
    # toc-text: 14px, weight 400
    if text: add_run(p, txt(text), FONT_B, css_pt(14), COLORS['white'])

def render_bullet_list(slide, el, bx=0, by=0):
    lx, ty, w, _ = coords(el)
    ax, ay = bx+lx, by+ty
    if w==0: w=1168
    lis = el.find_all('li', recursive=False)
    tb = add_tb(slide, ax, ay, w, len(lis)*30)
    tf = tb.text_frame; set_tf(tf)
    for i, li in enumerate(lis):
        p = tf.paragraphs[0] if i==0 else tf.add_paragraph()
        # bullet-list li: 14px, line-height 1.65, margin-bottom 10px
        set_para_spacing(p, line_height=1.65, space_after=Pt(7))
        set_bullet(p, '•', COLORS['gold'], css_pt(14))
        render_rich(p, li, COLORS['white'], css_pt(14), FONT_B, COLORS['gold_light'])

def render_metric_card(slide, el, bx=0, by=0):
    lx, ty, w, h = coords(el)
    ax, ay = bx+lx, by+ty
    if w==0: w=150
    if h==0: h=80
    add_rrect(slide, ax, ay, w, h, fill=COLORS['navy_mid'],
              border=RGBColor(0x1E,0x2C,0x48), bw=Pt(0.5), radius=0.06)
    val = el.find(class_='metric-value')
    lbl = el.find(class_='metric-label')
    if val:
        tb = add_tb(slide, ax, ay+10, w, 36)
        tf = tb.text_frame; set_tf(tf)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        # metric-value: 26px Serif, bold 900
        add_run(tf.paragraphs[0], txt(val), FONT_T, css_pt(26), COLORS['gold'], bold=True)
    if lbl:
        tb = add_tb(slide, ax, ay+h-30, w, 24)
        tf = tb.text_frame; set_tf(tf)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        # metric-label: 11px
        add_run(tf.paragraphs[0], txt(lbl), FONT_B, css_pt(11), COLORS['text_muted'])

def render_tags_line(slide, el, bx, by):
    lx, ty, w, _ = coords(el)
    if w==0: w=1168
    tags = el.find_all(class_='status-tag')
    if not tags: return
    tb = add_tb(slide, bx+lx, by+ty, w, 24)
    tf = tb.text_frame; set_tf(tf)
    p = tf.paragraphs[0]
    for tag in tags:
        tc2 = find_cls(tag, 'tag-')
        tc = TAG_COLORS.get(tc2, (None, COLORS['white']))[1] if tc2 else COLORS['white']
        # status-tag: 11px
        add_run(p, txt(tag), FONT_B, css_pt(11), tc, bold=True)
        add_run(p, '   ', FONT_B, css_pt(11), COLORS['text_muted'])

# ── Component Registry ──

# Known components: class name → renderer function
_RENDERERS = {}

def register_renderer(class_name, func):
    """Register a custom renderer for a CSS class.

    The renderer function signature must be: func(slide, el, bx, by)
    where bx, by are the body region offset in px.

    Example (in AI-generated wrapper script):
        from html_to_pptx import *
        def render_my_widget(slide, el, bx=0, by=0):
            lx, ty, w, h = coords(el)
            ...
        register_renderer('my-widget', render_my_widget)
        convert(sys.argv[1], sys.argv[2])
    """
    _RENDERERS[class_name] = func

def get_known_components():
    """Return set of all component class names handled by this script."""
    return set(_RENDERERS.keys()) | {
        'col-card', 'emphasis-box', 'mini-table', 'section-label',
        'flow-box', 'flow-arrow', 'toc-item', 'bullet-list',
        'metric-card', 'battle-card', 'timeline',
        # Structural (not dispatched by class):
        'slide-cover', 'slide-header', 'slide-body', 'slide-footer',
        'cover-content', 'cover-badge', 'cover-title', 'cover-sub',
        'cover-line', 'cover-version', 'card-bar',
        # Sub-components (handled inside parent renderers):
        'status-tag', 'card-list', 'dim-tag', 'year-badge', 'year-theme',
        'toc-num', 'toc-text', 'metric-value', 'metric-label',
        'battle-num', 'battle-name', 'battle-dept',
        'timeline-line', 'timeline-item', 'timeline-dot',
        'timeline-year', 'timeline-label', 'timeline-desc',
        'heat-table',
        # Heat-table cell classes:
        'h-attack', 'h-break', 'h-deep', 'h-base', 'h-mature', 'h-lead', 'h-tbd',
        # Status-tag variant classes:
        'tag-done', 'tag-attack', 'tag-base', 'tag-tbd', 'tag-break', 'tag-deep',
        # Navigation (skipped in conversion):
        'nav-bar', 'nav-btn', 'nav-dot', 'nav-label',
        'nav-progress', 'page-num', 'slide-chapter', 'slide-title',
        # Typography helpers:
        'body-text', 'body-text-sm', 'small-text', 'subtitle',
        'section-label', 'phase-label', 'phase-desc',
    }

def scan_unknown_components(html_path):
    """Scan HTML file and return set of CSS classes not in known components.

    Returns: (all_classes, unknown_classes)
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')
    known = get_known_components()
    all_cls = set()
    for el in soup.find_all(True):
        for c in (el.get('class') or []):
            all_cls.add(c)
    # Filter out generic/structural classes
    skip = {'slide', 'active', 'presentation', 'slide-container'}
    unknown = all_cls - known - skip
    return all_cls, unknown

# ── Body Renderer ──
def render_body(slide, body, bx=56, by=124):
    for child in body.children:
        if not isinstance(child, Tag): continue
        # Check custom renderers first
        matched = False
        for cls_name, func in _RENDERERS.items():
            if hcls(child, cls_name):
                func(slide, child, bx, by)
                matched = True
                break
        if matched:
            continue
        # Built-in renderers
        if hcls(child, 'col-card'): render_col_card(slide, child, bx, by)
        elif hcls(child, 'emphasis-box'): render_emphasis_box(slide, child, bx, by)
        elif hcls(child, 'mini-table') or child.name == 'table': render_table(slide, child, bx, by)
        elif hcls(child, 'section-label'): render_section_label(slide, child, bx, by)
        elif hcls(child, 'flow-box'): render_flow_box(slide, child, bx, by)
        elif hcls(child, 'flow-arrow'): render_flow_arrow(slide, child, bx, by)
        elif hcls(child, 'toc-item'): render_toc_item(slide, child, bx, by)
        elif hcls(child, 'bullet-list'): render_bullet_list(slide, child, bx, by)
        elif hcls(child, 'metric-card'): render_metric_card(slide, child, bx, by)
        elif child.get('data-ppt')=='text' and child.find(class_='status-tag'):
            render_tags_line(slide, child, bx, by)
        elif child.get('data-ppt')=='text':
            lx, ty, w, _ = coords(child)
            if w==0: w=400
            tb = add_tb(slide, bx+lx, by+ty, w, 24)
            tf = tb.text_frame; set_tf(tf)
            render_rich(tf.paragraphs[0], child, COLORS['white'], css_pt(14))

# ── Main ──
def convert(hp, pp):
    with open(hp, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    sels = sorted(soup.find_all('div', class_='slide'),
                  key=lambda x: int(x.get('data-slide',0)))

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)
    bl = prs.slide_layouts[6]

    st = {'total':0, 'cover':0, 'content':0, 'toc':0}
    for el in sels:
        slide = prs.slides.add_slide(bl)
        set_bg(slide, COLORS['navy'])
        dtype = el.get('data-type','content')
        st['total'] += 1

        if dtype=='cover' or hcls(el, 'slide-cover'):
            st['cover'] += 1; render_cover(slide, el)
        else:
            st['toc' if dtype=='toc' else 'content'] += 1
            render_header(slide, el.find(class_='slide-header'))
            body = el.find(class_='slide-body')
            if body: render_body(slide, body, 56, 124)
            render_footer(slide, el.find(class_='slide-footer'))

    prs.save(pp)
    sz = Path(pp).stat().st_size / 1024
    print(f"\n---转换完成---")
    print(f"源文件：{Path(hp).name}")
    print(f"输出文件：{pp}")
    print(f"总页数：{st['total']}（封面 {st['cover']} + 目录 {st['toc']} + 内容 {st['content']}）")
    print(f"文件大小：{sz:.0f} KB")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.html> <output.pptx>"); sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
