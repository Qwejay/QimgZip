import os
import sys
import json
import platform
import subprocess
import concurrent.futures

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget, QLabel, QComboBox, QHBoxLayout, QFrame, 
                               QStackedLayout, QFileDialog, QLineEdit, QScrollArea, 
                               QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMenu, QGraphicsOpacityEffect, QSpinBox, 
                               QAbstractItemView, QCheckBox, QListWidget, QSlider, 
                               QStackedWidget, QFileIconProvider, QLayout)
from PySide6.QtCore import (Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, 
                            QTimer, QParallelAnimationGroup, QFileInfo)
from PySide6.QtGui import (QDragEnterEvent, QDropEvent, QFont, QColor, QIcon, QAction)
from PIL import Image, ImageSequence

__app_name__ = "QimgZip"
__version__ = "1.0.1"
__author__ = "QwejayHuang"
__company__ = "QwejayHuang"
__description__ = "极简风格图像批量压缩工具"


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def get_data_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


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
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame { background-color: #f8f9fa; border: 2px dashed #ced4da; border-radius: 12px; }
            QFrame:hover { background-color: #e9ecef; border: 2px dashed #adb5bd; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.icon_label.setStyleSheet('QLabel { background: transparent; color: #adb5bd; font-size: 72px; border: none; padding-bottom: 0px; font-family: "Segoe UI Emoji", "Apple Color Emoji"; }')
        self._set_default_icon()
        layout.addWidget(self.icon_label)

        self.label = QLabel("将图片/文件夹拖拽至此处\n或 点击选择文件")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.setStyleSheet("QLabel { background: transparent; color: #495057; font-size: 15px; font-weight: bold; border: none; padding: 10px; }")
        layout.addWidget(self.label)

        self.sub_label = QLabel("支持 JPG / PNG / WebP / GIF 等主流格式")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.sub_label.setStyleSheet("QLabel { background: transparent; color: #868e96; font-size: 12px; border: none; padding-bottom: 10px; }")
        layout.addWidget(self.sub_label)
        self.setLayout(layout)

    def _set_default_icon(self):
        svg_path = get_resource_path("icon.svg")
        ico_path = get_resource_path("icon.ico")
        
        if os.path.exists(svg_path):
            self.icon_label.setPixmap(QIcon(svg_path).pixmap(80, 80))
        elif os.path.exists(ico_path):
            self.icon_label.setPixmap(QIcon(ico_path).pixmap(80, 80))
        elif getattr(sys, 'frozen', False):
            provider = QFileIconProvider()
            exe_icon = provider.icon(QFileInfo(sys.executable))
            if not exe_icon.isNull():
                self.icon_label.setPixmap(exe_icon.pixmap(80, 80))
            else:
                self.icon_label.clear()
                self.icon_label.setText("📦")
        else:
            self.icon_label.clear()
            self.icon_label.setText("📦")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QFrame { background-color: #e7f5ff; border: 2px dashed #339af0; border-radius: 12px; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("QFrame { background-color: #f8f9fa; border: 2px dashed #ced4da; border-radius: 12px; } QFrame:hover { background-color: #e9ecef; border: 2px dashed #adb5bd; }")

    def dropEvent(self, event: QDropEvent):
        self.dragLeaveEvent(event)
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path): files.append(path)
            elif os.path.isdir(path): files.extend(self.get_files_from_dir(path))
        if files: self._add_files_to_main(files)

    def get_files_from_dir(self, dir_path):
        files = []
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                if self.is_supported_file(file_path): files.append(file_path)
        return files

    def is_supported_file(self, file_path):
        try:
            if not os.path.exists(file_path) or not os.access(file_path, os.R_OK): return False
            ext = os.path.splitext(file_path)[1].lower()
            return ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.ico', '.tga'}
        except Exception: 
            return False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = QFileDialog()
            dialog.setWindowTitle("选择图像文件")
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("图像文件 (*.jpg *.jpeg *.png *.webp *.gif *.bmp *.tiff);;所有文件 (*.*)")
            if dialog.exec():
                files = []
                for path in dialog.selectedFiles():
                    if os.path.isfile(path): files.append(path)
                    elif os.path.isdir(path): files.extend(self.get_files_from_dir(path))
                if files: self._add_files_to_main(files)

    def _add_files_to_main(self, files):
        main_window = self.window()
        if isinstance(main_window, MainWindow):
            main_window.add_files(files)
            self.label.setText(f"已就绪：{len(main_window.files)} 个文件")
            self.sub_label.setText("可继续拖拽添加，或点击「开始压缩」")

    def show_success(self, count, saved_mb):
        self.icon_label.clear()
        self.icon_label.setText("✅")
        msg = f"压缩完成！共 {count} 个文件，节省 {saved_mb:.2f} MB" if saved_mb > 0 else f"压缩完成！共 {count} 个文件"
        self.label.setText(msg)
        self.label.setStyleSheet("QLabel { background: transparent; color: #2b8a3e; font-size: 15px; font-weight: bold; border: none; padding: 10px; }")
        self.sub_label.setText("拖拽新文件以继续")
        QTimer.singleShot(4000, self.reset_label)

    def reset_label(self):
        self._set_default_icon()
        self.label.setText("将图片/文件夹拖拽至此处\n或 点击选择文件")
        self.label.setStyleSheet("QLabel { background: transparent; color: #495057; font-size: 15px; font-weight: bold; border: none; padding: 10px; }")
        self.sub_label.setText("支持 JPG / PNG / WebP / GIF 等主流格式")


class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        self.animation_group = QParallelAnimationGroup()
        self.pos_anim = QPropertyAnimation(self, b"geometry")
        self.pos_anim.setDuration(150)
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.op_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.op_anim.setDuration(200)
        self.is_hovered = False

    def enterEvent(self, event):
        if not self.is_hovered and self.isEnabled():
            self.is_hovered = True
            geo = self.geometry()
            self.pos_anim.setStartValue(geo)
            self.pos_anim.setEndValue(geo.adjusted(0, -2, 0, -2))
            self.op_anim.setStartValue(1.0)
            self.op_anim.setEndValue(0.85)
            self.animation_group.start()

    def leaveEvent(self, event):
        if self.is_hovered:
            self.is_hovered = False
            geo = self.geometry()
            self.pos_anim.setStartValue(geo)
            self.pos_anim.setEndValue(geo.adjusted(0, 2, 0, 2))
            self.op_anim.setStartValue(0.85)
            self.op_anim.setEndValue(1.0)
            self.animation_group.start()


class SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._is_loading = False
        self.ui_refs = {}
        
        self.PRESETS = {
            "原生画质 (微损)": {
                "resize_mode": "不调整", "max_long_side": 2560, "scale_ratio": 100,
                "resample_algo": "Lanczos (高质量)", "strip_exif": False,
                "jpg_quality": 85, "jpg_subsampling": "4:4:4 (高画质)",
                "png_compress_level": 9, "png_quantize": False, "png_colors": 256,
                "webp_mode": "有损压缩", "webp_quality": 85, "webp_method": 4, "gif_colors": 256
            },
            "均衡推荐 (常用)": {
                "resize_mode": "限制长边", "max_long_side": 2560, "scale_ratio": 100,
                "resample_algo": "Lanczos (高质量)", "strip_exif": True,
                "jpg_quality": 75, "jpg_subsampling": "4:2:0 (较小体积)",
                "png_compress_level": 9, "png_quantize": False, "png_colors": 256,
                "webp_mode": "有损压缩", "webp_quality": 75, "webp_method": 4, "gif_colors": 128
            },
            "极致压缩 (体积优先)": {
                "resize_mode": "限制长边", "max_long_side": 1920, "scale_ratio": 100,
                "resample_algo": "Bicubic (平滑)", "strip_exif": True,
                "jpg_quality": 60, "jpg_subsampling": "4:2:0 (较小体积)",
                "png_compress_level": 9, "png_quantize": True, "png_colors": 128,
                "webp_mode": "有损压缩", "webp_quality": 60, "webp_method": 6, "gif_colors": 64
            }
        }
        
        self.default_settings = {
            "compress_mode": "均衡推荐 (常用)",
            "output_mode": "覆盖原图", "output_suffix": "_压缩", "output_dir": ""
        }
        self.default_settings.update(self.PRESETS["均衡推荐 (常用)"])
        self.settings = self.load_settings()
        
        self.setObjectName("settings_panel_bg")

        self.setStyleSheet("""
            #settings_panel_bg { background-color: #fdfdfd; font-family: "Microsoft YaHei", sans-serif; }
            QLabel { color: #343a40; font-size: 13px; }
            QLabel.title { font-size: 15px; font-weight: bold; color: #212529; margin-bottom: 5px; }
            QLabel.desc { color: #868e96; font-size: 12px; }
            
            QListWidget { background: #f8f9fa; border: none; border-right: 1px solid #e9ecef; outline: none; }
            QListWidget::item { padding: 12px 10px; color: #495057; border-radius: 6px; margin: 2px 6px; font-size: 13px; }
            QListWidget::item:hover { background-color: #e9ecef; }
            QListWidget::item:selected { background-color: #e7f5ff; color: #1864ab; font-weight: bold; }
            
            QFrame.card { background: white; border: 1px solid #e9ecef; border-radius: 8px; }
            
            QLineEdit, QSpinBox { color: #495057; font-size: 13px; padding: 5px 8px; border: 1px solid #ced4da; border-radius: 6px; background: white; min-height: 20px; }
            QLineEdit:hover, QSpinBox:hover { border-color: #adb5bd; }
            QLineEdit:focus, QSpinBox:focus { border-color: #339af0; }
            QSpinBox:disabled, QLineEdit:disabled { background: #f1f3f5; color: #adb5bd; }
            
            QComboBox { color: #495057; font-size: 13px; }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #495057;
                selection-background-color: #e7f5ff;
                selection-color: #1864ab;
                border: 1px solid #ced4da;
                outline: none;
            }
            
            QCheckBox { font-size: 13px; color: #495057; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #ced4da; border-radius: 4px; background: white; }
            QCheckBox::indicator:checked { background: #339af0; border-color: #339af0; }
            
            QSlider::groove:horizontal { border-radius: 2px; height: 4px; background: #e9ecef; }
            QSlider::handle:horizontal { background: #339af0; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
            QSlider::handle:horizontal:hover { background: #228be6; transform: scale(1.1); }
            QSlider::sub-page:horizontal { background: #339af0; border-radius: 2px; }
        """)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(130)
        self.nav_list.addItem("🚀 压缩策略")
        self.nav_list.addItem("📏 尺寸调整")
        self.nav_list.addItem("🖼️ 图片格式")
        self.nav_list.addItem("📁 输出设置")
        self.nav_list.setCurrentRow(0)
        main_layout.addWidget(self.nav_list)

        # 右侧内容区
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(12)

        self.stack = QStackedWidget()
        
        # --- Page 1: 策略 ---
        page_strategy = QWidget()
        l_strat = QVBoxLayout(page_strategy)
        l_strat.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._add_card(l_strat, "预设模式", "快速选择适合的压缩强度配置", [
            self._create_row("压缩策略:", self._create_combo("compress_mode", ["均衡推荐 (常用)", "原生画质 (微损)", "极致压缩 (体积优先)", "自定义"], self._on_preset_changed))
        ])
        self._add_card(l_strat, "通用处理", "跨格式的通用优化配置", [
            self._create_row(self._create_checkbox("strip_exif", "剥离 EXIF 等元数据信息 (可节省一定体积)"), None)
        ])
        self.stack.addWidget(page_strategy)

        # --- Page 2: 尺寸 ---
        page_resize = QWidget()
        l_resize = QVBoxLayout(page_resize)
        l_resize.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._add_card(l_resize, "尺寸与缩放", "缩小超大分辨率图片是减小体积的最有效手段", [
            self._create_row("缩放模式:", self._create_combo("resize_mode", ["不调整", "限制长边", "按比例缩放"], self._on_resize_mode_changed)),
            self._create_row("最大长边 (px):", self._create_spin("max_long_side", 100, 8000, " px"), "row_max_side"),
            self._create_row("缩放比例 (%):", self._create_spin("scale_ratio", 1, 100, " %"), "row_scale_ratio"),
            self._create_row("插值算法:", self._create_combo("resample_algo", ["Lanczos (高质量)", "Bicubic (平滑)", "Nearest (快速)"]))
        ])
        self.stack.addWidget(page_resize)

        # --- Page 3: 格式 ---
        page_format = QWidget()
        l_fmt = QVBoxLayout(page_format)
        l_fmt.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        fmt_content = QWidget()
        fmt_l = QVBoxLayout(fmt_content)
        fmt_l.setContentsMargins(0,0,0,0)

        self._add_card(fmt_l, "JPEG 设置", None, [
            self._create_slider_row("压缩质量:", "jpg_quality"),
            self._create_row("色度采样:", self._create_combo("jpg_subsampling", ["4:4:4 (高画质)", "4:2:0 (较小体积)"]))
        ])
        self._add_card(fmt_l, "PNG 设置", None, [
            self._create_row(self._create_checkbox("png_quantize", "启用颜色量化 (转为索引色，大幅减小体积)", self._on_png_q_changed), None),
            self._create_row("最大颜色数:", self._create_combo("png_colors", ["256", "128", "64"]), "row_png_colors"),
            self._create_row("压缩努力度:", self._create_spin("png_compress_level", 1, 9, " 级"))
        ])
        self._add_card(fmt_l, "WebP & GIF 设置", None, [
            self._create_row("WebP 模式:", self._create_combo("webp_mode", ["有损压缩", "无损压缩"], self._on_webp_mode_changed)),
            self._create_slider_row("WebP 质量:", "webp_quality", "row_webp_quality"),
            self._create_row("WebP 编码复杂度:", self._create_spin("webp_method", 0, 6, " (0最快-6最小)")),
            self._create_row("GIF 色彩数:", self._create_combo("gif_colors", ["256", "128", "64", "32"]))
        ])
        scroll.setWidget(fmt_content)
        l_fmt.addWidget(scroll)
        self.stack.addWidget(page_format)

        # --- Page 4: 输出 ---
        page_out = QWidget()
        l_out = QVBoxLayout(page_out)
        l_out.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        dir_layout = QHBoxLayout()
        self.ui_refs["output_dir"] = QLineEdit()
        self.ui_refs["output_dir"].setPlaceholderText("选择或输入绝对路径...")
        btn_browse = QPushButton("浏览...")
        btn_browse.setStyleSheet("QPushButton { background: #f8f9fa; border: 1px solid #ced4da; border-radius: 6px; padding: 4px 12px; } QPushButton:hover{background: #e9ecef;}")
        btn_browse.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.ui_refs["output_dir"])
        dir_layout.addWidget(btn_browse)
        
        self._add_card(l_out, "保存位置", "定义压缩后文件的存储方式", [
            self._create_row("输出模式:", self._create_combo("output_mode", ["覆盖原图", "追加后缀", "输出到指定文件夹"], self._on_out_mode_changed)),
            self._create_row("文件后缀:", self._create_lineedit("output_suffix", "_压缩版"), "row_out_suffix"),
            self._create_row("目标文件夹:", dir_layout, "row_out_dir")
        ])
        self.stack.addWidget(page_out)

        right_layout.addWidget(self.stack)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_style = "QPushButton { background: #e9ecef; color: #495057; border: none; padding: 7px 18px; border-radius: 6px; font-weight: bold; } QPushButton:hover { background: #dee2e6; }"
        btn_primary = "QPushButton { background: #339af0; color: white; border: none; padding: 7px 25px; border-radius: 6px; font-weight: bold; } QPushButton:hover { background: #228be6; }"

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(btn_style)
        cancel_btn.clicked.connect(self.return_to_main)
        
        save_btn = QPushButton("保存设置")
        save_btn.setStyleSheet(btn_primary)
        save_btn.clicked.connect(self.save_settings)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        right_layout.addLayout(btn_layout)

        main_layout.addWidget(right_container, stretch=1)
        
        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self._sync_ui_to_settings()

    def _add_card(self, layout, title, desc, rows):
        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(15, 15, 15, 15)
        
        tl = QLabel(title)
        tl.setProperty("class", "title")
        cl.addWidget(tl)
        
        if desc:
            dl = QLabel(desc)
            dl.setProperty("class", "desc")
            cl.addWidget(dl)
            cl.addSpacing(8)
            
        for row, name in rows:
            if isinstance(row, QWidget):
                cl.addWidget(row)
                if name: self.ui_refs[name] = row
            elif isinstance(row, QLayout):
                cl.addLayout(row)
                if name: self.ui_refs[name] = row
        layout.addWidget(card)

    def _create_row(self, label_text, widget_or_layout, ref_name=None):
        if isinstance(label_text, QWidget):
            layout = QHBoxLayout()
            layout.addWidget(label_text)
            layout.addStretch()
            w = QWidget()
            w.setLayout(layout)
            return w, ref_name
            
        layout = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(100)
        layout.addWidget(lbl)
        if isinstance(widget_or_layout, QWidget): layout.addWidget(widget_or_layout)
        else: layout.addLayout(widget_or_layout)
        layout.addStretch()
        w = QWidget()
        w.setLayout(layout)
        return w, ref_name

    def _create_slider_row(self, label_text, key, ref_name=None):
        layout = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(100)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(1, 100)
        slider.setFixedWidth(120)
        
        spin = QSpinBox()
        spin.setRange(1, 100)
        spin.setSuffix(" %")
        spin.setFixedWidth(65)
        
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        
        self.ui_refs[key] = spin
        self.ui_refs[f"{key}_slider"] = slider
        slider.valueChanged.connect(self._mark_custom)
        
        layout.addWidget(lbl)
        layout.addWidget(slider)
        layout.addSpacing(8)
        layout.addWidget(spin)
        layout.addStretch()
        w = QWidget()
        w.setLayout(layout)
        return w, ref_name

    def _create_combo(self, key, items, callback=None):
        cb = QComboBox()
        cb.addItems(items)
        self.ui_refs[key] = cb
        if callback: cb.currentTextChanged.connect(callback)
        if key != "compress_mode":
            cb.currentTextChanged.connect(self._mark_custom)
        return cb

    def _create_spin(self, key, min_val, max_val, suffix=""):
        sb = QSpinBox()
        sb.setRange(min_val, max_val)
        sb.setSuffix(suffix)
        self.ui_refs[key] = sb
        sb.valueChanged.connect(self._mark_custom)
        return sb

    def _create_checkbox(self, key, text, callback=None):
        cb = QCheckBox(text)
        self.ui_refs[key] = cb
        if callback: cb.toggled.connect(callback)
        cb.toggled.connect(self._mark_custom)
        return cb
        
    def _create_lineedit(self, key, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        self.ui_refs[key] = le
        le.textChanged.connect(self._mark_custom)
        return le

    def _mark_custom(self):
        if self._is_loading: return
        cb = self.ui_refs["compress_mode"]
        if cb.currentText() != "自定义":
            self._is_loading = True
            cb.setCurrentText("自定义")
            self._is_loading = False

    def _on_preset_changed(self, mode):
        if self._is_loading or mode == "自定义": return
        if mode in self.PRESETS:
            self._is_loading = True
            preset = self.PRESETS[mode]
            self.settings.update(preset)
            self.settings["compress_mode"] = mode
            self._sync_ui_to_settings()
            self._is_loading = False

    def _on_resize_mode_changed(self, mode):
        self.ui_refs["row_max_side"].setVisible(mode == "限制长边")
        self.ui_refs["row_scale_ratio"].setVisible(mode == "按比例缩放")

    def _on_png_q_changed(self, checked):
        self.ui_refs["row_png_colors"].setVisible(checked)
        
    def _on_webp_mode_changed(self, mode):
        self.ui_refs["row_webp_quality"].setVisible(mode == "有损压缩")

    def _on_out_mode_changed(self, mode):
        self.ui_refs["row_out_suffix"].setVisible(mode == "追加后缀")
        self.ui_refs["row_out_dir"].setVisible(mode == "输出到指定文件夹")
        
    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if d: 
            self.ui_refs["output_dir"].setText(d)
            self._mark_custom()

    def _sync_ui_to_settings(self):
        self._is_loading = True
        s = self.settings
        
        self.ui_refs["compress_mode"].setCurrentText(s.get("compress_mode", "均衡推荐 (常用)"))
        self.ui_refs["strip_exif"].setChecked(s.get("strip_exif", True))
        
        self.ui_refs["resize_mode"].setCurrentText(s.get("resize_mode", "限制长边"))
        self.ui_refs["max_long_side"].setValue(s.get("max_long_side", 1920))
        self.ui_refs["scale_ratio"].setValue(s.get("scale_ratio", 100))
        self.ui_refs["resample_algo"].setCurrentText(s.get("resample_algo", "Lanczos (高质量)"))
        
        self.ui_refs["jpg_quality"].setValue(s.get("jpg_quality", 80))
        self.ui_refs["jpg_quality_slider"].setValue(s.get("jpg_quality", 80))
        self.ui_refs["jpg_subsampling"].setCurrentText(s.get("jpg_subsampling", "4:2:0 (较小体积)"))
        
        self.ui_refs["png_quantize"].setChecked(s.get("png_quantize", False))
        self.ui_refs["png_colors"].setCurrentText(str(s.get("png_colors", 256)))
        self.ui_refs["png_compress_level"].setValue(s.get("png_compress_level", 9))
        
        self.ui_refs["webp_mode"].setCurrentText(s.get("webp_mode", "有损压缩"))
        self.ui_refs["webp_quality"].setValue(s.get("webp_quality", 80))
        self.ui_refs["webp_quality_slider"].setValue(s.get("webp_quality", 80))
        self.ui_refs["webp_method"].setValue(s.get("webp_method", 4))
        
        self.ui_refs["gif_colors"].setCurrentText(str(s.get("gif_colors", 128)))
        
        self.ui_refs["output_mode"].setCurrentText(s.get("output_mode", "追加后缀"))
        self.ui_refs["output_suffix"].setText(s.get("output_suffix", "_压缩版"))
        self.ui_refs["output_dir"].setText(s.get("output_dir", ""))
        
        self._on_resize_mode_changed(s.get("resize_mode", "限制长边"))
        self._on_png_q_changed(s.get("png_quantize", False))
        self._on_webp_mode_changed(s.get("webp_mode", "有损压缩"))
        self._on_out_mode_changed(s.get("output_mode", "追加后缀"))
        
        self._is_loading = False

    def load_settings(self):
        try:
            p = get_data_path("settings.json")
            if not os.path.exists(p): return self.default_settings.copy()
            with open(p, "r", encoding="utf-8") as f: s = json.load(f)
            for k, v in self.default_settings.items():
                if k not in s: s[k] = v
            return s
        except Exception: 
            return self.default_settings.copy()

    def save_settings(self):
        s = self.settings
        s["compress_mode"] = self.ui_refs["compress_mode"].currentText()
        s["strip_exif"] = self.ui_refs["strip_exif"].isChecked()
        s["resize_mode"] = self.ui_refs["resize_mode"].currentText()
        s["max_long_side"] = self.ui_refs["max_long_side"].value()
        s["scale_ratio"] = self.ui_refs["scale_ratio"].value()
        s["resample_algo"] = self.ui_refs["resample_algo"].currentText()
        
        s["jpg_quality"] = self.ui_refs["jpg_quality"].value()
        s["jpg_subsampling"] = self.ui_refs["jpg_subsampling"].currentText()
        
        s["png_quantize"] = self.ui_refs["png_quantize"].isChecked()
        s["png_colors"] = int(self.ui_refs["png_colors"].currentText())
        s["png_compress_level"] = self.ui_refs["png_compress_level"].value()
        
        s["webp_mode"] = self.ui_refs["webp_mode"].currentText()
        s["webp_quality"] = self.ui_refs["webp_quality"].value()
        s["webp_method"] = self.ui_refs["webp_method"].value()
        
        s["gif_colors"] = int(self.ui_refs["gif_colors"].currentText())
        
        s["output_mode"] = self.ui_refs["output_mode"].currentText()
        s["output_suffix"] = self.ui_refs["output_suffix"].text()
        s["output_dir"] = self.ui_refs["output_dir"].text()

        try:
            with open(get_data_path("settings.json"), "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False, indent=4)
            if isinstance(self.parent, MainWindow):
                self.parent.settings = self.settings
            self.return_to_main()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败: {str(e)}")

    def return_to_main(self):
        if isinstance(self.parent, MainWindow):
            self.parent.show_main_panel()


class CompressWorker(QThread):
    progress = Signal(str, str, float, float)
    finished = Signal(int, float)

    def __init__(self, files, settings):
        super().__init__()
        self.files = files.copy()
        self.settings = settings
        self.success_count = 0
        self.total_saved = 0.0
        self._is_running = True

    def run(self):
        max_workers = os.cpu_count() or 4
        
        if self.settings.get("output_mode") == "输出到指定文件夹":
            out_dir = self.settings.get("output_dir", "")
            if out_dir and not os.path.exists(out_dir):
                try: os.makedirs(out_dir)
                except Exception: pass
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._process_single_file, fp): fp for fp in self.files if self._is_running}
            for future in concurrent.futures.as_completed(futures):
                if not self._is_running:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                fp = futures[future]
                try:
                    res_type, out_path, o_size, c_size = future.result()
                    if res_type == "success":
                        self.total_saved += (o_size - c_size) / 1024.0
                        self.success_count += 1
                        self.progress.emit(fp, out_path, float(o_size), float(c_size))
                    elif res_type == "skip":
                        self.progress.emit(fp, "skip:larger", float(o_size), float(o_size))
                    else:
                        self.progress.emit(fp, f"error:{out_path}", float(o_size), 0.0)
                except Exception as e:
                    self.progress.emit(fp, f"error:{str(e)}", 0.0, 0.0)
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
                        try: os.remove(output_path)
                        except Exception: pass
                    return ("skip", file_path, origin_size, origin_size)
            return ("error", "failed", origin_size, 0)
        except Exception as e: 
            return ("error", str(e), 0, 0)

    def _get_output_path(self, file_path, ext_override=None):
        mode = self.settings.get("output_mode", "追加后缀")
        base_dir = os.path.dirname(file_path)
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        ext = ext_override if ext_override else ext
        
        if mode == "覆盖原图": return os.path.join(base_dir, base_name + ext)
        elif mode == "输出到指定文件夹":
            out_dir = self.settings.get("output_dir", base_dir)
            if not out_dir or not os.path.exists(out_dir): out_dir = base_dir
            return os.path.join(out_dir, base_name + ext)
        else:
            suffix = self.settings.get("output_suffix", "_压缩版")
            return os.path.join(base_dir, base_name + suffix + ext)

    def _resize_image(self, img):
        mode = self.settings.get("resize_mode", "不调整")
        if mode == "不调整": return img
        
        algo_str = self.settings.get("resample_algo", "Lanczos")
        algo = Image.Resampling.LANCZOS
        if "Bicubic" in algo_str: algo = Image.Resampling.BICUBIC
        elif "Nearest" in algo_str: algo = Image.Resampling.NEAREST
        
        w, h = img.width, img.height
        new_w, new_h = w, h
        
        if mode == "限制长边":
            max_side = self.settings.get("max_long_side", 1920)
            if max(w, h) > max_side:
                ratio = max_side / float(max(w, h))
                new_w, new_h = int(w * ratio), int(h * ratio)
        elif mode == "按比例缩放":
            ratio = self.settings.get("scale_ratio", 100) / 100.0
            if ratio < 1.0:
                new_w, new_h = int(w * ratio), int(h * ratio)
                
        if new_w != w or new_h != h:
            return img.resize((new_w, new_h), algo)
        return img

    def compress_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.jpg', '.jpeg'): return self._compress_jpg(file_path)
        elif ext == '.png': return self._compress_png(file_path)
        elif ext == '.gif': return self._compress_gif(file_path)
        elif ext == '.webp': return self._compress_webp(file_path)
        elif ext in ('.bmp', '.tiff', '.tif', '.ico', '.tga'): return self._compress_generic(file_path)
        return None

    def _save_safely(self, img, input_path, output_path, **kwargs):
        if input_path == output_path:
            temp_path = input_path + ".tmp"
            img.save(temp_path, **kwargs)
            os.replace(temp_path, output_path)
        else:
            img.save(output_path, **kwargs)

    def _compress_jpg(self, input_path):
        out = self._get_output_path(input_path)
        q = self.settings.get("jpg_quality", 80)
        sub = 0 if "4:4:4" in self.settings.get("jpg_subsampling", "4:2:0") else 2
        
        with Image.open(input_path) as img:
            exif = img.info.get('exif') if not self.settings.get("strip_exif", True) else None
            img = self._resize_image(img)
            if img.mode != 'RGB': img = img.convert('RGB')
            
            kwargs = {'format': 'JPEG', 'quality': q, 'optimize': True, 'progressive': True, 'subsampling': sub}
            if exif: kwargs['exif'] = exif
            
            self._save_safely(img, input_path, out, **kwargs)
        return (out, os.path.getsize(out))

    def _compress_png(self, input_path):
        out = self._get_output_path(input_path)
        with Image.open(input_path) as img:
            img = self._resize_image(img)
            if self.settings.get("png_quantize", False):
                if img.mode != 'RGBA': img = img.convert('RGBA')
                img = img.quantize(colors=self.settings.get("png_colors", 256), method=Image.Quantize.MEDIANCUT)
                
            kwargs = {'format': 'PNG', 'optimize': True, 'compress_level': self.settings.get("png_compress_level", 9)}
            if not self.settings.get("strip_exif", True) and 'exif' in img.info:
                kwargs['exif'] = img.info['exif']
                
            self._save_safely(img, input_path, out, **kwargs)
        return (out, os.path.getsize(out))

    def _compress_gif(self, input_path):
        out = self._get_output_path(input_path)
        max_c = self.settings.get("gif_colors", 128)
        with Image.open(input_path) as img:
            frames, durations = [], []
            loop = img.info.get('loop', 0)
            for frame in ImageSequence.Iterator(img):
                f = frame.copy()
                if f.mode != 'P':
                    try: f = f.quantize(colors=max_c, method=Image.Quantize.MEDIANCUT)
                    except Exception: f = f.convert('P', palette=Image.ADAPTIVE, colors=max_c)
                frames.append(f)
                durations.append(frame.info.get('duration', 100))
                
            if len(frames) > 50 and self.settings.get("compress_mode") == "极致压缩 (体积优先)":
                frames = frames[::2]
                durations = durations[::2]
                
            kwargs = {'save_all': True, 'append_images': frames[1:] if len(frames)>1 else [], 'duration': durations, 'loop': loop, 'optimize': True}
            self._save_safely(frames[0], input_path, out, **kwargs)
        return (out, os.path.getsize(out))

    def _compress_webp(self, input_path):
        out = self._get_output_path(input_path)
        lossless = self.settings.get("webp_mode") == "无损压缩"
        q = self.settings.get("webp_quality", 80)
        m = self.settings.get("webp_method", 4)
        
        with Image.open(input_path) as img:
            img = self._resize_image(img)
            exif = img.info.get('exif') if not self.settings.get("strip_exif", True) else None
            kwargs = {'format': 'WEBP', 'lossless': lossless, 'method': m}
            if not lossless: kwargs['quality'] = q
            if exif: kwargs['exif'] = exif
            self._save_safely(img, input_path, out, **kwargs)
        return (out, os.path.getsize(out))

    def _compress_generic(self, input_path):
        out = self._get_output_path(input_path, ".png")
        with Image.open(input_path) as img:
            img = self._resize_image(img)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA' if img.mode in ('RGBA', 'LA', 'P') else 'RGB')
            kwargs = {'format': 'PNG', 'optimize': True, 'compress_level': 9}
            if self.settings.get("png_quantize", False):
                img = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            img.save(out, **kwargs)
            if self.settings.get("output_mode") == "覆盖原图" and input_path != out:
                try: os.remove(input_path)
                except Exception: pass
        return (out, os.path.getsize(out))

    def stop(self):
        self._is_running = False


class FileTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cellDoubleClicked.connect(self.on_double_click)

    def on_double_click(self, row, col):
        self.open_image(row)

    def open_image(self, row):
        if isinstance(self.parent, MainWindow):
            path = self.parent.files[row]
            try:
                if platform.system() == 'Windows': os.startfile(path)
                elif platform.system() == 'Darwin': subprocess.call(('open', path))
                else: subprocess.call(('xdg-open', path))
            except Exception: pass

    def open_folder(self, row):
        if isinstance(self.parent, MainWindow):
            path = self.parent.files[row]
            try:
                if platform.system() == 'Windows': subprocess.call(f'explorer /select,"{os.path.normpath(path)}"')
                elif platform.system() == 'Darwin': subprocess.call(['open', '-R', path])
                else: subprocess.call(['xdg-open', os.path.dirname(path)])
            except Exception: pass

    def show_context_menu(self, pos):
        menu = QMenu(self)
        row = self.rowAt(pos.y())
        if row >= 0:
            menu.addAction("打开图片", lambda: self.open_image(row))
            menu.addAction("打开所在文件夹", lambda: self.open_folder(row))
            menu.addSeparator()
            menu.addAction("移除选中项", lambda: self.remove_file(row))
            menu.addSeparator()
        menu.addAction("清空列表", self.clear_all)
        menu.exec(self.mapToGlobal(pos))

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
        self.setWindowTitle(f"{__app_name__} {__version__} —— {__author__}")

        if getattr(sys, 'frozen', False):
            provider = QFileIconProvider()
            exe_icon = provider.icon(QFileInfo(sys.executable))
            if not exe_icon.isNull(): self.setWindowIcon(exe_icon)
        else:
            svg_path = get_resource_path("icon.svg")
            ico_path = get_resource_path("icon.ico")
            if os.path.exists(svg_path):
                self.setWindowIcon(QIcon(svg_path))
            elif os.path.exists(ico_path):
                self.setWindowIcon(QIcon(ico_path))

        self.setStyleSheet("""
            QMainWindow { background-color: #ffffff; font-family: "Microsoft YaHei", sans-serif; }
            QTableWidget { border: 1px solid #dee2e6; border-radius: 8px; background-color: white; font-size: 13px; gridline-color: #f1f3f5; outline: none; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #f8f9fa; color: #495057; }
            QTableWidget::item:selected { background-color: #e7f5ff; color: #1864ab; }
            QHeaderView::section { background-color: #f8f9fa; padding: 8px; border: none; border-bottom: 1px solid #dee2e6; font-weight: bold; color: #495057; }
            QStatusBar { background-color: #f8f9fa; color: #868e96; border-top: 1px solid #dee2e6; padding: 2px; }
            QStatusBar QLabel { color: #868e96; font-size: 13px; }
            QMenu { background-color: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 25px 6px 20px; border-radius: 4px; color: #495057; }
            QMenu::item:selected { background-color: #e7f5ff; color: #1864ab; }
        """)
        
        self.action_btn_style = "QPushButton { background: #339af0; color: white; border: none; padding: 0px 16px; border-radius: 8px; font-size: 15px; min-width: 120px; min-height: 44px; font-weight: bold; } QPushButton:hover { background: #228be6; } QPushButton:pressed { background: #1c7ed6; }"
        self.stop_btn_style = "QPushButton { background: #fa5252; color: white; border: none; padding: 0px 16px; border-radius: 8px; font-size: 15px; min-width: 120px; min-height: 44px; font-weight: bold; } QPushButton:hover { background: #e03131; } QPushButton:pressed { background: #c92a2a; }"
        self.icon_btn_style = "QPushButton { background: #f8f9fa; color: #495057; border: 1px solid #dee2e6; border-radius: 8px; font-size: 18px; font-weight: bold; min-width: 44px; max-width: 44px; min-height: 44px; } QPushButton:hover { background: #e9ecef; } QPushButton:pressed { background: #dee2e6; }"

        self.files = []
        self.has_compressed = False
        self.settingsPanel = SettingsPanel(self)
        self.settings = self.settingsPanel.settings
        
        self.init_ui()

    def init_ui(self):
        self.setMinimumSize(540, 580)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.stacked_layout = QStackedLayout(central_widget)

        self.main_panel = QWidget()
        layout = QVBoxLayout(self.main_panel)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.drop_area = DropArea(self)
        self.drop_area.setMinimumHeight(180)
        layout.addWidget(self.drop_area)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        self.file_list = FileTableWidget(self)
        self.file_list.setColumnCount(5)
        self.file_list.setHorizontalHeaderLabels(["文件名", "原大小", "压缩后", "节省", "状态"])
        self.file_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.file_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.file_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.file_list.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.file_list.setColumnWidth(1, 85)
        self.file_list.setColumnWidth(2, 85)
        self.file_list.setColumnWidth(3, 75)
        self.file_list.setColumnWidth(4, 55)
        self.file_list.setMinimumHeight(200)
        self.file_list.setVisible(False)
        self.file_list.setShowGrid(False)
        self.file_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_list.verticalHeader().setVisible(False)
        self.file_list.horizontalHeaderItem(0).setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for i in range(1, 5): self.file_list.horizontalHeaderItem(i).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        list_layout.addWidget(self.file_list)

        list_container.hide()
        layout.addWidget(list_container)
        self.list_container = list_container

        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(0, 10, 0, 0)

        self.toggle_list_btn = AnimatedButton("▼")
        self.toggle_list_btn.setStyleSheet(self.icon_btn_style)
        self.toggle_list_btn.clicked.connect(self.toggle_file_list)
        button_layout.addWidget(self.toggle_list_btn)

        self.action_btn = AnimatedButton("🚀 开始压缩")
        self.action_btn.setStyleSheet(self.action_btn_style)
        self.action_btn.clicked.connect(self.toggle_action)
        button_layout.addWidget(self.action_btn)

        self.settings_btn = AnimatedButton("⚙")
        self.settings_btn.setStyleSheet(self.icon_btn_style)
        self.settings_btn.clicked.connect(self.show_settings)
        button_layout.addWidget(self.settings_btn)

        layout.addLayout(button_layout)
        
        self.stacked_layout.addWidget(self.main_panel)
        self.stacked_layout.addWidget(self.settingsPanel)
        self.stacked_layout.setCurrentWidget(self.main_panel)

        self.statusBar = self.statusBar()
        self.status_label = QLabel("")
        self.statusBar.addWidget(self.status_label)

    def toggle_file_list(self):
        if self.list_container.isVisible(): self.hide_file_list()
        else: self.show_file_list()

    def show_file_list(self, event=None):
        if not self.list_container.isVisible():
            self.list_container.show()
            self.file_list.setVisible(True)
            self.toggle_list_btn.setText("▲")
            self.update_status()
            if self.file_list.rowCount() > 0: self.file_list.scrollToBottom()

    def hide_file_list(self):
        self.list_container.hide()
        self.file_list.setVisible(False)
        self.toggle_list_btn.setText("▼")
        self.update_status()

    def show_message(self, message, duration=3000):
        if duration == 0 and "处理中" in self.status_label.text(): return
        self.status_label.setText(message)
        if duration > 0: QTimer.singleShot(duration, self.update_status)

    def update_status(self):
        if not self.files:
            self.status_label.setText("")
            return
        if len(self.files) == 1: self.status_label.setText(os.path.basename(self.files[0]))
        else: self.status_label.setText(f"就绪: {len(self.files)} 个文件")

    def _create_table_item(self, text, center=True, color=None):
        item = QTableWidgetItem(text)
        if center: item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if color: item.setForeground(QColor(color))
        return item

    def add_files(self, files):
        if self.has_compressed:
            self.clear_files()
            self.has_compressed = False

        existing = set(self.files)
        new_files = [f for f in files if f not in existing]
        if not new_files: return

        self.file_list.setUpdatesEnabled(False)
        for f in new_files:
            self.files.append(f)
            r = self.file_list.rowCount()
            self.file_list.insertRow(r)
            self.file_list.setItem(r, 0, self._create_table_item(os.path.basename(f), False))
            self.file_list.setItem(r, 1, self._create_table_item(format_size(os.path.getsize(f))))
            self.file_list.setItem(r, 2, self._create_table_item(""))
            self.file_list.setItem(r, 3, self._create_table_item(""))
            self.file_list.setItem(r, 4, self._create_table_item("待处理", color="#adb5bd"))
        self.file_list.setUpdatesEnabled(True)

        if not self.list_container.isVisible(): self.show_file_list()
        if self.file_list.isVisible(): self.file_list.scrollToBottom()
        self.update_status()

    def show_settings(self):
        self.animation = QPropertyAnimation(self.stacked_layout.currentWidget(), b"geometry")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setStartValue(self.stacked_layout.currentWidget().geometry())
        self.stacked_layout.setCurrentWidget(self.settingsPanel)
        self.animation.setEndValue(self.settingsPanel.geometry())
        self.animation.start()

    def show_main_panel(self):
        self.animation = QPropertyAnimation(self.stacked_layout.currentWidget(), b"geometry")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setStartValue(self.stacked_layout.currentWidget().geometry())
        self.stacked_layout.setCurrentWidget(self.main_panel)
        self.animation.setEndValue(self.main_panel.geometry())
        self.animation.start()

    def toggle_action(self):
        if "开始压缩" in self.action_btn.text():
            if not self.files:
                self.show_message("请先添加图像文件", 2000)
                return
            self.start_compress()
            self.action_btn.setText("⏹ 停止")
            self.action_btn.setStyleSheet(self.stop_btn_style)
        else:
            self.stop_compress()
            self.action_btn.setText("🚀 开始压缩")
            self.action_btn.setStyleSheet(self.action_btn_style)

    def start_compress(self):
        if not self.files: return
        if not self.list_container.isVisible(): self.show_file_list()
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
                    self.file_list.item(i, 4).setText("失败")
                    self.file_list.item(i, 4).setForeground(QColor("#fa5252"))
                elif result.startswith("skip"):
                    self.file_list.item(i, 2).setText(format_size(origin_size))
                    self.file_list.item(i, 3).setText("—")
                    self.file_list.item(i, 4).setText("跳过")
                    self.file_list.item(i, 4).setForeground(QColor("#adb5bd"))
                else:
                    self.file_list.item(i, 0).setText(os.path.basename(result))
                    self.file_list.item(i, 2).setText(format_size(compressed_size))
                    if origin_size > 0:
                        pct = (1 - compressed_size / origin_size) * 100
                        self.file_list.item(i, 3).setText("<0.1%" if 0 < pct < 0.1 else f"{pct:.1f}%")
                    else: self.file_list.item(i, 3).setText("—")
                    self.file_list.item(i, 4).setText("完成")
                    self.file_list.item(i, 4).setForeground(QColor("#2b8a3e"))
                self.file_list.scrollToItem(self.file_list.item(i, 0))
                break

        succ = sum(1 for i in range(self.file_list.rowCount()) if self.file_list.item(i, 4).text() == "完成")
        tot = self.file_list.rowCount()
        self.show_message(f"正在处理... ({succ}/{tot})", 0)
        self.action_btn.setText(f"⏹ 停止 ({succ}/{tot})")

    def compress_finished(self, success_count, total_saved_kb):
        self.action_btn.setText("🚀 开始压缩")
        self.action_btn.setStyleSheet(self.action_btn_style)
        if success_count > 0:
            saved_mb = total_saved_kb / 1024.0
            self.status_label.setText("")
            QTimer.singleShot(100, lambda: self.show_message(f"压缩完成！共 {success_count} 个文件，节省 {saved_mb:.2f} MB", 5000))
            self.drop_area.show_success(success_count, saved_mb)
            self.has_compressed = True
        else:
            self.show_message("未压缩任何文件", 3000)
            self.update_status()

    def clear_files(self):
        self.files.clear()
        self.file_list.setRowCount(0)
        self.drop_area.reset_label()
        self.status_label.setText("")
        self.list_container.hide()
        self.has_compressed = False
        if self.toggle_list_btn.text() == "▲": self.toggle_list_btn.setText("▼")

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            reply = QMessageBox.question(self, '确认退出', '当前正在压缩图片，确认要中断并退出吗？',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait(2000)
                event.accept()
            else: event.ignore()
        else: event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    if getattr(sys, 'frozen', False):
        provider = QFileIconProvider()
        exe_icon = provider.icon(QFileInfo(sys.executable))
        if not exe_icon.isNull():
            app.setWindowIcon(exe_icon)
    else:
        svg_path = get_resource_path("icon.svg")
        ico_path = get_resource_path("icon.ico")
        if os.path.exists(svg_path):
            app.setWindowIcon(QIcon(svg_path))
        elif os.path.exists(ico_path):
            app.setWindowIcon(QIcon(ico_path))

    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
