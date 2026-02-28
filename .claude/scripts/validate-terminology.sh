#!/bin/bash
# 术语一致性校验脚本
# 用法: ./scripts/validate-terminology.sh <文档路径> [术语表路径]
#
# 功能:
#   1. 检测文档内同义术语混用（基于常见模式）
#   2. 若提供术语表，检查文档是否使用了非标准术语
#   3. 检测中英文术语混用

set -euo pipefail

DOC_PATH="${1:?用法: $0 <文档路径> [术语表路径]}"
GLOSSARY_PATH="${2:-}"

if [ ! -f "$DOC_PATH" ]; then
    echo "[ERROR] 文档不存在: $DOC_PATH"
    exit 1
fi

echo "=== 术语一致性校验 ==="
echo "文档: $DOC_PATH"
echo ""

ISSUES=0

# ---- 1. 同义术语混用检测 ----
echo "--- 1. 同义术语混用检测 ---"

# 常见的同义术语对（可扩展）
declare -A TERM_PAIRS=(
    ["用户令牌|访问令牌|access token"]="令牌/token类术语"
    ["接口|API|api"]="接口/API术语"
    ["数据库|DB|db"]="数据库术语"
    ["服务器|server|Server"]="服务器术语"
    ["客户端|client|Client"]="客户端术语"
    ["配置文件|config|配置"]="配置术语"
    ["日志|log|Log"]="日志术语"
    ["请求|request|Request"]="请求术语"
    ["响应|response|Response"]="响应术语"
    ["认证|鉴权|身份验证|authentication"]="认证术语"
    ["授权|权限|authorization"]="授权术语"
)

for pattern in "${!TERM_PAIRS[@]}"; do
    label="${TERM_PAIRS[$pattern]}"
    IFS='|' read -ra terms <<< "$pattern"
    found_terms=()
    for term in "${terms[@]}"; do
        count=$(grep -c "$term" "$DOC_PATH" 2>/dev/null || true)
        if [ "$count" -gt 0 ]; then
            found_terms+=("$term($count)")
        fi
    done
    if [ ${#found_terms[@]} -gt 1 ]; then
        echo "[!] $label - 发现多种表述共存: ${found_terms[*]}"
        ISSUES=$((ISSUES + 1))
    fi
done

if [ $ISSUES -eq 0 ]; then
    echo "[OK] 未发现明显的同义术语混用"
fi
echo ""

# ---- 2. 术语表对照检查 ----
if [ -n "$GLOSSARY_PATH" ] && [ -f "$GLOSSARY_PATH" ]; then
    echo "--- 2. 术语表对照检查 ---"
    echo "术语表: $GLOSSARY_PATH"

    GLOSSARY_ISSUES=0
    # 术语表格式: 每行 "标准术语|非标准术语1|非标准术语2|..."
    while IFS= read -r line; do
        # 跳过空行和注释
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        IFS='|' read -ra parts <<< "$line"
        standard="${parts[0]}"
        for i in $(seq 1 $((${#parts[@]} - 1))); do
            nonstandard="${parts[$i]}"
            count=$(grep -c "$nonstandard" "$DOC_PATH" 2>/dev/null || true)
            if [ "$count" -gt 0 ]; then
                echo "[!] 使用了非标准术语「$nonstandard」($count 处)，应使用「$standard」"
                GLOSSARY_ISSUES=$((GLOSSARY_ISSUES + 1))
            fi
        done
    done < "$GLOSSARY_PATH"

    if [ $GLOSSARY_ISSUES -eq 0 ]; then
        echo "[OK] 所有术语符合术语表定义"
    else
        ISSUES=$((ISSUES + GLOSSARY_ISSUES))
    fi
    echo ""
else
    echo "--- 2. 术语表对照检查 ---"
    echo "[跳过] 未提供术语表文件"
    echo ""
fi

# ---- 3. 中英文术语混用检测 ----
echo "--- 3. 中英文术语混用检测 ---"

# 检测同一行内中英文术语未加括号说明的情况
MIX_COUNT=$(grep -cP '[\x{4e00}-\x{9fff}][a-zA-Z]|[a-zA-Z][\x{4e00}-\x{9fff}]' "$DOC_PATH" 2>/dev/null || true)
if [ "$MIX_COUNT" -gt 0 ]; then
    echo "[INFO] 发现 $MIX_COUNT 行存在中英文混排（可能需要人工确认是否需要括号说明）"
    grep -nP '[\x{4e00}-\x{9fff}][a-zA-Z]|[a-zA-Z][\x{4e00}-\x{9fff}]' "$DOC_PATH" 2>/dev/null | head -10
    if [ "$MIX_COUNT" -gt 10 ]; then
        echo "...（共 $MIX_COUNT 行，仅显示前10行）"
    fi
else
    echo "[OK] 未发现中英文术语混排"
fi
echo ""

# ---- 汇总 ----
echo "=== 校验汇总 ==="
if [ $ISSUES -eq 0 ]; then
    echo "[OK] 术语一致性检查通过，未发现问题"
else
    echo "[!] 发现 $ISSUES 个术语一致性问题，建议使用 /doc-revise 处理"
fi

exit $ISSUES