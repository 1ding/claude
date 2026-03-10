#!/bin/bash
# UserPromptSubmit hook：强制触发容量检查
# 每次用户提交消息时自动注入，替代 capacity-management.md 中的触发点1

echo "【容量检查-触发点1】执行任何操作前必须：①扫描本对话所有[LOADED *]记录求和，加上所有[CAP DELTA]chars÷3.5，再加50K，得到已用量；②用ls -l预估本轮待加载文件大小÷3.5；③已用+预估 > 950K，拒绝执行并告知用户。不得跳过此步骤。"
