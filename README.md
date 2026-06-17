# QimgZip 🖼️ 

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PySide6](https://img.shields.io/badge/PySide-6-1ea362.svg)
![Pillow](https://img.shields.io/badge/Pillow-Latest-yellow.svg)

**QimgZip** 是一款基于 Python (PySide6 + Pillow) 开发的现代化、轻量级的高性能批量图片压缩工具。专为创作者、前端开发者和设计师打造，不仅能轻松应对数千张图片的极限并发压缩，还提供了专业级的图像调优选项。

## ✨ 核心特性 (Features)

- 🚀 **极致并发性能**：内置多线程引擎，自动压榨多核 CPU 性能。实测拖入 5000+ 张图片及深层嵌套文件夹，UI 依然丝滑流畅，压缩快如闪电。
- 🎛️ **智能策略预设 (全新)**：
  - **原生画质 (微损)**：高采样率保留细节，适合摄影修图。
  - **均衡推荐 (常用)**：自动平衡体积与观感，适合日常建站。
  - **极致压缩 (体积优先)**：强制颜色量化与分辨率限制，专治“硬盘焦虑”。
- 📏 **专业级尺寸处理**：支持「限制最大长边」与「按比例缩放」，并提供 Lanczos / Bicubic / Nearest 多种专业插值算法，从根本上减小超大图体积。
- 🎨 **硬核格式控制**：
  - **通用设置**: 一键剥离 EXIF 元数据，彻底清理冗余体积。
  - **JPEG**: 自定义画质 (1-100)，支持 4:4:4 / 4:2:0 色度子采样控制。
  - **PNG**: 独家智能颜色量化（强制转换 256/128/64 索引色），极大幅度减小 PNG 体积。
  - **WebP / GIF**: 支持 WebP 无损/有损切换及编码复杂度调节；支持 GIF 逐帧降色优化。
- 📁 **灵活的输出管理**：不仅支持“覆盖原图”和“追加自定义后缀”，现已支持 **“输出到独立目标文件夹”**，绝不污染源文件。
- 📊 **实时数据面板**：直观展示每个文件的原大小、压缩后大小、节省比例 (<0.1% 精度)，以及总节省空间。支持双击预览、右键快速定位。
- 🖥️ **现代 UI UX**：基于 Qt6 的全新卡片式侧边栏设置界面，自带丝滑悬停与展开动画。完美支持 Windows/macOS 高分屏 (High-DPI)，界面锐利不模糊。

## 📸 界面预览 (Screenshots)

<img width="541" height="607" alt="image" src="https://github.com/user-attachments/assets/dbdadd0d-f3a6-4c32-82c4-c75c6bb99bc1" />
<img width="541" height="608" alt="image" src="https://github.com/user-attachments/assets/62c79773-d6e6-41fe-b370-0cc70c69c9cb" />
<img width="540" height="612" alt="image" src="https://github.com/user-attachments/assets/99f32b64-b9a4-466f-b008-888a7796cefd" />

## 🛠️ 安装与运行 (Installation & Usage)

### 方式一：直接运行 (推荐普通用户)
前往 [Releases 页面](../../releases) 下载最新版本的打包程序，双击即可使用，无需配置任何环境。

### 方式二：源码运行 (推荐开发者)
1. 克隆本仓库到本地：
   ```bash
   git clone https://github.com/QwejayHuang/QimgZip.git
   cd QimgZip
   
## 📄 许可证 / License
- 本项目基于 GPL-3.0 license 。
