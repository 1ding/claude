# 执行内容编写

执行文档内容编写。

## 适用场景

-   从大纲编写完整文档
-   编写新文档的首个版本

## 不适用场景（请改用对应 skill）

-   恢复上次中断的编写 → `/doc-resume`
-   修订已有文档 → `/doc-revise` 或 `/doc-fix`

## 输入

$ARGUMENTS

## 先决条件检查

**在执行任何步骤前，先完成以下检查：**

扫描当前会话历史中的 `[LOADED *]` 记录，确认：
-   [ ] 已存在 `[LOADED target]` 或 `[LOADED outline]` 记录（目标文档或大纲已加载）

如未满足，输出以下提示并**立即中止**，不执行后续任何步骤：

> ⚠️ 请先加载目标文档或大纲：
> -   `/load-target /path/to/目标文档或大纲`
> -   `/load-outline /path/to/大纲文件`
>
> 可选加载（按需）：`/load-spec`、`/load-upstream`、`/load-context`

## 执行步骤

### 1. 确认已加载内容

从会话历史扫描所有 `[LOADED *]` 记录，整理可用输入：
-   目标文档 / 大纲（必须）
-   规范文档（`[LOADED spec]`、`[LOADED layout]`、`[LOADED style]`、`[LOADED domain]`，可选）
-   关联文档（`[LOADED upstream]` 等，可选）
-   参考材料（`[LOADED refs]`，可选）

读取 `projects/{项目}/CLAUDE.md`（获取所属领域和项目内文档关联关系表）和 `projects/{项目}/decisions.md`（均从目标文档路径推断项目目录）。

### 2. 辅助规范加载

以下文件立即读取（始终需要，约 4.5K tokens，不产生 `[LOADED *]` 标记）：

-   `.claude/rules-ext/capacity-management.md`（容量评估与分批策略）
-   `.claude/rules-ext/structure-constraints.md`（每批编写后执行章节拆分判断）
-   `.claude/rules-ext/quality-checklist.md`（阶段二复核时使用）

> 注：`.claude/rules/version-management.md` 由 Claude Code 自动加载，无需重复读取。

以下文件按需读取（条件触发时加载）：

-   `.claude/rules-ext/handoff-template.md` — 仅当容量判定为**不足**需中断时读取
-   `.claude/rules-ext/decisions-template.md` — 仅当需要**记录用户裁决**时读取

### 3. 执行编写流程

按以下阶段执行：

-   阶段零：会话初始化（输入识别、内部准备、输入评估与确认、容量评估、编写方案与规划）
-   阶段一：后台编写（按容量管理规范定义的分批策略执行）
-   阶段二：编写汇总（按质量检查清单全面复核、编写总览、遗留事项）

### 4. 版本流转与验证

编写过程中在 `drafts/` 使用 R 版本命名（如 `_v0.01_R01@...`）。阶段二完成后，按以下顺序完成版本流转与验证：

1.   在 `drafts/` 中执行 R 转常规版本号（版本号递增 0.01，去掉 R 修订号，归并修订记录）
2.   执行验证脚本：
     ```
     .claude/scripts/validate-all.sh {终稿路径} {术语表路径（如有）} --schema {对应schema文件（如有）}
     ```
     将验证结果整合到编写汇总报告中。

> 提交到 `outputs/` 须用户明确指令（"提交到 outputs"、"发布正式版本"等），不在本命令中自动执行。

-   编写计划文件写入 `projects/{项目}/plans/编写计划_{目标文档名}.md`
