# 初始化文档项目

根据用户指令初始化一个新的文档项目。

## 输入

$ARGUMENTS

## 执行步骤

### 1. 解析参数

从用户输入中识别：
-   **项目名**（必选）：用于创建 `projects/{项目名}/` 目录
-   **所属领域**（必选，未指定则询问）：如 `software`，对应 `specs/{领域}/`
-   **文档清单**（可选）：项目中计划编写的文档列表及关联关系

### 2. 创建目录结构

在 `projects/{项目名}/` 下创建以下目录和文件：

```
projects/{项目名}/
├── CLAUDE.md          ← 项目级配置
├── decisions.md       ← 决策日志（格式见 .claude/rules-ext/decisions-template.md）
├── refs/              ← 参考材料
├── drafts/            ← 工作目录（所有版本历史）
├── plans/             ← 计划文件、大纲、交接文件
├── outputs/           ← 当前正式版（每个文档只有一个文件）
└── history/           ← 旧正式版归档
```

### 3. 生成项目级 CLAUDE.md

根据用户提供的信息，生成 `projects/{项目名}/CLAUDE.md`，包含：
-   所属领域声明
-   项目内文档关联关系表（如用户提供了文档清单）

格式参照 `.claude/rules-ext/association-rules.md` 中的项目级 CLAUDE.md 声明格式。

若用户未提供文档清单，生成带占位说明的模板，提示用户后续补充。

同时读取 `.claude/rules-ext/decisions-template.md`，按其格式生成空的 `projects/{项目名}/decisions.md` 决策日志。

### 4. 验证领域配置

检查 `specs/{领域}/CLAUDE.md` 是否存在：
-   存在：确认领域关联关系已就绪
-   不存在：提醒用户需要创建领域级配置

### 5. 输出确认

```
项目已初始化：projects/{项目名}/
所属领域：{领域}
目录结构：已创建 refs/ drafts/ plans/ outputs/ history/
项目配置：projects/{项目名}/CLAUDE.md 已生成

后续操作：
- 将参考材料放入 refs/
- 使用 /doc-outline 生成文档大纲
- 使用 /doc-write 执行内容编写
```
