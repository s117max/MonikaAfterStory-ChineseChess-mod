# MonikaAfterStory-ChineseChess-mod

一个为 [Monika After Story (MAS)](https://www.monikaafterstory.com/) 制作的中国象棋小游戏模组。

这个模组为 MAS 添加了一个可游玩的中国象棋内容，包含基础界面、规则判断、对弈流程以及 AI 落子逻辑。

## 功能特性

- 在 MAS 中添加中国象棋小游戏入口
- 提供完整的中国象棋基础规则实现
- 支持与 AI 对弈
- 包含棋盘、棋子与落点高亮资源
- 使用 Ren'Py 脚本与 Python 逻辑混合实现

## 项目结构

- `header.rpy`：子模组注册、事件挂载与基础持久化变量
- `main.rpy`：主要界面、规则说明、难度选择与游戏流程入口
- `engine.rpy` / `displayable.rpy` / `ai.rpy`：游戏显示与交互逻辑
- `py/mas_xiangqi_core.py`：象棋规则、棋盘状态与合法走子判断
- `py/mas_xiangqi_ai_core.py`：AI 对弈相关逻辑
- `mod_assets/`：棋盘、棋子、高亮图片等资源文件

## 安装方法

1. 确保你已经正确安装 Monika After Story。
2. 打开 MAS 的游戏目录，并进入 `game` 文件夹。
3. 将本仓库中的文件和文件夹复制到 MAS 的 `game/Submods` 目录中。
4. 启动游戏后，在对应的小游戏入口中即可体验中国象棋内容。



## 许可证

本项目采用 [MIT License](./LICENSE) 发布。

## 说明

这是一个 MAS 模组项目仓库。
如果你计划分发、修改或二次开发本项目，请先确认你使用的相关素材、资源与依赖内容符合各自的授权要求。
