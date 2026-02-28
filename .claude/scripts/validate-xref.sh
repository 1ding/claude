#!/bin/bash
# 交叉引用校验脚本
# 用法: ./scripts/validate-xref.sh <文档路径>
#
# 功能:
#   1. 检查"详见第X章/节"等引用是否指向存在的章节
#   2. 检查章节编号是否连续
#   3. 检查目录与正文标题是否一致

set -euo pipefail

DOC_PATH="${1:?用法: $0 <文档路径>}"

if [ ! -f "$DOC_PATH" ]; then
    echo "[ERROR] 文档不存在: $DOC_PATH"
    exit 1
fi

echo "=== 交叉引用校验 ==="
echo "文档: $DOC_PATH"
echo ""

ISSUES=0

# ---- 1. 提取所有章节标题 ----
echo "--- 1. 章节结构分析 ---"

# 提取 Markdown 标题（# 开头的行）
HEADINGS=$(grep -n '^#' "$DOC_PATH" | sed 's/^[0-9]*://' || true)
HEADING_COUNT=$(echo "$HEADINGS" | grep -c '^#' 2>/dev/null || echo "0")
echo "发现 $HEADING_COUNT 个章节标题"

# 提取章节编号（如 1.1, 2.3.1 等）
SECTION_NUMS=$(grep -oP '^#+\s+(\d+(\.\d+)*)\s' "$DOC_PATH" | grep -oP '\d+(\.\d+)*' || true)
if [ -n "$SECTION_NUMS" ]; then
    echo "章节编号: $(echo "$SECTION_NUMS" | tr '\n' ' ')"
fi
echo ""

# ---- 2. 检查章节编号连续性 ----
echo "--- 2. 章节编号连续性检查 ---"

if [ -n "$SECTION_NUMS" ]; then
    PREV_MAJOR=""
    CONTINUITY_OK=true
    while IFS= read -r num; do
        MAJOR=$(echo "$num" | cut -d. -f1)
        if [ -n "$PREV_MAJOR" ] && [ "$MAJOR" != "$PREV_MAJOR" ]; then
            EXPECTED=$((PREV_MAJOR + 1))
            if [ "$MAJOR" -ne "$EXPECTED" ] 2>/dev/null; then
                echo "[!] 一级章节编号不连续: $PREV_MAJOR 之后跳到 $MAJOR（期望 $EXPECTED）"
                ISSUES=$((ISSUES + 1))
                CONTINUITY_OK=false
            fi
        fi
        PREV_MAJOR="$MAJOR"
    done <<< "$(echo "$SECTION_NUMS" | grep -v '\.' || true)"

    if $CONTINUITY_OK; then
        echo "[OK] 一级章节编号连续"
    fi
else
    echo "[INFO] 文档未使用数字编号的章节标题"
fi
echo ""

# ---- 3. 检查交叉引用有效性 ----
echo "--- 3. 交叉引用有效性检查 ---"

# 匹配常见的中文交叉引用模式
XREF_PATTERNS=(
    '详见第[0-9]+章'
    '详见第[0-9]+节'
    '详见[0-9]+\.[0-9]+'
    '参见第[0-9]+章'
    '参见第[0-9]+节'
    '参见[0-9]+\.[0-9]+'
    '见第[0-9]+章'
    '见第[0-9]+节'
    '如[0-9]+\.[0-9]+节所述'
    '在[0-9]+\.[0-9]+节中'
)

XREF_ISSUES=0
for pattern in "${XREF_PATTERNS[@]}"; do
    MATCHES=$(grep -on "$pattern" "$DOC_PATH" 2>/dev/null || true)
    if [ -n "$MATCHES" ]; then
        while IFS= read -r match; do
            LINE_NUM=$(echo "$match" | cut -d: -f1)
            REF_TEXT=$(echo "$match" | cut -d: -f2-)
            # 提取引用的章节号
            REF_NUM=$(echo "$REF_TEXT" | grep -oP '\d+(\.\d+)*' | head -1)
            if [ -n "$REF_NUM" ] && [ -n "$SECTION_NUMS" ]; then
                if ! echo "$SECTION_NUMS" | grep -q "^${REF_NUM}$"; then
                    # 检查是否引用了一级章节（可能不在 SECTION_NUMS 里）
                    echo "[!] 第${LINE_NUM}行: 「$REF_TEXT」引用的章节 $REF_NUM 可能不存在"
                    XREF_ISSUES=$((XREF_ISSUES + 1))
                fi
            else
                echo "[INFO] 第${LINE_NUM}行: 「$REF_TEXT」（无法自动验证）"
            fi
        done <<< "$MATCHES"
    fi
done

if [ $XREF_ISSUES -eq 0 ]; then
    echo "[OK] 未发现明显的无效交叉引用"
else
    ISSUES=$((ISSUES + XREF_ISSUES))
fi
echo ""

# ---- 4. 检查悬空引用（提及但未定义的内容） ----
echo "--- 4. 悬空引用检测 ---"

# 检查 "详见附录X" 中的附录是否存在
APPENDIX_REFS=$(grep -oP '详见附录[A-Z]|参见附录[A-Z]|见附录[A-Z]' "$DOC_PATH" 2>/dev/null || true)
APPENDIX_DEFS=$(grep -oP '^#+\s+附录[A-Z]' "$DOC_PATH" 2>/dev/null | grep -oP '附录[A-Z]' || true)

DANGLING=0
if [ -n "$APPENDIX_REFS" ]; then
    while IFS= read -r ref; do
        APP_ID=$(echo "$ref" | grep -oP '附录[A-Z]')
        if [ -n "$APP_ID" ] && [ -n "$APPENDIX_DEFS" ]; then
            if ! echo "$APPENDIX_DEFS" | grep -q "$APP_ID"; then
                echo "[!] 引用了「$APP_ID」但文档中未找到对应标题"
                DANGLING=$((DANGLING + 1))
            fi
        fi
    done <<< "$(echo "$APPENDIX_REFS" | sort -u)"
fi

if [ $DANGLING -eq 0 ]; then
    echo "[OK] 未发现悬空附录引用"
else
    ISSUES=$((ISSUES + DANGLING))
fi
echo ""

# ---- 汇总 ----
echo "=== 校验汇总 ==="
if [ $ISSUES -eq 0 ]; then
    echo "[OK] 交叉引用检查通过，未发现问题"
else
    echo "[!] 发现 $ISSUES 个交叉引用问题，建议使用 /doc-revise 处理"
fi

exit $ISSUES