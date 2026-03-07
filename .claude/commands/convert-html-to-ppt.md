# HTML 幻灯片转 PPTX 文件

将 `/convert-to-ppt-style-html` 生成的 HTML 幻灯片文件转换为正式 .pptx 文件。

## 用法

```
/convert-html-to-ppt /path/to/slides.html [output.pptx] [附加指令]
```

## 输入

$ARGUMENTS

## 先决条件检查

### 参数解析

若 $ARGUMENTS 首个词为文件路径（含 `/` 或以 `.html` 结尾）：
1.  提取 HTML 文件路径
2.  验证文件存在且为 `.html` 文件
3.  若第二个参数以 `.pptx` 结尾，作为输出路径；否则自动生成
4.  剩余内容视为附加指令

若无文件路径 → 报错中止：

> ⚠️ 请提供 HTML 幻灯片路径：
> ```
> /convert-html-to-ppt /path/to/slides.html
> ```

### 依赖检查

验证 Python 依赖可用：

```bash
/home/1ding/claude/.venv/bin/python3 -c "import pptx, bs4, lxml; print('OK')"
```

若失败 → 安装依赖：

```bash
/home/1ding/claude/.venv/bin/pip install python-pptx beautifulsoup4 lxml
```

## 执行步骤

### 1. 运行转换脚本

```bash
/home/1ding/claude/.venv/bin/python3 /home/1ding/claude/.claude/scripts/html_to_pptx.py "{HTML文件路径}" ["{输出路径}"]
```

### 2. 验证输出

确认 .pptx 文件已生成，报告文件大小。

### 3. 报告

```
---转换完成---
源文件：{HTML 文件名}
输出文件：{PPTX 文件路径}
总页数：{N}（标题页 {N} + 章节页 {N} + 内容页 {N} + 两栏页 {N}）
文件大小：{N} KB
```

## 注意事项

-   输入必须是 `/convert-to-ppt-style-html` 生成的 HTML 文件（含 `.ppt-container` 结构）
-   PPTX 保留内容结构和配色方案，但不会像素级还原 HTML 的绝对定位布局
-   默认输出到 HTML 同目录，文件名去掉 `-slides` 后缀并改为 `.pptx` 扩展名
