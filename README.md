# Phoo - 键盘驱动的文件分类工具

[English](README_EN.md) | [日本語](README_JP.md)

> 只需按一下键盘，文件就分类好了！

## 关于 Phoo

Phoo 最初是受到 **Slidebox**（早期 Android/iOS 上的经典图片管理 App）的启发——用最少的操作完成文件分类。

本项目 fork 并大幅重构自 [ASD-image-classifier-Python](https://github.com/RxinnotRstar/ASD-image-classifier-Python)，在原版基础上增加了诸多实用功能：
- 动态照片（Motion Photo/Live Photo）支持
- 文件查重、日期自动修正
- 现代化 UI 改进
- 等等...

**⚠️ 免责声明**：本项目是纯 vibe coding（即兴编程）的产物，作为程序员的第一个正式项目，代码中难免有诸多外行之处，还请多多包涵，欢迎 Issue 和 PR！

---

Phoo 是一个基于 Python 的文件分类工具，通过快捷键将图片、视频、Flash 文件快速归入对应文件夹，大幅提升整理效率。

## 功能特点

- **快捷键分类**：自定义快捷键，一键将文件分入对应文件夹（支持任意数量分类）
- **多格式支持**：图片（JPG/PNG/GIF/BMP/TIFF/ICO）、视频（MP4/AVI/MOV/WMV/FLV/MKV）、Flash（SWF）
- **复制/移动模式**：默认复制模式（安全保留原文件），可切换移动模式
- **视频预览**：自动提取视频首帧作为缩略图预览（需 opencv-python）
- **文件信息展示**：预览区右上角显示文件类型和拍摄日期（EXIF > 文件名解析 > 文件时间）
- **智能日期识别**：支持主流手机/APP命名格式（IMG_、VID_、Screenshot、mmexport、时间戳等）
- **撤销操作**：Ctrl+Z 撤销，支持连续撤销（重启后失效）
- **删除文件**：Delete 键删除当前文件（带确认对话框）
- **跳过浏览**：W 键跳过当前文件，可循环浏览
- **排序方式**：按名称、时间、大小排序，支持正序/倒序
- **子文件夹扫描**：可选是否包含子目录
- **配置持久化**：自动保存配置，下次启动无需重新设置
- **重名保护**：自动重名处理，避免文件覆盖

## 快速开始

### 环境要求

- Python 3.7+
- Windows / macOS / Linux

### 安装依赖

```bash
pip install pillow pywin32
```

> 可选：安装 `opencv-python` 以启用视频缩略图预览
> ```bash
> pip install opencv-python
> ```

### 运行

```bash
python phoo.py
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `1` `2` `3` ... | 将当前文件分类到对应文件夹 |
| `W` | 跳过当前文件，查看下一个 |
| `Delete` | 删除当前文件（带确认） |
| `Ctrl+Z` | 撤销上一次操作 |
| `Tab` | 切换复制/移动模式 |

> 快捷键可通过设置面板自定义。

## 使用教程

### 1. 设置输入文件夹
- 点击【浏览...】选择要处理的文件夹
- 勾选【包含子文件夹】可扫描所有子目录

### 2. 设置输出文件夹
- 为每个分类设置目标文件夹，至少需要 2 个
- 可自定义每个分类对应的快捷键

### 3. 开始分类
- 按下对应快捷键，文件自动进入目标文件夹
- 不小心按错？Ctrl+Z 撤销即可
- 不想分类的文件按 W 跳过，按 Delete 可直接删除

### 4. 其他功能
- 双击预览图片可用默认程序打开
- 排序选项支持按时间、大小、名称排序

## 打包为 EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed phoo.py
```

打包后的 EXE 文件生成在 `dist/` 目录中。

## 技术栈

- Python 3
- Tkinter（GUI）
- Pillow（图片处理 + EXIF 读取）
- OpenCV（可选，视频缩略图）

## 许可证

[MIT License](LICENSE)

## 灵感与致谢

- **Slidebox**：项目最初的灵感来源
- **[RxinnotRstar](https://github.com/RxinnotRstar)**：感谢提供的原始框架和思路，参见 [ASD-image-classifier-Python](https://github.com/RxinnotRstar/ASD-image-classifier-Python)
- **[YZH0916](https://github.com/YZH0916)**：现任维护者

⚠️ 作为非科班出身的第一个项目，代码质量和使用体验方面难免有诸多不足，如有建议欢迎提出！
