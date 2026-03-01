# 加载语言风格规范

将语言风格与逻辑结构规范读取到当前会话上下文（语言风格、术语规范、句式要求、逻辑表达规则等）。

## 用法

```
/load-style [/path/to/style-spec.md]
```

如果不提供参数，默认加载 `/home/1ding/claude/projects/specs/common/outputs` 目录下的 C02 文件（语言风格规范）。

## 执行步骤

1.   如果 $ARGUMENTS 为空：
     -   查找 `/home/1ding/claude/projects/specs/common/outputs/C02*.md` 文件
     -   选择最新版本（按文件名排序取最后一个）
2.   如果 $ARGUMENTS 不为空：
     -   读取 $ARGUMENTS 指定的文件
3.   输出加载确认：
   ```
   [LOADED style] {文件路径} | ~{字节数÷3.5取整} tokens
   ```

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及估算合计。

容量检查（以 200K 为基准）：
-   合计 > 120K tokens → ⚠️ 已超过 60%，谨慎继续加载
-   合计 > 160K tokens → 🔴 已超过 80%，强烈建议停止加载
