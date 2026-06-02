# QimgZip 🖼️ 

![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PyQt5](https://img.shields.io/badge/PyQt-5-orange.svg)
![Pillow](https://img.shields.io/badge/Pillow-Latest-yellow.svg)

**QimgZip** 是一款基于 Python (PyQt5 + Pillow) 开发的现代化、轻量级的高性能批量图片压缩工具。专为创作者和开发者设计，能够轻松应对数千张图片的极限并发压缩。

## ✨ 核心特性 (Features)

- 🚀 **多线程压缩**：内置多线程引擎，自动压榨多核 CPU 性能。实测拖入 3000+ 张图片及深层嵌套文件夹，UI 依然丝滑流畅，压缩快如闪电。
- 📁 **拖拽即用**：支持直接拖放单个文件、多个文件或包含复杂子目录的文件夹。
- 🎨 **全格式支持**：支持 JPG、PNG、WebP、GIF 及 BMP、TIFF 等十余种常规图像格式。
- ⚙️ **专业级自定义设置**：
  - **JPEG**: 自定义画质 (1-100)。
  - **PNG**: 提供“快速/标准/极限”三档压缩率（完美兼容带 Alpha 透明通道的 RGBA 图像减色）。
  - **WebP / GIF**: 自定义 WebP 质量及 GIF 最大色彩数。
  - **输出模式**: 支持“覆盖原图”或“追加自定义后缀”。
- 📊 **实时数据面板**：直观展示每个文件的原大小、压缩后大小、节省比例 (<0.1% 精度)，以及总节省空间。
- 🖱️ **快捷交互**：双击列表即可预览图片；支持右键菜单一键「打开所在文件夹」或「移除项」。
- 🖥️ **现代 UI 与高分屏支持**：加入平滑的悬停与切换动画，并强制开启了高 DPI 缩放，确保在 4K 屏幕上文字与界面依然清晰锐利。

## 📸 界面预览 (Screenshots)
<img width="874" height="1022" alt="image" src="https://github.com/user-attachments/assets/c246988a-ee6e-4f63-aa92-1c7d6f4450b6" />

## 🛠️ 安装与运行 (Installation & Usage)

1. **克隆仓库并运行**
2. **下载二进制文件运行**
   
## 📄 许可证 / License
- 本项目基于 MIT License 开源，允许商用、修改和分发，但请保留原作者信息。
