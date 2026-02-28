#!/bin/bash
# 将 drafts/ 中的最新版本转为正式版本
# 用法: ./promote-to-official.sh <项目路径> <文档名前缀>

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "用法: $0 <项目路径> <文档名前缀>"
    echo "示例: $0 projects/ClariSphere 01-战略规划"
    exit 1
fi

PROJECT_DIR="$1"
DOC_PREFIX="$2"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

# 创建必要的目录
mkdir -p "$PROJECT_DIR/outputs"
mkdir -p "$PROJECT_DIR/history"

# 查找 drafts/ 中的最新版本
LATEST_DRAFT=$(ls "$PROJECT_DIR/drafts/${DOC_PREFIX}"_v*.md 2>/dev/null | sort | tail -1)

if [ -z "$LATEST_DRAFT" ]; then
    echo "错误: 在 drafts/ 中未找到匹配的文件: ${DOC_PREFIX}_v*.md"
    exit 1
fi

echo "找到最新草稿: $(basename "$LATEST_DRAFT")"

# 检查是否为常规版本号（不能带 _R）
if [[ "$(basename "$LATEST_DRAFT")" =~ _R[0-9]+@ ]]; then
    echo "错误: 最新草稿是临时版本（带R修订号），不能直接提交到 outputs/"
    echo "      请先执行 R转常规版本号操作"
    echo "      文件名: $(basename "$LATEST_DRAFT")"
    exit 1
fi

# 检查 outputs/ 中是否存在旧版本
OLD_OFFICIAL=$(ls "$PROJECT_DIR/outputs/${DOC_PREFIX}"_v*.md 2>/dev/null | head -1)

if [ -n "$OLD_OFFICIAL" ]; then
    echo "发现旧正式版本: $(basename "$OLD_OFFICIAL")"
    echo "移动到 history/..."
    mv "$OLD_OFFICIAL" "$PROJECT_DIR/history/"
    echo "  已移动: $(basename "$OLD_OFFICIAL") -> history/"
fi

# 复制最新草稿到 outputs/
echo "复制最新草稿到 outputs/..."
cp "$LATEST_DRAFT" "$PROJECT_DIR/outputs/"
echo "  已复制: $(basename "$LATEST_DRAFT") -> outputs/"

echo ""
echo "========================================"
echo "转正式版本完成！"
echo ""
echo "当前正式版本: $(basename "$LATEST_DRAFT")"
echo "位置: $PROJECT_DIR/outputs/$(basename "$LATEST_DRAFT")"
if [ -n "$OLD_OFFICIAL" ]; then
    echo "旧版本已归档: $PROJECT_DIR/history/$(basename "$OLD_OFFICIAL")"
fi
