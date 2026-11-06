#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
砂金小狐狸桌宠 (shajincw) v4.0 · 住在桌面上的小狐狸
================================================================================
v4.0 核心特性：
1. 1:1 还原参考图「奶油白 · 浅薄荷绿 · 香槟金」轻拟物磨砂 UI：
   - 狐狸正下方悬浮全圆角胶囊工具栏（4 个线性图标：🍴喂食、Aa改名、⊻底部收纳、···大小滑块/更多）。
   - 右下角同款「今天想吃点什么？」1×4 横向点心卡片（小饼干、三文鱼、甜桃子、热可可）。
   - 右上角同款「把文件交给我」卡片（含原文件名 / 改名后实时预览表、「再想一下」与浅薄荷绿「确认改名」胶囊按钮）。
2. 极简文件重命名：直接在原文件名（不含扩展名）后面原样追加输入内容（输入什么就加什么，不乱套壳）。
3. 滑块无级调节大小 + 更小巧的尺寸下限：
   - 提供丝滑的悬浮拖动滑块（25% ~ 160%），最小可缩至约 45px 迷你尺寸，默认尺寸也更精致。
4. 屏幕底部自动吸附与两段式探头收纳（保持原尺寸下沉裁剪，仅露两只耳朵与紫眼睛上半张脸）。
5. 真实进食消化排便生理循环 + 6 阶段贝塞尔喂食动画 + 零荧光纯净原画立绘。
"""

from __future__ import annotations

import enum
import json
import math
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import (
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
    QScreen,
    QTransform,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


def resource_path(rel_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel_path
    return Path(__file__).resolve().parent / rel_path


STATE_FILE = Path.home() / ".shajincw_pet_v4.json"


# ==============================================================================
# 集中式视觉与动画配置（严格复刻参考设计图配色）
# ==============================================================================
class Theme:
    """奶油白 · 浅薄荷绿 · 香槟金 低饱和治愈系配色"""
    CARD_BG         = QColor(245, 246, 243, 246)  # #F5F6F3 温润浅灰奶油白卡片底
    TILE_BG         = QColor(250, 251, 248, 252)  # #FAFBF8 点心方块/内层亮白底
    BORDER_WARM     = QColor(226, 228, 222, 235)  # #E2E4DE 柔和暖灰外描边
    BORDER_INNER    = QColor(255, 255, 255, 210)  # 纯白高光内描边
    CHAMPAGNE_LINE  = QColor(213, 211, 200, 245)  # #D5D3C8 香槟金米灰输入框描边
    CHAMPAGNE_GOLD  = QColor(232, 198, 138, 245)  # #E8C68A 香槟金粒子/光环
    MINT_BTN_BG     = QColor(203, 224, 214, 250)  # #CBE0D6 浅薄荷绿主按钮/高亮胶囊底
    MINT_BTN_TEXT   = QColor(59, 77, 70, 255)     # #3B4D46 深灰绿按钮文字
    ICON_STROKE     = QColor(92, 107, 100, 245)   # #5C6B64 胶囊工具栏线性图标色
    TEXT_TITLE      = QColor(58, 68, 64, 255)     # #3A4440 标题深灰绿
    TEXT_SUB        = QColor(132, 142, 136, 235)  # #848E88 辅助说明文字
    SHADOW_COLOR    = QColor(45, 52, 48, 28)      # 柔和弥散阴影


class AnimConfig:
    DT_ACTIVE_MS      = 16
    DT_IDLE_MS        = 42

    HOVER_SCALE       = 1.03
    HOVER_LIFT_PX     = -3.5
    HOVER_DUR         = 0.20
    CLICK_DUR         = 0.16
    MENU_FADE_DUR     = 0.20
    MENU_HIDE_DELAY   = 1.80
    BUBBLE_IN_DUR     = 0.20
    BUBBLE_OUT_DUR    = 0.24

    # 屏幕底部吸附与探头收纳参数
    SNAP_BOTTOM_DIST  = 42
    TUCK_DURATION     = 0.46
    EXPAND_DURATION   = 0.45
    PEEK_STAGE1_DUR   = 0.17
    PEEK_PAUSE_DUR    = 0.13
    UNTUCK_HIDE_WAIT  = 1.45
    # 收纳时下沉比例：仅露出两只耳朵、头顶墨镜与两只紫色大眼睛（约占全身 38%）
    TUCK_SINK_RATIO   = 0.62
    PEEK_STAGE1_RATIO = 0.47


class AnimPriorityState(enum.IntEnum):
    IDLE        = 10
    TUCK_DOCK   = 20
    CLICK_REACT = 30
    FEEDING     = 40
    DRAGGING    = 50
    FILE_DROP   = 60


class DockState(enum.Enum):
    FREE           = "free"
    SINKING        = "sinking"
    TUCKED         = "tucked"
    PEEKING_STEP1  = "peeking_step1"
    PEEKING_PAUSE  = "peeking_pause"
    EXPANDING      = "expanding"
    EXPANDED_HOLD  = "expanded_hold"


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 4.0 * t * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def ease_out_back(t: float, overshoot: float = 1.28) -> float:
    t = max(0.0, min(1.0, t))
    c3 = overshoot + 1.0
    return 1.0 + c3 * ((t - 1.0) ** 3) + overshoot * ((t - 1.0) ** 2)


def bezier_quad(p0: QPointF, p1: QPointF, p2: QPointF, t: float) -> QPointF:
    u = 1.0 - t
    return QPointF(
        u * u * p0.x() + 2 * u * t * p1.x() + t * t * p2.x(),
        u * u * p0.y() + 2 * u * t * p1.y() + t * t * p2.y(),
    )


# ==============================================================================
# 台词与参考图 4 款点心配置（小饼干、三文鱼、甜桃子、热可可）
# ==============================================================================
CLICK_QUOTES = [
    "摸摸头，心情 +1",
    "唔～摸耳朵会痒的呀。",
    "所有，或者一无所有～今天运气不错哦。",
    "呼噜噜……勉强让你再摸一下下巴。",
    "有文件要改名吗？直接拖给我就好～",
]

IDLE_QUOTES = [
    "（轻轻呼吸）今天也会陪你一起工作哦～",
    "盯——累了的话，喝杯热可可歇会儿吧。",
    "呼噜……晒着屏幕的光有点犯困了呢。",
]

FEED_QUOTES = [
    "好吃～",
    "谢谢款待！",
    "再来一点？",
    "一口小点心，充满干劲啦～",
]

HUNGRY_QUOTES = [
    "肚子咕噜噜叫了……想吃小饼干或三文鱼～",
]

THIRSTY_QUOTES = [
    "有点渴了呢，想喝杯热可可或吃个甜桃子～",
]

POOP_QUOTES = [
    "噗——消化完排出来啦，点一下便便就能清理掉哦～",
]


@dataclass
class SnackItem:
    key: str
    name: str
    hunger_gain: float
    thirst_gain: float
    gut_gain: float


SNACK_ITEMS = [
    SnackItem("cookie", "小饼干", 25.0, -2.0, 32.0),
    SnackItem("salmon", "三文鱼", 30.0, 5.0, 36.0),
    SnackItem("peach",  "甜桃子", 16.0, 22.0, 22.0),
    SnackItem("cocoa",  "热可可", 10.0, 32.0, 14.0),
]


# ==============================================================================
# 「把文件交给我」重命名弹窗（1:1 还原参考图右上角卡片 + 极简原文件名后直接追加）
# ==============================================================================
class RenameCardDialog(QDialog):
    """
    参考图右上角「把文件交给我」卡片：
    - 简单直接：在原文件名（不含扩展名）后面直接追加用户输入的内容！
      例如 000.jpg：输入 (555) -> 000(555).jpg；输入 _555 -> 000_555.jpg；输入 555 -> 000555.jpg
    """

    ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|]')

    def __init__(self, file_paths: list[Path], parent_pet: "ShajinFoxPet"):
        super().__init__(parent_pet)
        self.pet = parent_pet
        self.file_paths = file_paths
        self.renamed_count = 0

        self.setWindowTitle("把文件交给我")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(410)
        self._drag_pos: Optional[QPoint] = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        card = QFrame(self)
        card.setObjectName("MainCard")
        card.setStyleSheet(
            """
            QFrame#MainCard {
                background-color: #F5F6F3;
                border: 1.5px solid #E2E4DE;
                border-radius: 22px;
            }
            QLabel {
                color: #3A4440;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                background: transparent;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #D5D3C8;
                border-radius: 12px;
                padding: 8px 12px;
                color: #3B4D46;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
                font-weight: bold;
                selection-background-color: #CBE0D6;
            }
            QLineEdit:focus {
                border-color: #9EC5B5;
            }
            QFrame#PreviewTable {
                background-color: #FAFBF8;
                border: 1px solid #E6E8E2;
                border-radius: 14px;
            }
            QPushButton#BtnClose {
                background-color: #EAECE7;
                color: #5C6B64;
                border: none;
                border-radius: 13px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#BtnClose:hover {
                background-color: #DCE0D8;
            }
            QPushButton#BtnCancel {
                background-color: #F7F8F5;
                color: #5C6B64;
                border: 1px solid #DFR2DC;
                border: 1px solid #DFE2DC;
                border-radius: 16px;
                padding: 7px 18px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#BtnCancel:hover {
                background-color: #ECEEE9;
            }
            QPushButton#BtnConfirm {
                background-color: #CBE0D6;
                color: #3B4D46;
                border: none;
                border-radius: 16px;
                padding: 7px 20px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#BtnConfirm:hover {
                background-color: #B8D4C7;
            }
            """
        )

        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(20, 18, 20, 18)
        vbox.setSpacing(10)

        # 顶部标题行 + 右上角圆形关闭按钮
        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("把文件交给我")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3A4440;")
        lbl_sub = QLabel(f"已接收 {len(self.file_paths)} 个文件 · 在原文件名后直接追加内容")
        lbl_sub.setStyleSheet("font-size: 11px; color: #848E88;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        top_row.addLayout(title_box)
        top_row.addStretch()

        btn_close = QPushButton("×")
        btn_close.setObjectName("BtnClose")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.clicked.connect(self.reject)
        top_row.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignTop)
        vbox.addLayout(top_row)

        # 输入框（直接追加到原词后面）
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入要加在原名后的内容，如 (555) 或 _555")
        self.input_edit.textChanged.connect(self._update_preview_rows)
        self.input_edit.returnPressed.connect(self._do_confirm)
        vbox.addWidget(self.input_edit)

        # 实时预览双列表格（原文件名 | 改名后）
        table_frame = QFrame()
        table_frame.setObjectName("PreviewTable")
        t_layout = QVBoxLayout(table_frame)
        t_layout.setContentsMargins(12, 10, 12, 10)
        t_layout.setSpacing(6)

        hdr_row = QHBoxLayout()
        h1 = QLabel("原文件名")
        h1.setStyleSheet("font-size: 11px; color: #848E88; font-weight: bold;")
        h2 = QLabel("改名后")
        h2.setStyleSheet("font-size: 11px; color: #848E88; font-weight: bold;")
        hdr_row.addWidget(h1, 1)
        hdr_row.addWidget(h2, 1)
        t_layout.addLayout(hdr_row)

        self.preview_rows: list[tuple[QLabel, QLabel]] = []
        for p in self.file_paths[:4]:
            r_layout = QHBoxLayout()
            lbl_orig = QLabel(p.name)
            lbl_orig.setStyleSheet("font-size: 12px; color: #5C6B64;")
            lbl_new = QLabel(p.name)
            lbl_new.setStyleSheet("font-size: 12px; color: #3B4D46; font-weight: bold;")
            r_layout.addWidget(lbl_orig, 1)
            r_layout.addWidget(lbl_new, 1)
            t_layout.addLayout(r_layout)
            self.preview_rows.append((lbl_orig, lbl_new))

        if len(self.file_paths) > 4:
            more_lbl = QLabel(f"… 以及其余 {len(self.file_paths) - 4} 个文件")
            more_lbl.setStyleSheet("font-size: 11px; color: #848E88;")
            t_layout.addWidget(more_lbl)

        vbox.addWidget(table_frame)

        # 底部胶囊按钮行：「再想一下」 | 「确认改名」
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("再想一下")
        btn_cancel.setObjectName("BtnCancel")
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("确认改名")
        btn_ok.setObjectName("BtnConfirm")
        btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_ok.clicked.connect(self._do_confirm)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        vbox.addLayout(btn_row)

        root.addWidget(card)
        self._update_preview_rows()

    @staticmethod
    def build_new_name(orig_path: Path, suffix_str: str) -> str:
        """极简直接追加：在原文件名（stem）后直接加上输入的内容，再拼回扩展名（suffix）"""
        if not suffix_str:
            return orig_path.name
        return f"{orig_path.stem}{suffix_str}{orig_path.suffix}"

    def _update_preview_rows(self):
        raw = self.input_edit.text()
        preview_suffix = raw if raw else "(555)"
        for p, (_, lbl_new) in zip(self.file_paths[:4], self.preview_rows):
            lbl_new.setText(self.build_new_name(p, preview_suffix))

    def _do_confirm(self):
        raw = self.input_edit.text()
        if not raw:
            self.pet.show_speech("还没有输入要追加的内容哦～", force=True)
            self.input_edit.setFocus()
            return
        if self.ILLEGAL_CHARS.search(raw):
            self.pet.show_speech("文件名不能包含 \\ / : * ? \" < > | 字符哦～", force=True)
            return

        success_list = []
        conflict_list = []
        error_list = []

        for p in self.file_paths:
            if not p.exists():
                error_list.append(p.name)
                continue
            new_name = self.build_new_name(p, raw)
            target = p.with_name(new_name)
            if target == p:
                continue
            if target.exists():
                conflict_list.append(target.name)
                continue
            try:
                p.rename(target)
                success_list.append(target.name)
            except Exception:
                error_list.append(p.name)

        self.renamed_count = len(success_list)
        self.accept()

        if success_list:
            self.pet.trigger_click_bounce()
            self.pet.spawn_gentle_particles(count=4, kind="star")
            if len(success_list) == 1 and not conflict_list:
                self.pet.show_speech(f"改好啦～已变成 {success_list[0]}", force=True)
            else:
                msg = f"已更新 {len(success_list)} 个文件名！"
                if conflict_list:
                    msg += f"（跳过同名文件 {len(conflict_list)} 个）"
                self.pet.show_speech(msg, force=True)
        elif conflict_list:
            self.pet.show_speech(f"「{conflict_list[0]}」已存在，未覆盖原文件～", force=True)
        elif error_list:
            self.pet.show_speech(f"部分文件重命名未成功～", force=True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


# ==============================================================================
# 砂金小狐狸主窗口 (ShajinFoxPet v4.0)
# ==============================================================================
class ShajinFoxPet(QWidget):
    """住在桌面上的小狐狸 v4.0"""

    # 基础画布尺寸更紧凑精致，支持 25% ~ 160% 滑块无级缩放
    BASE_CANVAS_W = 310
    BASE_CANVAS_H = 340
    BASE_FOX_W    = 168.0
    BASE_FOX_H    = 196.0

    def __init__(self):
        super().__init__()

        # 1. 状态与设置（默认 scale=0.85 更小巧精致，最小支持 0.25 即约 42px 迷你尺寸！）
        self.scale_factor = 0.85
        self.hunger = 85.0
        self.thirst = 86.0
        self.fun = 88.0
        self.food_in_gut = 20.0
        self.digestion_progress = 25.0
        self.warned_near_poop = False
        self.poops: list[dict] = []

        self.auto_tuck_enabled = True
        self.pin_expanded = False
        self.hide_all_text = False

        self.load_state()

        # 2. 动画状态机与时间轴
        self.last_frame_ts = time.perf_counter()
        self.elapsed_time = 0.0
        self.anim_state = AnimPriorityState.IDLE

        self.breath_phase = random.uniform(0, 6.28)
        self.idle_quirk_timer = random.uniform(5.0, 10.0)
        self.idle_quirk_type = ""
        self.idle_quirk_t = 0.0
        self.idle_quirk_dur = 0.85
        self.idle_tilt_dir = 1.0

        self.is_mouse_inside = False
        self.hover_progress = 0.0
        self.hovered_btn_id = ""
        self.hovered_snack_idx = -1

        self.click_anim_t = 0.0
        self.click_anim_active = False

        self.dragging = False
        self.drag_offset = QPoint()
        self.mouse_down_global = QPoint()
        self.last_drag_global = QPoint()
        self.drag_tilt_deg = 0.0
        self.near_bottom_magnet = False

        # 底部横向胶囊工具栏 & 弹出面板状态
        self.toolbar_prog = 0.0          # 0.0 ~ 1.0
        self.toolbar_hide_countdown = 0.0
        self.food_card_open = False      # 「今天想吃点什么？」1×4 卡片
        self.food_card_prog = 0.0
        self.size_card_open = False      # 大小滑块调节卡片
        self.size_card_prog = 0.0
        self.dragging_slider = False     # 是否正在拖动大小滑块

        # 6 阶段顺序贝塞尔喂食动画
        self.feeding_active = False
        self.feeding_snack: Optional[SnackItem] = None
        self.feeding_elapsed = 0.0
        self.feeding_start_pt = QPointF(155, 160)
        self.feeding_mouth_pt = QPointF(140, 130)
        self.feeding_sparkles_spawned = False

        # 屏幕底部探头收纳状态机
        self.dock_state = DockState.FREE
        self.dock_anim_t = 0.0
        self.dock_sink_progress = 0.0
        self.dock_sink_from = 0.0
        self.dock_sink_to = 0.0
        self.dock_pause_timer = 0.0
        self.dock_untuck_countdown = 0.0

        # 对话气泡与粒子
        self.bubble_text = "摸摸它，陪你工作～"
        self.bubble_hold_timer = 3.5
        self.bubble_alpha_prog = 1.0
        self.particles: list[dict] = []
        self.drag_hover_file = False

        sprite_file = resource_path("assets/pet_sprite.png")
        self.pet_pixmap = QPixmap(str(sprite_file))
        self.snack_pixmaps: dict[str, QPixmap] = {}
        for k in ("cookie", "salmon", "peach", "cocoa"):
            sp = resource_path(f"assets/snack_{k}.png")
            if sp.exists():
                self.snack_pixmaps[k] = QPixmap(str(sp))

        self._init_window()
        self._init_tray()
        self._init_timers()

    # ==========================================================================
    # 窗口与托盘初始化
    # ==========================================================================
    def _init_window(self):
        self.setWindowTitle("住在桌面上的小狐狸 (shajincw)")
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._apply_window_size()

        icon_path = resource_path("assets/pet_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.move(avail.right() - self.width() - 48, avail.bottom() - self.height() - 20)

    def _ui_scale(self) -> float:
        """UI 面板缩放系数：当狐狸缩得很小（如 25%）时，工具栏和文字保持至少 0.72 倍可读尺寸"""
        return max(0.72, min(1.25, self.scale_factor))

    def _apply_window_size(self):
        us = max(self.scale_factor, 0.72)
        w = max(230, int(self.BASE_CANVAS_W * us))
        h = max(250, int(self.BASE_CANVAS_H * us))
        self.setFixedSize(w, h)

    def _init_tray(self):
        icon_path = resource_path("assets/pet_icon.ico")
        tray_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon(self.pet_pixmap)
        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip("住在桌面上的小狐狸 (shajincw)")
        self.tray.setContextMenu(self._build_context_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.dock_state in (DockState.TUCKED, DockState.SINKING):
                self._start_expand_full()
            self.showNormal()
            self.raise_()

    def _init_timers(self):
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._on_frame_tick)
        self.frame_timer.start(AnimConfig.DT_ACTIVE_MS)

        self.bio_timer = QTimer(self)
        self.bio_timer.timeout.connect(self._on_bio_tick)
        self.bio_timer.start(4000)

    def load_state(self):
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.scale_factor = max(0.25, min(1.60, float(data.get("scale_factor", 0.85))))
                self.hunger = float(data.get("hunger", 85.0))
                self.thirst = float(data.get("thirst", 86.0))
                self.fun = float(data.get("fun", 88.0))
                self.food_in_gut = float(data.get("food_in_gut", 20.0))
                self.digestion_progress = float(data.get("digestion_progress", 25.0))
                self.poops = data.get("poops", [])[:3]
                self.auto_tuck_enabled = bool(data.get("auto_tuck_enabled", True))
                self.pin_expanded = bool(data.get("pin_expanded", False))
                self.hide_all_text = bool(data.get("hide_all_text", False))
        except Exception:
            pass

    def save_state(self):
        try:
            data = {
                "scale_factor": round(self.scale_factor, 2),
                "hunger": round(self.hunger, 1),
                "thirst": round(self.thirst, 1),
                "fun": round(self.fun, 1),
                "food_in_gut": round(self.food_in_gut, 1),
                "digestion_progress": round(self.digestion_progress, 1),
                "poops": self.poops[:3],
                "auto_tuck_enabled": self.auto_tuck_enabled,
                "pin_expanded": self.pin_expanded,
                "hide_all_text": self.hide_all_text,
            }
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ==========================================================================
    # 核心坐标与布局（1:1 复刻参考图）
    # ==========================================================================
    def _current_screen_geometry(self) -> QRect:
        center_global = self.geometry().center()
        screen: Optional[QScreen] = QGuiApplication.screenAt(center_global)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1920, 1040)

    def _fox_anchor(self) -> tuple[float, float, float, float]:
        """
        返回狐狸中心 (cx, cy) 与宽高 (fw, fh)。
        - 支持 25% ~ 160% 无级缩放（25% 时仅 42×49px 迷你尺寸）；
        - 收纳时保持狐狸当前大小不变，通过向下位移沉入窗口底边外，仅露耳朵与紫眼睛上半张脸。
        """
        s = self.scale_factor
        us = self._ui_scale()
        fw = self.BASE_FOX_W * s
        fh = self.BASE_FOX_H * s
        cx = self.width() * 0.5
        toolbar_reserve = 46.0 * us
        base_cy = self.height() - toolbar_reserve - (fh * 0.5)
        # 收纳到底部时，狐狸下沉使得窗口底边刚好切在紫眼睛下方（露出顶部 38% 的高度）
        sink_target_cy = self.height() + (fh * 0.5) - (fh * (1.0 - AnimConfig.TUCK_SINK_RATIO))
        cy = base_cy + self.dock_sink_progress * (sink_target_cy - base_cy)
        return cx, cy, fw, fh

    def _get_pill_toolbar_rect(self) -> QRectF:
        """参考图左上角：狐狸正下方居中的全圆角横向胶囊工具栏"""
        us = self._ui_scale()
        tw = 152.0 * us
        th = 34.0 * us
        tx = (self.width() - tw) * 0.5
        ty = self.height() - th - 6.0 * us
        return QRectF(tx, ty, tw, th)

    def _get_pill_toolbar_buttons(self) -> dict[str, QRectF]:
        """胶囊工具栏内的 4 个线性图标按钮：feed(🍴)、rename(Aa)、tuck(⊻)、more(···)"""
        bar = self._get_pill_toolbar_rect()
        keys = ["feed", "rename", "tuck", "more"]
        cell_w = bar.width() / len(keys)
        rects: dict[str, QRectF] = {}
        for i, k in enumerate(keys):
            rects[k] = QRectF(bar.left() + i * cell_w, bar.top(), cell_w, bar.height())
        return rects

    def _get_snack_card_rect(self) -> QRectF:
        """参考图右下角：「今天想吃点什么？」1×4 单行横向点心卡片"""
        us = self._ui_scale()
        cw = min(self.width() - 12.0, 236.0 * us)
        ch = 96.0 * us
        bar = self._get_pill_toolbar_rect()
        cx = (self.width() - cw) * 0.5
        cy = max(8.0, bar.top() - ch - 8.0 * us)
        return QRectF(cx, cy, cw, ch)

    def _get_snack_tile_rects(self) -> list[tuple[SnackItem, QRectF, QRectF]]:
        """返回 4 个点心的 (SnackItem, 圆角方形图标底板QRectF, 整体点击区QRectF)"""
        card = self._get_snack_card_rect()
        us = self._ui_scale()
        pad_x = 10.0 * us
        top_y = card.top() + 28.0 * us
        col_w = (card.width() - pad_x * 2) / 4.0
        tile_sz = min(40.0 * us, col_w - 6.0 * us)
        out = []
        for i, item in enumerate(SNACK_ITEMS):
            col_x = card.left() + pad_x + i * col_w
            tile_x = col_x + (col_w - tile_sz) * 0.5
            tile_r = QRectF(tile_x, top_y, tile_sz, tile_sz)
            hit_r = QRectF(col_x, top_y - 2 * us, col_w, card.height() - 28.0 * us)
            out.append((item, tile_r, hit_r))
        return out

    def _get_size_slider_card_rect(self) -> QRectF:
        """点击工具栏 ··· 弹出的「体型大小滑块 + 状态」轻拟物卡片"""
        us = self._ui_scale()
        cw = min(self.width() - 16.0, 216.0 * us)
        ch = 72.0 * us
        bar = self._get_pill_toolbar_rect()
        cx = (self.width() - cw) * 0.5
        cy = max(8.0, bar.top() - ch - 8.0 * us)
        return QRectF(cx, cy, cw, ch)

    def _get_slider_track_rect(self) -> QRectF:
        card = self._get_size_slider_card_rect()
        us = self._ui_scale()
        return QRectF(card.left() + 16 * us, card.top() + 34 * us, card.width() - 32 * us, 14 * us)

    # ==========================================================================
    # 屏幕底部自动吸附与两段式探头收纳（核心需求）
    # ==========================================================================
    def _distance_to_screen_bottom(self) -> int:
        avail = self._current_screen_geometry()
        return avail.bottom() - (self.y() + self.height())

    def _align_window_to_screen_bottom(self):
        avail = self._current_screen_geometry()
        tx = max(avail.left() + 4, min(self.x(), avail.right() - self.width() - 4))
        ty = avail.bottom() - self.height() + 1
        self.move(tx, ty)

    def _start_sink_to_bottom(self):
        self._align_window_to_screen_bottom()
        self.food_card_open = False
        self.size_card_open = False
        self.dock_state = DockState.SINKING
        self.dock_anim_t = 0.0
        self.dock_sink_from = self.dock_sink_progress
        self.dock_sink_to = 1.0
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def _start_peek_sequence(self):
        if self.dock_state == DockState.SINKING and self.dock_sink_progress < 0.55:
            self._start_expand_full()
            return
        self.dock_state = DockState.PEEKING_STEP1
        self.dock_anim_t = 0.0
        self.dock_sink_from = self.dock_sink_progress
        self.dock_sink_to = AnimConfig.PEEK_STAGE1_RATIO
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def _start_expand_full(self):
        self.dock_state = DockState.EXPANDING
        self.dock_anim_t = 0.0
        self.dock_sink_from = self.dock_sink_progress
        self.dock_sink_to = 0.0
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def _update_dock_state_machine(self, dt: float):
        if self.dock_state == DockState.FREE:
            self.dock_sink_progress = 0.0
            return

        if self.dock_state == DockState.SINKING:
            self.dock_anim_t += dt / AnimConfig.TUCK_DURATION
            k = ease_in_out_cubic(self.dock_anim_t)
            self.dock_sink_progress = self.dock_sink_from + (self.dock_sink_to - self.dock_sink_from) * k
            if self.dock_anim_t >= 1.0:
                self.dock_sink_progress = 1.0
                self.dock_state = DockState.TUCKED

        elif self.dock_state == DockState.PEEKING_STEP1:
            self.dock_anim_t += dt / AnimConfig.PEEK_STAGE1_DUR
            k = ease_out_cubic(self.dock_anim_t)
            self.dock_sink_progress = self.dock_sink_from + (self.dock_sink_to - self.dock_sink_from) * k
            if self.dock_anim_t >= 1.0:
                self.dock_sink_progress = AnimConfig.PEEK_STAGE1_RATIO
                self.dock_state = DockState.PEEKING_PAUSE
                self.dock_pause_timer = AnimConfig.PEEK_PAUSE_DUR

        elif self.dock_state == DockState.PEEKING_PAUSE:
            self.dock_pause_timer -= dt
            if self.dock_pause_timer <= 0.0:
                self._start_expand_full()

        elif self.dock_state == DockState.EXPANDING:
            self.dock_anim_t += dt / AnimConfig.EXPAND_DURATION
            k = ease_out_back(self.dock_anim_t, overshoot=1.10)
            self.dock_sink_progress = max(0.0, self.dock_sink_from + (self.dock_sink_to - self.dock_sink_from) * k)
            if self.dock_anim_t >= 1.0:
                self.dock_sink_progress = 0.0
                self.dock_state = DockState.EXPANDED_HOLD
                self.dock_untuck_countdown = AnimConfig.UNTUCK_HIDE_WAIT

        elif self.dock_state == DockState.EXPANDED_HOLD:
            busy = (
                self.is_mouse_inside
                or self.pin_expanded
                or not self.auto_tuck_enabled
                or self.feeding_active
                or self.food_card_open
                or self.size_card_open
            )
            if busy:
                self.dock_untuck_countdown = AnimConfig.UNTUCK_HIDE_WAIT
            else:
                self.dock_untuck_countdown -= dt
                if self.dock_untuck_countdown <= 0.0:
                    self._start_sink_to_bottom()

    # ==========================================================================
    # 喂食、改名弹窗与滑块调大小
    # ==========================================================================
    def toggle_food_card(self):
        self.size_card_open = False
        self.food_card_open = not self.food_card_open
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)
        self.update()

    def toggle_size_card(self):
        self.food_card_open = False
        self.size_card_open = not self.size_card_open
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)
        self.update()

    def start_feeding_snack(self, snack: SnackItem, start_pt: QPointF):
        self.food_card_open = False
        if self.hunger >= 99.0 and self.food_in_gut >= 88.0 and snack.hunger_gain > 15.0:
            self.trigger_click_bounce()
            self.show_speech("肚子已经圆滚滚啦，消化一会儿再吃吧～")
            return

        cx, cy, fw, fh = self._fox_anchor()
        self.feeding_active = True
        self.feeding_snack = snack
        self.feeding_elapsed = 0.0
        self.feeding_start_pt = QPointF(start_pt)
        self.feeding_mouth_pt = QPointF(cx - fw * 0.05, cy - fh * 0.12)
        self.feeding_sparkles_spawned = False

        self.hunger = max(0.0, min(100.0, self.hunger + snack.hunger_gain))
        self.thirst = max(0.0, min(100.0, self.thirst + snack.thirst_gain))
        self.fun = min(100.0, self.fun + 10.0)
        self.food_in_gut = min(100.0, self.food_in_gut + snack.gut_gain)
        if snack.thirst_gain >= 20.0 and self.food_in_gut > 0:
            boost = min(self.food_in_gut, 10.0)
            self.food_in_gut -= boost
            self.digestion_progress = min(100.0, self.digestion_progress + boost)
            self._check_digestion_to_poop()

        self.save_state()
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def _update_feeding_sequence(self, dt: float):
        if not self.feeding_active:
            return
        self.feeding_elapsed += dt
        if self.feeding_elapsed >= 0.86 and not self.feeding_sparkles_spawned:
            self.feeding_sparkles_spawned = True
            self.spawn_gentle_particles(count=4, kind="mixed", origin=self.feeding_mouth_pt)
            self.show_speech(random.choice(FEED_QUOTES))
        if self.feeding_elapsed >= 1.18:
            self.feeding_active = False
            self.feeding_snack = None

    def _check_digestion_to_poop(self):
        if self.digestion_progress >= 100.0:
            self.digestion_progress = 0.0
            self.warned_near_poop = False
            if len(self.poops) < 3:
                rx = random.choice([-68, -52, 52, 68])
                ry = random.randint(62, 78)
                self.poops.append({"rx": rx, "ry": ry})
                self.trigger_click_bounce()
                self.show_speech(random.choice(POOP_QUOTES))
                self.save_state()

    def set_pet_scale(self, new_scale: float, announce: bool = False):
        old_bottom = self.y() + self.height()
        old_cx = self.x() + self.width() // 2
        self.scale_factor = max(0.25, min(1.60, round(new_scale, 2)))
        self._apply_window_size()
        self.move(old_cx - self.width() // 2, old_bottom - self.height())
        if self.dock_state != DockState.FREE:
            self._align_window_to_screen_bottom()
        if announce:
            self.show_speech(f"大小 {int(self.scale_factor * 100)}%")
        self.save_state()
        self.update()

    def _set_scale_from_slider_x(self, mouse_x: float):
        track = self._get_slider_track_rect()
        ratio = max(0.0, min(1.0, (mouse_x - track.left()) / max(1.0, track.width())))
        # 映射到 0.25 (25%) ~ 1.50 (150%)
        new_scale = 0.25 + ratio * 1.25
        self.set_pet_scale(new_scale, announce=False)

    def open_rename_dialog(self, paths: Optional[list[Path]] = None):
        self.food_card_open = False
        self.size_card_open = False
        if not paths:
            files, _ = QFileDialog.getOpenFileNames(self, "把文件交给我 · 选择要改名的文件")
            if not files:
                return
            paths = [Path(f) for f in files]

        dlg = RenameCardDialog(paths, self)
        avail = self._current_screen_geometry()
        gx = min(avail.right() - dlg.width() - 16, max(avail.left() + 16, self.x() - 40))
        gy = min(avail.bottom() - 280, max(avail.top() + 20, self.y() - 40))
        dlg.move(gx, gy)
        dlg.exec()

    # ==========================================================================
    # 气泡与柔和粒子
    # ==========================================================================
    def show_speech(self, text: str, duration: float = 3.2, force: bool = False):
        if self.hide_all_text and not force:
            return
        self.bubble_text = text
        self.bubble_hold_timer = duration
        if self.bubble_alpha_prog < 0.05:
            self.bubble_alpha_prog = 0.01
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)
        self.update()

    def trigger_click_bounce(self):
        self.click_anim_active = True
        self.click_anim_t = 0.0
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def spawn_gentle_particles(
        self, count: int = 3, kind: str = "mixed", origin: Optional[QPointF] = None
    ):
        cx, cy, fw, fh = self._fox_anchor()
        base_pt = origin if origin is not None else QPointF(cx, cy - fh * 0.22)
        s = self._ui_scale()
        palette = [
            Theme.CHAMPAGNE_GOLD,
            QColor(234, 162, 174, 230),
            QColor(156, 206, 190, 230),
        ]
        for _ in range(count):
            angle = random.uniform(-math.pi * 0.85, -math.pi * 0.15)
            speed = random.uniform(16.0, 30.0) * s
            p_type = kind if kind != "mixed" else random.choice(["heart", "star", "dot"])
            self.particles.append({
                "type": p_type,
                "x": base_pt.x() + random.uniform(-18 * s, 18 * s),
                "y": base_pt.y() + random.uniform(-10 * s, 10 * s),
                "vx": math.cos(angle) * speed * 0.45,
                "vy": -abs(math.sin(angle)) * speed,
                "size": random.uniform(4.2, 6.5) * s,
                "life": 0.0,
                "max_life": random.uniform(0.65, 0.90),
                "color": random.choice(palette),
            })
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    # ==========================================================================
    # 主帧循环与状态优先级
    # ==========================================================================
    def _determine_priority_state(self) -> AnimPriorityState:
        if self.drag_hover_file:
            return AnimPriorityState.FILE_DROP
        if self.dragging:
            return AnimPriorityState.DRAGGING
        if self.feeding_active:
            return AnimPriorityState.FEEDING
        if self.click_anim_active:
            return AnimPriorityState.CLICK_REACT
        if self.dock_state not in (DockState.FREE, DockState.EXPANDED_HOLD):
            return AnimPriorityState.TUCK_DOCK
        return AnimPriorityState.IDLE

    def _on_frame_tick(self):
        now = time.perf_counter()
        dt = min(0.08, max(0.004, now - self.last_frame_ts))
        self.last_frame_ts = now
        self.elapsed_time += dt

        self.anim_state = self._determine_priority_state()
        self.breath_phase += dt * 2.0

        # 悬停放大 3% 缓动
        target_hover = 1.0 if (self.is_mouse_inside or self.drag_hover_file) else 0.0
        step_h = dt / AnimConfig.HOVER_DUR
        if self.hover_progress < target_hover:
            self.hover_progress = min(target_hover, self.hover_progress + step_h)
        elif self.hover_progress > target_hover:
            self.hover_progress = max(target_hover, self.hover_progress - step_h)

        # 底部横向胶囊工具栏淡入/自动隐藏
        should_show_toolbar = (
            (self.is_mouse_inside or self.food_card_open or self.size_card_open or self.toolbar_hide_countdown > 0.0)
            and not self.dragging
            and self.dock_sink_progress < 0.15
        )
        if self.is_mouse_inside or self.food_card_open or self.size_card_open:
            self.toolbar_hide_countdown = AnimConfig.MENU_HIDE_DELAY
        elif self.toolbar_hide_countdown > 0.0:
            self.toolbar_hide_countdown = max(0.0, self.toolbar_hide_countdown - dt)

        if should_show_toolbar:
            self.toolbar_prog = min(1.0, self.toolbar_prog + dt / AnimConfig.MENU_FADE_DUR)
        else:
            self.toolbar_prog = max(0.0, self.toolbar_prog - dt / AnimConfig.MENU_FADE_DUR)
            if self.toolbar_prog <= 0.02:
                self.food_card_open = False
                self.size_card_open = False

        # 点心卡片与滑块卡片缓动
        t_fc = 1.0 if self.food_card_open else 0.0
        if self.food_card_prog < t_fc:
            self.food_card_prog = min(t_fc, self.food_card_prog + dt / 0.18)
        elif self.food_card_prog > t_fc:
            self.food_card_prog = max(t_fc, self.food_card_prog - dt / 0.16)

        t_sc = 1.0 if self.size_card_open else 0.0
        if self.size_card_prog < t_sc:
            self.size_card_prog = min(t_sc, self.size_card_prog + dt / 0.18)
        elif self.size_card_prog > t_sc:
            self.size_card_prog = max(t_sc, self.size_card_prog - dt / 0.16)

        if self.click_anim_active:
            self.click_anim_t += dt / AnimConfig.CLICK_DUR
            if self.click_anim_t >= 1.0:
                self.click_anim_t = 0.0
                self.click_anim_active = False

        if not self.dragging:
            self.drag_tilt_deg *= math.pow(0.001, dt)
            if abs(self.drag_tilt_deg) < 0.05:
                self.drag_tilt_deg = 0.0

        if self.feeding_active:
            self._update_feeding_sequence(dt)

        self._update_dock_state_machine(dt)

        # 待机随机小动作
        if self.anim_state == AnimPriorityState.IDLE and self.dock_sink_progress < 0.1:
            if self.idle_quirk_type:
                self.idle_quirk_t += dt / self.idle_quirk_dur
                if self.idle_quirk_t >= 1.0:
                    self.idle_quirk_type = ""
                    self.idle_quirk_t = 0.0
                    self.idle_quirk_timer = random.uniform(6.0, 13.0)
            else:
                self.idle_quirk_timer -= dt
                if self.idle_quirk_timer <= 0.0:
                    self.idle_quirk_type = random.choice(["tilt", "stretch", "hop"])
                    self.idle_quirk_dur = random.uniform(0.75, 1.10)
                    self.idle_tilt_dir = random.choice([-1.0, 1.0])
                    self.idle_quirk_t = 0.0
        else:
            self.idle_quirk_type = ""
            self.idle_quirk_t = 0.0

        if self.bubble_hold_timer > 0.0:
            self.bubble_hold_timer -= dt
            self.bubble_alpha_prog = min(1.0, self.bubble_alpha_prog + dt / AnimConfig.BUBBLE_IN_DUR)
        else:
            self.bubble_alpha_prog = max(0.0, self.bubble_alpha_prog - dt / AnimConfig.BUBBLE_OUT_DUR)

        for pt in self.particles[:]:
            pt["life"] += dt
            pt["x"] += pt["vx"] * dt
            pt["y"] += pt["vy"] * dt
            pt["vy"] += 20.0 * dt
            if pt["life"] >= pt["max_life"]:
                self.particles.remove(pt)

        has_motion = (
            self.anim_state != AnimPriorityState.IDLE
            or bool(self.idle_quirk_type)
            or bool(self.particles)
            or self.bubble_alpha_prog > 0.01
            or 0.01 < self.toolbar_prog < 0.99
            or 0.01 < self.food_card_prog < 0.99
            or 0.01 < self.size_card_prog < 0.99
            or 0.01 < self.hover_progress < 0.99
        )
        desired_ms = AnimConfig.DT_ACTIVE_MS if has_motion else AnimConfig.DT_IDLE_MS
        if self.frame_timer.interval() != desired_ms:
            self.frame_timer.setInterval(desired_ms)

        self.update()

    def _on_bio_tick(self):
        self.hunger = max(0.0, self.hunger - 0.36)
        self.thirst = max(0.0, self.thirst - 0.42)
        self.fun = max(0.0, self.fun - (0.34 + len(self.poops) * 0.25))

        if self.food_in_gut > 0.1:
            hydration_mult = 1.22 if self.thirst >= 45.0 else 0.72
            step = min(self.food_in_gut, 2.8 * hydration_mult)
            self.food_in_gut = max(0.0, self.food_in_gut - step)
            self.digestion_progress = min(100.0, self.digestion_progress + step * 1.12)
            self._check_digestion_to_poop()

        if (
            self.bubble_alpha_prog <= 0.01
            and not self.hide_all_text
            and self.dock_sink_progress < 0.5
            and random.random() < 0.20
        ):
            if self.poops and random.random() < 0.55:
                self.show_speech(random.choice(POOP_QUOTES))
            elif self.hunger < 32.0:
                self.show_speech(random.choice(HUNGRY_QUOTES))
            elif self.thirst < 32.0:
                self.show_speech(random.choice(THIRSTY_QUOTES))
            else:
                self.show_speech(random.choice(IDLE_QUOTES))

        self.save_state()

    # ==========================================================================
    # 右键菜单
    # ==========================================================================
    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #F5F6F3;
                color: #3A4440;
                border: 1.5px solid #E2E4DE;
                border-radius: 14px;
                padding: 6px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background-color: #CBE0D6;
                color: #3B4D46;
            }
            QMenu::separator {
                height: 1px;
                background: #E2E4DE;
                margin: 4px 8px;
            }
            """
        )

        menu.addAction("🍴 今天想吃点什么？（点心面板）", self.toggle_food_card)
        menu.addAction("Aa 把文件交给我（批量改名）", lambda: self.open_rename_dialog())
        menu.addAction("🎚️ 滑块调节大小与状态面板", self.toggle_size_card)
        if self.poops:
            menu.addAction(f"🧹 清理小便便 ({len(self.poops)})", self._clean_all_poops)

        menu.addSeparator()

        act_tuck = QAction(
            "✓ 开启底部自动探头收纳" if self.auto_tuck_enabled else "○ 开启底部自动探头收纳",
            self,
        )
        act_tuck.triggered.connect(self._toggle_auto_tuck)
        menu.addAction(act_tuck)

        act_pin = QAction(
            "✓ 固定展开（不自动沉回底部）" if self.pin_expanded else "○ 固定展开（不自动沉回底部）",
            self,
        )
        act_pin.triggered.connect(self._toggle_pin_expanded)
        menu.addAction(act_pin)

        if self.dock_state == DockState.FREE:
            menu.addAction("⊻ 立即藏进屏幕底部", self._manual_tuck_now)
        else:
            menu.addAction("🐾 唤出并回到桌面", self._exit_dock_mode)

        menu.addSeparator()
        act_txt = QAction(
            "👁️ 恢复显示文字气泡" if self.hide_all_text else "🙈 隐藏所有文字气泡",
            self,
        )
        act_txt.triggered.connect(self._toggle_hide_text)
        menu.addAction(act_txt)

        menu.addSeparator()
        menu.addAction("🚪 退出小狐狸桌宠", self.quit_pet)
        return menu

    def _clean_all_poops(self):
        self.poops.clear()
        self.fun = min(100.0, self.fun + 10.0)
        self.trigger_click_bounce()
        self.show_speech("清理干净啦～")
        self.save_state()

    def _toggle_auto_tuck(self):
        self.auto_tuck_enabled = not self.auto_tuck_enabled
        if not self.auto_tuck_enabled and self.dock_state != DockState.FREE:
            self._exit_dock_mode()
        self.save_state()

    def _toggle_pin_expanded(self):
        self.pin_expanded = not self.pin_expanded
        if self.pin_expanded and self.dock_state in (DockState.TUCKED, DockState.SINKING):
            self._start_expand_full()
        self.save_state()

    def _manual_tuck_now(self):
        self.auto_tuck_enabled = True
        self.pin_expanded = False
        self._start_sink_to_bottom()

    def _exit_dock_mode(self):
        self.dock_state = DockState.FREE
        self.dock_sink_progress = 0.0
        avail = self._current_screen_geometry()
        self.move(self.x(), max(avail.top() + 20, avail.bottom() - self.height() - 60))
        self.update()

    def _toggle_hide_text(self):
        self.hide_all_text = not self.hide_all_text
        if self.hide_all_text:
            self.bubble_hold_timer = 0.0
            self.bubble_alpha_prog = 0.0
        else:
            self.show_speech("文字气泡已开启～", force=True)
        self.save_state()
        self.update()

    def quit_pet(self):
        self.save_state()
        self.tray.hide()
        QApplication.quit()

    # ==========================================================================
    # 鼠标、滑块拖动与文件拖放事件
    # ==========================================================================
    def enterEvent(self, event):
        self.is_mouse_inside = True
        self.toolbar_hide_countdown = AnimConfig.MENU_HIDE_DELAY
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)
        if self.dock_state in (DockState.TUCKED, DockState.SINKING):
            self._start_peek_sequence()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_mouse_inside = False
        self.hovered_btn_id = ""
        self.hovered_snack_idx = -1
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)
        super().leaveEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier or self.size_card_open:
            step = 0.06 if event.angleDelta().y() > 0 else -0.06
            self.set_pet_scale(self.scale_factor + step, announce=True)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._build_context_menu().exec(event.globalPosition().toPoint())
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()
        s = self.scale_factor
        cx, cy, _, _ = self._fox_anchor()

        # 1. 检查是否正在操作「大小调节滑块卡片」
        if self.size_card_open and self.size_card_prog > 0.5:
            track = self._get_slider_track_rect().adjusted(-8, -8, 8, 8)
            if track.contains(pos):
                self.dragging_slider = True
                self._set_scale_from_slider_x(pos.x())
                return
            if not self._get_size_slider_card_rect().contains(pos) and not self._get_pill_toolbar_rect().contains(pos):
                self.size_card_open = False

        # 2. 检查是否点击了「今天想吃点什么？」1×4 点心卡片
        if self.food_card_open and self.food_card_prog > 0.5:
            for item, tile_r, hit_r in self._get_snack_tile_rects():
                if hit_r.contains(pos):
                    self.start_feeding_snack(item, tile_r.center())
                    return
            if not self._get_snack_card_rect().contains(pos) and not self._get_pill_toolbar_rect().contains(pos):
                self.food_card_open = False

        # 3. 检查是否点击了狐狸正下方的横向胶囊工具栏（🍴 / Aa / ⊻ / ···）
        if self.toolbar_prog > 0.35 and self.dock_sink_progress < 0.25:
            for key, rect in self._get_pill_toolbar_buttons().items():
                if rect.contains(pos):
                    if key == "feed":
                        self.toggle_food_card()
                    elif key == "rename":
                        self.open_rename_dialog()
                    elif key == "tuck":
                        self._manual_tuck_now()
                    elif key == "more":
                        self.toggle_size_card()
                    return

        # 4. 检查是否点击了地面小便便
        for idx, poop in enumerate(self.poops):
            px = cx + poop["rx"] * s
            py = cy + poop["ry"] * s
            if math.hypot(pos.x() - px, pos.y() - py) <= 20 * max(0.7, s):
                self.poops.pop(idx)
                self.spawn_gentle_particles(count=3, kind="star", origin=QPointF(px, py))
                self.show_speech("清理干净啦～")
                self.save_state()
                return

        # 5. 开始拖动或轻点小狐狸
        self.dragging = True
        self.food_card_open = False
        self.size_card_open = False
        gpos = event.globalPosition().toPoint()
        self.mouse_down_global = gpos
        self.last_drag_global = gpos
        self.drag_offset = gpos - self.frameGeometry().topLeft()
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def mouseMoveEvent(self, event):
        pos = event.position()

        if self.dragging_slider and (event.buttons() & Qt.MouseButton.LeftButton):
            self._set_scale_from_slider_x(pos.x())
            return

        if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            gpos = event.globalPosition().toPoint()
            dx = gpos.x() - self.last_drag_global.x()
            self.last_drag_global = gpos

            target_tilt = max(-8.5, min(8.5, dx * 0.6))
            self.drag_tilt_deg = self.drag_tilt_deg * 0.65 + target_tilt * 0.35

            if (gpos - self.mouse_down_global).manhattanLength() > 10 and self.dock_state != DockState.FREE:
                self.dock_state = DockState.FREE
                self.dock_sink_progress = 0.0

            new_top_left = gpos - self.drag_offset
            avail = self._current_screen_geometry()
            dist_bottom = avail.bottom() - (new_top_left.y() + self.height())

            if self.auto_tuck_enabled and -15 <= dist_bottom <= AnimConfig.SNAP_BOTTOM_DIST:
                self.near_bottom_magnet = True
                magnet_y = avail.bottom() - self.height() + 1
                blended_y = int(new_top_left.y() * 0.55 + magnet_y * 0.45)
                self.move(new_top_left.x(), blended_y)
            else:
                self.near_bottom_magnet = False
                self.move(new_top_left)
            return

        # 悬停反馈检测
        hover_btn = ""
        hover_snack = -1
        if self.food_card_open and self.food_card_prog > 0.5:
            for idx, (_, _, hit_r) in enumerate(self._get_snack_tile_rects()):
                if hit_r.contains(pos):
                    hover_snack = idx
                    break
        if hover_snack == -1 and self.toolbar_prog > 0.35 and self.dock_sink_progress < 0.25:
            for key, rect in self._get_pill_toolbar_buttons().items():
                if rect.contains(pos):
                    hover_btn = key
                    break

        if hover_btn != self.hovered_btn_id or hover_snack != self.hovered_snack_idx:
            self.hovered_btn_id = hover_btn
            self.hovered_snack_idx = hover_snack
            self.setCursor(
                QCursor(Qt.CursorShape.PointingHandCursor)
                if (hover_btn or hover_snack >= 0)
                else QCursor(Qt.CursorShape.ArrowCursor)
            )
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging_slider:
                self.dragging_slider = False
                self.save_state()
                return

            if self.dragging:
                self.dragging = False
                self.near_bottom_magnet = False
                gpos = event.globalPosition().toPoint()
                move_dist = (gpos - self.mouse_down_global).manhattanLength()

                if move_dist < 6:
                    if self.dock_state in (DockState.TUCKED, DockState.SINKING):
                        self._start_expand_full()
                    else:
                        self.trigger_click_bounce()
                        self.spawn_gentle_particles(count=random.randint(3, 5), kind="mixed")
                        self.fun = min(100.0, self.fun + 3.5)
                        self.show_speech(random.choice(CLICK_QUOTES))
                else:
                    dist_bottom = self._distance_to_screen_bottom()
                    if self.auto_tuck_enabled and -30 <= dist_bottom <= AnimConfig.SNAP_BOTTOM_DIST:
                        if self.pin_expanded:
                            self._align_window_to_screen_bottom()
                            self.dock_state = DockState.EXPANDED_HOLD
                        else:
                            self._start_sink_to_bottom()
                    else:
                        self.dock_state = DockState.FREE
                        self.dock_sink_progress = 0.0

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
            if urls:
                if self.dock_state in (DockState.TUCKED, DockState.SINKING):
                    self._start_expand_full()
                self.drag_hover_file = True
                self.show_speech("交给我吧～", duration=4.0, force=True)
                self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)
                event.acceptProposedAction()
                self.update()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.drag_hover_file = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self.drag_hover_file = False
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            QTimer.singleShot(30, lambda: self.open_rename_dialog(paths))
        self.update()

    # ==========================================================================
    # 绘制渲染（1:1 复刻参考图视觉）
    # ==========================================================================
    def _compute_fox_transform_params(self) -> tuple[float, float, float, float, float]:
        s = self.scale_factor
        breath_sin = math.sin(self.breath_phase)
        ox = 0.0
        oy = breath_sin * 2.0 * s
        sx = 1.0 - breath_sin * 0.006
        sy = 1.0 + breath_sin * 0.008
        rot = math.sin(self.breath_phase * 0.5) * 0.8

        hk = ease_out_cubic(self.hover_progress)
        oy += AnimConfig.HOVER_LIFT_PX * s * hk
        hover_scale = 1.0 + (AnimConfig.HOVER_SCALE - 1.0) * hk
        sx *= hover_scale
        sy *= hover_scale

        if self.anim_state == AnimPriorityState.FILE_DROP and self.drag_hover_file:
            oy -= 3.0 * s
            rot = math.sin(self.elapsed_time * 5.0) * 2.0
        elif self.anim_state == AnimPriorityState.DRAGGING:
            rot = self.drag_tilt_deg
            oy -= 3.5 * s
        elif self.anim_state == AnimPriorityState.FEEDING:
            t = self.feeding_elapsed
            if 0.22 <= t <= 0.82:
                lean_k = math.sin(((t - 0.22) / 0.60) * math.pi)
                rot -= 5.0 * lean_k
                ox -= 3.0 * s * lean_k
                oy -= 2.0 * s * lean_k
            elif 0.86 < t <= 1.16:
                hop_k = math.sin(((t - 0.86) / 0.30) * math.pi)
                oy -= 8.0 * s * hop_k
                sx *= 1.0 - 0.022 * hop_k
                sy *= 1.0 + 0.028 * hop_k
        elif self.anim_state == AnimPriorityState.CLICK_REACT:
            p = self.click_anim_t
            wave = math.sin(p * math.pi * 2.0) * math.exp(-p * 2.4)
            sx *= 1.0 + 0.042 * wave
            sy *= 1.0 - 0.042 * wave
            oy += 3.0 * s * wave
        elif self.anim_state == AnimPriorityState.IDLE and self.idle_quirk_type:
            qk = math.sin(self.idle_quirk_t * math.pi)
            if self.idle_quirk_type == "tilt":
                rot += 3.8 * self.idle_tilt_dir * qk
            elif self.idle_quirk_type == "stretch":
                sy *= 1.0 + 0.024 * qk
                sx *= 1.0 - 0.015 * qk
                oy -= 2.5 * s * qk
            elif self.idle_quirk_type == "hop":
                oy -= 5.5 * s * qk

        return ox, oy, sx, sy, rot

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        s = self.scale_factor
        us = self._ui_scale()
        cx, cy, fw, fh = self._fox_anchor()
        ox, oy, sx, sy, rot = self._compute_fox_transform_params()
        draw_cx = cx + ox
        draw_cy = cy + oy

        # 1. 地面柔和椭圆浅影
        shadow_vis = max(0.0, 1.0 - self.dock_sink_progress * 1.6)
        if shadow_vis > 0.02:
            sh_w = fw * 0.68 * shadow_vis
            sh_h = 14.0 * s * shadow_vis
            sh_y = cy + fh * 0.43
            grad = QRadialGradient(QPointF(draw_cx, sh_y), sh_w * 0.55)
            grad.setColorAt(0.0, QColor(60, 68, 64, int(42 * shadow_vis)))
            grad.setColorAt(1.0, QColor(60, 68, 64, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawEllipse(QRectF(draw_cx - sh_w / 2.0, sh_y - sh_h / 2.0, sh_w, sh_h))

        # 2. 拖动接近屏幕底边磁吸时的细线提示
        if self.near_bottom_magnet:
            pen = QPen(Theme.CHAMPAGNE_GOLD, 2.0 * us, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(cx - 65 * us), self.height() - 2, int(cx + 65 * us), self.height() - 2)

        # 3. 拖放文件靠近时的柔和香槟金虚线光环
        if self.drag_hover_file:
            painter.save()
            halo_r = QRectF(draw_cx - fw * 0.52, draw_cy - fh * 0.50, fw * 1.04, fh * 0.96)
            pen = QPen(Theme.CHAMPAGNE_GOLD, 2.0 * us, Qt.PenStyle.DashLine)
            pen.setDashOffset(self.elapsed_time * 10.0)
            painter.setPen(pen)
            painter.setBrush(QColor(250, 244, 228, 32))
            painter.drawRoundedRect(halo_r, 32 * s, 32 * s)
            painter.restore()

        # 4. 绘制小狐狸本体（零荧光干净原画）
        if not self.pet_pixmap.isNull():
            painter.save()
            t = QTransform()
            t.translate(draw_cx, draw_cy)
            t.rotate(rot)
            t.scale(sx, sy)
            painter.setTransform(t)
            painter.drawPixmap(
                QRectF(-fw / 2.0, -fh / 2.0, fw, fh),
                self.pet_pixmap,
                QRectF(0, 0, self.pet_pixmap.width(), self.pet_pixmap.height()),
            )
            painter.restore()

        # 5. 绘制地面小便便
        if self.dock_sink_progress < 0.3:
            for poop in self.poops:
                px = cx + poop["rx"] * s
                py = cy + poop["ry"] * s
                self._draw_cute_poop(painter, px, py, max(0.6, s))

        # 6. 绘制 6 阶段贝塞尔喂食飞行点心
        if self.feeding_active and self.feeding_snack is not None:
            self._draw_feeding_flight(painter, us)

        # 7. 绘制小狐狸正下方横向全圆角胶囊工具栏（🍴 / Aa / ⊻ / ···）
        if self.toolbar_prog > 0.02 and self.dock_sink_progress < 0.25:
            self._draw_reference_pill_toolbar(painter, us)

        # 8. 绘制参考图右下角同款「今天想吃点什么？」1×4 横向点心卡片
        if self.food_card_prog > 0.02 and self.dock_sink_progress < 0.25:
            self._draw_reference_snack_card(painter, us)

        # 9. 绘制「滑块调大小 + 状态」悬浮卡片
        if self.size_card_prog > 0.02 and self.dock_sink_progress < 0.25:
            self._draw_size_slider_card(painter, us)

        # 10. 绘制柔和粒子
        self._draw_gentle_particles(painter)

        # 11. 绘制头顶小巧圆角对话气泡
        if not self.hide_all_text and self.bubble_alpha_prog > 0.02 and self.bubble_text:
            self._draw_speech_bubble(painter, draw_cx, draw_cy, fw, fh, us)

    # ==========================================================================
    # 参考图同款组件绘制方法
    # ==========================================================================
    def _draw_frosted_card(self, painter: QPainter, rect: QRectF, radius: float):
        """绘制参考图同款奶油白轻拟物容器（弥散阴影 + 暖灰细外框 + 纯白内高光）"""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Theme.SHADOW_COLOR)
        painter.drawRoundedRect(rect.translated(0, 3.0), radius, radius)

        painter.setBrush(Theme.CARD_BG)
        painter.setPen(QPen(Theme.BORDER_WARM, 1.2))
        painter.drawRoundedRect(rect, radius, radius)

        inner = rect.adjusted(1.2, 1.2, -1.2, -1.2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(Theme.BORDER_INNER, 1.0))
        painter.drawRoundedRect(inner, max(2.0, radius - 1.2), max(2.0, radius - 1.2))

    def _draw_reference_pill_toolbar(self, painter: QPainter, us: float):
        """1:1 绘制参考图左上角：小狐狸下方的横向全圆角胶囊工具栏（4 个线性图标）"""
        painter.save()
        prog = ease_out_cubic(self.toolbar_prog)
        painter.setOpacity(prog)

        bar = self._get_pill_toolbar_rect()
        slide_y = (1.0 - prog) * 6.0 * us
        painter.translate(0, slide_y)

        self._draw_frosted_card(painter, bar, bar.height() * 0.5)

        btns = self._get_pill_toolbar_buttons()
        for key, r in btns.items():
            is_hov = (self.hovered_btn_id == key) or (
                (key == "feed" and self.food_card_open)
                or (key == "more" and self.size_card_open)
            )
            if is_hov:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(Theme.MINT_BTN_BG)
                painter.drawRoundedRect(r.adjusted(4 * us, 4 * us, -4 * us, -4 * us), 12 * us, 12 * us)

            c = r.center()
            pen = QPen(Theme.MINT_BTN_TEXT if is_hov else Theme.ICON_STROKE, 1.7 * us)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            if key == "feed":
                # 🍴 线性小勺子与小叉子并排图标
                sx = c.x() - 3.5 * us
                fx = c.x() + 3.5 * us
                painter.drawEllipse(QPointF(sx, c.y() - 3.5 * us), 2.2 * us, 3.0 * us)
                painter.drawLine(QPointF(sx, c.y() - 0.5 * us), QPointF(sx, c.y() + 6.5 * us))
                painter.drawLine(QPointF(fx - 2.0 * us, c.y() - 6.0 * us), QPointF(fx - 2.0 * us, c.y() - 1.5 * us))
                painter.drawLine(QPointF(fx + 2.0 * us, c.y() - 6.0 * us), QPointF(fx + 2.0 * us, c.y() - 1.5 * us))
                painter.drawLine(QPointF(fx - 2.0 * us, c.y() - 1.5 * us), QPointF(fx + 2.0 * us, c.y() - 1.5 * us))
                painter.drawLine(QPointF(fx, c.y() - 1.5 * us), QPointF(fx, c.y() + 6.5 * us))

            elif key == "rename":
                # Aa 图标
                font = QFont("Microsoft YaHei", max(8, int(9.5 * us)), QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(r, Qt.AlignmentFlag.AlignCenter, "Aa")

            elif key == "tuck":
                # ⊻ 向下箭头落到横线上（收纳至屏幕底边图标）
                painter.drawLine(QPointF(c.x(), c.y() - 6.0 * us), QPointF(c.x(), c.y() + 2.5 * us))
                painter.drawLine(QPointF(c.x() - 4.0 * us, c.y() - 1.2 * us), QPointF(c.x(), c.y() + 2.8 * us))
                painter.drawLine(QPointF(c.x() + 4.0 * us, c.y() - 1.2 * us), QPointF(c.x(), c.y() + 2.8 * us))
                painter.drawLine(QPointF(c.x() - 5.5 * us, c.y() + 5.8 * us), QPointF(c.x() + 5.5 * us, c.y() + 5.8 * us))

            elif key == "more":
                # ··· 三个小圆点图标
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(Theme.MINT_BTN_TEXT if is_hov else Theme.ICON_STROKE)
                for dx in (-5.0 * us, 0.0, 5.0 * us):
                    painter.drawEllipse(QPointF(c.x() + dx, c.y()), 1.5 * us, 1.5 * us)

        painter.restore()

    def _draw_reference_snack_card(self, painter: QPainter, us: float):
        """1:1 绘制参考图右下角：「今天想吃点什么？」1×4 横向点心卡片"""
        painter.save()
        k = ease_out_back(self.food_card_prog, overshoot=1.12)
        painter.setOpacity(min(1.0, self.food_card_prog * 1.15))

        card = self._get_snack_card_rect()
        c = card.center()
        painter.translate(c)
        painter.scale(0.90 + 0.10 * k, 0.90 + 0.10 * k)
        painter.translate(-c)

        self._draw_frosted_card(painter, card, 20.0 * us)

        # 左上角小标题「今天想吃点什么？」
        painter.setPen(Theme.TEXT_TITLE)
        painter.setFont(QFont("Microsoft YaHei", max(8, int(8.5 * us)), QFont.Weight.Bold))
        painter.drawText(
            QRectF(card.left() + 14 * us, card.top() + 7 * us, card.width() - 28 * us, 18 * us),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "今天想吃点什么？",
        )

        # 4 个横向排列的点心项（圆角方形浅底板 + 手绘扁平图标 + 下方文字）
        painter.setFont(QFont("Microsoft YaHei", max(7, int(8.0 * us)), QFont.Weight.Bold))
        for idx, (item, tile_r, hit_r) in enumerate(self._get_snack_tile_rects()):
            is_hov = (self.hovered_snack_idx == idx)
            painter.setPen(QPen(Theme.MINT_BTN_BG if is_hov else Theme.BORDER_WARM, 1.2))
            painter.setBrush(Theme.MINT_BTN_BG if is_hov else Theme.TILE_BG)
            painter.drawRoundedRect(tile_r, 11.0 * us, 11.0 * us)

            self._draw_snack_illustration(painter, item.key, tile_r.center(), tile_r.width() * 0.34)

            painter.setPen(Theme.TEXT_TITLE)
            lbl_r = QRectF(hit_r.left(), tile_r.bottom() + 3 * us, hit_r.width(), 16 * us)
            painter.drawText(lbl_r, Qt.AlignmentFlag.AlignCenter, item.name)

        painter.restore()

    def _draw_snack_illustration(self, painter: QPainter, key: str, center: QPointF, r: float):
        """优先绘制高精度 3D 拟物点心图标 PNG（小饼干、三文鱼、甜桃子、热可可）"""
        painter.save()
        cx, cy = center.x(), center.y()
        pm = self.snack_pixmaps.get(key)
        if pm is not None and not pm.isNull():
            sz = r * 2.45
            painter.drawPixmap(
                QRectF(cx - sz * 0.5, cy - sz * 0.5, sz, sz),
                pm,
                QRectF(0, 0, pm.width(), pm.height()),
            )
            painter.restore()
            return

        if key == "cookie":
            # 小饼干：暖棕黄曲奇 + 巧克力碎点
            painter.setPen(QPen(QColor(180, 132, 76), 1.1))
            painter.setBrush(QColor(234, 190, 126))
            painter.drawEllipse(center, r, r)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(122, 82, 48))
            for dx, dy in ((-0.35, -0.25), (0.28, -0.30), (-0.10, 0.32), (0.32, 0.22)):
                painter.drawEllipse(QPointF(cx + dx * r, cy + dy * r), r * 0.14, r * 0.14)

        elif key == "salmon":
            # 三文鱼：珊瑚粉圆角块 + 三道斜向白色脂肪纹理
            rect = QRectF(cx - r * 1.05, cy - r * 0.68, r * 2.1, r * 1.36)
            painter.setPen(QPen(QColor(216, 118, 98), 1.1))
            painter.setBrush(QColor(244, 152, 132))
            painter.drawRoundedRect(rect, r * 0.38, r * 0.38)
            painter.setPen(QPen(QColor(255, 245, 240, 220), 1.5))
            for ox in (-0.45 * r, 0.0, 0.45 * r):
                painter.drawLine(
                    QPointF(cx + ox - 0.2 * r, cy - 0.45 * r),
                    QPointF(cx + ox + 0.2 * r, cy + 0.45 * r),
                )

        elif key == "peach":
            # 甜桃子：粉嫩水蜜桃 + 顶部薄荷绿小叶子
            painter.setPen(QPen(QColor(218, 128, 142), 1.1))
            painter.setBrush(QColor(246, 176, 186))
            painter.drawEllipse(QPointF(cx, cy + r * 0.1), r * 0.92, r * 0.86)
            # 绿叶
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(138, 198, 166))
            painter.drawEllipse(QPointF(cx + r * 0.25, cy - r * 0.72), r * 0.38, r * 0.20)

        elif key == "cocoa":
            # 热可可：薄荷灰绿马克杯 + 右侧杯柄 + 两缕热气
            cup_r = QRectF(cx - r * 0.75, cy - r * 0.35, r * 1.4, r * 1.25)
            painter.setPen(QPen(QColor(126, 158, 146), 1.3))
            painter.setBrush(QColor(192, 218, 208))
            painter.drawRoundedRect(cup_r, r * 0.28, r * 0.28)
            # 杯柄
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(
                QRectF(cx + r * 0.42, cy - r * 0.15, r * 0.55, r * 0.75),
                -90 * 16,
                180 * 16,
            )
            # 两缕竖向热气
            painter.setPen(QPen(QColor(150, 168, 160, 190), 1.2))
            painter.drawLine(QPointF(cx - r * 0.25, cy - r * 0.55), QPointF(cx - r * 0.25, cy - r * 0.92))
            painter.drawLine(QPointF(cx + r * 0.15, cy - r * 0.55), QPointF(cx + r * 0.15, cy - r * 0.92))

        painter.restore()

    def _draw_size_slider_card(self, painter: QPainter, us: float):
        """绘制点击 ··· 弹出的「滑块无级调大小 (25% ~ 150%) + 饱食/心情简报」卡片"""
        painter.save()
        k = ease_out_back(self.size_card_prog, overshoot=1.10)
        painter.setOpacity(min(1.0, self.size_card_prog * 1.15))

        card = self._get_size_slider_card_rect()
        c = card.center()
        painter.translate(c)
        painter.scale(0.90 + 0.10 * k, 0.90 + 0.10 * k)
        painter.translate(-c)

        self._draw_frosted_card(painter, card, 18.0 * us)

        # 标题行：小狐狸大小 | 百分比
        painter.setPen(Theme.TEXT_TITLE)
        painter.setFont(QFont("Microsoft YaHei", max(7, int(8.2 * us)), QFont.Weight.Bold))
        painter.drawText(
            QRectF(card.left() + 14 * us, card.top() + 8 * us, card.width() - 28 * us, 18 * us),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"小狐狸大小：{int(self.scale_factor * 100)}%",
        )
        painter.setPen(Theme.TEXT_SUB)
        painter.setFont(QFont("Microsoft YaHei", max(7, int(7.5 * us))))
        painter.drawText(
            QRectF(card.left() + 14 * us, card.top() + 8 * us, card.width() - 28 * us, 18 * us),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"饱食 {int(self.hunger)}%",
        )

        # 滑块轨道 (25% ~ 150%)
        track = self._get_slider_track_rect()
        bar_h = 6.0 * us
        bar_y = track.center().y() - bar_h * 0.5
        bar_r = QRectF(track.left(), bar_y, track.width(), bar_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(224, 228, 222))
        painter.drawRoundedRect(bar_r, bar_h * 0.5, bar_h * 0.5)

        ratio = max(0.0, min(1.0, (self.scale_factor - 0.25) / 1.25))
        fill_w = max(bar_h, track.width() * ratio)
        painter.setBrush(Theme.MINT_BTN_BG)
        painter.drawRoundedRect(QRectF(track.left(), bar_y, fill_w, bar_h), bar_h * 0.5, bar_h * 0.5)

        # 滑块圆形手柄
        knob_x = track.left() + track.width() * ratio
        knob_r = 7.5 * us
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(Theme.ICON_STROKE, 1.6 * us))
        painter.drawEllipse(QPointF(knob_x, track.center().y()), knob_r, knob_r)

        painter.restore()

    def _draw_feeding_flight(self, painter: QPainter, us: float):
        t = self.feeding_elapsed
        if t > 0.86 or self.feeding_snack is None:
            return

        p0 = self.feeding_start_pt
        p_float = QPointF(p0.x(), p0.y() - 14.0 * us)
        p_end = self.feeding_mouth_pt
        ctrl = QPointF((p_float.x() + p_end.x()) * 0.5, min(p_float.y(), p_end.y()) - 36.0 * us)

        if t <= 0.18:
            k = ease_out_cubic(t / 0.18)
            cur_pt = QPointF(p0.x(), p0.y() - 14.0 * us * k)
            scale = 0.85 + 0.20 * k
            alpha = 1.0
        elif t <= 0.62:
            k = ease_in_out_cubic((t - 0.18) / 0.44)
            cur_pt = bezier_quad(p_float, ctrl, p_end, k)
            scale = 1.05
            alpha = 1.0
        else:
            k = ease_in_out_cubic((t - 0.62) / 0.24)
            cur_pt = p_end
            scale = max(0.1, 1.05 * (1.0 - k))
            alpha = max(0.0, 1.0 - k)

        painter.save()
        painter.setOpacity(alpha)
        self._draw_snack_illustration(painter, self.feeding_snack.key, cur_pt, 11.0 * us * scale)
        painter.restore()

    def _draw_cute_poop(self, painter: QPainter, px: float, py: float, s: float):
        painter.save()
        painter.setPen(QPen(Theme.ICON_STROKE, 1.3 * s))
        painter.setBrush(QColor(172, 128, 96))
        painter.drawRoundedRect(QRectF(px - 10 * s, py + 2 * s, 20 * s, 6.5 * s), 3 * s, 3 * s)
        painter.drawRoundedRect(QRectF(px - 7.5 * s, py - 3 * s, 15 * s, 6 * s), 3 * s, 3 * s)
        painter.drawEllipse(QRectF(px - 4 * s, py - 7.5 * s, 8 * s, 5.5 * s))
        painter.restore()

    def _draw_gentle_particles(self, painter: QPainter):
        for pt in self.particles:
            prog = pt["life"] / pt["max_life"]
            alpha = math.sin(prog * math.pi)
            col = QColor(pt["color"])
            col.setAlpha(int(210 * max(0.0, min(1.0, alpha))))

            painter.save()
            painter.translate(pt["x"], pt["y"])
            sz = pt["size"] * (0.75 + 0.35 * math.sin(prog * math.pi))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(col)

            if pt["type"] == "heart":
                path = QPainterPath()
                path.moveTo(0, sz * 0.35)
                path.cubicTo(-sz, -sz * 0.35, -sz * 0.5, -sz, 0, -sz * 0.35)
                path.cubicTo(sz * 0.5, -sz, sz, -sz * 0.35, 0, sz * 0.35)
                painter.drawPath(path)
            elif pt["type"] == "star":
                poly = QPolygonF([
                    QPointF(0, -sz),
                    QPointF(sz * 0.28, -sz * 0.28),
                    QPointF(sz, 0),
                    QPointF(sz * 0.28, sz * 0.28),
                    QPointF(0, sz),
                    QPointF(-sz * 0.28, sz * 0.28),
                    QPointF(-sz, 0),
                    QPointF(-sz * 0.28, -sz * 0.28),
                ])
                painter.drawPolygon(poly)
            else:
                painter.drawEllipse(QPointF(0, 0), sz * 0.55, sz * 0.55)
            painter.restore()

    def _draw_speech_bubble(
        self, painter: QPainter, cx: float, cy: float, fw: float, fh: float, us: float
    ):
        painter.save()
        k = ease_out_cubic(self.bubble_alpha_prog)
        painter.setOpacity(k)

        font = QFont("Microsoft YaHei", max(8, int(8.5 * us)), QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()

        max_bw = int(215 * us)
        text_bound = fm.boundingRect(
            QRect(0, 0, max_bw - int(22 * us), 160),
            Qt.TextFlag.TextWordWrap,
            self.bubble_text,
        )
        bw = max(int(84 * us), min(max_bw, text_bound.width() + int(24 * us)))
        bh = max(int(28 * us), text_bound.height() + int(12 * us))

        bx = max(6.0, min(self.width() - bw - 6.0, cx - bw * 0.5))
        float_up = (1.0 - k) * 5.0 * us
        ideal_by = cy - fh * 0.48 - bh - 5.0 * us + float_up
        by = max(4.0, min(self.height() - bh - 10.0, ideal_by))

        rect = QRectF(bx, by, bw, bh)
        self._draw_frosted_card(painter, rect, bh * 0.48)

        painter.setPen(Theme.TEXT_TITLE)
        painter.drawText(
            rect.adjusted(8 * us, 3 * us, -8 * us, -3 * us),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.bubble_text,
        )
        painter.restore()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = ShajinFoxPet()
    pet.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
