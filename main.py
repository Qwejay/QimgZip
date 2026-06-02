import sys
import os
import json
import platform
import subprocess
import concurrent.futures
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                            QWidget, QLabel, QListWidget, QDialog, QComboBox,
                            QRadioButton, QButtonGroup, QHBoxLayout, QFrame, QStackedLayout,
                            QFileDialog, QLineEdit, QScrollArea, QSizePolicy, QGroupBox, QMessageBox, QStatusBar,
                            QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QInputDialog,
                            QGraphicsOpacityEffect, QCheckBox, QToolTip, QAction, QSlider, QSpinBox)

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QTimer, QParallelAnimationGroup
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QPalette, QColor, QIcon
from PIL import Image, ImageSequence


def format_size(size_bytes):
    if size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


class DropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 2px dashed #cccccc;
                border-radius: 10px;
            }
            QFrame:hover {
                background-color: #e8e8e8;
                border: 2px dashed #999999;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.icon_label = QLabel("🖼")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.icon_label.setStyleSheet("""
            QLabel { background: transparent; color: #999999; font-size: 48px; border: none; padding: 0px; padding-bottom: 0px; font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji"; }
        """)
        layout.addWidget(self.icon_label)

        self.label = QLabel("将图片/文件夹拖拽至此处\n或 点击选择文件")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.label.setStyleSheet("""
            QLabel { background: transparent; color: #666666; font-size: 16px; font-weight: bold; border: none; padding: 10px; }
        """)
        layout.addWidget(self.label)

        self.sub_label = QLabel("支持 JPG / PNG / WebP / GIF 等常规图像格式")
        self.sub_label.setAlignment(Qt.AlignCenter)
        self.sub_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.sub_label.setStyleSheet("""
            QLabel { background: transparent; color: #999999; font-size: 12px; border: none; padding: 0px; padding-bottom: 10px; }
        """)
        layout.addWidget(self.sub_label)
        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame { background-color: #e3f2fd; border: 2px dashed #2196F3; border-radius: 10px; }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame { background-color: #f5f5f5; border: 2px dashed #cccccc; border-radius: 10px; }
            QFrame:hover { background-color: #e8e8e8; border: 2px dashed #999999; }
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("""
            QFrame { background-color: #f5f5f5; border: 2px dashed #cccccc; border-radius: 10px; }
            QFrame:hover { background-color: #e8e8e8; border: 2px dashed #999999; }
        """)
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                files.extend(self.get_files_from_dir(path))
        if files:
            main_window = self.window()
            if isinstance(main_window, MainWindow):
                main_window.add_files(files)
                total_files = len(main_window.files)
                self.label.setText(f"已就绪：{total_files} 个文件")
                self.sub_label.setText("可继续拖拽添加，或点击「开始压缩」")

    def get_files_from_dir(self, dir_path):
        files = []
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                if self.is_supported_file(file_path):
                    files.append(file_path)
        return files

    def is_supported_file(self, file_path):
        try:
            if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
                return False
            ext = os.path.splitext(file_path)[1].lower()
            supported = {
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif',
                '.ico', '.tga', '.jp2', '.j2k', '.ppm', '.pgm', '.pbm', '.dds', '.dib'
            }
            return ext in supported
        except Exception:
            return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.open_file_dialog()

    def open_file_dialog(self):
        dialog = QFileDialog()
        dialog.setWindowTitle("选择图像文件")
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter(
            "支持的图像格式 (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tiff *.tif *.ico *.tga *.jp2 *.j2k *.ppm *.pgm *.pbm *.dds *.dib);;"
            "常用网页格式 (*.jpg *.jpeg *.png *.webp *.gif);;"
            "所有文件 (*.*)"
        )
        if dialog.exec_():
            files = []
            for path in dialog.selectedFiles():
                if os.path.isfile(path):
                    files.append(path)
                elif os.path.isdir(path):
                    files.extend(self.get_files_from_dir(path))
            if files:
                main_window = self.window()
                if isinstance(main_window, MainWindow):
                    main_window.add_files(files)
                    total_files = len(main_window.files)
                    self.label.setText(f"已就绪：{total_files} 个文件")
                    self.sub_label.setText("可继续拖拽添加，或点击「开始压缩」")

    def show_success(self, count, saved_mb):
        self.icon_label.setText("✅")
        if saved_mb > 0:
            self.label.setText(f"✓ 压缩完成：共 {count} 个文件，节省 {saved_mb:.2f} MB")
        else:
            self.label.setText(f"✓ 压缩完成：共 {count} 个文件")
        self.label.setStyleSheet("""
            QLabel { background: transparent; color: #4CAF50; font-size: 16px; font-weight: bold; border: none; padding: 10px; }
        """)
        self.sub_label.setText("拖拽新文件以继续")
        QTimer.singleShot(5000, self.reset_label)

    def reset_label(self):
        self.icon_label.setText("🖼")
        self.label.setText("将图片/文件夹拖拽至此处\n或 点击选择文件")
        self.label.setStyleSheet("""
            QLabel { background: transparent; color: #666666; font-size: 16px; font-weight: bold; border: none; padding: 10px; }
        """)
        self.sub_label.setText("支持 JPG / PNG / WebP / GIF 等常规图像格式")


class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self.animation_group = QParallelAnimationGroup()

        self.position_animation = QPropertyAnimation(self, b"geometry")
        self.position_animation.setDuration(150)
        self.position_animation.setEasingCurve(QEasingCurve.OutCubic)

        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutCubic)

        self.is_hovered = False

    def enterEvent(self, event):
        if not self.is_hovered and self.isEnabled():
            self.is_hovered = True
            current_geometry = self.geometry()
            self.position_animation.setStartValue(current_geometry)
            self.position_animation.setEndValue(current_geometry.adjusted(0, -2, 0, -2))
            self.opacity_animation.setStartValue(1.0)
            self.opacity_animation.setEndValue(0.85)
            self.animation_group.start()

    def leaveEvent(self, event):
        if self.is_hovered:
            self.is_hovered = False
            current_geometry = self.geometry()
            self.position_animation.setStartValue(current_geometry)
            self.position_animation.setEndValue(current_geometry.adjusted(0, 2, 0, 2))
            self.opacity_animation.setStartValue(0.85)
            self.opacity_animation.setEndValue(1.0)
            self.animation_group.start()


class SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.default_settings = {
            "jpg_quality": 70, "png_compress_level": 9, "gif_max_colors": 64,
            "webp_quality": 75, "output_mode": "replace", "output_suffix": "_压缩版"
        }
        self.settings = self.load_settings()
        
        self.setStyleSheet("""
            QWidget { background-color: white; }
            QLabel { color: #333333; font-size: 13px; font-weight: bold; }
            
            QComboBox { color: #333333; font-size: 13px; padding: 4px 8px; border: 1px solid #dcdcdc; border-radius: 6px; background: white; min-width: 180px; min-height: 28px; }
            QComboBox:hover { border-color: #b0b0b0; }
            QComboBox:focus { border-color: #2196F3; }
            
            QGroupBox { border: 1px solid #e0e0e0; border-radius: 8px; margin-top: 15px; padding-top: 15px; background-color: #fafafa; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 15px; top: 0px; color: #2196F3; font-weight: bold; font-size: 13px; padding: 0 5px; }
            
            QLineEdit { padding: 4px 8px; border: 1px solid #dcdcdc; border-radius: 6px; font-size: 13px; background: white; min-height: 28px; }
            QLineEdit:hover { border-color: #b0b0b0; }
            QLineEdit:focus { border-color: #2196F3; }
            
            QSpinBox { padding: 4px 8px; border: 1px solid #dcdcdc; border-radius: 6px; font-size: 13px; background: white; min-height: 28px; min-width: 100px; }
            QSpinBox:hover { border-color: #b0b0b0; }
            QSpinBox:focus { border-color: #2196F3; }
        """)
        self.init_ui()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(20, 20, 20, 20)
        outer_layout.setSpacing(15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")

        content = QWidget()
        content.setStyleSheet("background: white;")
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(5, 5, 5, 5)

        quality_group = QGroupBox("输出质量")
        quality_layout = QVBoxLayout()
        quality_layout.setSpacing(10)
        quality_layout.setContentsMargins(15, 20, 15, 15)

        jpg_layout = QHBoxLayout()
        jpg_label = QLabel("JPEG 质量")
        jpg_label.setFixedWidth(110)
        jpg_layout.addWidget(jpg_label)
        self.jpg_quality = QSpinBox()
        self.jpg_quality.setRange(1, 100)
        self.jpg_quality.setValue(self.settings.get("jpg_quality", 70))
        self.jpg_quality.setSuffix(" %")
        jpg_layout.addWidget(self.jpg_quality)
        jpg_layout.addStretch()
        quality_layout.addLayout(jpg_layout)

        png_layout = QHBoxLayout()
        png_label = QLabel("PNG 压缩率")
        png_label.setFixedWidth(110)
        png_layout.addWidget(png_label)
        self.png_compress = QComboBox()
        self.png_compress.addItems(["快速", "标准", "极限"])
        compress_map = {"快速": 1, "标准": 6, "极限": 9}
        current_level = self.settings.get("png_compress_level", 9)
        for name, level in compress_map.items():
            if level == current_level:
                self.png_compress.setCurrentText(name)
                break
        png_layout.addWidget(self.png_compress)
        png_layout.addStretch()
        quality_layout.addLayout(png_layout)

        gif_layout = QHBoxLayout()
        gif_label = QLabel("GIF 色彩数")
        gif_label.setFixedWidth(110)
        gif_layout.addWidget(gif_label)
        self.gif_colors = QComboBox()
        self.gif_colors.addItems(["32", "64", "128", "256"])
        gif_max = str(self.settings.get("gif_max_colors", 64))
        idx = self.gif_colors.findText(gif_max)
        if idx >= 0:
            self.gif_colors.setCurrentIndex(idx)
        gif_layout.addWidget(self.gif_colors)
        gif_layout.addStretch()
        quality_layout.addLayout(gif_layout)

        webp_layout = QHBoxLayout()
        webp_label = QLabel("WebP 质量")
        webp_label.setFixedWidth(110)
        webp_layout.addWidget(webp_label)
        self.webp_quality = QSpinBox()
        self.webp_quality.setRange(1, 100)
        self.webp_quality.setValue(self.settings.get("webp_quality", 75))
        self.webp_quality.setSuffix(" %")
        webp_layout.addWidget(self.webp_quality)
        webp_layout.addStretch()
        quality_layout.addLayout(webp_layout)

        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)

        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()
        output_layout.setSpacing(10)
        output_layout.setContentsMargins(15, 20, 15, 15)

        mode_layout = QHBoxLayout()
        mode_label = QLabel("保存方式")
        mode_label.setFixedWidth(110)
        mode_layout.addWidget(mode_label)
        self.output_mode = QComboBox()
        self.output_mode.addItems(["覆盖原图", "追加后缀"])
        if self.settings.get("output_mode", "replace") == "replace":
            self.output_mode.setCurrentText("覆盖原图")
        else:
            self.output_mode.setCurrentText("追加后缀")
        mode_layout.addWidget(self.output_mode)
        mode_layout.addStretch()
        output_layout.addLayout(mode_layout)

        suffix_layout = QHBoxLayout()
        suffix_label = QLabel("后缀名")
        suffix_label.setFixedWidth(110)
        suffix_layout.addWidget(suffix_label)
        self.output_suffix = QLineEdit()
        self.output_suffix.setPlaceholderText("输出文件名后缀")
        self.output_suffix.setText(self.settings.get("output_suffix", "_压缩版"))
        suffix_layout.addWidget(self.output_suffix)
        suffix_layout.addStretch()
        output_layout.addLayout(suffix_layout)

        self.output_mode.currentTextChanged.connect(self._on_output_mode_changed)
        self._on_output_mode_changed(self.output_mode.currentText())

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        
        icon_btn_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0f0f0, stop:1 #e8e8e8);
                color: #333333; border: 1px solid #e0e0e0; border-radius: 6px;
                font-size: 18px; font-weight: bold;
                min-width: 44px; max-width: 44px; 
                min-height: 44px; max-height: 44px;
                padding: 0px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e8e8e8, stop:1 #d8d8d8); border-color: #d0d0d0; }
            QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d8d8d8, stop:1 #c8c8c8); }
        """

        self.reset_btn = AnimatedButton("↺")
        self.reset_btn.setToolTip("恢复默认设置")
        self.reset_btn.setStyleSheet(icon_btn_style)
        self.reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(self.reset_btn)

        self.apply_btn = AnimatedButton("保存")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: white; border: none; padding: 0px 16px;
                border-radius: 6px; font-size: 15px; min-width: 100px; min-height: 44px; max-height: 44px; font-weight: bold;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:pressed { background: #1565C0; }
        """)
        self.apply_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.apply_btn)

        self.back_btn = AnimatedButton("↩")
        self.back_btn.setToolTip("返回")
        self.back_btn.setStyleSheet(icon_btn_style)
        self.back_btn.clicked.connect(self.return_to_main)
        btn_layout.addWidget(self.back_btn)

        outer_layout.addLayout(btn_layout)

    def _on_output_mode_changed(self, text):
        self.output_suffix.setEnabled(text == "追加后缀")
        
    def reset_to_default(self):
        self.jpg_quality.setValue(self.default_settings["jpg_quality"])
        compress_map_reverse = {1: "快速", 6: "标准", 9: "极限"}
        self.png_compress.setCurrentText(compress_map_reverse.get(self.default_settings["png_compress_level"], "极限"))
        self.gif_colors.setCurrentText(str(self.default_settings["gif_max_colors"]))
        self.webp_quality.setValue(self.default_settings["webp_quality"])
        mode = "覆盖原图" if self.default_settings["output_mode"] == "replace" else "追加后缀"
        self.output_mode.setCurrentText(mode)
        self.output_suffix.setText(self.default_settings["output_suffix"])

    def load_settings(self):
        try:
            settings_path = self._get_settings_path()
            if not os.path.exists(settings_path):
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(self.default_settings, f, ensure_ascii=False, indent=4)
                return self.default_settings.copy()
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            for key, value in self.default_settings.items():
                if key not in settings:
                    settings[key] = value
            return settings
        except Exception:
            return self.default_settings.copy()

    def _get_settings_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

    def save_settings(self):
        compress_map = {"快速": 1, "标准": 6, "极限": 9}
        png_level = compress_map.get(self.png_compress.currentText(), 9)
        output_mode_val = "replace" if self.output_mode.currentText() == "覆盖原图" else "suffix"

        self.settings = {
            "jpg_quality": self.jpg_quality.value(),
            "png_compress_level": png_level,
            "gif_max_colors": int(self.gif_colors.currentText()),
            "webp_quality": self.webp_quality.value(),
            "output_mode": output_mode_val,
            "output_suffix": self.output_suffix.text()
        }
        try:
            settings_path = self._get_settings_path()
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            if isinstance(self.parent, MainWindow):
                self.parent.settings = self.settings
            self.return_to_main()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败: {str(e)}")

    def return_to_main(self):
        if isinstance(self.parent, MainWindow):
            self.parent.show_main_panel()


class CompressWorker(QThread):
    progress = pyqtSignal(str, str, float, float)
    finished = pyqtSignal(int, float)

    def __init__(self, files, settings):
        super().__init__()
        self.files = files.copy()
        self.settings = settings
        self.success_count = 0
        self.total_saved = 0.0
        self._is_running = True

    def run(self):
        max_workers = os.cpu_count() or 4
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for file_path in self.files:
                if not self._is_running:
                    break
                futures[executor.submit(self._process_single_file, file_path)] = file_path
                
            for future in concurrent.futures.as_completed(futures):
                if not self._is_running:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                file_path = futures[future]
                try:
                    res_type, output_path, origin_size, compressed_size = future.result()
                    
                    if res_type == "success":
                        self.total_saved += (origin_size - compressed_size) / 1024.0
                        self.success_count += 1
                        self.progress.emit(file_path, output_path, float(origin_size), float(compressed_size))
                    elif res_type == "skip":
                        self.progress.emit(file_path, "skip:larger", float(origin_size), float(origin_size))
                    else:
                        self.progress.emit(file_path, f"error:{output_path}", float(origin_size), 0.0)
                except Exception as e:
                    self.progress.emit(file_path, f"error:{str(e)}", 0.0, 0.0)

        self.finished.emit(self.success_count, self.total_saved)

    def _process_single_file(self, file_path):
        try:
            origin_size = os.path.getsize(file_path)
            result = self.compress_file(file_path)

            if result:
                output_path, compressed_size = result
                if origin_size > compressed_size:
                    return ("success", output_path, origin_size, compressed_size)
                else:
                    if output_path != file_path and os.path.exists(output_path):
                        os.remove(output_path)
                    return ("skip", file_path, origin_size, origin_size)
            else:
                return ("error", "failed", origin_size, 0)
        except Exception as e:
            return ("error", str(e), 0, 0)

    def compress_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        output_path = self._get_output_path(file_path)

        try:
            if ext in ('.jpg', '.jpeg'):
                return self._compress_jpg(file_path, output_path)
            elif ext == '.png':
                return self._compress_png(file_path, output_path)
            elif ext == '.gif':
                return self._compress_gif(file_path, output_path)
            elif ext == '.webp':
                return self._compress_webp(file_path, output_path)
            elif ext in ('.bmp', '.tiff', '.tif', '.ico', '.tga', '.jp2', '.j2k', '.ppm', '.pgm', '.pbm', '.dds', '.dib'):
                return self._compress_generic(file_path, output_path)
            else:
                return None
        except Exception as e:
            print(f"压缩错误 {file_path}: {str(e)}")
            return None

    def _get_output_path(self, file_path):
        if self.settings.get("output_mode", "replace") == "replace":
            return file_path
        else:
            suffix = self.settings.get("output_suffix", "_压缩版")
            base, ext = os.path.splitext(file_path)
            return base + suffix + ext

    def _compress_jpg(self, input_path, output_path):
        quality = self.settings.get("jpg_quality", 70)
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            save_kwargs = {
                'format': 'JPEG',
                'quality': quality,
                'optimize': True,
                'progressive': True
            }
            if quality <= 80:
                save_kwargs['subsampling'] = 2 
            else:
                save_kwargs['subsampling'] = 1

            if input_path == output_path:
                temp_path = input_path + ".tmp"
                img.save(temp_path, **save_kwargs)
                os.replace(temp_path, output_path)
            else:
                img.save(output_path, **save_kwargs)

        compressed_size = os.path.getsize(output_path)
        return (output_path, compressed_size)

    def _compress_png(self, input_path, output_path):
        compress_level = self.settings.get("png_compress_level", 9)
        with Image.open(input_path) as img:
            if compress_level == 9:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                # ---------------- 核心修复点：PNG 压缩报错 ----------------
                # 指定 method=2 (Fast Octree) 来完美支持 RGBA 图像的减色压缩
                img = img.quantize(colors=256, method=2, dither=Image.Dither.FLOYDSTEINBERG)
                
            save_kwargs = {
                'format': 'PNG',
                'optimize': True,
                'compress_level': compress_level
            }

            if input_path == output_path:
                temp_path = input_path + ".tmp"
                img.save(temp_path, **save_kwargs)
                os.replace(temp_path, output_path)
            else:
                img.save(output_path, **save_kwargs)

        compressed_size = os.path.getsize(output_path)
        return (output_path, compressed_size)

    def _compress_gif(self, input_path, output_path):
        max_colors = self.settings.get("gif_max_colors", 64)
        with Image.open(input_path) as img:
            frames = []
            durations = []
            loop = img.info.get('loop', 0)

            for frame in ImageSequence.Iterator(img):
                frame_copy = frame.copy()
                if frame_copy.mode != 'P':
                    try:
                        frame_copy = frame_copy.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
                    except Exception:
                        frame_copy = frame_copy.convert('P', palette=Image.ADAPTIVE, colors=max_colors)
                elif len(frame_copy.getpalette() or []) // 3 > max_colors:
                    try:
                        frame_copy = frame_copy.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
                    except Exception:
                        pass
                frames.append(frame_copy)
                durations.append(frame.info.get('duration', 100))

            if len(frames) > 30:
                step = len(frames) / 30
                sampled = []
                sampled_dur = []
                for i in range(30):
                    idx = int(i * step)
                    sampled.append(frames[idx])
                    sampled_dur.append(durations[idx])
                frames = sampled
                durations = sampled_dur

            save_kwargs = {
                'save_all': True,
                'append_images': frames[1:] if len(frames) > 1 else [],
                'duration': durations,
                'loop': loop,
                'optimize': True
            }

            if input_path == output_path:
                temp_path = input_path + ".tmp"
                frames[0].save(temp_path, **save_kwargs)
                os.replace(temp_path, output_path)
            else:
                frames[0].save(output_path, **save_kwargs)

        compressed_size = os.path.getsize(output_path)
        return (output_path, compressed_size)

    def _compress_webp(self, input_path, output_path):
        quality = self.settings.get("webp_quality", 75)
        with Image.open(input_path) as img:
            if input_path == output_path:
                temp_path = input_path + ".tmp"
                img.save(temp_path, 'WEBP', quality=quality, method=6)
                os.replace(temp_path, output_path)
            else:
                img.save(output_path, 'WEBP', quality=quality, method=6)

        compressed_size = os.path.getsize(output_path)
        return (output_path, compressed_size)

    def _compress_generic(self, input_path, output_path):
        with Image.open(input_path) as img:
            ext = os.path.splitext(input_path)[1].lower()
            
            if ext in ('.tiff', '.tif'):
                if input_path == output_path:
                    temp_path = input_path + ".tmp"
                    img.save(temp_path, 'TIFF', compression='tiff_lzw')
                    os.replace(temp_path, output_path)
                else:
                    img.save(output_path, 'TIFF', compression='tiff_lzw')
                actual_output_path = output_path
                
            else:
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGBA' if img.mode in ('RGBA', 'LA', 'P') else 'RGB')
                
                base_out, _ = os.path.splitext(output_path)
                actual_output_path = base_out + ".png"
                
                img.save(actual_output_path, 'PNG', optimize=True, compress_level=9)
                
                is_replace_mode = self.settings.get("output_mode", "replace") == "replace"
                if is_replace_mode and input_path != actual_output_path:
                    if os.path.exists(input_path):
                        try:
                            os.remove(input_path)
                        except Exception:
                            pass

        compressed_size = os.path.getsize(actual_output_path)
        return (actual_output_path, compressed_size)

    def stop(self):
        self._is_running = False


class FileTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        # 绑定双击事件
        self.cellDoubleClicked.connect(self.on_double_click)

    def on_double_click(self, row, col):
        self.open_image(row)

    def open_image(self, row):
        if isinstance(self.parent, MainWindow):
            path = self.parent.files[row]
            try:
                if platform.system() == 'Windows':
                    os.startfile(path)
                elif platform.system() == 'Darwin':
                    subprocess.call(('open', path))
                else:
                    subprocess.call(('xdg-open', path))
            except Exception as e:
                print(f"打开图片失败: {e}")

    def open_folder(self, row):
        if isinstance(self.parent, MainWindow):
            path = self.parent.files[row]
            try:
                if platform.system() == 'Windows':
                    subprocess.call(f'explorer /select,"{os.path.normpath(path)}"')
                elif platform.system() == 'Darwin':
                    subprocess.call(['open', '-R', path])
                else:
                    subprocess.call(['xdg-open', os.path.dirname(path)])
            except Exception as e:
                print(f"打开文件夹失败: {e}")

    def show_context_menu(self, pos):
        menu = QMenu(self)

        row = self.rowAt(pos.y())
        if row >= 0:
            open_action = QAction("打开图片", self)
            open_action.triggered.connect(lambda: self.open_image(row))
            menu.addAction(open_action)

            folder_action = QAction("打开所在文件夹", self)
            folder_action.triggered.connect(lambda: self.open_folder(row))
            menu.addAction(folder_action)
            
            menu.addSeparator()

            delete_action = QAction("移除选中项", self)
            delete_action.triggered.connect(lambda: self.remove_file(row))
            menu.addAction(delete_action)
            
            menu.addSeparator()

        clear_action = QAction("清空列表", self)
        clear_action.triggered.connect(self.clear_all)
        menu.addAction(clear_action)

        menu.exec_(self.mapToGlobal(pos))

    def remove_file(self, row):
        if isinstance(self.parent, MainWindow):
            self.parent.files.pop(row)
            self.removeRow(row)
            self.parent.update_status()

    def clear_all(self):
        if isinstance(self.parent, MainWindow):
            self.parent.clear_files()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QimgZip 1.1 —— QwejayHuang")

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QMainWindow { background-color: #ffffff; }
            QTableWidget { border: 1px solid #e0e0e0; border-radius: 8px; background-color: white; font-size: 13px; gridline-color: #f5f5f5; outline: none; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #f5f5f5; }
            QTableWidget::item:selected { background-color: #e8f0fe; color: #1a73e8; outline: none; }
            QHeaderView::section { background-color: #f8f8f8; padding: 8px; border: none; border-bottom: 1px solid #e0e0e0; font-weight: bold; }
            QStatusBar { background-color: #f5f5f5; color: #666666; border-top: 1px solid #e0e0e0; padding: 5px; }
            QStatusBar QLabel { color: #666666; font-size: 14px; padding: 5px; border-radius: 4px; }
            QStatusBar QLabel:hover { background-color: #e8e8e8; }
            QMenu { background-color: white; border: 1px solid #e0e0e0; border-radius: 4px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 2px; }
            QMenu::item:selected { background-color: #e8f0fe; color: #1a73e8; }
        """)
        
        self.icon_btn_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0f0f0, stop:1 #e8e8e8);
                color: #333333; border: 1px solid #e0e0e0; border-radius: 6px;
                font-size: 18px; font-weight: bold;
                min-width: 44px; max-width: 44px; 
                min-height: 44px; max-height: 44px;
                padding: 0px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e8e8e8, stop:1 #d8d8d8); border-color: #d0d0d0; }
            QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d8d8d8, stop:1 #c8c8c8); }
        """
        
        self.action_btn_style = """
            QPushButton {
                background: #2196F3; color: white; border: none; padding: 0px 16px;
                border-radius: 6px; font-size: 15px; min-width: 100px; min-height: 44px; max-height: 44px; font-weight: bold;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:pressed { background: #1565C0; }
            QPushButton:disabled { background: #BDBDBD; color: #E0E0E0; }
        """
        
        self.stop_btn_style = """
            QPushButton {
                background: #F44336; color: white; border: none; padding: 0px 16px;
                border-radius: 6px; font-size: 15px; min-width: 100px; min-height: 44px; max-height: 44px; font-weight: bold;
            }
            QPushButton:hover { background: #D32F2F; }
            QPushButton:pressed { background: #B71C1C; }
        """

        self.files = []
        self.settings = self.load_settings()
        self.has_compressed = False
        self.init_ui()

    def init_ui(self):
        self.setMinimumSize(580, 650)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.stacked_layout = QStackedLayout(central_widget)

        self.main_panel = QWidget()
        layout = QVBoxLayout(self.main_panel)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.drop_area = DropArea(self)
        self.drop_area.setMinimumHeight(200)
        layout.addWidget(self.drop_area)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        self.file_list = FileTableWidget(self)
        self.file_list.setColumnCount(5)
        self.file_list.setHorizontalHeaderLabels(["文件名", "原大小", "压缩后", "节省", "状态"])
        self.file_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.file_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.file_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.file_list.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.file_list.setColumnWidth(1, 90)
        self.file_list.setColumnWidth(2, 90)
        self.file_list.setColumnWidth(3, 80)
        self.file_list.setColumnWidth(4, 50)
        self.file_list.setMinimumHeight(200)
        self.file_list.setVisible(False)
        self.file_list.setShowGrid(False)
        self.file_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_list.verticalHeader().setVisible(False)
        self.file_list.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.file_list.horizontalHeaderItem(1).setTextAlignment(Qt.AlignCenter)
        self.file_list.horizontalHeaderItem(2).setTextAlignment(Qt.AlignCenter)
        self.file_list.horizontalHeaderItem(3).setTextAlignment(Qt.AlignCenter)
        self.file_list.horizontalHeaderItem(4).setTextAlignment(Qt.AlignCenter)
        self.file_list.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.file_list.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        list_layout.addWidget(self.file_list)

        list_container.hide()
        layout.addWidget(list_container)
        self.list_container = list_container

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(0, 10, 0, 0)

        self.toggle_list_btn = AnimatedButton("▼")
        self.toggle_list_btn.setStyleSheet(self.icon_btn_style)
        self.toggle_list_btn.clicked.connect(self.toggle_file_list)
        button_layout.addWidget(self.toggle_list_btn)

        self.action_btn = AnimatedButton("开始压缩")
        self.action_btn.setStyleSheet(self.action_btn_style)
        self.action_btn.clicked.connect(self.toggle_action)
        button_layout.addWidget(self.action_btn)

        self.settings_btn = AnimatedButton("⚙")
        self.settings_btn.setStyleSheet(self.icon_btn_style)
        self.settings_btn.clicked.connect(self.show_settings)
        button_layout.addWidget(self.settings_btn)

        layout.addLayout(button_layout)
        self.stacked_layout.addWidget(self.main_panel)

        self.settings_panel = SettingsPanel(self)
        self.stacked_layout.addWidget(self.settings_panel)
        self.stacked_layout.setCurrentWidget(self.main_panel)

        self.statusBar = self.statusBar()
        self.status_label = QLabel("")
        self.statusBar.addWidget(self.status_label)

    def toggle_file_list(self):
        if self.list_container.isVisible():
            self.hide_file_list()
        else:
            self.show_file_list()

    def show_file_list(self, event=None):
        if not self.list_container.isVisible():
            self.list_container.show()
            self.file_list.setVisible(True)
            self.toggle_list_btn.setText("▲")
            self.update_status()
            if self.file_list.rowCount() > 0:
                self.file_list.scrollToBottom()

    def hide_file_list(self):
        self.list_container.hide()
        self.file_list.setVisible(False)
        self.toggle_list_btn.setText("▼")
        self.update_status()

    def show_message(self, message, duration=3000):
        if duration == 0 and "处理中" in self.status_label.text():
            return
        self.status_label.setText(message)
        if duration > 0:
            QTimer.singleShot(duration, self.update_status)

    def update_status(self):
        if not self.files:
            self.status_label.setText("")
            return
        latest_file = self.files[-1]
        file_name = os.path.basename(latest_file)
        if len(self.files) == 1:
            self.status_label.setText(file_name)
        else:
            self.status_label.setText(f"共 {len(self.files)} 个文件")
            if len(self.status_label.text()) > 50:
                self.status_label.setText(f"共 {len(self.files)} 个文件 - {file_name[:30]}...")

    def add_files(self, files):
        if self.has_compressed:
            self.clear_files()
            self.has_compressed = False

        existing_files = set(self.files)
        new_files = [f for f in files if f not in existing_files]
        
        if not new_files:
            return

        self.file_list.setUpdatesEnabled(False)
        
        for file_path in new_files:
            self.files.append(file_path)
            row = self.file_list.rowCount()
            self.file_list.insertRow(row)
            
            self.file_list.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            
            origin_size = os.path.getsize(file_path)
            size_item = QTableWidgetItem(format_size(origin_size))
            size_item.setTextAlignment(Qt.AlignCenter)
            self.file_list.setItem(row, 1, size_item)
            
            empty_item = QTableWidgetItem("")
            empty_item.setTextAlignment(Qt.AlignCenter)
            self.file_list.setItem(row, 2, empty_item)
            
            saved_item = QTableWidgetItem("")
            saved_item.setTextAlignment(Qt.AlignCenter)
            self.file_list.setItem(row, 3, saved_item)
            
            status_item = QTableWidgetItem("●")
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor("#9E9E9E"))
            self.file_list.setItem(row, 4, status_item)

        self.file_list.setUpdatesEnabled(True)

        if not self.list_container.isVisible():
            self.show_file_list()
            
        if self.file_list.isVisible():
            self.file_list.scrollToBottom()
        self.update_status()

    def show_settings(self):
        self.animation = QPropertyAnimation(self.stacked_layout.currentWidget(), b"geometry")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        start_geometry = self.stacked_layout.currentWidget().geometry()
        self.animation.setStartValue(start_geometry)
        self.stacked_layout.setCurrentWidget(self.settings_panel)
        end_geometry = self.settings_panel.geometry()
        self.animation.setEndValue(end_geometry)
        self.animation.start()

    def show_main_panel(self):
        self.animation = QPropertyAnimation(self.stacked_layout.currentWidget(), b"geometry")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        start_geometry = self.stacked_layout.currentWidget().geometry()
        self.animation.setStartValue(start_geometry)
        self.stacked_layout.setCurrentWidget(self.main_panel)
        end_geometry = self.main_panel.geometry()
        self.animation.setEndValue(end_geometry)
        self.animation.start()

    def toggle_action(self):
        if self.action_btn.text() in ("开始压缩", "开始"):
            if not self.files:
                self.show_message("请先添加图像文件", 2000)
                return
            self.start_compress()
            self.action_btn.setText("停止")
            self.action_btn.setStyleSheet(self.stop_btn_style)
        else:
            self.stop_compress()
            self.action_btn.setText("开始压缩")
            self.action_btn.setStyleSheet(self.action_btn_style)

    def start_compress(self):
        if not self.files:
            return
        if not self.list_container.isVisible():
            self.show_file_list()
        self.worker = CompressWorker(self.files, self.settings)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.compress_finished)
        self.worker.start()
        self.show_message("处理中...", 0)

    def stop_compress(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.worker.wait(3000)
        self.compress_finished(0, 0.0)

    def update_progress(self, file_path, result, origin_size, compressed_size):
        file_name = os.path.basename(file_path)

        for i in range(self.file_list.rowCount()):
            if self.file_list.item(i, 0).text() == file_name:
                if result.startswith("error"):
                    self.file_list.item(i, 2).setText("—")
                    self.file_list.item(i, 3).setText("—")
                    self.file_list.item(i, 4).setText("✗")
                    self.file_list.item(i, 4).setForeground(QColor("#F44336"))
                elif result.startswith("skip"):
                    self.file_list.item(i, 2).setText(format_size(origin_size))
                    self.file_list.item(i, 3).setText("—")
                    self.file_list.item(i, 4).setText("—")
                    self.file_list.item(i, 4).setForeground(QColor("#9E9E9E"))
                else:
                    self.file_list.item(i, 0).setText(os.path.basename(result))
                    self.file_list.item(i, 2).setText(format_size(compressed_size))
                    
                    if origin_size > 0:
                        pct = (1 - compressed_size / origin_size) * 100
                        if 0 < pct < 0.1:
                            self.file_list.item(i, 3).setText("<0.1%")
                        else:
                            self.file_list.item(i, 3).setText(f"{pct:.1f}%")
                    else:
                        self.file_list.item(i, 3).setText("—")
                        
                    self.file_list.item(i, 4).setText("✓")
                    self.file_list.item(i, 4).setForeground(QColor("#4CAF50"))

                self.file_list.scrollToItem(self.file_list.item(i, 0))
                break

        success_count = sum(1 for i in range(self.file_list.rowCount())
                          if self.file_list.item(i, 4).text() == "✓")
        total_count = self.file_list.rowCount()
        self.show_message(f"正在处理... ({success_count}/{total_count})", 0)
        self.action_btn.setText(f"停止 ({success_count}/{total_count})")

    def compress_finished(self, success_count, total_saved_kb):
        self.action_btn.setText("开始压缩")
        self.action_btn.setStyleSheet(self.action_btn_style)
        
        if success_count > 0:
            saved_mb = total_saved_kb / 1024.0
            self.status_label.setText("")
            QTimer.singleShot(100, lambda: self.show_message(
                f"✓ 压缩完成：共 {success_count} 个文件，节省 {saved_mb:.2f} MB", 5000))
            self.drop_area.show_success(success_count, saved_mb)
            self.has_compressed = True
        else:
            self.show_message("无文件被压缩", 3000)
            self.update_status()

    def load_settings(self):
        default_settings = {
            "jpg_quality": 70, "png_compress_level": 9, "gif_max_colors": 64,
            "webp_quality": 75, "output_mode": "replace", "output_suffix": "_压缩版"
        }
        try:
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
            if not os.path.exists(settings_path):
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(default_settings, f, ensure_ascii=False, indent=4)
                return default_settings
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            return settings
        except Exception as e:
            return default_settings

    def clear_files(self):
        self.files.clear()
        self.file_list.setRowCount(0)
        self.drop_area.reset_label()
        self.status_label.setText("")
        self.list_container.hide()
        self.has_compressed = False
        if self.toggle_list_btn.text() == "▲":
            self.toggle_list_btn.setText("▼")


if __name__ == '__main__':
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
