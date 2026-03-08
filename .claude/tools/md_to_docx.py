#!/usr/bin/env python3
"""MD to DOCX Converter — 基于《排版格式规范》的 Markdown → Word 转换器.

格式规范（源自 md2docx.js）：
- 标题/正文字体：仿宋 (FangSong)
- 字号：小三号 (15pt)
- 行间距：最小 30pt
- + 自然段落：第1层首行缩进1cm，第n层左缩进 n*1cm
- - 列表项：符号1cm，悬挂缩进1cm，第n层左缩进 n*1cm
- 标题自动编号（从二级开始）
- 表格、代码块、ASCII 图（文本保留）
"""

import sys, re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, Twips, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import copy

# ── Constants (matching md2docx.js) ──
FONT_HEADING = 'FangSong'
FONT_BODY = 'FangSong'
FONT_CODE = 'FangSong'
FONT_GRAPH = 'Sarasa Term SC'

FONT_SIZE = Pt(15)          # 小三号 = 15pt
FONT_SIZE_GRAPH = Pt(12)
LINE_SPACING = Pt(30)       # 最小行高 30pt
SPACING_BEFORE = Pt(3)      # 段前 3pt
SPACING_AFTER = Pt(6)       # 段后 6pt
FIRST_LEVEL_SPACING_BEFORE = Pt(18)  # 第一级段前 18pt
INDENT_UNIT = Cm(1)         # 1cm 缩进单位

# ── Node types ──
HEADING = 'heading'
CONTENT = 'content'       # + 开头
LIST_ITEM = 'list_item'   # - 开头
CODE_BLOCK = 'code_block'
GRAPH_BLOCK = 'graph_block'
TABLE = 'table'
TEXT = 'text'


# ── Markdown Parser ──
class MarkdownParser:
    def __init__(self, content):
        self.lines = content.split('\n')
        self.pos = 0
        self.nodes = []

    def parse(self):
        while self.pos < len(self.lines):
            node = self._parse_line()
            if node:
                self.nodes.append(node)
        return self.nodes

    def _parse_line(self):
        if self.pos >= len(self.lines):
            return None
        line = self.lines[self.pos]
        if not line.strip():
            self.pos += 1
            return None

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if stripped.startswith('#'):
            return self._parse_heading(stripped)
        if stripped.startswith('```'):
            return self._parse_code_block(indent, stripped)
        if stripped.startswith('|'):
            return self._parse_table(indent)
        if stripped.startswith('+'):
            return self._parse_content(indent, stripped)
        if stripped.startswith('-') and not re.match(r'^\|.*-.*\|$', stripped):
            return self._parse_list_item(indent, stripped)

        self.pos += 1
        return {'type': TEXT, 'content': stripped, 'indent': indent}

    def _parse_heading(self, line):
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m:
            level = len(m.group(1))
            content = re.sub(r'^[\d.]+\s+', '', m.group(2))
            self.pos += 1
            return {'type': HEADING, 'content': content, 'level': level}
        self.pos += 1
        return {'type': TEXT, 'content': line, 'indent': 0}

    def _parse_content(self, indent, line):
        content = re.sub(r'^\+\s*', '', line)
        self.pos += 1
        return {'type': CONTENT, 'content': content, 'indent': indent}

    def _parse_list_item(self, indent, line):
        content = re.sub(r'^-\s*', '', line)
        self.pos += 1
        return {'type': LIST_ITEM, 'content': content, 'indent': indent}

    def _parse_code_block(self, indent, first_line):
        m = re.match(r'^```(\w*)$', first_line)
        language = m.group(1) if m else ''
        is_graph = language in ('graph', 'mermaid', 'dot')
        self.pos += 1
        lines = []
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if line.strip() == '```':
                self.pos += 1
                break
            lines.append(line)
            self.pos += 1
        return {
            'type': GRAPH_BLOCK if is_graph else CODE_BLOCK,
            'content': '\n'.join(lines),
            'indent': indent,
            'language': language,
            'raw_lines': lines,
        }

    def _parse_table(self, indent):
        lines = []
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if not line.strip().startswith('|'):
                break
            lines.append(line.strip())
            self.pos += 1
        return {'type': TABLE, 'content': '', 'indent': indent, 'raw_lines': lines}


# ── DOCX Generator ──
class DocxGenerator:
    def __init__(self):
        self.doc = Document()
        self._setup_styles()
        self._heading_counters = [0] * 6  # for manual numbering

    def _setup_styles(self):
        """Configure default document styles."""
        style = self.doc.styles['Normal']
        font = style.font
        font.name = FONT_BODY
        font.size = FONT_SIZE
        style.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_BODY)

        pf = style.paragraph_format
        pf.line_spacing = LINE_SPACING
        pf.line_spacing_rule = 4  # AT_LEAST
        pf.space_before = SPACING_BEFORE
        pf.space_after = SPACING_AFTER

        # Page margins: 1 inch = 2.54cm
        for section in self.doc.sections:
            section.top_margin = Cm(2.54)
            section.bottom_margin = Cm(2.54)
            section.left_margin = Cm(2.54)
            section.right_margin = Cm(2.54)

    def _set_font(self, run, font_name=FONT_BODY, size=FONT_SIZE, bold=False, italic=False, color=None):
        """Set font properties on a run."""
        run.font.name = font_name
        run.font.size = size
        run.font.bold = bold
        run.font.italic = italic
        if color:
            run.font.color.rgb = color
        # Set East Asian font
        r = run._element
        rPr = r.find(qn('w:rPr'))
        if rPr is None:
            rPr = parse_xml(f'<w:rPr {nsdecls("w")}></w:rPr>')
            r.insert(0, rPr)
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} w:eastAsia="{font_name}"/>')
            rPr.insert(0, rFonts)
        else:
            rFonts.set(qn('w:eastAsia'), font_name)

    def _set_spacing(self, para, before=SPACING_BEFORE, after=SPACING_AFTER):
        """Set paragraph spacing."""
        pf = para.paragraph_format
        pf.space_before = before
        pf.space_after = after
        pf.line_spacing = LINE_SPACING
        pf.line_spacing_rule = 4  # AT_LEAST

    def _add_inline_text(self, para, text, font_name=FONT_BODY):
        """Parse inline formatting (**bold**, *italic*, `code`) and add runs."""
        pattern = r'(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`([^`]+)`)'
        last = 0
        for m in re.finditer(pattern, text):
            if m.start() > last:
                run = para.add_run(text[last:m.start()])
                self._set_font(run, font_name)
            if m.group(2):  # bold
                run = para.add_run(m.group(2))
                self._set_font(run, font_name, bold=True)
            elif m.group(4):  # italic
                run = para.add_run(m.group(4))
                self._set_font(run, font_name, italic=True)
            elif m.group(6):  # code
                run = para.add_run(m.group(6))
                self._set_font(run, FONT_CODE)
            last = m.end()
        if last < len(text):
            run = para.add_run(text[last:])
            self._set_font(run, font_name)
        if last == 0 and not text:
            pass  # empty

    def _heading_number(self, level):
        """Generate heading number string. Level 2 → '1', Level 3 → '1.1', etc."""
        # level is 1-based; numbering starts from level 2
        idx = level - 2  # 0-based for numbering
        if idx < 0:
            return ''
        # Increment current level
        self._heading_counters[idx] += 1
        # Reset all deeper levels
        for i in range(idx + 1, 6):
            self._heading_counters[i] = 0
        # Build number string
        parts = []
        for i in range(idx + 1):
            parts.append(str(self._heading_counters[i]))
        return '.'.join(parts) + ' '

    def generate(self, nodes):
        """Generate document from parsed nodes."""
        prev_type = None

        for node in nodes:
            ntype = node['type']

            if ntype == HEADING:
                level = node['level']
                heading_before = SPACING_BEFORE if prev_type == HEADING else FIRST_LEVEL_SPACING_BEFORE

                if level == 1:
                    # Level 1: document title, centered, no numbering
                    para = self.doc.add_paragraph()
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    self._set_spacing(para, heading_before, SPACING_AFTER)
                    run = para.add_run(node['content'])
                    self._set_font(run, FONT_HEADING, bold=True)
                    # Set outline level
                    self._set_outline_level(para, 0)
                else:
                    # Level 2+: auto-numbered
                    num_str = self._heading_number(level)
                    para = self.doc.add_paragraph()
                    self._set_spacing(para, heading_before, SPACING_AFTER)
                    run = para.add_run(num_str + node['content'])
                    self._set_font(run, FONT_HEADING, bold=True)
                    self._set_outline_level(para, level - 1)

            elif ntype == CONTENT:
                # + paragraph
                content_level = node['indent'] // 4
                para = self.doc.add_paragraph()

                if content_level == 0:
                    # First level: first-line indent 1cm, spacing 18pt before
                    para.paragraph_format.first_line_indent = INDENT_UNIT
                    self._set_spacing(para, FIRST_LEVEL_SPACING_BEFORE, SPACING_AFTER)
                else:
                    # Deeper levels: left indent n*1cm
                    para.paragraph_format.left_indent = Cm(content_level)
                    self._set_spacing(para, SPACING_BEFORE, SPACING_AFTER)

                self._add_inline_text(para, node['content'])

            elif ntype == LIST_ITEM:
                # - list item
                list_level = node['indent'] // 4
                para = self.doc.add_paragraph()

                # Left indent (n+1)*1cm, hanging indent 1cm
                para.paragraph_format.left_indent = Cm(list_level + 1)
                para.paragraph_format.first_line_indent = Cm(-1)

                if list_level == 0:
                    self._set_spacing(para, FIRST_LEVEL_SPACING_BEFORE, SPACING_AFTER)
                else:
                    self._set_spacing(para, SPACING_BEFORE, SPACING_AFTER)

                # Add bullet marker
                run = para.add_run('- ')
                self._set_font(run, FONT_BODY)
                self._add_inline_text(para, node['content'])

            elif ntype == CODE_BLOCK:
                # Code block header
                para = self.doc.add_paragraph()
                self._set_spacing(para)
                self._set_shading(para, 'F5F5F5')
                run = para.add_run(f'[{node["language"] or "text"}]')
                self._set_font(run, FONT_CODE, color=RGBColor(0x66, 0x66, 0x66))

                # Code lines
                for line in node['raw_lines']:
                    para = self.doc.add_paragraph()
                    self._set_spacing(para)
                    self._set_shading(para, 'F5F5F5')
                    run = para.add_run(line or ' ')
                    self._set_font(run, FONT_CODE)

                # End marker
                para = self.doc.add_paragraph()
                self._set_spacing(para)
                self._set_shading(para, 'F5F5F5')

            elif ntype == GRAPH_BLOCK:
                # ASCII graph as text (no Puppeteer in Python version)
                para = self.doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                self._set_spacing(para)
                run = para.add_run(f'[{node["language"]}]')
                self._set_font(run, FONT_GRAPH, size=FONT_SIZE_GRAPH,
                               color=RGBColor(0x66, 0x66, 0x66), italic=True)

                for line in node['raw_lines']:
                    para = self.doc.add_paragraph()
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    self._set_spacing(para)
                    run = para.add_run(line or ' ')
                    self._set_font(run, FONT_GRAPH, size=FONT_SIZE_GRAPH)

                # Empty line after
                para = self.doc.add_paragraph()
                self._set_spacing(para)

            elif ntype == TABLE:
                table_level = node['indent'] // 4
                rows_data = self._parse_table_data(node['raw_lines'])
                if rows_data:
                    self._create_table(rows_data, table_level)
                    # Empty paragraph after table
                    para = self.doc.add_paragraph()
                    self._set_spacing(para)

            elif ntype == TEXT:
                if node['content'].strip():
                    para = self.doc.add_paragraph()
                    self._set_spacing(para)
                    self._add_inline_text(para, node['content'])

            prev_type = ntype

        return self.doc

    def _set_outline_level(self, para, level):
        """Set outline level for navigation pane."""
        pPr = para._element.get_or_add_pPr()
        outline = pPr.find(qn('w:outlineLvl'))
        if outline is None:
            outline = parse_xml(f'<w:outlineLvl {nsdecls("w")} w:val="{level}"/>')
            pPr.append(outline)
        else:
            outline.set(qn('w:val'), str(level))

    def _set_shading(self, para, color):
        """Set paragraph background shading."""
        pPr = para._element.get_or_add_pPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}" w:val="clear"/>')
        pPr.append(shd)

    def _parse_table_data(self, lines):
        """Parse markdown table lines into rows of cells."""
        rows = []
        for line in lines:
            if re.match(r'^\|[\s\-:|]+\|$', line):
                continue  # skip separator
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells:
                rows.append(cells)
        return rows

    def _create_table(self, rows_data, indent_level=0):
        """Create a Word table from parsed data."""
        if not rows_data:
            return
        n_cols = len(rows_data[0])
        n_rows = len(rows_data)

        table = self.doc.add_table(rows=n_rows, cols=n_cols)
        table.alignment = WD_TABLE_ALIGNMENT.LEFT

        # Set table width and indent
        tbl = table._tbl
        tblPr = tbl.find(qn('w:tblPr'))
        if tblPr is None:
            tblPr = parse_xml(f'<w:tblPr {nsdecls("w")}></w:tblPr>')
            tbl.insert(0, tblPr)

        # Table indent
        indent_twips = int((indent_level * 1 + 0.2) * 567)
        tblInd = parse_xml(f'<w:tblInd {nsdecls("w")} w:w="{indent_twips}" w:type="dxa"/>')
        tblPr.append(tblInd)

        # Table width
        table_width = int((15.5 - indent_level * 1) * 567)
        tblW = tblPr.find(qn('w:tblW'))
        if tblW is not None:
            tblPr.remove(tblW)
        tblW = parse_xml(f'<w:tblW {nsdecls("w")} w:w="{table_width}" w:type="dxa"/>')
        tblPr.append(tblW)

        # Set borders
        borders_xml = f'''<w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>
        </w:tblBorders>'''
        tblPr.append(parse_xml(borders_xml))

        # Fill cells
        col_width = table_width // n_cols
        for i, row_data in enumerate(rows_data):
            row = table.rows[i]
            is_header = (i == 0)
            for j, cell_text in enumerate(row_data):
                if j >= n_cols:
                    break
                cell = row.cells[j]
                # Clear default paragraph
                cell.text = ''
                para = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
                self._set_spacing(para, SPACING_BEFORE, SPACING_AFTER)

                run = para.add_run(cell_text)
                font_name = FONT_HEADING if is_header else FONT_BODY
                self._set_font(run, font_name, bold=is_header)

                # Header shading
                if is_header:
                    tc = cell._tc
                    tcPr = tc.get_or_add_tcPr()
                    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="E7E6E6" w:val="clear"/>')
                    tcPr.append(shd)

                # Cell margins
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                mar = parse_xml(f'''<w:tcMar {nsdecls("w")}>
                    <w:top w:w="0" w:type="dxa"/>
                    <w:bottom w:w="57" w:type="dxa"/>
                    <w:left w:w="113" w:type="dxa"/>
                    <w:right w:w="113" w:type="dxa"/>
                </w:tcMar>''')
                tcPr.append(mar)

                # Column width
                tcW = tcPr.find(qn('w:tcW'))
                if tcW is not None:
                    tcPr.remove(tcW)
                tcW = parse_xml(f'<w:tcW {nsdecls("w")} w:w="{col_width}" w:type="dxa"/>')
                tcPr.append(tcW)

    def save(self, output_path):
        """Save the document."""
        self.doc.save(output_path)


# ── Main ──
def convert(input_path, output_path):
    content = Path(input_path).read_text(encoding='utf-8')
    parser = MarkdownParser(content)
    nodes = parser.parse()
    print(f'Parsed {len(nodes)} nodes from {input_path}')

    gen = DocxGenerator()
    gen.generate(nodes)
    gen.save(output_path)

    sz = Path(output_path).stat().st_size / 1024
    print(f'\n---转换完成---')
    print(f'源文件：{Path(input_path).name}')
    print(f'输出文件：{output_path}')
    print(f'文件大小：{sz:.0f} KB')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: md_to_docx.py <input.md> [output.docx]')
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.rsplit('.', 1)[0] + '.docx'
    convert(inp, out)
