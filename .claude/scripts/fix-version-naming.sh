#!/bin/bash
# 修正 drafts 目录中文件名与修订记录不一致的问题
# 根据文件内修订记录的最后一条，调整文件名

set -e

if [ -z "$1" ]; then
    echo "用法: $0 <drafts目录路径>"
    echo "示例: $0 projects/MyProject/drafts"
    exit 1
fi

DRAFTS_DIR="$1"

if [ ! -d "$DRAFTS_DIR" ]; then
    echo "错误: 目录不存在: $DRAFTS_DIR"
    exit 1
fi

echo "开始检查和修正文件名..."
echo "========================================"

for file in "$DRAFTS_DIR"/*.md; do
    if [ ! -f "$file" ]; then
        continue
    fi

    filename=$(basename "$file")
    echo ""
    echo "检查: $filename"

    # 提取文件名中的版本号和时间戳
    if [[ "$filename" =~ ^(.+)_v([0-9]+\.[0-9]+)(@[0-9]+)\.md$ ]]; then
        prefix="${BASH_REMATCH[1]}"
        file_version="${BASH_REMATCH[2]}"
        timestamp="${BASH_REMATCH[3]}"

        # 读取文件最后的修订记录
        last_record=$(grep -E "^\| [0-9R]\." "$file" | tail -1)

        if [ -z "$last_record" ]; then
            echo "  [跳过] 未找到修订记录"
            continue
        fi

        # 提取修订记录中的版本号
        if [[ "$last_record" =~ ^\|[[:space:]]*([0-9]+\.[0-9]+|R\.[0-9]+) ]]; then
            record_version="${BASH_REMATCH[1]}"

            echo "  文件名版本: v$file_version"
            echo "  记录版本: $record_version"

            # 判断是否需要修正
            if [[ "$record_version" =~ ^R\.([0-9]+)$ ]]; then
                # 最后一条是 R.xx，需要添加 _R{修订号}
                r_num=$(printf "%02d" "$((10#${BASH_REMATCH[1]}))")
                new_filename="${prefix}_v${file_version}_R${r_num}${timestamp}.md"

                if [ "$filename" != "$new_filename" ]; then
                    echo "  [需修正] → $new_filename"
                    mv "$file" "$DRAFTS_DIR/$new_filename"
                    echo "  [已修正]"
                else
                    echo "  [OK] 文件名已正确"
                fi
            elif [[ "$record_version" =~ ^([0-9]+\.[0-9]+)$ ]]; then
                # 最后一条是常规版本号
                record_ver="${BASH_REMATCH[1]}"

                # 检查文件名是否带 _R
                if [[ "$filename" =~ _R[0-9]+@ ]]; then
                    echo "  [警告] 文件名带R但记录是常规版本号，可能需要手动检查"
                elif [ "$file_version" != "$record_ver" ]; then
                    echo "  [警告] 文件名版本号($file_version)与记录版本号($record_ver)不一致"
                else
                    echo "  [OK] 文件名已正确"
                fi
            fi
        else
            echo "  [跳过] 无法解析修订记录格式"
        fi
    else
        echo "  [跳过] 文件名格式不符合版本化命名规范"
    fi
done

echo ""
echo "========================================"
echo "检查完成！"
