# 长期工作规范

## Git 推送规范
- 功能开发完成后，先在本地 commit
- 必须等用户口头确认满意后，再 `git push` 推送到 GitHub
- 不要在用户未确认前主动 push

## 版本号规范
- 每次功能改动时必须同步更新 `__version__`（phoo.py L118）
- 语义化版本：主版本.次版本.修订号（如 2.1.0）
- 新功能 → 升次版本号；Bug 修复 → 升修订号

## 项目背景
- 项目：Phoo（图片/视频分类工具，tkinter GUI）
- 仓库：https://github.com/YZH0916/ASD-image-classifier （私有）
- 分支：phoo-refactor（唯一分支，已设为 GitHub 默认分支，master 已删除）
- 本地路径：d:\workbuddy\WB project\WB009asd-\
- 入口文件：phoo.py
- GitHub 账号：YZH0916（已通过 gh 登录）
- 当前版本：v2.2.6
