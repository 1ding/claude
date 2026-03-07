# 1 总则

+   **文档编号**：TW-FMT-PPT-02
+   **文档名称**：PPT 风格 HTML 页面生成规范
+   **文档密级**：【内部资料】 -- 不主动对外公开。
+   **适用对象**：AI 文档转换助手
+   **管理要点**：本规范定义将 PPT 内容稿（由 TW-FMT-PPT-01 规范生成的 Markdown 文件）转换为 800×450 尺寸、扁平化设计风格 HTML 演示页面的完整规则，包括 Markdown 解析映射、页面尺寸、设计系统、布局计算、CSS 样式、HTML 模板及质量检查规则。

# 2 Markdown 输入解析规则

## 2.1 标题层级映射

+   Markdown 标题层级与 HTML 页面类型的对应关系如下表所示。

    | Markdown 标记 | 含义       | HTML 页面类型             | CSS 类           |
    | ------------- | ---------- | ------------------------- | ---------------- |
    | `#`           | 文档标题页 | 标题页（Title Slide）     | `layout-title`   |
    | `##`          | 章节分隔页 | 章节页（Section Divider） | `layout-section` |
    | `###`         | 单页 PPT   | 标题+内容页               | `layout-content` |
    | `####`        | 子主题     | 标题+内容页（面包屑三级） | `layout-content` |

## 2.2 内容标注识别与处理

+   Markdown 标注与 HTML 处理方式的映射关系如下表所示。

    | Markdown 标注     | 含义         | HTML 处理方式                           |
    | ----------------- | ------------ | --------------------------------------- |
    | `[KEY]`           | 核心信息强调 | `.highlight` 类包裹文字，或左侧加粗色条 |
    | `[DATA]`          | 数据或数字   | `.data-card` 组件，大号数字+小标签      |
    | `[CHART:bar]`     | 柱状图建议   | CSS Grid 创建简化柱状图视觉             |
    | `[CHART:line]`    | 折线图建议   | 箭头符号或简化趋势展示                  |
    | `[CHART:pie]`     | 饼图建议     | 百分比卡片网格展示                      |
    | `[CHART:flow]`    | 流程图建议   | 带箭头的横向或纵向卡片链                |
    | `[CHART:compare]` | 对比图建议   | 两栏布局或对比卡片                      |
    | `[CHART:table]`   | 表格建议     | 网格布局或列表结构                      |
    | `[CODE:single]`   | 单栏代码     | `<pre><code>`，width: 740px             |
    | `[CODE:double]`   | 双栏代码     | 两栏布局，每栏 width: 355px             |

## 2.3 布局选择策略

+   根据页面内容特征，按以下优先级选择布局：

-   有 `[CODE:double]` → 两栏布局（`layout-two-columns`）
-   有 `[CHART:compare]` 或成对 `[DATA]` → 两栏布局
-   有 4-6 个 `[DATA]` → 2×2 或 3×2 网格布局
-   要点数 ≥6 且字数少 → 3 列网格布局
-   其他情况 → 标题+内容页（`layout-content`）

# 3 尺寸与区域规范

## 3.1 页面尺寸

-   容器尺寸：800px × 450px（16:9 比例）
-   页面间距：20px
-   左右边距：30px

## 3.2 区域划分

+   页面内部分为三个区域，定位和尺寸如下表所示。

    | 区域   | 定位        | 尺寸                | 说明                |
    | ------ | ----------- | ------------------- | ------------------- |
    | 标题栏 | top: 30px   | 宽 740px × 高 25px  | 底部 1px 浅灰分隔线 |
    | 内容区 | top: 66px   | 宽 740px × 高 349px | 不可超出            |
    | 页脚   | bottom: 5px | 高 20px             | 无背景，纯文字      |

+   标题栏底部计算：30px(top) + 25px(height) + 1px(border) = 56px，内容区从 66px 开始，间距 10px。

## 3.3 区域示意图

    ```graph
    ┌────────────────────────────────────────┐ 0px
    │  ┌─ 标题栏 ─────────────────────────┐  │ 30px
    │  │  面包屑 + LOGO      (高度25px)   │  │
    │  └──────────────────── 1px灰线 ─────┘  │ 56px
    │  ┌─ 内容区 ─────────────────────────┐  │ 66px
    │  │     (宽度740px × 高度349px)      │  │
    │  └──────────────────────────────────┘  │ 415px
    │  公司信息 / www.tenward.com    第X页   │ 425px
    └────────────────────────────────────────┘ 450px
    ```

# 4 设计系统规范

## 4.1 配色方案

-   **主色调**：`#6366f1`（主题蓝紫，面包屑/进度条/图标）、`#8b5cf6`（紫色，面包屑三级）
-   **辅助色**：`#10b981`（翠绿，成功）、`#f59e0b`（琥珀，警告）、`#3b82f6`（天蓝，信息）
-   **中性色**：`#1e293b`（深蓝灰，标题）、`#334155`（主文本）、`#64748b`（次要文本）、`#94a3b8`（浅文本/页脚）、`#e2e8f0`（边框/分隔线）、`#f8fafc`（浅背景）、`#ffffff`（卡片背景）

## 4.2 字号体系

+   各用途的字号和字重如下表所示。

    | 用途         | 字号    | 字重 | 说明      |
    | ------------ | ------- | ---- | --------- |
    | 正文内容     | 13px    | 400  | 核心字号  |
    | 面包屑标题   | 14px    | 600  | 粗体      |
    | 卡片标题     | 14px    | 600  | 粗体      |
    | 页脚         | 10px    | 100  | 细体      |
    | 标题页主标题 | 26px    | 700  | 加粗      |
    | 标题页副标题 | 12px    | 400  | 常规      |
    | 紧凑场景     | 11-12px | 400  | 最小 11px |

## 4.3 扁平化设计原则

-   **无阴影**：所有元素使用 1px 边框，不应使用 box-shadow。
-   **无渐变图标**：图标使用纯色方块（28px）+ 字符。
-   **简洁列表**：6px 纯色圆点，与文字对齐。
-   **统一边距**：保持上下左右边距一致。
-   **柔和分隔**：使用 1px 浅灰色分隔线（`#e2e8f0`）。

## 4.4 字体渲染

+   所有页面应在 body 元素添加以下属性：

    ```css
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
    ```

# 5 布局框架规范

## 5.1 标题页

+   对应 Markdown `#` 标题。无标题栏、无页脚、全屏渐变背景。

-   主标题：top 165px，字号 26px，水平居中
-   副标题：top 215px，字号 12px，水平居中
-   作者信息：bottom 50px，字号 8px，水平居中

## 5.2 章节分隔页

+   对应 Markdown `##` 标题。简化标题页样式，无页脚。

-   章节标题：top 180px，字号 22px，水平居中
-   渐变背景：使用较浅的渐变色

## 5.3 标题+内容页

+   对应 Markdown `###` 或 `####` 标题。

-   标题栏：top 30px，高 25px，底部 1px 分隔线
-   内容区：top 66px，宽 740px × 高 349px

## 5.4 两栏布局

+   触发条件：`[CODE:double]`、`[CHART:compare]`、成对 `[DATA]`。

-   左栏：left 30px，width 355px，height 349px
-   右栏：left 415px，width 355px，height 349px
-   栏间距：30px
-   内边距：18px（可调整为 14-16px）
-   两栏直接放在 ppt-content 下，不应用 content-box 包裹。

## 5.5 网格布局

+   触发条件：4-6 个 `[DATA]`（2×2 或 3×2 网格）、6-9 个简短要点（3×3 网格）、3 个主要模块（3 列布局）。

-   标准间距：14px
-   紧凑间距：10-12px
-   尺寸计算见第 6 章。

# 6 精确计算方法

## 6.1 基础计算公式

+   多列布局（宽度）：

    ```text
    每列宽度 = (740 - gap × (列数-1)) / 列数
    ```

+   多行布局（高度）：

    ```text
    每行高度 = (349 - gap × (行数-1)) / 行数
    ```

+   元素坐标：

    ```text
    left = 30 + i × (列宽 + gap)    // i 从 0 开始
    top = 66 + j × (行高 + gap)     // j 从 0 开始
    ```

## 6.2 常用布局精确尺寸

+   **2 列布局**（gap=30px）：列宽 355px。左列 left 30px，右列 left 415px。验证：30 + 355 + 30 + 355 = 770。

+   **3 列布局**（gap=14px）：可用宽度 740 - 28 = 712px，分配 237px + 237px + 238px。位置：列 1 left 30px，列 2 left 281px，列 3 left 532px。

+   **2×2 网格**（gap=14px）：列宽 (740-14)/2 = 363px，行高 (349-14)/2 ≈ 167px + 168px。验证：宽 363 + 14 + 363 = 740，高 167 + 14 + 168 = 349。

+   **3 行垂直**（gap=14px）：每行高度 (349-28)/3 = 107px。位置：行 1 top 66px，行 2 top 187px，行 3 top 308px。

## 6.3 生成前计算流程

+   按以下 7 步执行：

-   **步骤 1**：解析 Markdown 内容（标题层级、标注类型和数量、要点和文字、代码块）。
-   **步骤 2**：选择页面布局（页面类型、布局方式、是否网格或两栏）。
-   **步骤 3**：列出元素清单（标题区、数据卡片、列表、代码块等，每个元素注明预估高度）。
-   **步骤 4**：精确计算高度（列出每个元素高度 + 间距，求和，验证 ≤349px）。
-   **步骤 5**：如超出则调整（优先级：减少分行 → 减小间距 → 减小 padding → 减小字号 → 精简文字 → 调整布局）。
-   **步骤 6**：重新计算直到满足。
-   **步骤 7**：验证边界（top: 66px，bottom ≤ 415px）。

## 6.4 内容紧凑化规则

-   横排优先于竖排：多个短数据项用 `·` 连接为一行。
-   去除冗余词汇：删除可从上下文推断的修饰语。
-   合并同类信息：同一条目的多个属性合并为一行（用 `|` 分隔）。
-   使用符号代替文字：`·`（顿号）、`→`（变为）、`-`（减少）、`+`（增加）。

# 7 生成规则

## 7.1 文件格式

-   单文件 HTML 格式。
-   CSS 内联在 `<style>` 标签中。
-   JavaScript 内联在 `<script>` 标签中。
-   不依赖外部资源。

## 7.2 页面结构

-   `#` 标题应使用 `layout-title` 类。
-   `##` 标题应使用 `layout-section` 类。
-   `###` 和 `####` 应有标题栏和页脚。
-   面包屑标题：`###` 显示为"父章节 › 页面标题"，`####` 显示为"父标题 › 子标题"。
-   面包屑最多 3 级，使用 `›` 分隔符。
-   页脚左侧：`上海天帷智慧数字技术有限公司 / www.tenward.com`。
-   页脚右侧：`第 X 页`。

## 7.3 内容规范

-   正文字号：13px（标准）、12px（紧凑）、11px（最小）。
-   行高：1.4-1.6。
-   元素间距：≥10px。
-   卡片 padding：12-18px（根据空间调整）。

## 7.4 标注处理

-   `[KEY]`：使用 `.highlight` 类或左侧彩色条强调。
-   `[DATA]`：使用 `.data-card` 组件，大号数字+小标签。
-   `[CHART:*]`：根据类型创建简化视觉图形。
-   `[CODE:single]`：单栏代码块，width: 740px。
-   `[CODE:double]`：两栏布局，每栏 width: 355px。

## 7.5 禁止项

-   不应使用 `overflow: hidden`、`overflow: auto`、`overflow-y: auto`、`overflow-x: auto`。
-   不应使用任何形式的滚动条。
-   内容不应超出 349px 边界。
-   不应省略计算步骤直接生成代码。
-   不应忽略 Markdown 中的标注信息。

## 7.6 代码注释规范

+   每个 content-box 应添加计算注释，格式如下：

    ```html
    <div class="content-box">
      <!--
        Markdown解析：
        - 标题层级: ### (内容页)
        - 标注识别: 2个[DATA], 1个[CHART:compare], 1个[KEY]
        - 布局选择: 两栏对比布局

        精确计算：总高349px
        分配：数据卡80px + gap12px + 对比区120px + gap12px + 要点列表110px = 334px
        验证：80+12+120+12+110 = 334 < 349
        剩余：15px
      -->
    </div>
    ```

# 8 CSS 样式模板

## 8.1 基础样式

    ```css
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                   "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue",
                   Arial, sans-serif;
      background: #e5e7eb;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeLegibility;
    }

    .ppt-container {
      width: 800px;
      height: 450px;
      margin: 20px auto;
      position: relative;
      background: #ffffff;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    .ppt-content {
      width: 100%;
      height: 100%;
      position: relative;
      background: #ffffff;
    }
    ```

## 8.2 标题栏样式

    ```css
    .title-bar {
      position: absolute;
      top: 30px;
      left: 30px;
      width: 740px;
      height: 25px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #e2e8f0;
    }

    .breadcrumb-title {
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .breadcrumb-title .level-1 { color: #6366f1; }
    .breadcrumb-title .level-2 { color: #334155; }
    .breadcrumb-title .level-3 { color: #8b5cf6; }
    .breadcrumb-title .separator { color: #94a3b8; font-weight: 400; }

    .company-logo {
      font-size: 12px;
      font-weight: 600;
      color: #6366f1;
      letter-spacing: 1px;
    }
    ```

## 8.3 页脚样式

    ```css
    .ppt-footer {
      position: absolute;
      bottom: 5px;
      left: 30px;
      right: 30px;
      height: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 10px;
      font-weight: 100;
      color: #94a3b8;
    }
    ```

## 8.4 内容区域样式

    ```css
    .content-box {
      position: absolute;
      top: 66px;
      left: 30px;
      width: 740px;
      max-height: 349px;
    }

    .left-column {
      position: absolute;
      top: 66px;
      left: 30px;
      width: 355px;
      height: 349px;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 18px;
    }

    .right-column {
      position: absolute;
      top: 66px;
      left: 415px;
      width: 355px;
      height: 349px;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 18px;
    }

    .column-title {
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #e2e8f0;
    }

    .column-content {
      font-size: 13px;
      color: #334155;
      line-height: 1.6;
    }
    ```

## 8.5 列表样式

    ```css
    .list-items {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .list-items li {
      display: flex;
      align-items: flex-start;
      margin-bottom: 10px;
      font-size: 13px;
      color: #334155;
      line-height: 1.6;
    }

    .list-items li:last-child { margin-bottom: 0; }

    .list-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #6366f1;
      margin-right: 10px;
      margin-top: 7px;
      flex-shrink: 0;
    }
    ```

## 8.6 卡片样式

    ```css
    .card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 14px;
    }

    .card-title {
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
      margin-bottom: 8px;
    }

    .card-content {
      font-size: 13px;
      color: #334155;
      line-height: 1.5;
    }

    .card-key {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-left: 3px solid #6366f1;
      border-radius: 6px;
      padding: 14px;
    }

    .card-key .card-title { color: #6366f1; }

    .data-card {
      background: #ffffff;
      border-radius: 6px;
      padding: 18px;
      border: 1px solid #e2e8f0;
      border-left: 3px solid #6366f1;
      text-align: center;
    }

    .data-value {
      font-size: 24px;
      font-weight: 700;
      color: #6366f1;
      margin-bottom: 6px;
    }

    .data-label {
      font-size: 11px;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 500;
    }
    ```

## 8.7 辅助样式

    ```css
    .highlight {
      background: #eff6ff;
      padding: 2px 6px;
      border-radius: 3px;
      font-weight: 500;
      color: #6366f1;
    }

    .flow-box {
      background: #ffffff;
      border: 1px solid #6366f1;
      border-radius: 6px;
      padding: 10px 16px;
      font-size: 13px;
      color: #334155;
      text-align: center;
      min-width: 80px;
    }

    .compare-container {
      display: flex;
      gap: 14px;
      align-items: stretch;
    }

    .compare-item {
      flex: 1;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 16px;
    }

    .compare-item.highlight-left { border-left: 3px solid #10b981; }
    .compare-item.highlight-right { border-left: 3px solid #f59e0b; }

    pre {
      background: #1e293b;
      color: #e2e8f0;
      padding: 14px;
      border-radius: 6px;
      font-size: 12px;
      line-height: 1.6;
      overflow-x: auto;
      margin: 0;
    }

    code {
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
    }

    .divider {
      width: 100%;
      height: 1px;
      background: #e2e8f0;
      margin: 16px 0;
    }

    .icon-text {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 6px;
      background: #6366f1;
      color: #ffffff;
      font-size: 14px;
      font-weight: 600;
      margin-right: 8px;
    }

    .icon-text.green { background: #10b981; }
    .icon-text.blue { background: #3b82f6; }
    .icon-text.orange { background: #f59e0b; }
    ```

## 8.8 标题页样式

    ```css
    .layout-title .ppt-content {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .layout-title .ppt-content::before {
      content: '';
      position: absolute;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
      border-radius: 50%;
      top: -100px;
      right: -100px;
    }

    .layout-title .ppt-content::after {
      content: '';
      position: absolute;
      width: 300px;
      height: 300px;
      background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
      border-radius: 50%;
      bottom: -80px;
      left: -80px;
    }

    .title-main {
      position: absolute;
      top: 165px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 26px;
      font-weight: 700;
      color: #ffffff;
      text-align: center;
      text-shadow: 0 2px 8px rgba(0,0,0,0.2);
      letter-spacing: 0.5px;
      z-index: 1;
      width: 700px;
    }

    .title-subtitle {
      position: absolute;
      top: 215px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 12px;
      font-weight: 400;
      color: rgba(255,255,255,0.9);
      text-align: center;
      z-index: 1;
    }

    .title-author {
      position: absolute;
      bottom: 50px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 8px;
      color: rgba(255,255,255,0.7);
      text-align: center;
      z-index: 1;
    }
    ```

## 8.9 章节页样式

    ```css
    .layout-section .ppt-content {
      background: linear-gradient(135deg, #818cf8 0%, #a78bfa 100%);
    }

    .section-title {
      position: absolute;
      top: 180px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 22px;
      font-weight: 700;
      color: #ffffff;
      text-align: center;
      text-shadow: 0 2px 6px rgba(0,0,0,0.15);
      letter-spacing: 0.5px;
      z-index: 1;
      width: 700px;
    }
    ```

# 9 HTML 结构模板

## 9.1 标题页模板

+   对应 Markdown `#` 标题。

    ```html
    <div class="ppt-container layout-title">
      <div class="ppt-content">
        <div class="title-main">主标题文字</div>
        <div class="title-subtitle">副标题文字</div>
        <div class="title-author">作者信息 · 日期</div>
      </div>
    </div>
    ```

## 9.2 章节页模板

+   对应 Markdown `##` 标题。

    ```html
    <div class="ppt-container layout-section">
      <div class="ppt-content">
        <div class="section-title">章节标题</div>
      </div>
    </div>
    ```

## 9.3 标题+内容页模板

+   对应 Markdown `###` 标题。

    ```html
    <div class="ppt-container layout-content">
      <div class="ppt-content">
        <div class="title-bar">
          <div class="breadcrumb-title">
            <span class="level-1">一级标题（章节名）</span>
            <span class="separator">›</span>
            <span class="level-2">二级标题（页面标题）</span>
          </div>
          <div class="company-logo">LOGO</div>
        </div>
        <div class="content-box">
          <!-- 内容区域：必须精确计算高度 -->
        </div>
      </div>
      <div class="ppt-footer">
        <span>上海天帷智慧数字技术有限公司 / www.tenward.com</span>
        <span>第 X 页</span>
      </div>
    </div>
    ```

## 9.4 两栏布局模板

+   对应 `[CODE:double]` 或 `[CHART:compare]` 标注。

    ```html
    <div class="ppt-container layout-two-columns">
      <div class="ppt-content">
        <div class="title-bar">
          <div class="breadcrumb-title">
            <span class="level-1">一级标题</span>
            <span class="separator">›</span>
            <span class="level-2">二级标题</span>
          </div>
          <div class="company-logo">LOGO</div>
        </div>
        <!-- 两栏直接放在 ppt-content 下 -->
        <div class="left-column">
          <h3 class="column-title">左栏标题</h3>
          <div class="column-content">左栏内容</div>
        </div>
        <div class="right-column">
          <h3 class="column-title">右栏标题</h3>
          <div class="column-content">右栏内容</div>
        </div>
      </div>
      <div class="ppt-footer">
        <span>上海天帷智慧数字技术有限公司 / www.tenward.com</span>
        <span>第 X 页</span>
      </div>
    </div>
    ```

## 9.5 翻页脚本

    ```html
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
    ```

# 10 质量检查规则

## 10.1 尺寸精确性

-   `.ppt-container`：width=800px，height=450px。
-   `.title-bar`：top=30px，height=25px，不应添加 padding，border-bottom=1px solid #e2e8f0。
-   `.content-box`：top=66px，width=740px，height=349px。
-   `.left-column`/`.right-column`：top=66px，height=349px。左栏 left=30px width=355px，右栏 left=415px width=355px。
-   `.ppt-footer`：bottom=5px，height=20px。

## 10.2 内容边界

-   每个页面的内容总高度应 ≤349px。
-   每个页面应有高度计算注释。
-   不应使用 overflow: auto/scroll/hidden。
-   两栏布局每栏内容应 ≤349px（含 padding）。

## 10.3 样式一致性

-   字号、配色、扁平化设计应符合第 4 章规范。
-   全文不应出现 box-shadow（ppt-container 除外）。
-   `.list-dot`：width=6px，height=6px，border-radius=50%。
-   所有间距应 ≥8px。

## 10.4 页面类型映射

-   `#` → `layout-title`（无标题栏、无页脚）。
-   `##` → `layout-section`（无标题栏、无页脚）。
-   `###` → `layout-content`（有标题栏、有页脚）。
-   `####` → `layout-content` + level-3 面包屑（颜色 #8b5cf6）。
-   面包屑 `###`：level-1（#6366f1）› level-2（#334155）。
-   面包屑 `####`：level-1（#6366f1）› level-3（#8b5cf6）。
-   分隔符 `›`：颜色 #94a3b8，font-weight 400。

## 10.5 翻页功能

-   应包含键盘翻页脚本（ArrowDown/PageDown/ArrowUp/PageUp）。
-   滚动距离 = 470px（450px 页面 + 20px 间距）。

# 修订记录

| 版本号 | 日期       | 修订内容                                                                                            | 修订人 |
| ------ | ---------- | --------------------------------------------------------------------------------------------------- | ------ |
| R.01   | 2026-03-07 | 规范驱动修订：符合 C01/C02/C11；删除完整转换示例和人类教学内容；合并 A-P 自检清单为精简质量检查规则 | AI     |
