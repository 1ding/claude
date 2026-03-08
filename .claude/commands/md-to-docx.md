# Markdown 转 DOCX 文档

将基于《排版格式规范》的 Markdown 文档转换为 Word (.docx) 文件。

## 用法

```
/md-to-docx /path/to/源文档.md [output.docx] [附加指令]
```

## 输入

$ARGUMENTS

## 先决条件检查

### 参数解析

若 $ARGUMENTS 首个词为文件路径（含 `/` 或以 `.md` 结尾）：
1.  提取 Markdown 文件路径
2.  **容量预检**：用 `ls -l` 获取文件大小，估算 tokens = 字节数 / 3.5；计算当前已用量；若超限且模型不含 "1m" → 拒绝
3.  验证文件存在且为 `.md` 文件
4.  若第二个参数以 `.docx` 结尾，作为输出路径；否则自动生成到 `../doc/` 目录，文件名格式：`{原文件名主体部分}_v{原文件版本标识}@{当前时间戳}.docx`
5.  剩余内容视为附加指令

若无文件路径 → 报错中止。

### 依赖检查

```bash
/usr/local/bin/node -e "require('.claude/tools/node_modules/docx'); console.log('OK')"
```

若失败 → 在 `.claude/tools/` 目录下执行 `/usr/local/bin/npm install docx puppeteer-core`

## 执行步骤

### 1. 执行转换脚本

```bash
cd /home/1ding/claude && /usr/local/bin/node .claude/tools/md2docx.js "{MD路径}" "{DOCX路径}"
```

### 2. 错误处理

若脚本报错 → 阅读错误信息，修复后重试（最多 3 次）。

### 3. 报告

```
---转换完成---
源文件：{文件名}
输出文件：{DOCX 文件路径}
文件大小：{N} KB
```

## 格式规范

转换遵循以下排版规范（与 md2docx.js 一致）：

| 元素 | 格式 |
|------|------|
| 字体 | 仿宋 (FangSong) |
| 字号 | 小三号 (15pt) |
| 行间距 | 最小 30pt |
| 段前/段后 | 3pt / 6pt（第一级段前 18pt） |
| `+` 段落 | 第1层首行缩进1cm，第n层左缩进 n×1cm |
| `-` 列表项 | 悬挂缩进1cm，第n层左缩进 (n+1)×1cm |
| `#` 标题 | 一级居中无编号，二级起自动编号（1、1.1、1.1.1...） |
| 表格 | 表头灰底加粗，黑色边框，按层级缩进 |
| 代码块 | 灰底等宽字体 |
| `graph` 图块 | Puppeteer 截图转 PNG 嵌入（需 Chrome/Edge） |
