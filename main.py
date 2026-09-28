import os
import sys
import json
import shutil
import platform
import subprocess
import random
import concurrent.futures

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget, QLabel, QComboBox, QHBoxLayout, QFrame, 
                               QStackedLayout, QFileDialog, QLineEdit, QScrollArea, 
                               QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMenu, QGraphicsOpacityEffect, QSpinBox, 
                               QAbstractItemView, QCheckBox, QListWidget, QSlider, 
                               QStackedWidget, QFileIconProvider, QLayout, QDialog)
from PySide6.QtCore import (Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, 
                            QTimer, QParallelAnimationGroup, QFileInfo, QPointF, QRectF, Property)
from PySide6.QtGui import (QDragEnterEvent, QDropEvent, QFont, QColor, QIcon,
                           QPainter, QPixmap, QPen, QBrush, QImage, QImageReader, QPainterPath)
from PIL import Image, ImageSequence

# 尝试导入 AVIF 格式支持插件
try:
    import pillow_avif
    HAS_AVIF = True
except ImportError:
    HAS_AVIF = False

# 解除大图片防炸弹限制
Image.MAX_IMAGE_PIXELS = None

__app_name__ = "QimgZip"
__version__ = "7.0.0"
__author__ = "QwejayHuang"
__company__ = "QwejayHuang"
__description__ = "Google MD3 风格双引擎图像压缩与 Squoosh 智能比对工具 (专业稳定版)"


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


def get_bin_path(binary_name):
    if sys.platform == "win32":
        os_dir, ext = "windows", ".exe"
    elif sys.platform == "darwin":
        os_dir, ext = "macos", ""
    else:
        os_dir, ext = "linux", ""

    bin_filename = f"{binary_name}{ext}"
    search_paths = [
        os.path.join("bin", os_dir, bin_filename),
        os.path.join("bin", bin_filename)
    ]

    for rel_p in search_paths:
        res_p = get_resource_path(rel_p)
        if os.path.exists(res_p): return res_p
        data_p = get_data_path(rel_p)
        if os.path.exists(data_p): return data_p

    which_path = shutil.which(binary_name)
    if which_path: return which_path
    return None


def format_size(size_bytes):
    if size_bytes < 0: return "0 B"
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024: return f"{size_bytes / 1024:.1f} KB"
    else: return f"{size_bytes / (1024 * 1024):.2f} MB"


# ==============================================================================
# MD3 胶囊按钮控件 (AnimatedButton) - 修复梯度越界，稳定流体粒子引擎
# ==============================================================================
class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, is_primary=True):
        super().__init__(text, parent)
        self.is_primary = is_primary
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
        self.animation_group = QParallelAnimationGroup()
        self.pos_anim = QPropertyAnimation(self, b"geometry")
        self.pos_anim.setDuration(120)
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.op_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.op_anim.setDuration(150)
        
        self.is_hovered = False
        self.setFixedHeight(40)
        self._progress = -1.0
        
        self.particles = []
        self.particle_timer = QTimer(self)
        self.particle_timer.timeout.connect(self._update_particles)

        if is_primary:
            self._base_style = """
                QPushButton { background-color: #0B57D0; color: #FFFFFF; border: none; border-radius: 20px; font-weight: 600; font-size: 14px; padding: 0 20px; }
                QPushButton:hover { background-color: #0842A0; }
                QPushButton:pressed { background-color: #062E6F; }
            """
        else:
            self._base_style = """
                QPushButton { background-color: #E1E3E1; color: #1F1F1F; border: none; border-radius: 20px; font-weight: 600; font-size: 13px; padding: 0 16px; }
                QPushButton:hover { background-color: #D3D5D3; }
                QPushButton:pressed { background-color: #C2C4C2; }
            """
        self.setStyleSheet(self._base_style)

    def set_progress(self, pct):
        if not self.is_primary: return
        self._progress = pct
        if pct < 0:
            self.setStyleSheet(self._base_style)
            self.particle_timer.stop()
            self.particles.clear()
        else:
            # 严格限制梯度边界，防止 QGradient 报错
            p1 = max(0.0, min(0.999, pct))
            p2 = min(1.0, p1 + 0.001)
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1EAB61, stop:{p1:.3f} #1EAB61,
                        stop:{p2:.3f} #0B57D0, stop:1 #0B57D0);
                    color: #FFFFFF; border: none; border-radius: 20px; font-weight: 600; font-size: 14px; padding: 0 20px;
                }}
            """)
            if not self.particle_timer.isActive():
                self._init_particles()
                self.particle_timer.start(30)

    def _init_particles(self):
        self.particles = []
        for _ in range(20):
            self.particles.append({
                'x': random.uniform(0, self.width()),
                'y': random.uniform(0, self.height()),
                'vx': random.uniform(1.0, 3.0),
                'vy': random.uniform(-0.3, 0.3),
                'size': random.uniform(2.0, 4.0),
                'alpha': random.uniform(30, 100)
            })

    def _update_particles(self):
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            if p['x'] > self.width() or p['y'] < 0 or p['y'] > self.height():
                p['x'] = -5
                p['y'] = random.uniform(0, self.height())
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event) 
        if self._progress >= 0 and self.particles:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            path = QPainterPath()
            prog_w = self.width() * self._progress
            path.addRoundedRect(0, 0, prog_w, self.height(), 20, 20)
            painter.setClipPath(path)
            
            painter.setPen(Qt.PenStyle.NoPen)
            for p in self.particles:
                painter.setBrush(QColor(255, 255, 255, int(p['alpha'])))
                painter.drawEllipse(QPointF(p['x'], p['y']), p['size'], p['size'])

    def enterEvent(self, event):
        if not self.is_hovered and self.isEnabled():
            self.is_hovered = True
            geo = self.geometry()
            self.pos_anim.setStartValue(geo)
            self.pos_anim.setEndValue(geo.adjusted(0, -1, 0, -1))
            self.op_anim.setStartValue(1.0)
            self.op_anim.setEndValue(0.92)
            self.animation_group.start()

    def leaveEvent(self, event):
        if self.is_hovered:
            self.is_hovered = False
            geo = self.geometry()
            self.pos_anim.setStartValue(geo)
            self.pos_anim.setEndValue(geo.adjusted(0, 1, 0, 1))
            self.op_anim.setStartValue(0.92)
            self.op_anim.setEndValue(1.0)
            self.animation_group.start()


# ==============================================================================
# MD3 Surface 拖拽区域 (DropArea)
# ==============================================================================
class DropArea(QFrame):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame#md3_drop { background-color: #F0F4F9; border: 2px dashed #C4C7C5; border-radius: 16px; }
            QFrame#md3_drop:hover { background-color: #E1E9F5; border: 2px dashed #0B57D0; }
        """)
        self.setObjectName("md3_drop")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(6)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.icon_label.setStyleSheet('QLabel { background: transparent; color: #adb5bd; font-size: 64px; border: none; }')
        self._set_default_icon()
        layout.addWidget(self.icon_label)

        self.label = QLabel("将图片/文件夹拖拽至此处\n或 点击浏览选择文件")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.setStyleSheet("QLabel { background: transparent; color: #1F1F1F; font-size: 15px; font-weight: bold; border: none; }")
        layout.addWidget(self.label)

        self.sub_label = QLabel("添加图片以开启画质比对")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.sub_label.setStyleSheet("QLabel { background: transparent; color: #444746; font-size: 12px; border: none; }")
        layout.addWidget(self.sub_label)

    def _set_default_icon(self):
        svg_path = get_resource_path("icon.svg")
        ico_path = get_resource_path("icon.ico")
        if os.path.exists(svg_path): self.icon_label.setPixmap(QIcon(svg_path).pixmap(64, 64))
        elif os.path.exists(ico_path): self.icon_label.setPixmap(QIcon(ico_path).pixmap(64, 64))
        else: self.icon_label.setText("☁️")

    def reset_label(self):
        self._set_default_icon()
        self.label.setText("将图片/文件夹拖拽至此处\n或 点击浏览选择文件")
        self.label.setStyleSheet("QLabel { background: transparent; color: #1F1F1F; font-size: 15px; font-weight: bold; border: none; }")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QFrame#md3_drop { background-color: #D3E3FD; border: 2px dashed #0B57D0; border-radius: 16px; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("QFrame#md3_drop { background-color: #F0F4F9; border: 2px dashed #C4C7C5; border-radius: 16px; } QFrame#md3_drop:hover { background-color: #E1E9F5; border: 2px dashed #0B57D0; }")

    def dropEvent(self, event: QDropEvent):
        self.dragLeaveEvent(event)
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path): files.append(path)
            elif os.path.isdir(path): files.extend(self.get_files_from_dir(path))
        if files:
            self.filesDropped.emit(files)

    def get_files_from_dir(self, dir_path):
        files = []
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                fp = os.path.join(root, filename)
                ext = os.path.splitext(fp)[1].lower()
                if ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.bmp', '.tiff'}:
                    files.append(fp)
        return files

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = QFileDialog()
            dialog.setWindowTitle("选择图像文件")
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("图像文件 (*.jpg *.jpeg *.png *.webp *.avif *.gif *.bmp *.tiff)")
            if dialog.exec():
                files = [f for f in dialog.selectedFiles() if os.path.isfile(f)]
                if files:
                    self.filesDropped.emit(files)


# ==============================================================================
# 后台极限异步加载器 (ThumbLoaderThread & CanvasLoaderThread) - 防阻塞防竞态
# ==============================================================================
class ThumbLoaderThread(QThread):
    thumbReady = Signal(int, QImage)
    
    def __init__(self, tasks, parent=None):
        super().__init__(parent)
        self.tasks = tasks
        
    def run(self):
        for idx, path in self.tasks:
            if self.isInterruptionRequested(): break
            try:
                reader = QImageReader(path)
                reader.setAutoTransform(True)
                sz = reader.size()
                if sz.isValid():
                    if sz.width() > 180 or sz.height() > 180:
                        sz.scale(180, 180, Qt.AspectRatioMode.KeepAspectRatio)
                        reader.setScaledSize(sz)
                    img = reader.read()
                    if not img.isNull():
                        self.thumbReady.emit(idx, img)
            except Exception: pass


class CanvasLoaderThread(QThread):
    """画布专供后台大图加载服务"""
    imagesLoaded = Signal(str, QImage, QImage, bool) # 返回 orig_path 进行标识校验
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.req_orig = ""
        self.req_comp = ""
        self.req_batch = False

    def load(self, orig, comp, is_batch):
        self.req_orig = orig
        self.req_comp = comp
        self.req_batch = is_batch
        self.start()

    def _load_qimage(self, path):
        if not path or not os.path.exists(path): return QImage()
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        img = reader.read()
        if not img.isNull(): return img
        # 兼容性备用读取方案
        try:
            with Image.open(path) as pil_img:
                if pil_img.mode != 'RGBA': pil_img = pil_img.convert('RGBA')
                data = pil_img.tobytes("raw", "RGBA")
                return QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888).copy()
        except Exception: return QImage()

    def run(self):
        current_orig = self.req_orig
        orig_img = self._load_qimage(current_orig)
        if self.isInterruptionRequested() or current_orig != self.req_orig: return
        
        is_comp = (self.req_orig != self.req_comp) and os.path.exists(self.req_comp) and not self.req_batch
        
        comp_img = QImage()
        if is_comp:
            comp_img = self._load_qimage(self.req_comp)
            
        if self.isInterruptionRequested() or current_orig != self.req_orig: return
        self.imagesLoaded.emit(current_orig, orig_img, comp_img, is_comp)


# ==============================================================================
# Squoosh 高性能画布 (SplitCompareCanvas) - 激光出场动画 & 重绘缓存
# ==============================================================================
class SplitCompareCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap_orig = QPixmap()
        self.pixmap_comp = QPixmap()
        
        self._cached_scaled_orig = None
        self._cached_scaled_comp = None

        self.is_compressed = False
        self.is_loading = False
        self.split_ratio = 0.5
        self._line_anim_progress = 0.0
        self.is_dragging = False
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setStyleSheet("background-color: #121212; border-radius: 12px;")

        self.intro_anim = QPropertyAnimation(self, b"line_anim_progress")
        self.intro_anim.setDuration(700)
        self.intro_anim.setEasingCurve(QEasingCurve.Type.OutExpo)

    @Property(float)
    def line_anim_progress(self):
        return self._line_anim_progress

    @line_anim_progress.setter
    def line_anim_progress(self, val):
        self._line_anim_progress = val
        self.update()

    def set_loading_state(self, is_loading):
        self.is_loading = is_loading
        self.update()

    def set_images_from_data(self, orig_img, comp_img, is_comp):
        self.is_loading = False
        self.pixmap_orig = QPixmap.fromImage(orig_img)
        self.pixmap_comp = QPixmap.fromImage(comp_img) if is_comp else QPixmap()
        
        was_compressed = self.is_compressed
        self.is_compressed = is_comp
        self.setCursor(Qt.CursorShape.SplitHCursor if self.is_compressed else Qt.CursorShape.ArrowCursor)
        
        self._cached_scaled_orig = None
        self._cached_scaled_comp = None

        if self.is_compressed and not was_compressed:
            self.intro_anim.setStartValue(0.0)
            self.intro_anim.setEndValue(1.0)
            self.intro_anim.start()
        elif self.is_compressed:
            self._line_anim_progress = 1.0 
            self.update()
        else:
            self.update()

    def resizeEvent(self, event):
        self._cached_scaled_orig = None
        self._cached_scaled_comp = None
        super().resizeEvent(event)

    def _draw_checkerboard(self, painter, rect):
        pixmap = QPixmap(16, 16)
        p = QPainter(pixmap)
        p.fillRect(0, 0, 8, 8, QColor("#1C1C1C"))
        p.fillRect(8, 8, 8, 8, QColor("#1C1C1C"))
        p.fillRect(8, 0, 8, 8, QColor("#262626"))
        p.fillRect(0, 8, 8, 8, QColor("#262626"))
        p.end()
        painter.drawTiledPixmap(rect, pixmap)

    def _draw_badge(self, painter, y, text, bg_color, align_right=False, alpha=1.0):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        
        x = self.width() - (tw + 36) if align_right else 16
        rect = QRectF(x, y, tw + 20, th + 10)
        
        base_c = QColor(bg_color)
        base_c.setAlpha(int(255 * alpha))
        painter.setBrush(base_c)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        
        painter.setPen(QColor(255, 255, 255, int(255 * alpha)))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0 or self.pixmap_orig.isNull():
            return

        painter = QPainter(self)
        self._draw_checkerboard(painter, self.rect())

        if self._cached_scaled_orig is None:
            self._cached_scaled_orig = self.pixmap_orig.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        off_x = (w - self._cached_scaled_orig.width()) // 2
        off_y = (h - self._cached_scaled_orig.height()) // 2
        img_w, img_h = self._cached_scaled_orig.width(), self._cached_scaled_orig.height()

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 状态 1：未处理完成时，仅隐藏对比条和渲染原图
        if not self.is_compressed or self.pixmap_comp.isNull():
            painter.drawPixmap(off_x, off_y, self._cached_scaled_orig)
            self._draw_badge(painter, 16, "待处理 (原图)", "#343A40", align_right=False)
        # 状态 2：压缩完成，激活汇聚光束与滑动对比
        else:
            if self._cached_scaled_comp is None:
                self._cached_scaled_comp = self.pixmap_comp.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            painter.drawPixmap(off_x, off_y, self._cached_scaled_comp)

            split_x = int(w * self.split_ratio)
            clip_w = max(0, split_x - off_x)
            if clip_w > 0:
                painter.setClipRect(off_x, off_y, min(clip_w, img_w), img_h)
                painter.drawPixmap(off_x, off_y, self._cached_scaled_orig)

            painter.setClipping(False)
            
            p = self._line_anim_progress
            pen = QPen(QColor("#0B57D0"), 3)
            painter.setPen(pen)
            
            center_y = h / 2
            
            painter.drawLine(QPointF(split_x, 0), QPointF(split_x, center_y * p))
            painter.drawLine(QPointF(split_x, h), QPointF(split_x, h - center_y * p))

            if p > 0.05:
                handle_r = 16 * p
                painter.setBrush(QBrush(QColor("#0B57D0")))
                painter.drawEllipse(QPointF(split_x, center_y), handle_r, handle_r)
                
                painter.setPen(QPen(QColor("white"), 2 * p))
                painter.drawLine(QPointF(split_x - 5 * p, center_y), QPointF(split_x + 5 * p, center_y))

            self._draw_badge(painter, 16, "原图", "#1F1F1F", align_right=False, alpha=p)
            self._draw_badge(painter, 16, "压缩后", "#1EAB61", align_right=True, alpha=p)

        if self.is_loading:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
            self._draw_badge(painter, h / 2 - 15, "⏳ 加载中...", "#1F1F1F", align_right=False)

    def mousePressEvent(self, event):
        if self.is_compressed and event.button() == Qt.MouseButton.LeftButton:
            self.intro_anim.stop() 
            self._line_anim_progress = 1.0 
            self.is_dragging = True
            self._update_ratio(event.position().x())

    def mouseMoveEvent(self, event):
        if self.is_compressed and (self.is_dragging or event.buttons() & Qt.MouseButton.LeftButton):
            self._update_ratio(event.position().x())

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

    def _update_ratio(self, mouse_x):
        self.split_ratio = max(0.01, min(0.99, mouse_x / float(self.width())))
        self.update()


# ==============================================================================
# MD3 缩略图卡片与滑动条 (Thumbnail Strip)
# ==============================================================================
class ThumbnailCard(QFrame):
    clicked = Signal(int)

    def __init__(self, index, orig_path, comp_path, parent=None):
        super().__init__(parent)
        self.index = index
        self.orig_path = orig_path
        self.comp_path = comp_path
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(145)
        self.setFixedHeight(75)
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            ThumbnailCard { background: #FFFFFF; border: 1px solid #E1E3E1; border-radius: 12px; }
            ThumbnailCard:hover { border: 2px solid #D3E3FD; background: #F0F4F9; }
        """)
        self.init_ui()
        self.update_info(self.comp_path)

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(50, 50)
        self.img_lbl.setStyleSheet("border-radius: 6px; background: transparent;")
        layout.addWidget(self.img_lbl)

        info_lay = QVBoxLayout()
        info_lay.setSpacing(2)
        info_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_name = QLabel()
        self.lbl_name.setStyleSheet("background: transparent; font-size: 12px; font-weight: 600; color: #1F1F1F; border: none;")

        self.lbl_size = QLabel()
        self.lbl_size.setStyleSheet("background: transparent; font-size: 11px; color: #444746; border: none;")
        
        self.lbl_saved = QLabel()
        self.lbl_saved.setStyleSheet("background: transparent; font-size: 11px; font-weight: bold; border: none;")

        info_lay.addWidget(self.lbl_name)
        info_lay.addWidget(self.lbl_size)
        info_lay.addWidget(self.lbl_saved)
        layout.addLayout(info_lay)

    def update_info(self, comp_path):
        self.comp_path = comp_path
        fname = os.path.basename(self.orig_path)
        if len(fname) > 8: fname = fname[:7] + ".."
        self.lbl_name.setText(fname)

        has_comp = self.comp_path != self.orig_path and os.path.exists(self.comp_path)
        s_orig = os.path.getsize(self.orig_path) if os.path.exists(self.orig_path) else 0
        s_comp = os.path.getsize(self.comp_path) if has_comp else s_orig

        if not has_comp:
            self.lbl_size.setText(format_size(s_orig))
            self.lbl_saved.setText("待处理")
            self.lbl_saved.setStyleSheet("background: transparent; font-size: 11px; font-weight: bold; color: #868E96; border: none;")
        else:
            pct = (1 - s_comp / float(s_orig)) * 100 if s_orig > 0 else 0
            self.lbl_size.setText(format_size(s_comp))
            self.lbl_saved.setText(f"-{pct:.0f}%" if pct > 0 else "同大")
            self.lbl_saved.setStyleSheet("background: transparent; font-size: 11px; font-weight: bold; color: #1EAB61; border: none;")

    def set_selected(self, selected):
        if selected:
            self.setStyleSheet("ThumbnailCard { background: #F0F4F9; border: 2px solid #0B57D0; border-radius: 12px; }")
        else:
            self.setStyleSheet("""
                ThumbnailCard { background: #FFFFFF; border: 1px solid #E1E3E1; border-radius: 12px; }
                ThumbnailCard:hover { border: 2px solid #D3E3FD; background: #F0F4F9; }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)


class ThumbnailStrip(QScrollArea):
    imageSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(95)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:horizontal { border: none; background: transparent; height: 8px; margin: 0px; }
            QScrollBar::handle:horizontal { background: #C4C7C5; min-width: 40px; border-radius: 4px; }
            QScrollBar::handle:horizontal:hover { background: #8E918F; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
        """)

        self.cards = []
        self.current_idx = -1
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.layout = QHBoxLayout(self.content_widget)
        self.layout.setContentsMargins(0, 0, 0, 10)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setWidget(self.content_widget)
        
        self._loaders = []

    def load_thumbnails(self, orig_files, output_map):
        for loader in self._loaders:
            if loader.isRunning(): loader.requestInterruption()
        self._loaders.clear()

        for c in self.cards: c.deleteLater()
        self.cards.clear()
        
        tasks = []
        for idx, orig_p in enumerate(orig_files):
            comp_p = output_map.get(orig_p, orig_p)
            card = ThumbnailCard(idx, orig_p, comp_p)
            card.clicked.connect(self._on_card_clicked)
            self.layout.addWidget(card)
            self.cards.append(card)
            tasks.append((idx, orig_p))

        if self.cards: self.select_card(0)
        
        loader = ThumbLoaderThread(tasks, self)
        loader.thumbReady.connect(self._apply_thumb)
        loader.start()
        self._loaders.append(loader)

    def _apply_thumb(self, idx, qimg):
        if 0 <= idx < len(self.cards):
            self.cards[idx].img_lbl.setPixmap(QPixmap.fromImage(qimg).scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))

    def update_card(self, orig_path, comp_path):
        for i, card in enumerate(self.cards):
            if card.orig_path == orig_path:
                card.update_info(comp_path)
                return i
        return -1

    def select_card(self, index):
        self.current_idx = index
        for i, card in enumerate(self.cards):
            card.set_selected(i == index)
        self.imageSelected.emit(index)

    def _on_card_clicked(self, index):
        self.select_card(index)


# ==============================================================================
# MD3 底部快捷控制栏 (QuickSettingsBar)
# ==============================================================================
class QuickSettingsBar(QFrame):
    settingsChanged = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._is_loading = False
        self.setStyleSheet("""
            QFrame#md3_bar { background: #FFFFFF; border: 1px solid #E1E3E1; border-radius: 12px; }
            QLabel { color: #1F1F1F; font-size: 13px; font-weight: 600; }
            QComboBox { color: #1F1F1F; font-size: 13px; padding: 5px 10px; border: 1px solid #E1E3E1; border-radius: 8px; background: #F4F7FC; }
            QSpinBox { color: #1F1F1F; font-size: 13px; padding: 5px; border: 1px solid #E1E3E1; border-radius: 8px; background: #F4F7FC; }
            QCheckBox { font-size: 13px; color: #1F1F1F; spacing: 6px; font-weight: 600; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #C4C7C5; border-radius: 4px; }
            QCheckBox::indicator:checked { background: #0B57D0; border-color: #0B57D0; }
            
            QSlider::groove:horizontal { height: 4px; background: #E1E3E1; border-radius: 2px; }
            QSlider::handle:horizontal { background: #0B57D0; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }
            QSlider::sub-page:horizontal { background: #0B57D0; border-radius: 2px; }
        """)
        self.setObjectName("md3_bar")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(16)

        layout.addWidget(QLabel("格式:"))
        self.cb_fmt = QComboBox()
        self.cb_fmt.addItems(["保持原格式", "转换为 WebP", "转换为 AVIF", "转换为 JPEG", "转换为 PNG"])
        self.cb_fmt.currentTextChanged.connect(self._on_fmt_changed)
        layout.addWidget(self.cb_fmt)

        self.chk_target = QCheckBox("限制:")
        self.chk_target.toggled.connect(self._on_target_toggled)
        layout.addWidget(self.chk_target)

        self.sp_target_kb = QSpinBox()
        self.sp_target_kb.setRange(10, 50000)
        self.sp_target_kb.setSuffix(" KB")
        self.sp_target_kb.setFixedWidth(85)
        self.sp_target_kb.valueChanged.connect(self._on_kb_changed)
        layout.addWidget(self.sp_target_kb)

        layout.addWidget(QLabel("质量:"))
        self.slider_q = QSlider(Qt.Orientation.Horizontal)
        self.slider_q.setRange(10, 95)
        self.slider_q.setFixedWidth(80)
        self.slider_q.valueChanged.connect(self._on_q_changed)
        layout.addWidget(self.slider_q)

        self.lbl_q_val = QLabel("75%")
        self.lbl_q_val.setFixedWidth(36)
        layout.addWidget(self.lbl_q_val)

        self.lbl_engine_tag = QLabel()
        self.lbl_engine_tag.setStyleSheet("color: #444746; font-size: 11px; background: #E1E3E1; padding: 4px 10px; border-radius: 8px; font-weight: bold;")
        self.update_engine_tag()
        layout.addWidget(self.lbl_engine_tag)

        layout.addStretch()

    def sync_from_settings(self):
        self._is_loading = True
        s = self.settings
        self.cb_fmt.setCurrentText(s.get("target_format", "保持原格式"))
        self.chk_target.setChecked(s.get("enable_target_size", False))
        self.sp_target_kb.setValue(s.get("target_kb", 200))
        self.sp_target_kb.setEnabled(s.get("enable_target_size", False))
        
        q = s.get("jpg_quality", 75)
        self.slider_q.setValue(q)
        self.lbl_q_val.setText(f"{q}%")
        self._is_loading = False

    def update_engine_tag(self):
        if get_bin_path("pngquant"):
            self.lbl_engine_tag.setText("pngquant 引擎")
        else:
            self.lbl_engine_tag.setText("Pillow 引擎")

    def _on_fmt_changed(self, val):
        if self._is_loading: return
        self.settings["target_format"] = val
        self.settingsChanged.emit()

    def _on_target_toggled(self, checked):
        if self._is_loading: return
        self.settings["enable_target_size"] = checked
        self.sp_target_kb.setEnabled(checked)
        self.settingsChanged.emit()

    def _on_kb_changed(self, val):
        if self._is_loading: return
        self.settings["target_kb"] = val
        self.settingsChanged.emit()

    def _on_q_changed(self, val):
        if self._is_loading: return
        self.lbl_q_val.setText(f"{val}%")
        self.settings["jpg_quality"] = val
        self.settings["webp_quality"] = val
        self.settings["avif_quality"] = val
        self.settingsChanged.emit()


# ==============================================================================
# CompressWorker 多线程任务
# ==============================================================================
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._process_single_file, fp): fp for fp in self.files if self._is_running}
            for future in concurrent.futures.as_completed(futures):
                if not self._is_running: break
                fp = futures[future]
                try:
                    res_type, out_path, o_size, c_size = future.result()
                    if res_type == "success":
                        self.total_saved += (o_size - c_size) / 1024.0
                        self.success_count += 1
                        self.progress.emit(fp, out_path, float(o_size), float(c_size))
                    else:
                        self.progress.emit(fp, f"error:{out_path}", float(o_size), 0.0)
                except Exception as e:
                    self.progress.emit(fp, f"error:{str(e)}", 0.0, 0.0)
        self.finished.emit(self.success_count, self.total_saved)

    def _process_single_file(self, file_path):
        try:
            origin_size = os.path.getsize(file_path)
            if self.settings.get("enable_target_size", False):
                result = self._compress_target_size(file_path)
            else:
                result = self.compress_file(file_path)

            if result:
                output_path, compressed_size = result
                return ("success", output_path, origin_size, compressed_size)
            return ("error", "failed", origin_size, 0)
        except Exception as e:
            return ("error", str(e), 0, 0)

    def _compress_target_size(self, input_path):
        target_kb = self.settings.get("target_kb", 200)
        target_bytes = target_kb * 1024
        low_q, high_q = 10, 95
        best_output = None
        
        saved_q = self.settings.get("jpg_quality", 75)
        for _ in range(5):
            mid_q = (low_q + high_q) // 2
            self.settings["jpg_quality"] = mid_q
            self.settings["webp_quality"] = mid_q
            self.settings["avif_quality"] = mid_q
            res = self.compress_file(input_path)
            if res and os.path.exists(res[0]):
                if res[1] <= target_bytes:
                    best_output = res
                    low_q = mid_q + 1
                else:
                    high_q = mid_q - 1
        self.settings["jpg_quality"] = saved_q

        if not best_output or best_output[1] > target_bytes:
            scale = 0.85
            saved_resize = self.settings.get("resize_mode", "不调整")
            saved_scale = self.settings.get("scale_ratio", 100)
            while scale >= 0.2:
                self.settings["resize_mode"] = "按比例缩放"
                self.settings["scale_ratio"] = int(scale * 100)
                res = self.compress_file(input_path)
                if res and res[1] <= target_bytes:
                    best_output = res
                    break
                scale -= 0.15
            self.settings["resize_mode"] = saved_resize
            self.settings["scale_ratio"] = saved_scale

        return best_output if best_output else self.compress_file(input_path)

    def _get_output_path(self, file_path, ext_override=None):
        target_fmt = self.settings.get("target_format", "保持原格式")
        fmt_ext_map = {"转换为 WebP": ".webp", "转换为 AVIF": ".avif", "转换为 JPEG": ".jpg", "转换为 PNG": ".png"}
        final_ext = fmt_ext_map.get(target_fmt, ext_override)
        base_dir = os.path.dirname(file_path)
        base_name, orig_ext = os.path.splitext(os.path.basename(file_path))
        if not final_ext: final_ext = orig_ext
        
        mode = self.settings.get("output_mode", "追加后缀")
        if mode == "覆盖原图" and target_fmt == "保持原格式":
            return os.path.join(base_dir, base_name + final_ext)
        elif mode == "输出到指定文件夹":
            out_dir = self.settings.get("output_dir", base_dir)
            if not out_dir or not os.path.exists(out_dir): out_dir = base_dir
            return os.path.join(out_dir, base_name + final_ext)
        else:
            suffix = self.settings.get("output_suffix", "_压缩版")
            return os.path.join(base_dir, base_name + suffix + final_ext)

    def compress_file(self, file_path):
        target_fmt = self.settings.get("target_format", "保持原格式")
        if target_fmt == "转换为 WebP": return self._compress_webp(file_path)
        elif target_fmt == "转换为 AVIF": return self._compress_avif(file_path)
        elif target_fmt == "转换为 JPEG": return self._compress_jpg(file_path)
        elif target_fmt == "转换为 PNG": return self._compress_png(file_path)

        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.jpg', '.jpeg'): return self._compress_jpg(file_path)
        elif ext == '.png': return self._compress_png(file_path)
        elif ext == '.gif': return self._compress_gif(file_path)
        elif ext == '.webp': return self._compress_webp(file_path)
        elif ext == '.avif': return self._compress_avif(file_path)
        else: return self._compress_generic(file_path)

    def _compress_jpg(self, input_path):
        out = self._get_output_path(input_path, ".jpg")
        q = self.settings.get("jpg_quality", 80)
        with Image.open(input_path) as img:
            exif = img.info.get('exif') if not self.settings.get("strip_exif", True) else None
            if img.mode != 'RGB': img = img.convert('RGB')
            kwargs = {'format': 'JPEG', 'quality': q, 'optimize': True, 'progressive': True}
            if exif: kwargs['exif'] = exif
            img.save(out, **kwargs)
        return (out, os.path.getsize(out))

    def _compress_png(self, input_path):
        out = self._get_output_path(input_path, ".png")
        strip_exif = self.settings.get("strip_exif", True)
        pngquant_bin = get_bin_path("pngquant")
        
        if pngquant_bin and self.settings.get("png_quantize", True):
            cmd = [pngquant_bin, "--colors=256", "--speed=3", "--force", "--output", out]
            if strip_exif: cmd.append("--strip")
            cmd.append(input_path)
            try:
                kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
                if res.returncode == 0 and os.path.exists(out): return (out, os.path.getsize(out))
            except Exception: pass

        with Image.open(input_path) as img:
            kwargs = {'format': 'PNG', 'optimize': True}
            img.save(out, **kwargs)
        return (out, os.path.getsize(out))

    def _compress_gif(self, input_path):
        out = self._get_output_path(input_path, ".gif")
        with Image.open(input_path) as img:
            img.save(out, format='GIF', optimize=True)
        return (out, os.path.getsize(out))

    def _compress_webp(self, input_path):
        out = self._get_output_path(input_path, ".webp")
        q = self.settings.get("webp_quality", 80)
        cwebp_bin = get_bin_path("cwebp")
        if cwebp_bin:
            cmd = [cwebp_bin, "-q", str(q), input_path, "-o", out]
            try:
                kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
                if res.returncode == 0 and os.path.exists(out): return (out, os.path.getsize(out))
            except Exception: pass

        with Image.open(input_path) as img:
            img.save(out, format='WEBP', quality=q)
        return (out, os.path.getsize(out))

    def _compress_avif(self, input_path):
        out = self._get_output_path(input_path, ".avif")
        q = self.settings.get("avif_quality", 65)
        with Image.open(input_path) as img:
            try: img.save(out, format='AVIF', quality=q)
            except Exception:
                out = self._get_output_path(input_path, ".webp")
                img.save(out, format='WEBP', quality=q)
        return (out, os.path.getsize(out))

    def _compress_generic(self, input_path):
        out = self._get_output_path(input_path, ".png")
        with Image.open(input_path) as img:
            img.save(out, format='PNG')
        return (out, os.path.getsize(out))

    def stop(self): self._is_running = False


# ==============================================================================
# SettingsPanel (高级参数弹窗)
# ==============================================================================
class SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.default_settings = {
            "compress_mode": "均衡推荐 (常用)", "target_format": "保持原格式",
            "enable_target_size": False, "target_kb": 200, "strip_exif": True,
            "resize_mode": "限制长边", "max_long_side": 1920, "scale_ratio": 100,
            "resample_algo": "Lanczos (高质量)", "jpg_quality": 75, "png_quantize": True,
            "png_colors": 256, "webp_quality": 75, "avif_quality": 65, "gif_colors": 128,
            "output_mode": "覆盖原图", "output_suffix": "_压缩", "output_dir": ""
        }
        self.settings = self.load_settings()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        lbl = QLabel("高级参数配置")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #1F1F1F;")
        layout.addWidget(lbl)

        self.chk_exif = QCheckBox("彻底擦除 GPS 地理位置与设备 EXIF 隐私")
        self.chk_exif.setStyleSheet("font-size: 13px; color: #1F1F1F; font-weight: 600;")
        self.chk_exif.setChecked(self.settings.get("strip_exif", True))
        self.chk_exif.toggled.connect(lambda c: self.settings.update({"strip_exif": c}))
        layout.addWidget(self.chk_exif)

        btn_back = AnimatedButton("保存并关闭", is_primary=True)
        btn_back.clicked.connect(self.save_and_return)
        layout.addStretch()
        layout.addWidget(btn_back)

    def load_settings(self):
        try:
            p = get_data_path("settings.json")
            if not os.path.exists(p): return self.default_settings.copy()
            with open(p, "r", encoding="utf-8") as f: s = json.load(f)
            for k, v in self.default_settings.items():
                if k not in s: s[k] = v
            return s
        except Exception: return self.default_settings.copy()

    def save_and_return(self):
        try:
            with open(get_data_path("settings.json"), "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception: pass
        if isinstance(self.parent, QDialog): self.parent.accept()


# ==============================================================================
# MainWindow 主界面
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} {__version__} —— {__author__}")
        self.files = []
        self.output_files_map = {}
        self._processed_count = 0
        self.is_processing = False

        if getattr(sys, 'frozen', False):
            provider = QFileIconProvider()
            exe_icon = provider.icon(QFileInfo(sys.executable))
            if not exe_icon.isNull(): self.setWindowIcon(exe_icon)
        else:
            svg_path = get_resource_path("icon.svg")
            ico_path = get_resource_path("icon.ico")
            if os.path.exists(svg_path): self.setWindowIcon(QIcon(svg_path))
            elif os.path.exists(ico_path): self.setWindowIcon(QIcon(ico_path))

        self.settingsPanel = SettingsPanel()
        self.settings = self.settingsPanel.settings
        
        self.canvas_loader = CanvasLoaderThread(self)
        self.canvas_loader.imagesLoaded.connect(self._apply_canvas_images)
        
        self.init_ui()

    def init_ui(self):
        self.setMinimumSize(780, 680)
        self.setStyleSheet("QMainWindow { background-color: #F3F6FC; }")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        self.workspace_stack = QStackedWidget()
        
        self.drop_area = DropArea(self)
        self.drop_area.filesDropped.connect(self.add_files) 
        self.workspace_stack.addWidget(self.drop_area)

        self.compare_container = QWidget()
        comp_lay = QVBoxLayout(self.compare_container)
        comp_lay.setContentsMargins(0, 0, 0, 0)
        comp_lay.setSpacing(12)

        self.compare_canvas = SplitCompareCanvas()
        comp_lay.addWidget(self.compare_canvas, stretch=1)

        self.thumb_strip = ThumbnailStrip()
        self.thumb_strip.imageSelected.connect(self._on_thumb_selected)
        comp_lay.addWidget(self.thumb_strip)

        self.workspace_stack.addWidget(self.compare_container)
        main_layout.addWidget(self.workspace_stack, stretch=1)

        self.quick_bar = QuickSettingsBar(self.settings, self)
        self.quick_bar.settingsChanged.connect(self.update_status_bar)
        main_layout.addWidget(self.quick_bar)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)

        self.btn_readd = AnimatedButton("清空列表", is_primary=False)
        self.btn_readd.clicked.connect(self.clear_files)
        btn_layout.addWidget(self.btn_readd)

        self.action_btn = AnimatedButton("开始处理", is_primary=True)
        self.action_btn.clicked.connect(self.toggle_action)
        btn_layout.addWidget(self.action_btn, stretch=1)

        self.btn_toggle_bar = AnimatedButton("收起参数", is_primary=False)
        self.btn_toggle_bar.clicked.connect(self.toggle_quick_bar)
        btn_layout.addWidget(self.btn_toggle_bar)

        self.btn_gear = AnimatedButton("设置", is_primary=False)
        self.btn_gear.setFixedSize(60, 40)
        self.btn_gear.clicked.connect(self.show_settings)
        btn_layout.addWidget(self.btn_gear)

        main_layout.addLayout(btn_layout)

        self.statusBar = self.statusBar()
        self.statusBar.setStyleSheet("QStatusBar { color: #444746; font-size: 13px; font-weight: bold; background: #F3F6FC; padding-left: 8px; }")
        self.status_msg_label = QLabel("就绪：拖拽或选择文件以开始")
        self.statusBar.addWidget(self.status_msg_label)

        self.quick_bar.sync_from_settings()

    def toggle_quick_bar(self):
        if self.quick_bar.isVisible():
            self.quick_bar.hide()
            self.btn_toggle_bar.setText("展开参数")
        else:
            self.quick_bar.show()
            self.btn_toggle_bar.setText("收起参数")

    def add_files(self, files):
        existing = set(self.files)
        new_files = [f for f in files if f not in existing]
        new_files.sort() # UX: 按首字母自然排序
        
        if new_files:
            self.files.extend(new_files)
            self.workspace_stack.setCurrentIndex(1)
            self.thumb_strip.load_thumbnails(self.files, self.output_files_map)
            
            if self.quick_bar.isVisible():
                self.quick_bar.hide()
                self.btn_toggle_bar.setText("展开参数")

            self.status_msg_label.setText(f"已加载 {len(self.files)} 个文件，等待处理")
            self.status_msg_label.setStyleSheet("color: #444746;")
        elif files:
            self.status_msg_label.setText("提示：所选文件已存在或不受支持")
            self.status_msg_label.setStyleSheet("color: #FA5252;")

    def toggle_action(self):
        if "开始处理" in self.action_btn.text() or "重新处理" in self.action_btn.text():
            if not self.files:
                QMessageBox.information(self, "提示", "列表为空，请先添加文件。")
                return
            self.start_compress()
        else:
            self.stop_compress()

    def start_compress(self):
        self.is_processing = True
        self.action_btn.setText("停止处理")
        self.action_btn.set_progress(0.0)
        self._processed_count = 0

        idx = self.thumb_strip.current_idx
        if idx != -1:
            orig_p = self.files[idx]
            comp_p = self.output_files_map.get(orig_p, orig_p)
            self.compare_canvas.set_loading_state(True)
            self.canvas_loader.load(orig_p, comp_p, is_batch=True)

        self.status_msg_label.setText(f"正在处理：{len(self.files)} 个文件...")
        self.status_msg_label.setStyleSheet("color: #1F1F1F;")
        
        self.worker = CompressWorker(self.files, self.settings)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.compress_finished)
        self.worker.start()

    def stop_compress(self):
        if hasattr(self, 'worker'): self.worker.stop()
        self.is_processing = False
        self.action_btn.set_progress(-1.0)
        self.action_btn.setText("开始处理")
        self.status_msg_label.setText("处理已取消")

    def update_progress(self, orig_p, comp_p, o_sz, c_sz):
        self._processed_count += 1
        pct = self._processed_count / max(1, len(self.files))
        self.action_btn.set_progress(pct)

        if not comp_p.startswith("error"):
            self.output_files_map[orig_p] = comp_p
            self.thumb_strip.update_card(orig_p, comp_p)

    def compress_finished(self, succ_cnt, total_saved_kb):
        self.is_processing = False
        self.action_btn.set_progress(-1.0)
        self.action_btn.setText("重新处理")
        
        idx = self.thumb_strip.current_idx
        if idx != -1:
            orig_p = self.files[idx]
            comp_p = self.output_files_map.get(orig_p, orig_p)
            self.compare_canvas.set_loading_state(True)
            self.canvas_loader.load(orig_p, comp_p, is_batch=False)

        if succ_cnt > 0:
            self.status_msg_label.setText(f"处理完成：共 {succ_cnt} 个文件，节省 {total_saved_kb/1024.0:.2f} MB")
            self.status_msg_label.setStyleSheet("color: #1EAB61;")
        else:
            self.status_msg_label.setText("处理异常：未成功处理任何文件")
            self.status_msg_label.setStyleSheet("color: #FA5252;")

    def _on_thumb_selected(self, index):
        if 0 <= index < len(self.files):
            orig_p = self.files[index]
            comp_p = self.output_files_map.get(orig_p, orig_p)
            self.compare_canvas.set_loading_state(True)
            self.canvas_loader.load(orig_p, comp_p, is_batch=self.is_processing)

    def _apply_canvas_images(self, req_path, orig_img, comp_img, is_comp):
        # 验证是否为当前选中的图片，防止多线程乱序闪图
        idx = self.thumb_strip.current_idx
        if idx != -1 and self.files[idx] == req_path:
            self.compare_canvas.set_images_from_data(orig_img, comp_img, is_comp)

    def clear_files(self):
        self.is_processing = False
        self.files.clear()
        self.output_files_map.clear()
        self.workspace_stack.setCurrentIndex(0)
        self.drop_area.reset_label()
        
        if not self.quick_bar.isVisible():
            self.quick_bar.show()
            self.btn_toggle_bar.setText("收起参数")

        self.status_msg_label.setText("就绪：拖拽或选择文件以开始")
        self.status_msg_label.setStyleSheet("color: #444746;")
        self.action_btn.set_progress(-1.0)
        self.action_btn.setText("开始处理")

    def update_status_bar(self):
        fmt = self.settings.get("target_format", "保持原格式")
        kb = f" {self.settings.get('target_kb')}KB上限" if self.settings.get("enable_target_size") else ""
        self.status_msg_label.setText(f"参数已更新：格式[{fmt}]{kb}")
        self.status_msg_label.setStyleSheet("color: #444746;")

    def show_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("高级参数")
        dlg.resize(400, 200)
        dlg.setStyleSheet("QDialog { background-color: #F8F9FA; }")
        lay = QVBoxLayout(dlg)
        self.settingsPanel.parent = dlg
        lay.addWidget(self.settingsPanel)
        dlg.exec()
        self.quick_bar.sync_from_settings()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
