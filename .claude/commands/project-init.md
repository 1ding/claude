# 项目初始化

初始化会话项目上下文：加载项目配置、关联关系和决策记录，为后续 doc-* 操作建立基础。

## 适用场景

-   新会话开始时明确当前工作项目
-   从其他项目切换时重置项目上下文

## 不适用场景

-   查看项目整体进度 → `/doc-status`
-   加载具体文档内容 → `/load-target`、`/load-upstream` 等

## 输入

$ARGUMENTS

## 先决条件检查

**参数解析（项目名称或路径）**

若 $ARGUMENTS 提供了项目名称（无路径分隔符）：
1.   在 `projects/` 下匹配同名目录
2.   匹配到唯一结果 → 继续执行
3.   匹配到多个结果 → 列出供选择，中止等待用户确认
4.   未找到 → 列出 `projects/` 下所有项目，中止等待用户确认

若 $ARGUMENTS 提供了路径（含 `/`）：
1.   直接使用该路径作为项目根目录

若 $ARGUMENTS 为空：
1.   列出 `projects/` 下所有项目及其 outputs/ 文件数量，中止等待用户选择

## 执行步骤

### 1. 读取项目配置

依次读取以下文件（不产生 `[LOADED *]` 标记，作为配置性读取）：

1.   `projects/{项目}/CLAUDE.md` — 项目角色定位、所属领域、文档命名规则、关联关系表
2.   `projects/{项目}/decisions.md` — 已有决策记录（若文件存在且非空模板）

读取完成后输出：

```
[LOADED project] projects/{项目}/CLAUDE.md | ~N tokens
[LOADED project] projects/{项目}/decisions.md | ~N tokens（或"暂无决策记录"）
```

### 2. 扫描项目状态

使用 `ls` 扫描以下目录（不读取文件内容）：

-   `drafts/` — 进行中文件（区分常规版本和 R 版本）
-   `outputs/` — 当前正式版文件
-   `plans/` — 大纲文件和交接文件（若有）

### 3. 输出初始化摘要

格式如下：

```
---项目初始化完成---

项目：{项目名}
领域：{所属领域}
AI 角色：{角色定位一句话}

文档状态：
| 文档     | drafts 最新版本 | outputs 正式版本 | 状态   |
| -------- | --------------- | ---------------- | ------ |
| {文档名} | {版本@时间戳}   | {版本@时间戳}    | {状态} |

状态说明：✓ 已发布 | 进行中 | 待发布（drafts有但outputs无）| 仅outputs（drafts无副本）

待处理：
- plans/ 中有交接文件：{文件名}（建议 /doc-resume 继续）
- decisions.md 中有 {N} 条决策记录

就绪，可执行 /load-upstream、/load-target 等加载具体文档。
```

**状态判断规则：**
-   drafts 有 R 版本 → "进行中（R 版本）"
-   drafts 有常规版本、outputs 无 → "待发布"
-   drafts 和 outputs 均有同名前缀文件 → "已发布"
-   仅 outputs 有（drafts 无同名前缀） → "仅 outputs（无工作副本）"

## 注意事项

-   本命令不加载任何领域规范（`/load-domain`）或背景文档（`/load-context`）— 需要时单独执行
-   本命令不修改任何文件
-   `[LOADED project]` 标记纳入容量计算（token 估算：文件字节数 ÷ 3.5）
