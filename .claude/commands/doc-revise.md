# 执行内容修订

执行文档内容修订。

## 适用场景

-   按修订意见进行系统性修订（意见驱动）
-   对标规范文档进行内容调整（规范驱动）
-   吸纳参考材料内容（参考吸纳驱动）
-   一致性对齐（一致性驱动）
-   全面质量自检（质量自检驱动）
-   结构改写、内容增补、内容精简、版本升级

## 不适用场景（请改用对应 skill）

-   改一两个小问题 → `/doc-fix`
-   只做格式调整 → `/doc-fmt`
-   只做跨文档比对（不修订） → `/doc-align`
-   恢复上次中断的修订 → `/doc-resume`

## 输入

$ARGUMENTS

## 先决条件检查

**在执行任何步骤前，先完成以下检查：**

扫描当前会话历史中的 `[LOADED *]` 记录，确认：
-   [ ] 已存在 `[LOADED target]` 记录（通过 `/load-target` 加载了目标文档）

如未满足，输出以下提示并**立即中止**，不执行后续任何步骤：

> ⚠️ 请先执行 `/load-target /path/to/目标文档` 后再运行本命令
>
> 如为一致性驱动或版本升级驱动，还需加载关联文档：`/load-upstream`、`/load-downstream` 等

## 执行步骤

### 1. 确认已加载内容

从会话历史扫描所有 `[LOADED *]` 记录，整理可用输入：
-   目标文档（必须）
-   规范文档（`[LOADED spec]`、`[LOADED layout]`、`[LOADED style]`、`[LOADED domain]`，可选）
-   关联文档（`[LOADED upstream]`、`[LOADED downstream]` 等，可选）
-   参考材料（`[LOADED refs]`，可选）

读取 `projects/{项目}/CLAUDE.md`（获取所属领域和项目内文档关联关系表）和 `projects/{项目}/decisions.md`（均从目标文档路径推断项目目录）。

### 2. 辅助规范加载

以下文件立即读取（始终需要，约 4.5K tokens，不产生 `[LOADED *]` 标记）：

-   `.claude/rules-ext/capacity-management.md`（容量评估与分批策略）
-   `.claude/rules-ext/structure-constraints.md`（每批修订后执行章节拆分判断）
-   `.claude/rules-ext/quality-checklist.md`（阶段二复核时使用）

> 注：`.claude/rules/version-management.md` 由 Claude Code 自动加载，无需重复读取。

以下文件按需读取（条件触发时加载）：

-   `.claude/rules-ext/association-rules.md` — 仅当驱动类型为**一致性驱动**时读取
-   `.claude/rules-ext/handoff-template.md` — 仅当容量判定为**不足**需中断时读取
-   `.claude/rules-ext/decisions-template.md` — 仅当需要**记录用户裁决**时读取

### 3. 执行修订流程

按以下阶段执行：

-   阶段零：会话初始化（输入识别、内部准备、输入评估与确认、容量评估、修订方案与规划）
-   阶段一：逐批后台修改（按容量管理规范定义的分批策略执行）
-   阶段二：修订汇总（按质量检查清单全面复核、修订总览、遗留事项）

支持的驱动类型（9种）：
-   意见驱动、规范驱动、参考吸纳驱动、一致性驱动、质量自检驱动
-   改写/重构驱动、增补/扩写驱动、精简/删减驱动、版本升级驱动

### 4. 验证与保存

修订过程中在 `drafts/` 使用 R 版本命名（如 `_v0.10_R01@...`）。阶段二完成后，执行验证并保持 R 版本标记：

1.   执行验证脚本：
     ```
     .claude/scripts/validate-all.sh {终稿路径} {术语表路径（如有）} --schema {对应schema文件（如有）}
     ```
     将验证结果整合到修订汇总报告中。
2.   修订完成的文件保持 R 版本命名（如 `_v0.10_R07@...`），不自动转常规版本号。

> R 转常规版本号须用户明确指令（"R转常规版本号"、"转常规版本"等）。
> 提交到 `outputs/` 须用户明确指令（"提交到 outputs"、"发布正式版本"等）。

-   修订计划文件写入 `projects/{项目}/plans/修订计划_{文档名}.md`
