# 工作区结构规范

## 顶层布局

```
claude code/                         # 工作区根目录
├── .claude/                         # AI 生产配置（稳定、可信赖）
│   ├── commands/                    # Skill 命令定义
│   ├── rules/                       # AI 行为规则（版本管理、容量管理等）
│   ├── rules-ext/                   # 补充规则、模板、清单（按需加载）
│   ├── specs/                       # 已定稿规范 schema（仅存放正式版本）
│   │   ├── common/                  # 通用规范 schema
│   │   └── software/                # 软件领域规范 schema
│   └── scripts/                     # 工具脚本
├── projects/                        # 工作项目区
│   ├── specs/                       # 规范项目（受版本管理）
│   └── {其他项目}/
└── claude.md                        # 工作区顶层说明
```

## .claude/ 与 projects/ 的职责分离

| 区域        | 职责                               | 内容来源              | AI 读写权限       |
| ----------- | ---------------------------------- | --------------------- | ----------------- |
| `.claude/`  | 生产配置，AI 执行工作的依据        | 从 projects/ 手动晋升 | 只读（规则/规范） |
| `projects/` | 研发工作区，所有编写和修订在此进行 | AI 日常工作产物       | 读写              |

**晋升规则**：`.claude/` 中的文件只能通过**用户手动复制**方式更新，AI 不得直接写入 `.claude/specs/` 或 `.claude/rules/`。

## projects/specs/ 项目结构

规范项目遵循标准版本管理目录结构：

```
projects/specs/
├── common/                          # 通用规范（C系列）
│   ├── drafts/                      # 工作区（所有修订历史）
│   ├── outputs/                     # 当前正式版（每文档一个）
│   ├── history/                     # 历史版本归档（备查）
│   ├── schemas/                     # 通用规范 schema 工作版本
│   └── refs/                        # 参考材料
└── software/                        # 软件领域规范
    ├── CLAUDE.md                    # 领域级关联关系配置
    ├── phase-specs/                 # 阶段文档编写规范（S系列：S01-S10）
    │   ├── drafts/
    │   ├── outputs/
    │   ├── history/
    │   └── schemas/                 # S系列 schema 工作版本
    ├── common-specs/                # 软件通用规范（P系列：编号、错误码等）
    │   ├── drafts/
    │   ├── outputs/
    │   ├── history/
    │   └── schemas/                 # P系列 schema 工作版本
    └── context/                     # 过程背景约束（N系列）
        ├── drafts/
        ├── outputs/
        ├── history/
        └── schemas/                 # N系列 schema 工作版本
```

## 业务项目结构

```
projects/{项目}/
├── drafts/                          # 工作区（所有修订历史）
├── outputs/                         # 当前正式版（每文档一个）
├── history/                         # 历史版本归档（备查，内容不受约束）
├── plans/                           # 编写/修订计划文件（容量管理分批时使用）
│   ├── 编写计划_{文档名}.md
│   ├── 修订计划_{文档名}.md
│   └── 交接_{文档名}_{日期}.md      # 跨会话交接文件（如有）
├── CLAUDE.md                        # 项目关联关系配置
└── decisions.md                     # 用户决策记录
```

## schemas/ 工作版本与 .claude/ 正式版本的流转

```
projects/specs/.../schemas/          # 工作版本（开发中，受版本管理）
        ↓  用户确认定稿后手动复制
.claude/specs/{领域}/               # 正式版本（AI 加载使用）
```

-   `projects/` 中的 schema 是**研发中版本**，可迭代修改
-   `.claude/` 中的 schema 是**已定稿版本**，不在此处修改
-   两者可能短期不同步，以 `.claude/` 为 AI 实际执行依据

## history/ 的定位

-   **归档区，备查用途**，AI 正常工作流程中不访问 `history/`
-   除非用户明确指示"查看历史版本"，否则 AI 不读取 `history/` 目录
-   `history/` 内容不受约束，放什么都合理

## 文件加载优先级

加载关联文档时（如 `/load-spec`、`/load-context`）：

1.   优先从 `outputs/` 加载（当前正式版）
2.   `outputs/` 不存在时，从 `drafts/` 取最新版本
3.   两处均不存在，报告缺失，不自动从 `history/` 降级

## load-spec 与 load-domain 的约定

两个命令按规范来源区分，功能相同（AI 读取后判断标记类型），约定如下：

| 命令           | 主要加载来源              | 典型内容                                                       |
| -------------- | ------------------------- | -------------------------------------------------------------- |
| `/load-spec`   | `specs/common/`           | C系列：内容表达、排版格式、通用结构、术语                      |
| `/load-domain` | `specs/{领域}/`（按领域） | 软件领域：S/P/N系列规范；后续可能扩展 security、finance 等领域 |

两者都可以接受任意文件路径，来源约定仅为惯例，不做强制校验。
