# Markdown 转 HTML 幻灯片

将 Markdown 文档转换为 1280x720 静态 HTML 演示幻灯片。输出为纯静态渲染（无动画/无交互），可直接转换为 PPT 或导出 PDF。

## 用法

```
/md-to-html /path/to/源文档.md [附加指令]
```

## 输入

$ARGUMENTS

## 先决条件检查

### 参数解析

若 $ARGUMENTS 首个词为文件路径（含 `/` 或以 `.md` 结尾）：
1.  提取文件路径
2.  **容量预检**：用 `ls -l` 获取文件大小，估算 tokens = 字节数 / 3.5；计算当前已用量（[LOADED *] 记录 + [CAP DELTA] chars / 3.5 + 50K）；若 已用量 + 估算 > 950K → 拒绝执行并告知用户
3.  读取源文档
4.  输出 `[LOADED target] {文件路径} | ~{tokens} tokens`
5.  路径之后的剩余内容视为附加指令

若无文件路径 → 检查会话中是否有 `[LOADED target]` 记录。均无则报错中止。

### 加载设计系统模板

```bash
cat .claude/specs/convert/ppt-slides-theme.html
```

读取模板文件并输出 `[LOADED spec] ppt-slides-theme.html | ~{tokens} tokens`。若不存在 → 报错中止。

## 静态输出约束（核心规则）

**目标：生成的 HTML 必须是"可截图即所见"的纯静态页面。**

### 全面禁止

-   CSS 动画：`@keyframes`、`animation`、`transition` 属性
-   交互效果：`:hover`、`:focus`、`:active` 伪类样式
-   JS 效果：除翻页导航外的所有 JavaScript
-   不可静态化的 CSS：`backdrop-filter`、`filter`（模糊等）
-   任何需要用户交互才能看到的视觉效果
-   **`linear-gradient`**：PPT 无法精确还原渐变，全部改用纯色
-   **`box-shadow`**（组件内）、**`text-shadow`**
-   任何 HTML 可实现但 PPT 无法还原的视觉效果

### 允许保留

-   翻页导航 JS（键盘/触摸/滚轮翻页）
-   纯色背景（`background:var(--navy-mid)` 等）
-   `border-radius`（圆角）
-   `box-shadow`（仅 slide-container 外框，组件内禁用）
-   `opacity`（静态透明度，非动态变化）
-   `border`（纯色实线）

## 布局规则

### 绝对定位优先

每个 slide 内的元素**尽可能使用绝对定位**（`position:absolute`），AI 计算像素坐标。

**slide 坐标系**（1280×720px）：

```
┌─ slide (position:relative; width:1280px; height:720px) ─────────┐
│                                                                   │
│  header: left:56px; top:32px; width:1168px; height:60px           │
│  ~~~~~~~~~~~~~~~~~~~~~~~~ 32px 间距 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~  │
│  body:   left:56px; top:124px; width:1168px; height:552px         │
│  ~~~~~~~~~~~~~~~~~~~~~~~~ 12px 间距 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~  │
│  footer: left:56px; top:688px; width:1168px; height:24px          │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

-   header 区：y=32px，高 60px（底边 y=92px）
-   间距：32px
-   body 区：y=124px，高 552px（底边 y=676px）—— **核心内容区，必须填满**
-   间距：12px
-   footer 区：y=688px，高 24px
-   左右边距：56px

### body 区内部布局

AI 须为 body 区内每个组件计算绝对坐标（px），填入 `style="position:absolute; left:Xpx; top:Ypx; width:Wpx; height:Hpx;"`。

**两栏布局参考坐标**：
-   左栏：left=0, width=560px
-   右栏：left=592px, width=576px
-   （body 区内相对坐标，gap=32px）

**三栏布局参考坐标**：
-   栏1：left=0, width=376px
-   栏2：left=396px, width=376px
-   栏3：left=792px, width=376px
-   （gap=20px）

### 防重叠：内容高度估算规则

卡片（col-card）、强调框（emphasis-box）等容器内部使用流式布局，文本换行由浏览器决定。AI 设置容器 `height` 前，**必须先估算内容实际高度**，确保容器能容纳内容且相邻元素不重叠。

**高度估算公式**：

```
容器所需高度 = 上下padding + Σ(每个子元素高度)

子元素高度估算：
  - <h3>：font-size × 1.4 + margin-bottom（通常 ≈ 29px）
  - <p> 单行：font-size × line-height + margin-bottom
  - <p> 多行：ceil(文本显示宽度 ÷ 容器内宽) × font-size × line-height + margin-bottom
  - <ul> bullet-list：Σ(每个 <li> 的行数 × 23px) + 各项 margin-bottom

文本显示宽度估算：
  - 中文字符：每字 ≈ font-size 宽
  - 英文/数字/符号：每字符 ≈ font-size × 0.6 宽
  - 容器内宽 = width - 左右padding（col-card 内宽 = width - 44px）
```

**关键规则**：

-   同一行的多个卡片（如三栏布局），height 取该行所有卡片中**最大估算高度**，确保齐平
-   垂直相邻的绝对定位元素，间距 ≥ **16px**（即下一个元素的 top ≥ 上一个元素的 top + height + 16）
-   容器 height 在估算值基础上 **+10% 安全余量**（向上取整到偶数）
-   最后一个元素的 top + height 不得超过 body 高度（552px）

**自检**：每个 slide 完成布局后，逐一检查所有绝对定位元素对（同层级）：若两个元素在水平方向有重叠（X 轴投影有交集），则它们在垂直方向的间距必须 ≥ 16px；反之亦然。

### 允许使用非绝对定位的场景

以下场景可使用 `display:block`（默认流式布局），因为文本换行由浏览器决定：
-   `<table>` 内部（表格单元格）
-   `<ul>` / `<li>` 内部（列表项文本）
-   卡片内的 `<p>` 段落（段落文本换行）

**flex 使用限制**：
-   布局层（slide-body 内元素的定位）：禁止 flex/grid，必须用绝对定位
-   叶子组件内（flow-box、metric-card、battle-card 等固定尺寸组件）：允许 `display:flex;align-items:center;justify-content:center;` 实现文字垂直水平居中

### data-block 属性（组件路由键，必须添加）

**每个标准组件必须加 `data-block` 属性**，html-to-pptx 转换器以此为首要路由键。

```
data-block="[组件 id]"
```

完整组件注册表见：`.claude/tools/html-to-pptx/components/registry.json`

| data-block 值 | 组件类型 | PPT 渲染器 |
|---------------|---------|-----------|
| `col-card` | 卡片（带金色顶条） | renderColCard |
| `table` | 数据表格（有/无 thead） | renderTable |
| `bullet-list` | 项目符号列表 | renderBulletList |
| `emphasis-box` | 强调框（金色左边框） | renderEmphasisBox |
| `metric-card` | 指标卡（大数字 + 标签） | renderMetricCard |
| `phase-block` | 阶段块（时间轴用） | renderPhaseBlock |
| `arrow-right` | 右箭头（阶段间连接） | renderArrowRight |
| `section-header` | 节标题（金色 + 下划线） | renderSectionHeader |
| `panel` | 通用面板容器 | renderPanel |
| `text` | 独立文本框 | renderText |
| `custom:描述` | 临时自定义组件 | 转换器自动尝试，或留占位框 |

**临时/非标准组件**：若内容需要但注册表中无合适组件，使用 `data-block="custom:brief-desc"`。转换器会尝试用 getComputedStyle 渲染，失败则生成灰色占位框（`⚠ brief-desc`），不影响其他页面。

### data-ppt 属性标记（保留，辅助标记）

| data-ppt 值 | 含义 |
|-------------|------|
| `text` | 文本框 |
| `shape` | 形状（卡片、强调框） |
| `table` | 表格 |
| `line` | 装饰线 |
| `group` | 容器（子元素独立转换） |
| `skip` | 跳过不转换（导航栏等） |

**示例（同时带 data-block 和 data-ppt）**：
```html
<div class="col-card" data-block="col-card" data-ppt="shape"
     style="position:absolute; left:0; top:0; width:560px; height:270px;">
    <div class="card-bar" data-ppt="line"></div>
    <h3 data-ppt="text">标题</h3>
    <p data-ppt="text">内容</p>
</div>

<!-- panel 内子组件用流式布局（无 position:absolute），转换器用 getBoundingClientRect 算实际位置 -->
<div data-block="panel"
     style="position:absolute; left:0; top:0; width:564px; height:300px;
            background:var(--navy-mid); border-radius:10px; padding:20px;">
    <div class="section-header" data-block="section-header">节标题</div>
    <ul class="bullet-list" data-block="bullet-list">
        <li><strong>要点：</strong>说明</li>
    </ul>
</div>
```

## 内容编排原则

**页面规划**：
-   源文档 `#` 一级标题 → 封面页
-   章节结构 → 目录页
-   源文档 `##` 二级标题 → 对应一个或多个内容页
-   同一 `##` 下内容过多时拆分为多页
-   结尾 → 结语页

**内容密度**：
-   每页 300-500 字有效内容
-   避免大段纯文字，优先转化为结构化组件
-   连续纯列表不超过 2 页

**编号引用必须带压缩标题**：
-   首次出现用完整名称，后续附带 4-8 字压缩标题（如"战役三·信息安全"）
-   不允许出现光秃秃的编号
-   全文同一编号的压缩标题必须一致

**页面填充策略（硬性要求）**：
-   body 区（552px 高）**必须填满**，所有组件的坐标+尺寸之和须覆盖 body 区域的 >=85%
-   AI 在计算每个组件的 top 和 height 时，必须确保最后一个组件的底边接近 body 底边（y=552px 相对于 body）
-   内容不足时：① 增大组件高度（卡片、列表、强调框）② 扩充内容文字 ③ 添加辅助组件 ④ 增加组件间距（最后手段）
-   内容过多时：拆分为多页，不缩小字号

**组件选择策略**（优先从注册表标准组件选取）：

| 内容特征 | 推荐组件（data-block） | 布局 |
|---------|----------------------|------|
| 2-3 个并列概念 | `col-card` | 两栏 / 三栏 |
| 4+ 个并列概念 | `col-card`（网格排列） | 网格 |
| 有明确要点的说明 | `bullet-list` + `emphasis-box` | 单栏 / 两栏一侧 |
| 结构化数据（有表头） | `table`（带 `<thead>`） | 单栏 |
| 对比/矩阵数据（热力图） | `table`（加 `heat-table` class + `h-*` cell class） | 单栏 |
| 独立背景容器（含多子组件） | `panel`（子组件流式布局） | 两栏 / 单栏 |
| 时间轴 / 五阶段演进 | `phase-block` × N + `arrow-right` × (N-1) | 横排 |
| 关键数字指标 | `metric-card` | 横排 2-4 个 |
| 节内分组标题 | `section-header`（panel 内） | 流式 |
| 关键结论 / 注意事项 | `emphasis-box` | 单栏 |
| 独立说明文字 | `text`（`<p data-block="text">`） | 单栏 |
| 无合适组件的自定义内容 | `custom:描述`（临时，下次补充到注册表） | 视情况 |

## 组件使用规则（方案 C：锁定层 + 开放层）

**锁定层**：
-   页面框架、导航 JS、基础排版、CSS 变量（原样复制）
-   模板中的 CSS 动画/hover 效果已移除，无需手动删除

**开放层**（AI 可自行创建新组件）：
-   自定义 CSS 写在 `/* === CUSTOM === */` 后
-   设计约束：背景只用 `--navy-mid`/`--navy-light`，强调只用 `--gold`/`--accent-*`，圆角 8-10px，字号 10-22px，边框 1px solid rgba(201,168,76,0.1~0.3)
-   **禁止**：`linear-gradient`、`radial-gradient`、`box-shadow`、`text-shadow`、`animation`、`transition`、`:hover`、以及任何 PPT 无法精确还原的 CSS 特性

## 生成 HTML

**结构要求**：
-   CSS 和 JS 从模板原样复制
-   `<title>` 替换为文档标题
-   封面页 `data-slide="0"` 且带 `active` class
-   每个 slide 有 `data-slide="N"` 和 `data-type="cover|toc|content"`
-   导航栏加 `data-ppt="skip"`
-   每个 slide 内部使用 `position:relative`，子元素用 `position:absolute` + 精确 px 坐标
-   **每个标准组件必须同时带 `data-block="[id]"` 和 `data-ppt="[type]"` 两个属性**

**样式规则**：
-   优先用模板预定义 class + inline style 定位
-   颜色用 CSS 变量（如 `var(--accent-red)`），不硬编码色值
-   所有颜色、背景必须为**纯色**（禁止 `linear-gradient`、`radial-gradient`）
-   **HTML-PPT 一致性原则**：只使用 PPT 能精确还原的 CSS 特性

**data-block 使用规则**：
-   从注册表（`.claude/tools/html-to-pptx/components/registry.json`）选取 `id`，写入 `data-block`
-   `panel` 组件内的子组件用**流式布局**（无 `position:absolute`）；转换器用 `getBoundingClientRect` 获取实际位置
-   找不到合适组件时：`data-block="custom:简短描述"`，转换器自动处理或生成占位框

## 输出

将 HTML 文件写入源文档所在目录的 `../doc/` 目录（不存在则创建）：

-   文件名：`{原文件名主体部分}_v{原文件版本标识}@{当前时间戳}.html`
    -   示例：源文件 `银行科技风险_v0.04@202603070717.md` → 输出 `银行科技风险_v0.04@202603081200.html`
-   输出 `[CAP DELTA]` 标记

## 报告

```
---生成完成---
源文档：{源文件名}
输出文件：{HTML 文件路径}
总页数：{N}（封面 1 + 目录 1 + 内容 {N} + 结语 1）
文件大小：{N} KB
```
