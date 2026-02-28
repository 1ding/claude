#!/bin/bash
# 查找文档的最新版本
# 用法: ./find-latest-version.sh <项目路径> <文档名前缀> [drafts|outputs]

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "用法: $0 <项目路径> <文档名前缀> [drafts|outputs]"
    echo "示例: $0 projects/ClariSphere 01-战略规划 drafts"
    echo "      $0 projects/ClariSphere 01-战略规划 outputs"
    exit 1
fi

PROJECT_DIR="$1"
DOC_PREFIX="$2"
LOCATION="${3:-drafts}"  # 默认查找 drafts

if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

SEARCH_DIR="$PROJECT_DIR/$LOCATION"

if [ ! -d "$SEARCH_DIR" ]; then
    echo "错误: 目录不存在: $SEARCH_DIR"
    exit 1
fi

# 查找匹配的文件并排序（按文件名排序，最新的在最后）
LATEST=$(ls "$SEARCH_DIR/${DOC_PREFIX}"_v*.md 2>/dev/null | sort | tail -1)

if [ -z "$LATEST" ]; then
    echo "未找到匹配的文件: $SEARCH_DIR/${DOC_PREFIX}_v*.md"
    exit 1
fi

echo "$LATEST"
