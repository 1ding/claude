#!/bin/bash
# 文档结构校验脚本
# 用法: ./scripts/validate-structure.sh <文档路径> [选项]
#
# 选项:
#   --schema <schema.yaml>   使用 Schema 文件进行结构校验
#   --max-depth <N>          最大层级深度（默认4，Schema 指定时以 Schema 为准）
#   --max-chars <N>          每章最大汉字数（默认10000，≈16K tokens）
#
# 功能:
#   1. 检查标题层级是否合理（无跳级）
#   2. 检查层级深度是否超限
#   3. 检查各章节字数是否超过单章上限（≈16K tokens）
#   4. 检查是否存在空章节或占位符
#   5. 检查 Markdown 格式基本规范
#   6. [Schema] 检查必须章节是否存在
#   7. [Schema] 检查必须元数据字段是否存在
#   8. [Schema] 检查必须附录是否存在
#   9. [Schema] 报告结构性规则清单

set -euo pipefail

# ── 参数解析 ──
DOC_PATH=""
SCHEMA_PATH=""
MAX_DEPTH=""
MAX_CHARS_PER_SECTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --schema)
            SCHEMA_PATH="${2:?--schema 需要指定 Schema 文件路径}"
            shift 2
            ;;
        --max-depth)
            MAX_DEPTH="${2:?--max-depth 需要指定数字}"
            shift 2
            ;;
        --max-chars)
            MAX_CHARS_PER_SECTION="${2:?--max-chars 需要指定数字}"
            shift 2
            ;;
        -h|--help)
            echo "用法: $0 <文档路径> [--schema <schema.yaml>] [--max-depth <N>] [--max-chars <N>]"
            exit 0
            ;;
        *)
            if [ -z "$DOC_PATH" ]; then
                DOC_PATH="$1"
            elif [ -z "$MAX_DEPTH" ]; then
                # 兼容旧用法: $0 <文档路径> [最大层级深度]
                MAX_DEPTH="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$DOC_PATH" ]; then
    echo "用法: $0 <文档路径> [--schema <schema.yaml>] [--max-depth <N>] [--max-chars <N>]"
    exit 1
fi

if [ ! -f "$DOC_PATH" ]; then
    echo "[ERROR] 文档不存在: $DOC_PATH"
    exit 1
fi

# ── Schema 辅助函数（纯 bash/grep 解析简单 YAML） ──

# 从 YAML 中读取简单标量值: yaml_get <file> <key>
yaml_get() {
    local file="$1" key="$2"
    grep -m1 "^${key}:" "$file" 2>/dev/null | sed "s/^${key}:[[:space:]]*//" | sed 's/[[:space:]]*#.*//' | sed 's/^["'"'"']\(.*\)["'"'"']$/\1/'
}

# 从 YAML 中读取嵌套标量值: yaml_get_nested <file> <parent> <key>
yaml_get_nested() {
    local file="$1" parent="$2" key="$3"
    sed -n "/^${parent}:/,/^[a-z_]/p" "$file" 2>/dev/null | grep -m1 "^  ${key}:" | sed "s/^  ${key}:[[:space:]]*//" | sed 's/[[:space:]]*#.*//'
}

# 从 YAML 列表中读取 title 字段（required: true 的项）: yaml_get_required_titles <file> <section>
yaml_get_required_titles() {
    local file="$1" section="$2"
    # 提取 section 下所有 title 行（仅 required: true 的项）
    awk -v section="$section" '
    BEGIN { in_section=0; in_item=0; title=""; required=0 }
    /^[a-z_]+:/ {
        if ($0 ~ "^"section":") { in_section=1; next }
        else if (in_section) { in_section=0 }
    }
    in_section && /^  - title:/ {
        if (in_item && required && title != "") print title
        title = $0; sub(/^  - title:[[:space:]]*"?/, "", title); sub(/"?[[:space:]]*$/, "", title)
        required = 0; in_item = 1
        next
    }
    in_section && in_item && /^    required:[[:space:]]*true/ { required = 1 }
    in_section && /^  - / && !/^  - title:/ {
        if (in_item && required && title != "") print title
        in_item = 0; title = ""; required = 0
    }
    END { if (in_item && required && title != "") print title }
    ' "$file"
}

# 从 YAML 列表中读取简单字符串列表: yaml_get_list <file> <section>
yaml_get_list() {
    local file="$1" section="$2"
    awk -v section="$section" '
    BEGIN { in_section=0 }
    /^[a-z_]+:/ {
        if ($0 ~ "^"section":") { in_section=1; next }
        else if (in_section) { in_section=0 }
    }
    in_section && /^  - / {
        val = $0; sub(/^  - [[:space:]]*/, "", val); sub(/[[:space:]]*#.*/, "", val)
        gsub(/^["'"'"']|["'"'"']$/, "", val)
        if (val != "") print val
    }
    ' "$file"
}

# 从 YAML 中读取 structural_rules 的 description: yaml_get_rules <file>
yaml_get_rules() {
    local file="$1"
    awk '
    BEGIN { in_rules=0; in_item=0; rule=""; desc="" }
    /^structural_rules:/ { in_rules=1; next }
    /^[a-z_]+:/ && !/^    / { if (in_rules) in_rules=0 }
    in_rules && /^  - rule:/ {
        if (in_item && desc != "") print rule "|" desc
        rule = $0; sub(/^  - rule:[[:space:]]*"?/, "", rule); sub(/"?[[:space:]]*$/, "", rule)
        desc = ""; in_item = 1
    }
    in_rules && in_item && /^    description:/ {
        desc = $0; sub(/^    description:[[:space:]]*"?/, "", desc); sub(/"?[[:space:]]*$/, "", desc)
    }
    END { if (in_item && desc != "") print rule "|" desc }
    ' "$file"
}

# ── 从 Schema 读取参数 ──
SCHEMA_DOC_TYPE=""
SCHEMA_DOC_NAME=""

if [ -n "$SCHEMA_PATH" ]; then
    if [ ! -f "$SCHEMA_PATH" ]; then
        echo "[ERROR] Schema 文件不存在: $SCHEMA_PATH"
        exit 1
    fi
    SCHEMA_DOC_TYPE=$(yaml_get "$SCHEMA_PATH" "doc_type")
    SCHEMA_DOC_NAME=$(yaml_get "$SCHEMA_PATH" "doc_type_name")

    # Schema 指定的深度（命令行参数优先）
    if [ -z "$MAX_DEPTH" ]; then
        SCHEMA_MAX_DEPTH=$(yaml_get_nested "$SCHEMA_PATH" "depth" "max")
        if [ -n "$SCHEMA_MAX_DEPTH" ]; then
            MAX_DEPTH="$SCHEMA_MAX_DEPTH"
        fi
    fi
fi

# 默认值
MAX_DEPTH="${MAX_DEPTH:-4}"
MAX_CHARS_PER_SECTION="${MAX_CHARS_PER_SECTION:-10000}"

# ── 输出头部 ──
echo "=== 文档结构校验 ==="
echo "文档: $DOC_PATH"
if [ -n "$SCHEMA_PATH" ]; then
    echo "Schema: $SCHEMA_DOC_TYPE - $SCHEMA_DOC_NAME"
fi
echo "最大层级深度: $MAX_DEPTH"
echo "每章最大汉字数: $MAX_CHARS_PER_SECTION（≈16K tokens）"
echo ""

ISSUES=0
TOTAL_LINES=$(wc -l < "$DOC_PATH")
echo "文档总行数: $TOTAL_LINES"
echo ""

# ---- 1. 标题层级跳级检查 ----
echo "--- 1. 标题层级跳级检查 ---"

PREV_LEVEL=0
SKIP_ISSUES=0
while IFS= read -r line; do
    LINE_NUM=$(echo "$line" | cut -d: -f1)
    HEADING=$(echo "$line" | cut -d: -f2-)
    # 计算 # 的数量
    LEVEL=$(echo "$HEADING" | grep -oP '^#+' | wc -c)
    LEVEL=$((LEVEL - 1))  # wc -c 包含换行符

    if [ $PREV_LEVEL -gt 0 ] && [ $LEVEL -gt $((PREV_LEVEL + 1)) ]; then
        echo "[!] 第${LINE_NUM}行: 标题层级跳级 (H$PREV_LEVEL → H$LEVEL): $(echo "$HEADING" | head -c 60)"
        SKIP_ISSUES=$((SKIP_ISSUES + 1))
    fi
    PREV_LEVEL=$LEVEL
done < <(grep -n '^#' "$DOC_PATH" || true)

if [ $SKIP_ISSUES -eq 0 ]; then
    echo "[OK] 标题层级无跳级"
else
    ISSUES=$((ISSUES + SKIP_ISSUES))
fi
echo ""

# ---- 2. 层级深度检查 ----
echo "--- 2. 层级深度检查 ---"

DEPTH_ISSUES=0
while IFS= read -r line; do
    LINE_NUM=$(echo "$line" | cut -d: -f1)
    HEADING=$(echo "$line" | cut -d: -f2-)
    LEVEL=$(echo "$HEADING" | grep -oP '^#+' | wc -c)
    LEVEL=$((LEVEL - 1))

    if [ $LEVEL -gt $MAX_DEPTH ]; then
        echo "[!] 第${LINE_NUM}行: 层级深度 H$LEVEL 超过上限 $MAX_DEPTH: $(echo "$HEADING" | head -c 60)"
        DEPTH_ISSUES=$((DEPTH_ISSUES + 1))
    fi
done < <(grep -n '^#' "$DOC_PATH" || true)

if [ $DEPTH_ISSUES -eq 0 ]; then
    echo "[OK] 所有标题层级在 H$MAX_DEPTH 以内"
else
    ISSUES=$((ISSUES + DEPTH_ISSUES))
fi
echo ""

# ---- 3. 章节字数检查（单章上限 ≈16K tokens） ----
echo "--- 3. 章节字数检查 ---"

# 获取所有一级标题的行号
H1_LINES=$(grep -n '^# ' "$DOC_PATH" | cut -d: -f1 || true)

if [ -n "$H1_LINES" ]; then
    SECTIONS=()
    SECTION_NAMES=()
    SECTION_STARTS=()
    PREV_LINE=""
    PREV_NAME=""

    while IFS= read -r h1_line; do
        if [ -n "$PREV_LINE" ]; then
            SECTIONS+=("$PREV_LINE:$((h1_line - 1))")
            SECTION_NAMES+=("$PREV_NAME")
        fi
        PREV_LINE="$h1_line"
        PREV_NAME=$(sed -n "${h1_line}p" "$DOC_PATH" | sed 's/^# //')
    done <<< "$H1_LINES"

    # 最后一个章节到文件末尾
    if [ -n "$PREV_LINE" ]; then
        SECTIONS+=("$PREV_LINE:$TOTAL_LINES")
        SECTION_NAMES+=("$PREV_NAME")
    fi

    # 统计各章节汉字数（UTF-8 中文字符，3字节/字）并检查
    BALANCE_ISSUES=0
    echo "章节字数统计（汉字数）:"
    for i in "${!SECTIONS[@]}"; do
        RANGE="${SECTIONS[$i]}"
        START_L="${RANGE%%:*}"
        END_L="${RANGE##*:}"
        NAME="${SECTION_NAMES[$i]}"

        # 提取章节内容（含多级标题），统计汉字数（匹配 CJK 统一表意文字范围）
        CHAR_COUNT=$(sed -n "${START_L},${END_L}p" "$DOC_PATH" | \
            grep -oP '[\x{4e00}-\x{9fff}\x{3400}-\x{4dbf}\x{f900}-\x{faff}]' 2>/dev/null | wc -l || echo 0)

        printf "  %-40s %d 字\n" "$NAME" "$CHAR_COUNT"

        if [ "$CHAR_COUNT" -gt "$MAX_CHARS_PER_SECTION" ]; then
            echo "  [!] 章节「$NAME」: ${CHAR_COUNT} 字，超过上限 ${MAX_CHARS_PER_SECTION} 字（≈16K tokens），建议拆分"
            BALANCE_ISSUES=$((BALANCE_ISSUES + 1))
        elif [ "$CHAR_COUNT" -lt 50 ] && [ "$END_L" -gt "$START_L" ]; then
            echo "  [!] 章节「$NAME」: ${CHAR_COUNT} 字，内容过少，可能为空章节"
            BALANCE_ISSUES=$((BALANCE_ISSUES + 1))
        fi
    done

    if [ $BALANCE_ISSUES -eq 0 ]; then
        echo "[OK] 各章节字数在上限以内"
    else
        ISSUES=$((ISSUES + BALANCE_ISSUES))
    fi
else
    echo "[INFO] 未发现一级标题"
fi
echo ""

# ---- 4. 占位符和 TODO 检测 ----
echo "--- 4. 占位符和 TODO 检测 ---"

PLACEHOLDER_PATTERNS=(
    'TODO'
    'FIXME'
    'XXX'
    'TBD'
    '待补充'
    '待完善'
    '待确认'
    '\[占位\]'
    '\[待定\]'
    '\.\.\.'
)

PLACEHOLDER_ISSUES=0
for pattern in "${PLACEHOLDER_PATTERNS[@]}"; do
    MATCHES=$(grep -n "$pattern" "$DOC_PATH" 2>/dev/null || true)
    if [ -n "$MATCHES" ]; then
        COUNT=$(echo "$MATCHES" | wc -l)
        # 排除代码块内的匹配（简单启发式：忽略以 ``` 包围的内容）
        echo "[!] 发现「$pattern」$COUNT 处:"
        echo "$MATCHES" | head -5 | sed 's/^/    /'
        if [ "$COUNT" -gt 5 ]; then
            echo "    ...（共 $COUNT 处，仅显示前5处）"
        fi
        PLACEHOLDER_ISSUES=$((PLACEHOLDER_ISSUES + COUNT))
    fi
done

if [ $PLACEHOLDER_ISSUES -eq 0 ]; then
    echo "[OK] 未发现占位符或 TODO 标记"
else
    ISSUES=$((ISSUES + PLACEHOLDER_ISSUES))
fi
echo ""

# ---- 5. Markdown 格式基本检查 ----
echo "--- 5. Markdown 格式检查 ---"

FORMAT_ISSUES=0

# 检查标题后是否有空行
PREV_WAS_HEADING=false
LINE_NUM=0
while IFS= read -r line; do
    LINE_NUM=$((LINE_NUM + 1))
    if $PREV_WAS_HEADING && [ -n "$line" ] && [[ ! "$line" =~ ^# ]]; then
        :
    fi
    if [[ "$line" =~ ^# ]]; then
        PREV_WAS_HEADING=true
    else
        PREV_WAS_HEADING=false
    fi
done < "$DOC_PATH"

# 检查表格对齐（简单检查：有 | 的行是否列数一致）
TABLE_GROUPS=$(grep -n '^|' "$DOC_PATH" 2>/dev/null || true)
if [ -n "$TABLE_GROUPS" ]; then
    PREV_COLS=0
    PREV_LINE_NUM=0
    TABLE_START=0
    while IFS= read -r tline; do
        T_LINE_NUM=$(echo "$tline" | cut -d: -f1)
        T_CONTENT=$(echo "$tline" | cut -d: -f2-)
        COLS=$(echo "$T_CONTENT" | grep -o '|' | wc -l)

        if [ $PREV_LINE_NUM -gt 0 ] && [ $((T_LINE_NUM - PREV_LINE_NUM)) -eq 1 ]; then
            # 连续表格行
            if [ $PREV_COLS -ne $COLS ] && [[ ! "$T_CONTENT" =~ ^[[:space:]]*\|[-:|[:space:]]+\|[[:space:]]*$ ]]; then
                echo "[!] 第${T_LINE_NUM}行: 表格列数不一致（$COLS 列 vs 前行 $PREV_COLS 列）"
                FORMAT_ISSUES=$((FORMAT_ISSUES + 1))
            fi
        fi
        PREV_LINE_NUM=$T_LINE_NUM
        PREV_COLS=$COLS
    done <<< "$TABLE_GROUPS"
fi

if [ $FORMAT_ISSUES -eq 0 ]; then
    echo "[OK] Markdown 格式基本规范"
else
    ISSUES=$((ISSUES + FORMAT_ISSUES))
fi
echo ""

# ======== Schema 校验（仅当 --schema 指定时执行） ========
if [ -n "$SCHEMA_PATH" ]; then

    # ---- 6. 必须章节检查 ----
    echo "--- 6. [Schema] 必须章节检查 ---"

    # 提取文档中的所有一级标题（去掉 # 和前后空格）
    DOC_H1_TITLES=$(grep '^# ' "$DOC_PATH" | sed 's/^# //' | sed 's/^[0-9]*[.、 ]*//' | sed 's/[[:space:]]*$//' || true)

    SECTION_ISSUES=0
    while IFS= read -r required_title; do
        [ -z "$required_title" ] && continue
        # 在文档一级标题中模糊匹配（标题可能有编号前缀）
        FOUND=false
        while IFS= read -r doc_title; do
            [ -z "$doc_title" ] && continue
            if [[ "$doc_title" == *"$required_title"* ]]; then
                FOUND=true
                break
            fi
        done <<< "$DOC_H1_TITLES"

        if $FOUND; then
            echo "[OK] 章节「$required_title」存在"
        else
            echo "[!!] 缺少必须章节「$required_title」"
            SECTION_ISSUES=$((SECTION_ISSUES + 1))
        fi
    done < <(yaml_get_required_titles "$SCHEMA_PATH" "required_sections")

    if [ $SECTION_ISSUES -eq 0 ]; then
        echo "[OK] 所有必须章节均已存在"
    else
        ISSUES=$((ISSUES + SECTION_ISSUES))
    fi
    echo ""

    # ---- 7. 必须元数据字段检查 ----
    echo "--- 7. [Schema] 必须元数据字段检查 ---"

    METADATA_ISSUES=0
    while IFS= read -r field; do
        [ -z "$field" ] && continue
        # 在文档中查找该字段名（可能在表格或键值对中）
        if grep -q "$field" "$DOC_PATH" 2>/dev/null; then
            echo "[OK] 元数据字段「$field」存在"
        else
            echo "[!!] 缺少必须元数据字段「$field」"
            METADATA_ISSUES=$((METADATA_ISSUES + 1))
        fi
    done < <(yaml_get_list "$SCHEMA_PATH" "required_metadata")

    if [ $METADATA_ISSUES -eq 0 ]; then
        echo "[OK] 所有必须元数据字段均已存在"
    else
        ISSUES=$((ISSUES + METADATA_ISSUES))
    fi
    echo ""

    # ---- 8. 必须附录检查 ----
    echo "--- 8. [Schema] 必须附录检查 ---"

    APPENDIX_ISSUES=0
    HAS_REQUIRED_APPENDICES=false
    while IFS= read -r appendix_title; do
        [ -z "$appendix_title" ] && continue
        HAS_REQUIRED_APPENDICES=true
        # 附录通常以"附录"或"Appendix"开头，或作为标题出现
        if grep -qi "$appendix_title" "$DOC_PATH" 2>/dev/null; then
            echo "[OK] 附录「$appendix_title」存在"
        else
            echo "[!!] 缺少必须附录「$appendix_title」"
            APPENDIX_ISSUES=$((APPENDIX_ISSUES + 1))
        fi
    done < <(yaml_get_required_titles "$SCHEMA_PATH" "required_appendices")

    if ! $HAS_REQUIRED_APPENDICES; then
        echo "[INFO] Schema 未定义必须附录"
    elif [ $APPENDIX_ISSUES -eq 0 ]; then
        echo "[OK] 所有必须附录均已存在"
    else
        ISSUES=$((ISSUES + APPENDIX_ISSUES))
    fi
    echo ""

    # ---- 9. 结构性规则清单 ----
    echo "--- 9. [Schema] 结构性规则清单 ---"

    RULE_COUNT=0
    while IFS='|' read -r rule desc; do
        [ -z "$rule" ] && continue
        RULE_COUNT=$((RULE_COUNT + 1))
        echo "  [$RULE_COUNT] $rule: $desc"
    done < <(yaml_get_rules "$SCHEMA_PATH")

    if [ $RULE_COUNT -eq 0 ]; then
        echo "[INFO] Schema 未定义结构性规则"
    else
        echo ""
        echo "[INFO] 以上 $RULE_COUNT 条规则需人工或 AI 辅助确认"
    fi
    echo ""

fi

# ---- 汇总 ----
echo "=== 校验汇总 ==="
if [ $ISSUES -eq 0 ]; then
    echo "[OK] 文档结构检查通过，未发现问题"
else
    echo "[!] 发现 $ISSUES 个结构问题，建议使用 /doc-revise 处理（超字数章节按 .claude/rules-ext/structure-constraints.md 拆分）"
fi

exit $ISSUES