# 加载排版格式规范

将排版格式规范文件读取到当前会话上下文（标题层级、列表样式、表格格式等视觉呈现规则）。

## 用法

```
/load-layout [/path/to/layout-spec.md]
```

如果不提供参数，默认加载 `/home/1ding/claude/projects/specs/common/outputs` 下 C01 开头的文件。

## 执行步骤

1.   确定目标文件：
     -   如果 $ARGUMENTS 非空：使用指定路径
     -   如果 $ARGUMENTS 为空：
         -   在 `/home/1ding/claude/projects/specs/common/outputs` 目录下查找 C01 开头的文件
         -   如果找到多个，使用最新的（按文件名排序取最后一个）
         -   如果未找到，报错提示
2.   读取目标文件
3.   输出加载确认：
   ```
   [LOADED layout] {文件路径} | ~{字节数÷3.5取整} tokens
   ```

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及估算合计。

容量检查（以 200K 为基准）：
-   合计 > 120K tokens → ⚠️ 已超过 60%，谨慎继续加载
-   合计 > 160K tokens → 🔴 已超过 80%，强烈建议停止加载
