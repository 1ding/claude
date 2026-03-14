#!/bin/bash
# PreToolUse hook（Skill）：skill 执行前强制触发容量检查
# 在每个 skill 执行前自动注入容量检查指令

echo "【容量检查-Skill前置检查】在执行本 skill 前必须：①扫描本对话所有[LOADED *]记录求和，加上所有[CAP DELTA]chars÷3.5，再加50K，得到已用量；②预估本 skill 将加载的文件大小（用ls -l）÷3.5，加上预估输出量；③已用+预估 > 180K（总容量200K，即剩余 < 20K），立即停止，写交接计划至 projects/{项目}/plans/交接_{文档名}_{YYYYMMDDHHmm}.md，并告知用户：新对话中输入 /session-resume {交接文件路径} 继续工作。不得跳过此步骤。"
