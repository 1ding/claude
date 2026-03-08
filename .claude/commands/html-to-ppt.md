# HTML 幻灯片转 PPTX 文件

将 `ppt-slides-theme.html` 模板生成的 HTML 幻灯片转换为 .pptx 文件。

**架构**：基础脚本（`.claude/tools/html_to_pptx.py`）处理所有已知组件；遇到未知组件时 AI 现写 renderer 并注册。

## 用法

```
/html-to-ppt /path/to/slides.html [output.pptx] [附加指令]
```

## 输入

$ARGUMENTS

## 先决条件检查

### 参数解析

若 $ARGUMENTS 首个词为文件路径（含 `/` 或以 `.html` 结尾）：
1.  提取 HTML 文件路径
2.  **容量预检**：用 `ls -l` 获取文件大小，估算 tokens = 字节数 / 3.5；计算当前已用量；若超限且模型不含 "1m" → 拒绝
3.  验证文件存在且为 `.html` 文件
4.  若第二个参数以 `.pptx` 结尾，作为输出路径；否则自动生成到 `../doc/` 目录，文件名格式：`{原文件名主体部分}_v{原文件版本标识}@{当前时间戳}.pptx`
5.  剩余内容视为附加指令

若无文件路径 → 报错中止。

### 依赖检查

```bash
/home/1ding/claude/.venv/bin/python3 -c "import pptx, bs4, lxml; print('OK')"
```

若失败 → 安装：`pip install python-pptx beautifulsoup4 lxml`

## 执行步骤

### 1. 扫描未知组件

运行基础脚本的扫描功能：

```bash
/home/1ding/claude/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.claude/tools')
from html_to_pptx import scan_unknown_components
all_cls, unknown = scan_unknown_components('{HTML路径}')
print(f'总 class 数: {len(all_cls)}')
print(f'未知 class: {unknown if unknown else \"无\"}')
"
```

### 2. 判断执行路径

-   **无未知组件** → 直接执行基础脚本（步骤 3A）
-   **有未知组件** → AI 读取 HTML 中该组件的 CSS 和使用方式，编写 renderer 函数，生成包装脚本（步骤 3B）

### 3A. 直接执行（无未知组件）

```bash
/home/1ding/claude/.venv/bin/python3 .claude/tools/html_to_pptx.py "{HTML路径}" "{PPTX路径}"
```

### 3B. 生成包装脚本（有未知组件）

AI 需要：
1.  读取 HTML 文件，找到未知 class 的 CSS 定义（在 `<style>` 中）和 HTML 使用位置
2.  分析组件的视觉结构（背景色、圆角、padding、字号、子元素结构）
3.  编写 renderer 函数，函数签名必须为 `def render_xxx(slide, el, bx=0, by=0):`
4.  生成包装脚本写入 `/tmp/html_to_pptx_ext.py`：

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '.claude/tools')
from html_to_pptx import *

# ── Custom renderers for unknown components ──

def render_my_widget(slide, el, bx=0, by=0):
    lx, ty, w, h = coords(el)
    ax, ay = bx+lx, by+ty
    # ... 使用基础脚本提供的工具函数：
    # add_rrect, add_rect, add_tb, add_run, render_rich, css_pt, etc.
    ...

register_renderer('my-widget', render_my_widget)

# ── Execute ──
if __name__ == '__main__':
    convert(sys.argv[1], sys.argv[2])
```

5.  执行包装脚本：

```bash
/home/1ding/claude/.venv/bin/python3 /tmp/html_to_pptx_ext.py "{HTML路径}" "{PPTX路径}"
```

### 4. 错误处理

若脚本报错 → 阅读错误信息，修复后重试（最多 3 次）。

### 5. 报告

```
---转换完成---
源文件：{HTML 文件名}
输出文件：{PPTX 文件路径}
总页数：{N}
文件大小：{N} KB
自定义组件：{列出 AI 额外编写的 renderer 名称，或"无"}
```

## 基础脚本可用工具函数

AI 编写自定义 renderer 时可直接使用以下函数（均已从基础脚本 export）：

| 函数 | 用途 |
|------|------|
| `px(val)` | HTML px → PPT Inches |
| `css_pt(css_px)` | CSS px → PPT Pt（×0.75） |
| `coords(el)` | 获取元素 (left, top, width, height) in px |
| `sty(el)` | 解析 inline style → dict |
| `hcls(el, cls)` | 检查元素是否有某 class |
| `txt(el)` | 获取元素文本（处理 HTML 实体） |
| `parse_c(style_val)` | 解析 CSS 颜色值 → RGBColor |
| `parse_fs(style_val)` | 解析 CSS font-size → Pt |
| `parse_lh(style_val)` | 解析 CSS line-height → float |
| `add_tb(slide, l, t, w, h)` | 添加文本框 |
| `add_rrect(slide, l, t, w, h, fill, border, bw, radius)` | 添加圆角矩形 |
| `add_rect(slide, l, t, w, h, fill)` | 添加矩形 |
| `add_run(para, text, font, size, color, bold)` | 添加文本 Run |
| `render_rich(para, el, color, size, font, bold_color)` | 渲染富文本（处理 strong/span） |
| `set_tf(tf)` | 设置 TextFrame 属性 |
| `set_para_spacing(p, line_height, space_before, space_after)` | 设置段落间距 |
| `set_bullet(p, char, color, size, indent_level)` | 设置 PPT 原生项目符号 |
| `COLORS` | 颜色常量字典 |
| `FONT_T` / `FONT_B` | 标题/正文字体名 |

## 精度保障原则

1.  **颜色零偏差**：使用 `COLORS` 字典中的精确 RGB 值
2.  **字号严格对应**：统一使用 `css_pt(css_px_value)` 换算
3.  **布局精确还原**：使用 `coords()` 读取 HTML 中的绝对定位坐标
4.  **行高同步**：使用 `set_para_spacing(line_height=...)` 还原 CSS line-height
5.  **文本完整性**：所有可见文本必须出现在 PPTX 中
