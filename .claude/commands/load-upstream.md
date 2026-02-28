# 加载上游关联文档

将上游文档读取到当前会话上下文。

## 用法

```
/load-upstream /path/to/upstream-file.md       # 直接指定文件
/load-upstream /path/to/project/               # 批量加载（需先 /load-target）
```

## 执行步骤

### 文件模式（参数以 .md 结尾）

1.   读取指定文件
2.   输出加载确认：
   ```
   [LOADED upstream] {文件路径} | ~{字节数÷3.5取整} tokens
   ```

### 目录模式（参数为目录路径）

1.   从会话历史找到最近一条 `[LOADED target]` 记录，获取目标文档文件名
2.   读取该目录下的 `CLAUDE.md`，在关联关系表中找到目标文档的上游文档列表
3.   按优先级（outputs/ 优先，其次 drafts/）逐一定位并读取各上游文档
4.   每加载一个文件输出一条 `[LOADED upstream]` 确认

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及估算合计。

容量检查（以 200K 为基准）：
-   合计 > 120K tokens → ⚠️ 已超过 60%，谨慎继续加载
-   合计 > 160K tokens → 🔴 已超过 80%，强烈建议停止加载
