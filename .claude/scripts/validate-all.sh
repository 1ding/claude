#!/bin/bash
# 文档全量校验入口脚本
# 用法: ./scripts/validate-all.sh <文档路径> [术语表路径] [--schema <schema.yaml>]
#
# 依次运行术语一致性、交叉引用、结构校验三个脚本，汇总结果

set -uo pipefail

# ── 参数解析 ──
DOC_PATH=""
GLOSSARY_PATH=""
SCHEMA_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --schema)
            SCHEMA_PATH="${2:?--schema 需要指定 Schema 文件路径}"
            shift 2
            ;;
        *)
            if [ -z "$DOC_PATH" ]; then
                DOC_PATH="$1"
            elif [ -z "$GLOSSARY_PATH" ]; then
                GLOSSARY_PATH="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$DOC_PATH" ]; then
    echo "用法: $0 <文档路径> [术语表路径] [--schema <schema.yaml>]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  文档全量校验"
echo "  文档: $DOC_PATH"
if [ -n "$SCHEMA_PATH" ]; then
    echo "  Schema: $SCHEMA_PATH"
fi
echo "============================================"
echo ""

TOTAL_ISSUES=0

# 1. 术语一致性
echo "============================================"
if ! "$SCRIPT_DIR/validate-terminology.sh" "$DOC_PATH" "$GLOSSARY_PATH"; then
    TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
fi
echo ""

# 2. 交叉引用
echo "============================================"
if ! "$SCRIPT_DIR/validate-xref.sh" "$DOC_PATH"; then
    TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
fi
echo ""

# 3. 结构校验
echo "============================================"
STRUCTURE_ARGS=("$DOC_PATH")
if [ -n "$SCHEMA_PATH" ]; then
    STRUCTURE_ARGS+=("--schema" "$SCHEMA_PATH")
fi
if ! "$SCRIPT_DIR/validate-structure.sh" "${STRUCTURE_ARGS[@]}"; then
    TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
fi
echo ""

# 汇总
echo "============================================"
echo "  全量校验汇总"
echo "============================================"
if [ $TOTAL_ISSUES -eq 0 ]; then
    echo "[OK] 全部检查通过（3/3 项）"
else
    echo "[!] $TOTAL_ISSUES / 3 个检查项存在问题（详见上方各项输出）"
    echo ""
    echo "建议操作:"
    echo "  - 使用 /doc-review 进行深度 AI 评审"
    echo "  - 使用 /doc-revise 执行修订（质量自检驱动）"
fi

exit $TOTAL_ISSUES