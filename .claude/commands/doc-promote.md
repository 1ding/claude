# 晋升文档为正式版本

将 `drafts/` 中的草稿晋升为正式版本：R 版本自动执行 R 转常规版本号，然后复制到 `outputs/`，旧正式版移入 `history/`。

## 用法

```
/doc-promote <文件路径或前缀> [新版本号]
/doc-promote [新版本号]
```

**参数**：

-   第一个参数若含 `/` 或以 `.md` 结尾 → 视为**文件路径或前缀**，直接定位目标文件
-   第一个参数若匹配 `v\d+\.\d+` → 视为**版本号覆盖**，目标文件从会话历史的 `[LOADED target]` 获取
-   无参数 → 目标文件从会话历史的 `[LOADED target]` 获取，版本号自动 +0.01

**示例**：

```
/doc-promote projects/ClariSphere/drafts/02-宏观需求_v0.12_R09@202602271800.md
/doc-promote projects/ClariSphere/drafts/02-宏观需求   ← 前缀，自动取最新版
/doc-promote v1.00                                    ← 指定版本号，文件从 load-target 获取
/doc-promote                                          ← 文件和版本号均从上下文获取
```

## 执行步骤

### 1. 解析参数，定位目标文件

**解析 $ARGUMENTS**：

```
if $ARGUMENTS 含 '/' 或以 '.md' 结尾:
    file_arg    = $ARGUMENTS（文件路径或前缀）
    version_arg = 空
elif $ARGUMENTS 匹配 v\d+\.\d+:
    file_arg    = 空
    version_arg = $ARGUMENTS
else:
    file_arg    = 空
    version_arg = 空
```

**定位目标文件**：

```
if file_arg 非空:
    if file_arg 以 '.md' 结尾:
        src_file = file_arg（直接使用）
    else:
        src_file = 执行以下命令取最新版：
            ls {file_arg}_v*.md 2>/dev/null | sort | tail -1
        若结果为空 → 报错中止
else:
    从会话历史查找最近一条 [LOADED target] 记录，提取文件路径
    若未找到 → 报错：
        ⚠️ 未找到目标文档。请提供文件路径或先使用 /load-target 加载文档。
        示例：/doc-promote projects/ClariSphere/drafts/02-宏观需求_v0.12_R09@...md
    src_file = 找到的路径
```

**从 src_file 路径提取关键信息**（通过 bash 命令）：

```bash
# 项目路径（drafts/ 的父目录）
PROJECT_DIR=$(dirname $(dirname {src_file}))

# 文档名前缀（文件名中 _v 之前的部分）
DOC_PREFIX=$(basename {src_file} | sed 's/_v[0-9].*//')
```

### 2. 判断版本类型

从 src_file 文件名判断：

-   **R 版本**（文件名匹配 `_R\d+@`）→ 执行步骤 3（R 转常规版本号）
-   **常规版本**（不含 `_R\d+@`）→ 跳至步骤 4（此时 version_arg 若非空，忽略并提示用户）

### 3. R 转常规版本号（调用脚本）

```bash
# 调用脚本，stdout 输出新文件路径，stderr 输出进度日志
NEW_FILE=$(python3 .claude/scripts/r-to-regular.py {src_file} {version_arg})
```

-   脚本自动：计算新版本号（+0.01 或使用 version_arg）、合并 R.xx 修订记录、写入新文件
-   若 src_file 已是常规版本，脚本直接返回 src_file 路径（退出码 0）

验证 `$NEW_FILE` 文件存在，确认可访问。

### 4. 晋升到 outputs/

```bash
bash .claude/scripts/promote-to-official.sh {PROJECT_DIR} {DOC_PREFIX}
```

脚本将：

-   若 `outputs/` 已有旧正式版 → 移动到 `history/`
-   将 `drafts/` 中按文件名排序最新的常规版本复制到 `outputs/`

### 5. 输出结果报告

```
---晋升完成---
文档：{DOC_PREFIX}
操作：R 转常规版本号（{旧版本_R修订} → {新版本}）+ 晋升    ← R 版本时
      直接晋升（{版本号}）                                   ← 已是常规版本时
新正式版：outputs/{文件名}
归档旧版：history/{旧文件名}（若无旧版则省略）
```
