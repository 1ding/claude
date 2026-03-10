# HTML 幻灯片转 PPTX 文件

将 `ppt-slides-theme.html` 模板生成的 HTML 幻灯片转换为 .pptx 文件。

**架构（组件模板架构 v4）**：
-   转换工具：`.claude/tools/html-to-pptx/index.js`（Node.js + Puppeteer + pptxgenjs）
-   组件注册表：`.claude/tools/html-to-pptx/components/registry.json`
-   路由策略：`data-block` 属性 → CSS class → tag → `data-ppt` → 占位框（兜底）
-   浏览器负责：`getBoundingClientRect()` 精确位置 + 结构化内容提取
-   Node.js 负责：预定义模板 renderer → pptxgenjs 输出

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
2.  **容量预检**：用 `ls -l` 获取文件大小，估算 tokens = 字节数 / 3.5；计算当前已用量；若已用量 + 估算 > 950K → 拒绝
3.  验证文件存在且为 `.html` 文件
4.  若第二个参数以 `.pptx` 结尾，作为输出路径；否则自动生成到 `../doc/` 目录，文件名格式：`{原文件名主体部分}_v{原文件版本标识}@{当前时间戳}.pptx`
5.  剩余内容视为附加指令

若无文件路径 → 报错中止。

### 依赖检查

```bash
node --version 2>/dev/null && \
ls /home/1ding/claude/.claude/tools/html-to-pptx/node_modules/pptxgenjs 2>/dev/null && \
echo "OK" || echo "MISSING"
```

若缺失 → 在工具目录执行：
```bash
cd /home/1ding/claude/.claude/tools/html-to-pptx && npm install puppeteer-core pptxgenjs
```

## 执行步骤

### 1. 执行转换

```bash
TS=$(date +%Y%m%d%H%M)
node /home/1ding/claude/.claude/tools/html-to-pptx/index.js \
  "{HTML路径}" \
  "{输出目录}/{文件名主体}_v{版本}@${TS}.pptx"
```

转换器自动处理所有已知组件（见注册表），未识别组件生成占位框，不中断流程。

### 2. 处理未识别组件（可选）

若输出 PPTX 有灰色占位框（`⚠ component-name`），说明该 HTML 中有未注册组件：

**方案 A（推荐）**：在下次 /md-to-html 时将该内容改用注册表中已有组件表达

**方案 B**：向注册表添加新组件：
1.  在 `.claude/tools/html-to-pptx/components/registry.json` 添加组件定义
2.  在 `.claude/tools/html-to-pptx/index.js` 中添加对应 renderer 函数（参照现有函数写法）
3.  在 `extractEl()` 的 switch 中添加 case
4.  重新执行转换

### 3. 错误处理

若脚本报错 → 阅读错误信息，修复后重试（最多 3 次）。

### 4. 报告

```
---转换完成---
源文件：{HTML 文件名}
输出文件：{PPTX 文件路径}
总页数：{N}
文件大小：{N} KB
```

## 组件开发规范（添加新组件时）

新 renderer 须遵循以下模式：

```javascript
// 1. 在 registry.json 添加组件元数据
// 2. 在 index.js 添加提取逻辑（browser 侧 extractEl switch）
// 3. 添加渲染函数
function renderMyComponent(slide, c) {
  const { p } = c;                         // p = {x, y, w, h}（slide 绝对像素坐标）
  addRRect(slide, p.x, p.y, p.w, p.h, C.navyMid);  // 背景
  addTB(slide, p.x+20, p.y+10, p.w-40, 30, c.text, {  // 文字
    color: C.gold, fontSize: ptOf(14), bold: true, fontFace: F.serif });
}
// 4. 在 renderComponent switch 中添加 case
// 5. 在 md-to-html 组件选择表中添加说明
```

**设计约束**（与 HTML 保持一致）：
- 背景色：`C.navy` / `C.navyMid` / `C.navyLight`
- 强调色：`C.gold` / `C.goldL` / `C.red` / `C.blue` / `C.green` / `C.teal` / `C.orange`
- 字体：`F.serif`（标题）/ `F.sans`（正文）
- 位置：`inOf(px)` 转换，字号：`ptOf(px)` 转换
