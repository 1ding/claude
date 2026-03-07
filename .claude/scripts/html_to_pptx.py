#!/usr/bin/env python3
"""
HTML Slides → PPTX 转换器

将 /ppt-to-html 生成的 800×450 HTML 幻灯片转换为 .pptx 文件。
解析 HTML 中的 .ppt-container 元素，按 CSS class 映射为对应的 PPTX slide。

用法：
    python html_to_pptx.py input.html [output.pptx]
"""

import sys
import re
import os
from bs4 import BeautifulSoup, Tag
from pptx import Presentation
from pptx.util import Inches, Pt, Emu


def Px(px):
    """像素转 EMU (96 DPI: 1px = 9525 EMU)"""
    return Emu(int(px * 9525))
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


# === 设计系统常量（与 TW-FMT-PPT-02 对齐） ===

# 页面尺寸 800x450 px → EMU (1px ≈ 12700 EMU, 但用 Px 换算)
SLIDE_WIDTH = Px(800)
SLIDE_HEIGHT = Px(450)

# 配色
COLOR_PRIMARY = RGBColor(0x63, 0x66, 0xF1)      # #6366f1 主题蓝紫
COLOR_PURPLE = RGBColor(0x8B, 0x5C, 0xF6)        # #8b5cf6 紫色
COLOR_GREEN = RGBColor(0x10, 0xB9, 0x81)          # #10b981 翠绿
COLOR_AMBER = RGBColor(0xF5, 0x9E, 0x0B)          # #f59e0b 琥珀
COLOR_BLUE = RGBColor(0x3B, 0x82, 0xF6)           # #3b82f6 天蓝
COLOR_TITLE = RGBColor(0x1E, 0x29, 0x3B)          # #1e293b 深蓝灰
COLOR_TEXT = RGBColor(0x33, 0x41, 0x55)            # #334155 主文本
COLOR_LIGHT = RGBColor(0x64, 0x74, 0x8B)          # #64748b 次要文本
COLOR_FOOTER = RGBColor(0x94, 0xA3, 0xB8)         # #94a3b8 页脚
COLOR_BORDER = RGBColor(0xE2, 0xE8, 0xF0)         # #e2e8f0 边框
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_BG_LIGHT = RGBColor(0xF8, 0xFA, 0xFC)       # #f8fafc 浅背景

# 渐变色
GRADIENT_START = RGBColor(0x66, 0x7E, 0xEA)       # #667eea
GRADIENT_END = RGBColor(0x76, 0x4B, 0xA2)         # #764ba2
SECTION_GRADIENT_START = RGBColor(0x81, 0x8C, 0xF8)  # #818cf8
SECTION_GRADIENT_END = RGBColor(0xA7, 0x8B, 0xFA)    # #a78bfa

# 区域定位 (px)
MARGIN_LEFT = 30
MARGIN_TOP = 30
TITLE_BAR_HEIGHT = 25
CONTENT_TOP = 66
CONTENT_WIDTH = 740
CONTENT_HEIGHT = 349
FOOTER_BOTTOM = 5
FOOTER_HEIGHT = 20

# 字号映射 (px → pt, 约 0.75 倍)
FONT_BODY = Pt(10)         # 13px
FONT_BREADCRUMB = Pt(10.5) # 14px
FONT_CARD_TITLE = Pt(10.5) # 14px
FONT_FOOTER = Pt(7.5)      # 10px
FONT_TITLE_MAIN = Pt(20)   # 26px
FONT_TITLE_SUB = Pt(9)     # 12px
FONT_SECTION = Pt(16.5)    # 22px
FONT_CODE = Pt(9)          # 12px
FONT_DATA_VALUE = Pt(18)   # 24px
FONT_DATA_LABEL = Pt(8)    # 11px
FONT_COMPACT = Pt(8.5)     # 11-12px

# 字体
FONT_FAMILY = "Microsoft YaHei"
FONT_CODE_FAMILY = "Consolas"

# 公司信息
COMPANY_INFO = "上海天帷智慧数字技术有限公司 / www.tenward.com"
LOGO_TEXT = "LOGO"


def hex_to_rgb(hex_str):
    """#rrggbb → RGBColor"""
    hex_str = hex_str.lstrip('#')
    return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def get_text(el):
    """提取元素的纯文本，清理空白"""
    if el is None:
        return ""
    text = el.get_text(separator=" ", strip=True)
    # 合并多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_direct_text(el):
    """提取元素的直接文本（不含子元素）"""
    if el is None:
        return ""
    return ''.join(
        child.string for child in el.children
        if isinstance(child, str) and child.strip()
    ).strip()


def add_gradient_background(slide, color_start, color_end):
    """为幻灯片添加渐变背景矩形"""
    bg_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Px(0), Px(0), SLIDE_WIDTH, SLIDE_HEIGHT
    )
    bg_shape.line.fill.background()

    fill = bg_shape.fill
    fill.gradient()
    fill.gradient_stops[0].color.rgb = color_start
    fill.gradient_stops[0].position = 0.0
    fill.gradient_stops[1].color.rgb = color_end
    fill.gradient_stops[1].position = 1.0

    # 放到最底层
    sp = bg_shape._element
    sp.getparent().remove(sp)
    slide.shapes._spTree.insert(2, sp)


def set_font(run, size=FONT_BODY, color=COLOR_TEXT, bold=False, font_name=FONT_FAMILY):
    """设置 run 的字体属性"""
    run.font.size = size
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = font_name


def add_textbox(slide, left, top, width, height, text="",
                font_size=FONT_BODY, font_color=COLOR_TEXT,
                bold=False, alignment=PP_ALIGN.LEFT,
                font_name=FONT_FAMILY, anchor=MSO_ANCHOR.TOP):
    """添加文本框并返回 (shape, text_frame)"""
    txbox = slide.shapes.add_textbox(Px(left), Px(top), Px(width), Px(height))
    tf = txbox.text_frame
    tf.word_wrap = True

    from pptx.oxml.ns import qn
    bodyPr = tf._txBody.find(qn('a:bodyPr'))
    anchor_map = {
        MSO_ANCHOR.TOP: 't',
        MSO_ANCHOR.MIDDLE: 'ctr',
        MSO_ANCHOR.BOTTOM: 'b',
    }
    bodyPr.set('anchor', anchor_map.get(anchor, 't'))

    if text:
        tf.paragraphs[0].text = text
        tf.paragraphs[0].alignment = alignment
        for run in tf.paragraphs[0].runs:
            set_font(run, font_size, font_color, bold, font_name)

    return txbox, tf


def add_paragraph(tf, text="", font_size=FONT_BODY, font_color=COLOR_TEXT,
                  bold=False, alignment=PP_ALIGN.LEFT, font_name=FONT_FAMILY,
                  space_before=Pt(0), space_after=Pt(0), bullet=False):
    """向 text_frame 追加段落"""
    p = tf.add_paragraph()
    p.alignment = alignment
    p.space_before = space_before
    p.space_after = space_after

    if bullet:
        # 添加圆点前缀
        run_dot = p.add_run()
        run_dot.text = "● "
        set_font(run_dot, Pt(6), COLOR_PRIMARY, False, font_name)

    run = p.add_run()
    run.text = text
    set_font(run, font_size, font_color, bold, font_name)
    return p


def add_bordered_rect(slide, left, top, width, height,
                      fill_color=COLOR_WHITE, border_color=COLOR_BORDER,
                      border_left_color=None, border_left_width=Pt(2.5)):
    """添加带边框的矩形"""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Px(left), Px(top), Px(width), Px(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(0.75)

    if border_left_color:
        # 用一个细矩形模拟左侧彩色条
        accent = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Px(left), Px(top), border_left_width, Px(height)
        )
        accent.fill.solid()
        accent.fill.fore_color.rgb = border_left_color
        accent.line.fill.background()

    return shape


def add_divider_line(slide, left, top, width):
    """添加水平分隔线"""
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Px(left), Px(top), Px(width), Pt(0.75)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_BORDER
    line.line.fill.background()
    return line


# === 幻灯片类型处理 ===

def create_title_slide(prs, container):
    """创建标题页（# 标题）"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白布局
    add_gradient_background(slide, GRADIENT_START, GRADIENT_END)

    # 提取内容
    title_el = container.select_one('.title-main')
    subtitle_el = container.select_one('.title-subtitle')
    author_el = container.select_one('.title-author')

    title_text = get_text(title_el) if title_el else ""
    subtitle_text = get_text(subtitle_el) if subtitle_el else ""
    author_text = get_text(author_el) if author_el else ""

    # 主标题
    if title_text:
        add_textbox(slide, 50, 155, 700, 50, title_text,
                    FONT_TITLE_MAIN, COLOR_WHITE, bold=True,
                    alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # 副标题
    if subtitle_text:
        add_textbox(slide, 50, 210, 700, 30, subtitle_text,
                    FONT_TITLE_SUB, COLOR_WHITE, alignment=PP_ALIGN.CENTER,
                    anchor=MSO_ANCHOR.MIDDLE)

    # 作者
    if author_text:
        add_textbox(slide, 50, 390, 700, 20, author_text,
                    Pt(6), COLOR_WHITE, alignment=PP_ALIGN.CENTER,
                    anchor=MSO_ANCHOR.MIDDLE)

    return slide


def create_section_slide(prs, container):
    """创建章节分隔页（## 标题）"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_gradient_background(slide, SECTION_GRADIENT_START, SECTION_GRADIENT_END)

    section_el = container.select_one('.section-title')
    section_text = get_text(section_el) if section_el else ""

    if section_text:
        add_textbox(slide, 50, 170, 700, 50, section_text,
                    FONT_SECTION, COLOR_WHITE, bold=True,
                    alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    return slide


def extract_list_items(el):
    """从 ul/ol 或含 .list-items 的元素中提取列表项文本"""
    items = []
    list_el = el.select_one('.list-items') or el.select_one('ul') or el.select_one('ol')
    if list_el:
        for li in list_el.find_all('li', recursive=False):
            text = get_text(li)
            # 移除圆点字符（如果 .list-dot 的文本混入了）
            text = re.sub(r'^[●•·]\s*', '', text)
            if text:
                items.append(text)
    return items


def extract_cards(container):
    """提取卡片信息"""
    cards = []
    for card in container.select('.card, .card-key'):
        title_el = card.select_one('.card-title')
        content_el = card.select_one('.card-content')
        is_key = 'card-key' in card.get('class', [])
        cards.append({
            'title': get_text(title_el),
            'content': get_text(content_el),
            'is_key': is_key,
            'items': extract_list_items(card),
        })
    return cards


def extract_data_cards(container):
    """提取数据卡片"""
    data_cards = []
    for dc in container.select('.data-card'):
        value_el = dc.select_one('.data-value')
        label_el = dc.select_one('.data-label')
        data_cards.append({
            'value': get_text(value_el),
            'label': get_text(label_el),
        })
    return data_cards


def render_content_elements(slide, container, left, top, width, max_height):
    """
    渲染内容区的各类元素到幻灯片上。
    返回当前 y 位置。
    """
    y = top
    gap = 8

    # 收集内容区的子元素
    content_el = container.select_one('.content-box')
    if content_el is None:
        # 可能是两栏布局，跳过
        return y

    # 数据卡片
    data_cards = extract_data_cards(content_el)
    if data_cards:
        card_gap = 10
        n = len(data_cards)
        card_w = (width - card_gap * (n - 1)) // n
        for i, dc in enumerate(data_cards):
            cx = left + i * (card_w + card_gap)
            add_bordered_rect(slide, cx, y, card_w, 60,
                              border_left_color=COLOR_PRIMARY)
            add_textbox(slide, cx + 8, y + 8, card_w - 16, 28, dc['value'],
                        FONT_DATA_VALUE, COLOR_PRIMARY, bold=True,
                        alignment=PP_ALIGN.CENTER)
            add_textbox(slide, cx + 8, y + 38, card_w - 16, 16, dc['label'],
                        FONT_DATA_LABEL, COLOR_LIGHT, alignment=PP_ALIGN.CENTER)
        y += 60 + gap

    # 卡片
    cards = extract_cards(content_el)
    if cards:
        # 尝试平铺（如果卡片数 <= 3 且宽度允许）
        if len(cards) <= 3 and len(cards) > 1:
            card_gap = 10
            card_w = (width - card_gap * (len(cards) - 1)) // len(cards)
            card_h = min(120, max_height - (y - top) - gap)
            for i, card in enumerate(cards):
                cx = left + i * (card_w + card_gap)
                border_color = COLOR_PRIMARY if card['is_key'] else None
                add_bordered_rect(slide, cx, y, card_w, card_h,
                                  border_left_color=border_color)
                # 卡片标题
                ty = y + 8
                if card['title']:
                    title_color = COLOR_PRIMARY if card['is_key'] else COLOR_TITLE
                    add_textbox(slide, cx + 12, ty, card_w - 24, 18,
                                card['title'], FONT_CARD_TITLE, title_color, bold=True)
                    ty += 22
                # 卡片内容
                if card['items']:
                    _, tf = add_textbox(slide, cx + 12, ty, card_w - 24, card_h - (ty - y) - 8)
                    tf.paragraphs[0].text = ""
                    for item in card['items']:
                        add_paragraph(tf, item, FONT_COMPACT, COLOR_TEXT,
                                      bullet=True, space_after=Pt(2))
                elif card['content']:
                    add_textbox(slide, cx + 12, ty, card_w - 24, card_h - (ty - y) - 8,
                                card['content'], FONT_BODY, COLOR_TEXT)
            y += card_h + gap
        else:
            # 纵向堆叠
            for card in cards:
                card_h = 60
                if card['items']:
                    card_h = max(60, 28 + len(card['items']) * 18)
                card_h = min(card_h, max_height - (y - top) - gap)
                if card_h <= 0:
                    break
                border_color = COLOR_PRIMARY if card['is_key'] else None
                add_bordered_rect(slide, left, y, width, card_h,
                                  border_left_color=border_color)
                ty = y + 8
                if card['title']:
                    title_color = COLOR_PRIMARY if card['is_key'] else COLOR_TITLE
                    add_textbox(slide, left + 12, ty, width - 24, 18,
                                card['title'], FONT_CARD_TITLE, title_color, bold=True)
                    ty += 22
                if card['items']:
                    _, tf = add_textbox(slide, left + 12, ty, width - 24, card_h - (ty - y) - 8)
                    tf.paragraphs[0].text = ""
                    for item in card['items']:
                        add_paragraph(tf, item, FONT_BODY, COLOR_TEXT,
                                      bullet=True, space_after=Pt(2))
                elif card['content']:
                    add_textbox(slide, left + 12, ty, width - 24, card_h - (ty - y) - 8,
                                card['content'], FONT_BODY, COLOR_TEXT)
                y += card_h + gap

    # 流程图 (flow-box)
    flow_boxes = content_el.select('.flow-box')
    if flow_boxes:
        n = len(flow_boxes)
        arrow_w = 20
        total_arrows = n - 1
        box_w = min(120, (width - arrow_w * total_arrows) // n)
        box_h = 36
        start_x = left + (width - (box_w * n + arrow_w * total_arrows)) // 2
        for i, fb in enumerate(flow_boxes):
            bx = start_x + i * (box_w + arrow_w)
            add_bordered_rect(slide, bx, y, box_w, box_h,
                              border_color=COLOR_PRIMARY)
            add_textbox(slide, bx + 4, y + 4, box_w - 8, box_h - 8,
                        get_text(fb), FONT_BODY, COLOR_TEXT,
                        alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            if i < n - 1:
                ax = bx + box_w + 2
                add_textbox(slide, ax, y + 4, arrow_w - 4, box_h - 8,
                            "→", Pt(14), COLOR_PRIMARY,
                            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        y += box_h + gap

    # 通用列表（不在卡片内的 .list-items）
    top_lists = content_el.select(':scope > .list-items, :scope > ul, :scope > ol')
    # 也处理直接子 div 内的列表（非卡片）
    if not top_lists:
        for child in content_el.children:
            if isinstance(child, Tag) and 'card' not in ' '.join(child.get('class', [])):
                sub_list = child.select_one('.list-items') or child.select_one('ul')
                if sub_list and sub_list not in [c for card_el in content_el.select('.card, .card-key') for c in card_el.select('.list-items, ul')]:
                    top_lists.append(sub_list)

    if top_lists and not cards and not data_cards:
        for list_el in top_lists:
            items = []
            for li in list_el.find_all('li', recursive=False):
                text = get_text(li)
                text = re.sub(r'^[●•·]\s*', '', text)
                if text:
                    items.append(text)
            if items:
                remaining = max_height - (y - top)
                box_h = min(remaining, len(items) * 22 + 8)
                _, tf = add_textbox(slide, left, y, width, box_h)
                tf.paragraphs[0].text = ""
                for item in items:
                    add_paragraph(tf, item, FONT_BODY, COLOR_TEXT,
                                  bullet=True, space_after=Pt(3))
                y += box_h + gap

    # 代码块 <pre>
    pre_blocks = content_el.select('pre')
    if pre_blocks:
        for pre in pre_blocks:
            code_text = pre.get_text()
            lines = code_text.strip().split('\n')
            code_h = min(max_height - (y - top), len(lines) * 14 + 16)
            if code_h <= 0:
                break
            # 深色背景
            bg = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Px(left), Px(y), Px(width), Px(code_h)
            )
            bg.fill.solid()
            bg.fill.fore_color.rgb = RGBColor(0x1E, 0x29, 0x3B)
            bg.line.fill.background()
            # 代码文本
            add_textbox(slide, left + 10, y + 6, width - 20, code_h - 12,
                        code_text.strip(), FONT_CODE,
                        RGBColor(0xE2, 0xE8, 0xF0), font_name=FONT_CODE_FAMILY)
            y += code_h + gap

    # 兜底：如果以上都没有提取到内容，提取所有文本
    if y == top + (60 + gap if data_cards else 0) and not cards and not flow_boxes and not pre_blocks:
        # 尝试提取 highlight 文本和普通段落
        all_text = get_text(content_el)
        if all_text:
            remaining = max(50, max_height - (y - top))
            add_textbox(slide, left, y, width, remaining,
                        all_text, FONT_BODY, COLOR_TEXT)

    return y


def create_content_slide(prs, container):
    """创建标题+内容页（### 或 #### 标题）"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 标题栏
    title_bar = container.select_one('.title-bar')
    breadcrumb = container.select_one('.breadcrumb-title')

    # 添加标题栏分隔线
    add_divider_line(slide, MARGIN_LEFT, MARGIN_TOP + TITLE_BAR_HEIGHT, CONTENT_WIDTH)

    # 面包屑标题
    if breadcrumb:
        parts = []
        for child in breadcrumb.children:
            if isinstance(child, Tag):
                cls = ' '.join(child.get('class', []))
                text = get_text(child)
                if 'separator' in cls:
                    parts.append(('sep', text))
                elif 'level-1' in cls:
                    parts.append(('l1', text))
                elif 'level-2' in cls:
                    parts.append(('l2', text))
                elif 'level-3' in cls:
                    parts.append(('l3', text))
                else:
                    parts.append(('l2', text))

        breadcrumb_text = ' '.join(p[1] for p in parts)
        txbox, tf = add_textbox(slide, MARGIN_LEFT, MARGIN_TOP, CONTENT_WIDTH - 60, TITLE_BAR_HEIGHT)
        tf.paragraphs[0].text = ""
        for ptype, ptext in parts:
            run = tf.paragraphs[0].add_run()
            run.text = ptext
            if ptype == 'l1':
                set_font(run, FONT_BREADCRUMB, COLOR_PRIMARY, bold=True)
            elif ptype == 'l2':
                set_font(run, FONT_BREADCRUMB, COLOR_TITLE, bold=True)
            elif ptype == 'l3':
                set_font(run, FONT_BREADCRUMB, COLOR_PURPLE, bold=True)
            elif ptype == 'sep':
                set_font(run, FONT_BREADCRUMB, COLOR_FOOTER, bold=False)
                run.text = f" {ptext} "

    # LOGO
    logo_el = container.select_one('.company-logo')
    logo_text = get_text(logo_el) if logo_el else LOGO_TEXT
    add_textbox(slide, MARGIN_LEFT + CONTENT_WIDTH - 50, MARGIN_TOP, 50, TITLE_BAR_HEIGHT,
                logo_text, Pt(9), COLOR_PRIMARY, bold=True, alignment=PP_ALIGN.RIGHT)

    # 内容区
    render_content_elements(slide, container,
                            MARGIN_LEFT, CONTENT_TOP,
                            CONTENT_WIDTH, CONTENT_HEIGHT)

    # 页脚
    page_num_el = container.select_one('.ppt-footer')
    page_text = ""
    if page_num_el:
        spans = page_num_el.find_all('span')
        if len(spans) >= 2:
            page_text = get_text(spans[-1])

    add_textbox(slide, MARGIN_LEFT, 450 - FOOTER_BOTTOM - FOOTER_HEIGHT,
                CONTENT_WIDTH // 2, FOOTER_HEIGHT,
                COMPANY_INFO, FONT_FOOTER, COLOR_FOOTER)

    if page_text:
        add_textbox(slide, MARGIN_LEFT + CONTENT_WIDTH // 2,
                    450 - FOOTER_BOTTOM - FOOTER_HEIGHT,
                    CONTENT_WIDTH // 2, FOOTER_HEIGHT,
                    page_text, FONT_FOOTER, COLOR_FOOTER, alignment=PP_ALIGN.RIGHT)

    return slide


def create_two_column_slide(prs, container):
    """创建两栏布局页"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 标题栏（同 content slide）
    breadcrumb = container.select_one('.breadcrumb-title')
    add_divider_line(slide, MARGIN_LEFT, MARGIN_TOP + TITLE_BAR_HEIGHT, CONTENT_WIDTH)

    if breadcrumb:
        parts = []
        for child in breadcrumb.children:
            if isinstance(child, Tag):
                cls = ' '.join(child.get('class', []))
                text = get_text(child)
                if 'separator' in cls:
                    parts.append(('sep', text))
                elif 'level-1' in cls:
                    parts.append(('l1', text))
                elif 'level-2' in cls:
                    parts.append(('l2', text))
                elif 'level-3' in cls:
                    parts.append(('l3', text))
                else:
                    parts.append(('l2', text))

        txbox, tf = add_textbox(slide, MARGIN_LEFT, MARGIN_TOP, CONTENT_WIDTH - 60, TITLE_BAR_HEIGHT)
        tf.paragraphs[0].text = ""
        for ptype, ptext in parts:
            run = tf.paragraphs[0].add_run()
            run.text = ptext
            if ptype == 'l1':
                set_font(run, FONT_BREADCRUMB, COLOR_PRIMARY, bold=True)
            elif ptype == 'l2':
                set_font(run, FONT_BREADCRUMB, COLOR_TITLE, bold=True)
            elif ptype == 'l3':
                set_font(run, FONT_BREADCRUMB, COLOR_PURPLE, bold=True)
            elif ptype == 'sep':
                set_font(run, FONT_BREADCRUMB, COLOR_FOOTER, bold=False)
                run.text = f" {ptext} "

    logo_el = container.select_one('.company-logo')
    logo_text = get_text(logo_el) if logo_el else LOGO_TEXT
    add_textbox(slide, MARGIN_LEFT + CONTENT_WIDTH - 50, MARGIN_TOP, 50, TITLE_BAR_HEIGHT,
                logo_text, Pt(9), COLOR_PRIMARY, bold=True, alignment=PP_ALIGN.RIGHT)

    # 左栏
    left_col = container.select_one('.left-column')
    right_col = container.select_one('.right-column')

    col_width = 355
    col_height = 349
    col_padding = 14

    for i, col in enumerate([left_col, right_col]):
        if col is None:
            continue
        col_left = MARGIN_LEFT if i == 0 else MARGIN_LEFT + col_width + 30

        # 列背景
        add_bordered_rect(slide, col_left, CONTENT_TOP, col_width, col_height)

        # 列标题
        col_title = col.select_one('.column-title, h3')
        cy = CONTENT_TOP + col_padding
        if col_title:
            add_textbox(slide, col_left + col_padding, cy,
                        col_width - col_padding * 2, 20,
                        get_text(col_title), FONT_CARD_TITLE, COLOR_TITLE, bold=True)
            cy += 24
            # 标题下分隔线
            add_divider_line(slide, col_left + col_padding, cy - 4,
                             col_width - col_padding * 2)

        # 列内容
        col_content = col.select_one('.column-content')
        if col_content:
            items = extract_list_items(col_content)
            if items:
                remaining = col_height - (cy - CONTENT_TOP) - col_padding
                _, tf = add_textbox(slide, col_left + col_padding, cy,
                                    col_width - col_padding * 2, remaining)
                tf.paragraphs[0].text = ""
                for item in items:
                    add_paragraph(tf, item, FONT_BODY, COLOR_TEXT,
                                  bullet=True, space_after=Pt(3))
            else:
                text = get_text(col_content)
                if text:
                    remaining = col_height - (cy - CONTENT_TOP) - col_padding
                    add_textbox(slide, col_left + col_padding, cy,
                                col_width - col_padding * 2, remaining,
                                text, FONT_BODY, COLOR_TEXT)

    # 页脚
    page_num_el = container.select_one('.ppt-footer')
    page_text = ""
    if page_num_el:
        spans = page_num_el.find_all('span')
        if len(spans) >= 2:
            page_text = get_text(spans[-1])

    add_textbox(slide, MARGIN_LEFT, 450 - FOOTER_BOTTOM - FOOTER_HEIGHT,
                CONTENT_WIDTH // 2, FOOTER_HEIGHT,
                COMPANY_INFO, FONT_FOOTER, COLOR_FOOTER)
    if page_text:
        add_textbox(slide, MARGIN_LEFT + CONTENT_WIDTH // 2,
                    450 - FOOTER_BOTTOM - FOOTER_HEIGHT,
                    CONTENT_WIDTH // 2, FOOTER_HEIGHT,
                    page_text, FONT_FOOTER, COLOR_FOOTER, alignment=PP_ALIGN.RIGHT)

    return slide


def detect_slide_type(container):
    """检测幻灯片类型"""
    classes = ' '.join(container.get('class', []))
    if 'layout-title' in classes:
        return 'title'
    elif 'layout-section' in classes:
        return 'section'
    elif 'layout-two-columns' in classes:
        return 'two-columns'
    elif 'layout-content' in classes:
        return 'content'
    else:
        # 尝试检测内部元素
        if container.select_one('.title-main'):
            return 'title'
        elif container.select_one('.section-title'):
            return 'section'
        elif container.select_one('.left-column'):
            return 'two-columns'
        else:
            return 'content'


def convert_html_to_pptx(html_path, output_path=None):
    """主转换函数"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'lxml')
    containers = soup.select('.ppt-container')

    if not containers:
        print(f"错误：未找到 .ppt-container 元素", file=sys.stderr)
        sys.exit(1)

    # 创建演示文稿
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    stats = {'title': 0, 'section': 0, 'content': 0, 'two-columns': 0}

    for container in containers:
        slide_type = detect_slide_type(container)
        stats[slide_type] = stats.get(slide_type, 0) + 1

        if slide_type == 'title':
            create_title_slide(prs, container)
        elif slide_type == 'section':
            create_section_slide(prs, container)
        elif slide_type == 'two-columns':
            create_two_column_slide(prs, container)
        else:
            create_content_slide(prs, container)

    # 输出路径
    if output_path is None:
        base = os.path.splitext(os.path.basename(html_path))[0]
        # 去掉 -slides 后缀
        base = re.sub(r'-slides.*$', '', base)
        output_dir = os.path.dirname(html_path)
        output_path = os.path.join(output_dir, f"{base}.pptx")

    prs.save(output_path)

    total = sum(stats.values())
    print(f"转换完成")
    print(f"源文件：{os.path.basename(html_path)}")
    print(f"输出文件：{output_path}")
    print(f"总页数：{total}（标题页 {stats['title']} + 章节页 {stats['section']} "
          f"+ 内容页 {stats['content']} + 两栏页 {stats['two-columns']}）")
    print(f"文件大小：{os.path.getsize(output_path) / 1024:.1f} KB")

    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python html_to_pptx.py input.html [output.pptx]", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    convert_html_to_pptx(input_file, output_file)
