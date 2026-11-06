#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
砂金小狐狸桌宠 (shajincw) v3.0 · 完整 UI 与交互升级版
================================================================================
核心特性：
1. 低饱和日系治愈 UI：奶油白、浅薄荷绿、香槟金、柔和紫配色，磨砂质感圆角卡片与统一矢量线条图标。
2. 紧凑透明窗口 + 精确透明区域鼠标穿透（通过 QBitmap 掩码裁剪，绝无大面积透明窗口遮挡桌面）。
3. 统一优先级状态机程序化动画（单张 PNG 驱动）：
   优先级：文件拖放 > 手动拖动 > 喂食互动 > 点击反馈 > 探头收纳 > 待机动画。
4. 弹出式小型精致食物菜单 + 6 阶段顺序贝塞尔曲线喂食动画 + 真实肠胃消化转便意排便系统。
5. 屏幕底部自动吸附与两段式探头收纳（保持原尺寸下沉裁剪仅露半颗脑袋与耳朵，悬停先轻探停顿再完整探出）。
6. 文件拖放添加后缀：悬停抬起+金色虚线光环+「交给我吧～」气泡，同名冲突与非法字符安全保护。
7. 空闲自适应降帧节能机制：活跃动画 60FPS 丝滑过渡，待机静止自动降至 24FPS 低 CPU 占用。
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
    QBitmap,
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
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QWidget,
)


def resource_path(rel_path: str) -> Path:
    """支持 PyInstaller 单文件打包后的资源路径解析"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel_path
    return Path(__file__).resolve().parent / rel_path


STATE_FILE = Path.home() / ".shajincw_pet_v3.json"


# ==============================================================================
# 集中式视觉与动画配置 (Theme & AnimConfig)
# ==============================================================================
class Theme:
    """日系治愈系低饱和配色（奶油白、浅薄荷绿、香槟金、柔和紫、深棕紫描边）"""
    CREAM_WHITE     = QColor(253, 250, 243, 244)  # #FDFAF3 奶油白磨砂底
    CREAM_WARM      = QColor(248, 241, 229, 240)  # #F8F1E5 暖奶油底
    MINT_LIGHT      = QColor(218, 242, 236, 242)  # #DAF2EC 浅薄荷绿底
    MINT_BORDER     = QColor(124, 198, 184, 235)  # #7CC6B8 薄荷青描边
    MINT_ACCENT     = QColor(94, 181, 166, 255)   # #5EB5A6 柔和薄荷主色
    CHAMPAGNE_GOLD  = QColor(236, 206, 148, 245)  # #ECCE94 香槟金
    CHAMPAGNE_SOFT  = QColor(250, 239, 214, 242)  # #FAEFD6 浅香槟底
    LAVENDER_SOFT   = QColor(238, 228, 248, 242)  # #EEE4F8 柔和浅紫底
    LAVENDER_MAIN   = QColor(178, 142, 208, 240)  # #B28ED0 柔和紫描边/强调
    ROSE_SOFT       = QColor(234, 162, 174, 235)  # #EAA2AE 低饱和粉
    TEXT_PRIMARY    = QColor(82, 58, 66, 255)     # #523A42 柔和深棕紫正文
    TEXT_SECONDARY  = QColor(136, 112, 120, 235)  # #887078 次级文字
    SHADOW_SOFT     = QColor(68, 46, 54, 34)      # 柔和投影色

    # 统一圆角与线条规范
    PEN_WIDTH_ICON  = 1.8
    PEN_WIDTH_CARD  = 1.5
    RADIUS_BUBBLE   = 16.0
    RADIUS_MENU     = 18.0
    RADIUS_CAPSULE  = 11.0
    BTN_CIRCLE_SIZE = 32.0


class AnimConfig:
    """统一交互动画时间与参数规范"""
    FPS_ACTIVE        = 60
    FPS_IDLE          = 24
    DT_ACTIVE_MS      = 16
    DT_IDLE_MS        = 42

    HOVER_SCALE       = 1.03        # 悬停放大 3%
    HOVER_LIFT_PX     = -4.0        # 悬停轻微抬起
    HOVER_DUR         = 0.20        # 按钮/角色悬停 200ms (150~250ms)
    CLICK_DUR         = 0.16        # 点击压缩回弹 160ms (120~180ms)
    MENU_FADE_DUR     = 0.22        # 菜单淡入缩放 220ms
    MENU_HIDE_DELAY   = 1.60        # 鼠标移开后隐藏菜单延迟
    BUBBLE_IN_DUR     = 0.22        # 气泡出现时长
    BUBBLE_OUT_DUR    = 0.25        # 气泡淡出时长

    # 底部吸附与两段式探头收纳参数
    SNAP_BOTTOM_DIST  = 42          # 距离屏幕底部 30~50px 触发磁吸
    TUCK_DURATION     = 0.48        # 收纳动画 480ms (350~600ms)
    EXPAND_DURATION   = 0.46        # 展开动画 460ms (350~600ms)
    PEEK_STAGE1_DUR   = 0.18        # 悬停第一阶段轻探时长
    PEEK_PAUSE_DUR    = 0.14        # 悬停轻探短暂停顿
    UNTUCK_HIDE_WAIT  = 1.45        # 鼠标移开后 1.45s (1~2s) 沉回底部
    # 收纳时狐狸下沉偏移量（保持原尺寸，仅露耳朵与上半部分脑袋约 96px）
    TUCK_SINK_RATIO   = 0.63
    PEEK_STAGE1_RATIO = 0.49        # 第一阶段向上先探出一点


class AnimPriorityState(enum.IntEnum):
    """清晰的动画状态优先级（数值越大优先级越高，避免争夺位置或变换属性）"""
    IDLE        = 10  # 待机呼吸 + 随机歪头/轻弹
    TUCK_DOCK   = 20  # 底部探头收纳与展开
    CLICK_REACT = 30  # 单击软弹反馈
    FEEDING     = 40  # 6 阶段顺序喂食动画
    DRAGGING    = 50  # 鼠标手动拖拽与惯性倾斜
    FILE_DROP   = 60  # 文件拖放悬停与处理


class DockState(enum.Enum):
    """屏幕底部探头收纳状态机"""
    FREE           = "free"            # 自由桌面状态
    SINKING        = "sinking"         # 正在缓缓沉入屏幕底部
    TUCKED         = "tucked"          # 已收纳（仅露半颗脑袋和两只耳朵）
    PEEKING_STEP1  = "peeking_step1"   # 鼠标移到脑袋上：先向上探一点
    PEEKING_PAUSE  = "peeking_pause"   # 短暂停顿观察
    EXPANDING      = "expanding"       # 完整探出身体
    EXPANDED_HOLD  = "expanded_hold"   # 完整展开保持中


# ==============================================================================
# 缓动曲线工具函数 (Easing Functions)
# ==============================================================================
def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 4.0 * t * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def ease_out_back(t: float, overshoot: float = 1.35) -> float:
    t = max(0.0, min(1.0, t))
    c3 = overshoot + 1.0
    return 1.0 + c3 * ((t - 1.0) ** 3) + overshoot * ((t - 1.0) ** 2)


def bezier_quad(p0: QPointF, p1: QPointF, p2: QPointF, t: float) -> QPointF:
    u = 1.0 - t
    x = u * u * p0.x() + 2 * u * t * p1.x() + t * t * p2.x()
    y = u * u * p0.y() + 2 * u * t * p1.y() + t * t * p2.y()
    return QPointF(x, y)


# ==============================================================================
# 角色台词与食物配置
# ==============================================================================
CLICK_QUOTES = [
    "唔～摸耳朵会痒的呀。",
    "所有，或者一无所有～今天运气不错哦。",
    "呼噜噜……勉强让你再摸一下下巴。",
    "有文件要加后缀吗？直接拖给我就好～",
    "墨镜才不会掉呢，这可是定制款！",
    "摇摇尾巴～待在你的桌面上真舒服。",
]

IDLE_QUOTES = [
    "（轻轻晃尾巴）今天也是稳赚不赔的一天～",
    "盯——累了的话，记得喝口水休息一下哦。",
    "呼噜……晒着屏幕的光有点犯困了呢。",
    "点数是三枚砂金，好运一直在你身边～",
]

FEED_QUOTES = [
    "好吃～",
    "谢谢款待！",
    "再来一点？",
    "唔～是本总监最喜欢的味道！",
    "幸福感拉满啦～",
]

HUNGRY_QUOTES = [
    "肚子咕噜噜叫了……有小点心吗？",
    "有点饿了呢，投喂一块金珀蛋挞吧～",
]

THIRSTY_QUOTES = [
    "嗓子有点干，想喝星光蜜桃茶～",
    "喝点水才能顺畅消化哦～",
]

BORED_QUOTES = [
    "好安静呀……陪我摇把骰子玩玩吧？",
    "尾巴都快闲得打结啦～",
]

DIGEST_QUOTES = [
    "唔……肚子里的食物快消化完了，咕噜噜……",
]

POOP_QUOTES = [
    "噗——排出来舒服多啦，帮我清一下小便便吧～",
]


@dataclass
class FoodItem:
    key: str
    name: str
    hunger_gain: float
    thirst_gain: float
    gut_gain: float
    color_main: QColor
    color_sub: QColor


FOOD_MENU_ITEMS = [
    FoodItem("tart", "金珀蛋挞", 26.0, 2.0, 34.0, QColor(242, 202, 120), QColor(214, 146, 76)),
    FoodItem("cake", "薄荷奶油糕", 28.0, 5.0, 36.0, QColor(138, 212, 198), QColor(252, 246, 236)),
    FoodItem("tea", "星光蜜桃茶", 8.0, 32.0, 10.0, QColor(232, 168, 186), QColor(250, 232, 238)),
    FoodItem("pudding", "焦糖猫爪冻", 22.0, 12.0, 28.0, QColor(238, 190, 132), QColor(186, 132, 218)),
]


# ==============================================================================
# 白圆角胶囊长条输入框（文件拖放后缀重命名，带安全防冲突检查）
# ==============================================================================
class WhiteCapsuleRenameBar(QWidget):
    """白圆角胶囊长条输入框：支持批量拖放、非法字符过滤、同名冲突保护"""

    ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|]')

    def __init__(self, parent_pet: "ShajinFoxPet"):
        super().__init__(parent_pet)
        self.pet = parent_pet
        self.file_paths: list[Path] = []
        self.hide()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 5, 8, 5)
        layout.setSpacing(6)

        self.file_tag = QLabel("000.jpg")
        self.file_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.file_tag)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入后缀如 555 回车 -> 000(555).jpg")
        self.input_edit.returnPressed.connect(self.confirm_rename)
        layout.addWidget(self.input_edit, 1)

        self.btn_ok = QPushButton("确认")
        self.btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ok.clicked.connect(self.confirm_rename)
        layout.addWidget(self.btn_ok)

        self.btn_close = QPushButton("×")
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.clicked.connect(self.close_bar)
        layout.addWidget(self.btn_close)

        self.setStyleSheet(
            """
            QLabel {
                background-color: #DAF2EC;
                color: #523A42;
                border: 1px solid #7CC6B8;
                border-radius: 11px;
                padding: 2px 9px;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                font-size: 11px;
                font-weight: bold;
            }
            QLineEdit {
                background: transparent;
                border: none;
                color: #523A42;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                font-size: 12px;
                font-weight: bold;
                selection-background-color: #B28ED0;
            }
            QPushButton {
                background-color: #B28ED0;
                color: #FFFFFF;
                border: none;
                border-radius: 11px;
                padding: 3px 10px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #9E78BF;
            }
            """
        )
        self.btn_close.setStyleSheet(
            """
            QPushButton {
                background-color: #F3ECE2;
                color: #523A42;
                border-radius: 10px;
                padding: 1px 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E6DBD0;
            }
            """
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Theme.SHADOW_SOFT)
        painter.drawRoundedRect(rect.translated(0, 2), 18, 18)

        painter.setBrush(QColor(255, 255, 255, 248))
        painter.setPen(QPen(Theme.MINT_BORDER, 1.8))
        painter.drawRoundedRect(rect, 18, 18)

    def open_for_files(self, paths: list[Path]):
        self.file_paths = paths
        first_name = paths[0].name
        if len(first_name) > 13:
            first_name = first_name[:10] + "…"
        self.file_tag.setText(f"{first_name} 等{len(paths)}项" if len(paths) > 1 else first_name)
        self.input_edit.clear()
        self.show()
        self.raise_()
        self.input_edit.setFocus()
        self.pet.update_window_mask()

    def close_bar(self):
        self.hide()
        self.pet.update_window_mask()
        self.pet.update()

    @staticmethod
    def format_new_filename(orig_path: Path, raw_suffix: str) -> str:
        s = raw_suffix.strip()
        if not s:
            return orig_path.name
        stem = orig_path.stem
        ext = orig_path.suffix
        inner = s
        while inner and inner[0] in ("（", "("):
            inner = inner[1:].strip()
        while inner and inner[-1] in ("）", ")"):
            inner = inner[:-1].strip()
        if not inner:
            return orig_path.name
        return f"{stem}({inner}){ext}"

    def confirm_rename(self):
        raw = self.input_edit.text().strip()
        if not raw:
            self.pet.show_speech("请输入要添加的后缀内容哦～", force=True)
            self.input_edit.setFocus()
            return

        if self.ILLEGAL_CHARS.search(raw):
            self.pet.show_speech("后缀不能包含 \\ / : * ? \" < > | 等非法字符哦～", force=True)
            return

        success_names = []
        skipped_conflicts = []
        failed_reasons = []

        for p in self.file_paths:
            if not p.exists():
                failed_reasons.append(f"{p.name} 不存在")
                continue
            new_name = self.format_new_filename(p, raw)
            target = p.with_name(new_name)
            if target == p:
                continue
            # 严禁无提示覆盖已存在的同名文件
            if target.exists():
                skipped_conflicts.append(target.name)
                continue
            try:
                p.rename(target)
                success_names.append(target.name)
            except Exception as exc:
                failed_reasons.append(f"{p.name} ({exc})")

        self.close_bar()

        if success_names:
            self.pet.trigger_click_bounce()
            self.pet.spawn_gentle_particles(count=4, kind="star")
            if len(success_names) == 1 and not skipped_conflicts and not failed_reasons:
                self.pet.show_speech(f"改好啦～已变成「{success_names[0]}」", force=True)
            else:
                msg = f"成功改名 {len(success_names)} 个文件！"
                if skipped_conflicts:
                    msg += f"（跳过同名冲突 {len(skipped_conflicts)} 个）"
                self.pet.show_speech(msg, force=True)
        else:
            if skipped_conflicts:
                self.pet.show_speech(f"目标文件「{skipped_conflicts[0]}」已存在，未覆盖原文件～", force=True)
            elif failed_reasons:
                self.pet.show_speech(f"改名未成功：{failed_reasons[0]}", force=True)


# ==============================================================================
# 砂金小狐狸主窗口 (ShajinFoxPet)
# ==============================================================================
class ShajinFoxPet(QWidget):
    """精致灵动的 Windows 砂金小狐狸桌面宠物"""

    CANVAS_W = 380
    CANVAS_H = 440

    def __init__(self):
        super().__init__()

        # 1. 可持久化配置与生理状态
        self.scale_factor = 1.0
        self.hunger = 84.0              # 饱食度 (0~100)
        self.thirst = 86.0              # 水分值 (0~100)
        self.fun = 85.0                 # 心情值 (0~100)
        self.food_in_gut = 20.0         # 肠胃待消化食物量
        self.digestion_progress = 25.0  # 便意进度 (0~100%，满100%排便)
        self.warned_near_poop = False
        self.poops: list[dict] = []

        self.auto_tuck_enabled = True   # 是否开启底部自动探头收纳
        self.pin_expanded = False       # 是否固定展开（不自动沉回底部）
        self.hide_all_text = False      # 是否隐藏所有文字与胶囊

        self.load_state()

        # 2. 动画状态机与时间轴
        self.last_frame_ts = time.perf_counter()
        self.elapsed_time = 0.0
        self.anim_state = AnimPriorityState.IDLE

        # 待机程序化微动画（呼吸 + 随机歪头/轻弹）
        self.breath_phase = random.uniform(0, 6.28)
        self.idle_quirk_timer = random.uniform(4.5, 9.0)
        self.idle_quirk_type = ""       # "tilt" | "stretch" | "hop"
        self.idle_quirk_t = 0.0
        self.idle_quirk_dur = 0.85
        self.idle_tilt_dir = 1.0

        # 鼠标悬停缓动状态
        self.is_mouse_inside = False
        self.hover_progress = 0.0       # 0.0 -> 1.0 (200ms 缓动)
        self.hovered_btn_id = ""
        self.btn_hover_prog: dict[str, float] = {}

        # 单击压缩回弹状态
        self.click_anim_t = 0.0
        self.click_anim_active = False

        # 拖拽平滑跟随与方向倾斜
        self.dragging = False
        self.drag_offset = QPoint()
        self.mouse_down_global = QPoint()
        self.last_drag_global = QPoint()
        self.drag_tilt_deg = 0.0        # 根据拖动水平速度产生的平滑倾斜角
        self.near_bottom_magnet = False # 拖动接近底部 30~50px 时的磁吸微反馈

        # 环绕式精致圆形菜单 & 弹出式小型食物菜单
        self.menu_visible_prog = 0.0    # 0.0 ~ 1.0 (淡入、缩放、轻微位移)
        self.menu_hide_countdown = 0.0
        self.food_menu_open = False
        self.food_menu_prog = 0.0       # 0.0 ~ 1.0

        # 6 阶段顺序喂食动画状态
        self.feeding_active = False
        self.feeding_food: Optional[FoodItem] = None
        self.feeding_elapsed = 0.0
        self.feeding_start_pt = QPointF(190, 210)
        self.feeding_mouth_pt = QPointF(172, 186)
        self.feeding_sparkles_spawned = False
        self.feeding_bounce_done = False

        # 屏幕底部自动吸附与探头收纳状态机
        self.dock_state = DockState.FREE
        self.dock_anim_t = 0.0
        self.dock_sink_progress = 0.0   # 0.0=完全展开, 1.0=完全收纳(仅露耳朵与半颗头)
        self.dock_sink_from = 0.0
        self.dock_sink_to = 0.0
        self.dock_pause_timer = 0.0
        self.dock_untuck_Countdown = 0.0
        self.dock_screen_bottom = 0

        # 气泡淡入/微缩放/上浮/淡出状态
        self.bubble_text = "喵呜～我是你的桌面小狐狸砂金，拖到屏幕底边会偷偷藏起来哦～"
        self.bubble_hold_timer = 4.2
        self.bubble_alpha_prog = 1.0

        # 柔和低饱和粒子系统
        self.particles: list[dict] = []
        self.drag_hover_file = False

        # 加载透明背景砂金小狐狸 PNG
        sprite_file = resource_path("assets/pet_sprite.png")
        self.pet_pixmap = QPixmap(str(sprite_file))

        self._init_window()
        self.rename_bar = WhiteCapsuleRenameBar(self)
        self._layout_rename_bar()
        self._init_tray()
        self._init_timers()
        self.update_window_mask()

    # ==========================================================================
    # 初始化与窗口管理
    # ==========================================================================
    def _init_window(self):
        self.setWindowTitle("砂金小狐狸桌宠 (shajincw)")
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._apply_scale_size()

        icon_path = resource_path("assets/pet_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.move(avail.right() - self.width() - 48, avail.bottom() - self.height() - 18)

    def _apply_scale_size(self):
        w = int(self.CANVAS_W * self.scale_factor)
        h = int(self.CANVAS_H * self.scale_factor)
        self.setFixedSize(w, h)
        if hasattr(self, "rename_bar"):
            self._layout_rename_bar()

    def _layout_rename_bar(self):
        s = self.scale_factor
        bw = min(self.width() - 12, max(285, int(348 * s)))
        bh = 40
        bx = (self.width() - bw) // 2
        by = int(self.height() - 62 * s)
        self.rename_bar.setGeometry(bx, by, bw, bh)

    def _init_tray(self):
        icon_path = resource_path("assets/pet_icon.ico")
        tray_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon(self.pet_pixmap)
        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip("砂金小狐狸桌宠 (shajincw)")
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
                self.scale_factor = max(0.65, min(1.55, float(data.get("scale_factor", 1.0))))
                self.hunger = float(data.get("hunger", 84.0))
                self.thirst = float(data.get("thirst", 86.0))
                self.fun = float(data.get("fun", 85.0))
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
    # 多显示器与任务栏工作区感知 + 窗口精确裁剪掩码 (防止透明大窗口遮挡桌面)
    # ==========================================================================
    def _current_screen_geometry(self) -> QRect:
        """获取狐狸当前所在显示器的工作区（自动避开 Windows 任务栏，支持多屏与高 DPI）"""
        center_global = self.geometry().center()
        screen: Optional[QScreen] = QGuiApplication.screenAt(center_global)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
        return QRect(0, 0, 1920, 1040)

    def _fox_anchor(self) -> tuple[float, float, float, float]:
        """
        返回狐狸绘制中心 (cx, cy) 与绘制宽高 (fw, fh)。
        探头收纳时：保持狐狸原有大小 fw, fh 完全不变，通过向下增加 sink_y 实现真实下沉裁剪！
        """
        s = self.scale_factor
        fw = 236.0 * s
        fh = 276.0 * s
        cx = self.width() * 0.5
        base_cy = self.height() - (fh * 0.5) - 34.0 * s
        # 当处于底部收纳时，向下位移使下半身移出窗口底边之外，仅留耳朵与上半颗脑袋在窗口底部内
        max_sink_px = fh * AnimConfig.TUCK_SINK_RATIO + 34.0 * s
        sink_offset_y = self.dock_sink_progress * max_sink_px
        cy = base_cy + sink_offset_y
        return cx, cy, fw, fh

    def update_window_mask(self):
        """
        动态计算非透明交互区域的 QBitmap 窗口掩码：
        - 只有狐狸身体（或收纳时露出的半颗脑袋）、可见菜单、便便、改名输入框接收鼠标事件；
        - 其余透明区域 100% 穿透点击到底层 Windows 桌面图标与窗口！
        - 同时保证收纳状态下露出的脑袋 100% 能接收鼠标悬停唤出事件！
        """
        bmp = QBitmap(self.size())
        bmp.fill(Qt.GlobalColor.color0)
        p = QPainter(bmp)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(Qt.GlobalColor.color1)

        s = self.scale_factor
        cx, cy, fw, fh = self._fox_anchor()

        # 1. 狐狸本体热区（包含收纳状态下露出底部的脑袋与双耳区域）
        fox_rect = QRectF(cx - fw * 0.48, cy - fh * 0.50, fw * 0.96, fh * 0.98)
        p.drawRoundedRect(fox_rect, 40 * s, 40 * s)

        # 2. 若功能按钮菜单可见，加入按钮与胶囊热区
        if self.menu_visible_prog > 0.05 and self.dock_sink_progress < 0.25:
            for rect in self._get_circular_button_rects().values():
                p.drawEllipse(rect.adjusted(-4, -4, 4, 4))
            if not self.hide_all_text:
                p.drawRoundedRect(self._get_status_strip_rect().adjusted(-4, -4, 4, 4), 12, 12)

        # 3. 若小型食物菜单打开，加入食物菜单卡片热区
        if self.food_menu_open and self.food_menu_prog > 0.05:
            p.drawRoundedRect(self._get_food_menu_rect().adjusted(-6, -6, 6, 6), 18, 18)

        # 4. 地面便便热区
        for poop in self.poops:
            px = cx + poop["rx"] * s
            py = cy + poop["ry"] * s
            p.drawEllipse(QPointF(px, py), 22 * s, 22 * s)

        # 5. 白圆角胶囊改名条热区
        if self.rename_bar.isVisible():
            p.drawRoundedRect(QRectF(self.rename_bar.geometry()).adjusted(-4, -4, 4, 4), 18, 18)

        p.end()
        self.setMask(bmp)

    # ==========================================================================
    # 屏幕底部自动吸附与两段式探头收纳系统（核心需求四）
    # ==========================================================================
    def _distance_to_screen_bottom(self) -> int:
        avail = self._current_screen_geometry()
        fox_bottom_global = self.y() + self.height()
        return avail.bottom() - fox_bottom_global

    def _align_window_to_screen_bottom(self):
        avail = self._current_screen_geometry()
        target_x = max(avail.left() + 6, min(self.x(), avail.right() - self.width() - 6))
        target_y = avail.bottom() - self.height() + 2
        self.move(target_x, target_y)

    def _start_sink_to_bottom(self):
        """松开鼠标或移开延迟到达后：平滑沉入屏幕底部进入探头收纳状态"""
        self._align_window_to_screen_bottom()
        self.food_menu_open = False
        self.dock_state = DockState.SINKING
        self.dock_anim_t = 0.0
        self.dock_sink_from = self.dock_sink_progress
        self.dock_sink_to = 1.0
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def _start_peek_sequence(self):
        """
        鼠标移到露出的半颗脑袋上：
        先向上探出一点 (PEEK_STAGE1_RATIO) -> 短暂停顿 (140ms) -> 再完整探出身体 (0.0)
        支持随时中断正在下沉的动画！
        """
        if self.dock_state == DockState.SINKING and self.dock_sink_progress < 0.55:
            # 还没沉到底就重新靠近：直接平滑展开到完整身体
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
            self.update_window_mask()
            if self.dock_anim_t >= 1.0:
                self.dock_sink_progress = 1.0
                self.dock_state = DockState.TUCKED
                self.update_window_mask()

        elif self.dock_state == DockState.PEEKING_STEP1:
            self.dock_anim_t += dt / AnimConfig.PEEK_STAGE1_DUR
            k = ease_out_cubic(self.dock_anim_t)
            self.dock_sink_progress = self.dock_sink_from + (self.dock_sink_to - self.dock_sink_from) * k
            self.update_window_mask()
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
            k = ease_out_back(self.dock_anim_t, overshoot=1.12)
            self.dock_sink_progress = max(0.0, self.dock_sink_from + (self.dock_sink_to - self.dock_sink_from) * k)
            self.update_window_mask()
            if self.dock_anim_t >= 1.0:
                self.dock_sink_progress = 0.0
                self.dock_state = DockState.EXPANDED_HOLD
                self.dock_untuck_Countdown = AnimConfig.UNTUCK_HIDE_WAIT
                self.update_window_mask()

        elif self.dock_state == DockState.EXPANDED_HOLD:
            # 鼠标移开且未固定展开、未在喂食或打开菜单时，延迟 1.45s 沉回底部
            busy = (
                self.is_mouse_inside
                or self.pin_expanded
                or not self.auto_tuck_enabled
                or self.feeding_active
                or self.food_menu_open
                or self.rename_bar.isVisible()
            )
            if busy:
                self.dock_untuck_Countdown = AnimConfig.UNTUCK_HIDE_WAIT
            else:
                self.dock_untuck_Countdown -= dt
                if self.dock_untuck_Countdown <= 0.0:
                    self._start_sink_to_bottom()

    # ==========================================================================
    # 喂食系统：小型食物菜单 + 6 阶段顺序贝塞尔曲线动画（核心需求三）
    # ==========================================================================
    def toggle_food_menu(self):
        self.food_menu_open = not self.food_menu_open
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)
        self.update_window_mask()
        self.update()

    def start_feeding_sequence(self, food: FoodItem, click_pos: QPointF):
        """
        选择食物后触发严格的 6 阶段顺序喂食动画：
        阶段 1 (0.00 ~ 0.18s)：食物从菜单位置轻轻浮起；
        阶段 2 (0.18 ~ 0.62s)：沿柔和的贝塞尔曲线飞向狐狸嘴边；
        阶段 3 (0.35 ~ 0.72s)：狐狸稍微前倾，模拟迎接食物；
        阶段 4 (0.62 ~ 0.86s)：食物在嘴边逐渐缩小、淡出，模拟被吃掉；
        阶段 5 (0.86 ~ 1.15s)：狐狸轻轻弹跳，出现少量低饱和金色星星或爱心；
        阶段 6 (0.92s)：随机显示「好吃～」「谢谢款待！」「再来一点？」等小气泡。
        """
        self.food_menu_open = False
        if self.hunger >= 99.0 and self.food_in_gut >= 88.0:
            self.trigger_click_bounce()
            self.show_speech("肚子已经圆滚滚啦，消化一会儿再吃吧～")
            return

        cx, cy, fw, fh = self._fox_anchor()
        self.feeding_active = True
        self.feeding_food = food
        self.feeding_elapsed = 0.0
        self.feeding_start_pt = QPointF(click_pos)
        # 砂金小狐狸嘴部坐标（位于中心偏左上）
        self.feeding_mouth_pt = QPointF(cx - fw * 0.05, cy - fh * 0.13)
        self.feeding_sparkles_spawned = False
        self.feeding_bounce_done = False

        # 真实生理指标更新
        self.hunger = min(100.0, self.hunger + food.hunger_gain)
        self.thirst = min(100.0, self.thirst + food.thirst_gain)
        self.food_in_gut = min(100.0, self.food_in_gut + food.gut_gain)
        self.save_state()
        self.update_window_mask()
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def _update_feeding_sequence(self, dt: float):
        if not self.feeding_active:
            return
        self.feeding_elapsed += dt
        t = self.feeding_elapsed

        # 阶段 5 & 6：0.86s 食物吃完瞬间，触发轻弹、柔和星心粒子与美食气泡
        if t >= 0.86 and not self.feeding_sparkles_spawned:
            self.feeding_sparkles_spawned = True
            self.spawn_gentle_particles(count=4, kind="mixed", origin=self.feeding_mouth_pt)
            self.show_speech(random.choice(FEED_QUOTES))

        if t >= 1.18:
            self.feeding_active = False
            self.feeding_food = None

    # ==========================================================================
    # 其他互动功能（喝水、玩玩具、消化排便、铲屎）
    # ==========================================================================
    def action_drink(self):
        self.food_menu_open = False
        tea = FOOD_MENU_ITEMS[2]  # 星光蜜桃茶
        btn_rects = self._get_circular_button_rects()
        start_pt = btn_rects["drink"].center() if "drink" in btn_rects else QPointF(self.width() * 0.3, self.height() * 0.5)
        self.start_feeding_sequence(tea, start_pt)
        # 喝水温和促进肠胃消化
        if self.food_in_gut > 0:
            step = min(self.food_in_gut, 12.0)
            self.food_in_gut -= step
            self.digestion_progress = min(100.0, self.digestion_progress + step * 1.1)
            self._check_digestion_to_poop()

    def action_play_toy(self):
        self.food_menu_open = False
        self.fun = min(100.0, self.fun + 26.0)
        self.hunger = max(0.0, self.hunger - 3.0)
        self.thirst = max(0.0, self.thirst - 3.0)
        if self.food_in_gut > 0:
            step = min(self.food_in_gut, 7.0)
            self.food_in_gut -= step
            self.digestion_progress = min(100.0, self.digestion_progress + step)

        self.trigger_click_bounce()
        self.spawn_gentle_particles(count=4, kind="star")
        pts = random.randint(1, 6)
        self.show_speech(random.choice([
            f"叮～金色骰子转出了 {pts} 点，和朋友玩真开心！",
            "喵呜～（扑向小筹码）心情变好啦！",
            f"是 {pts} 点呢，今天好运站在我们这边～",
        ]))
        self._check_digestion_to_poop()
        self.save_state()

    def _check_digestion_to_poop(self):
        if self.digestion_progress >= 82.0 and not self.warned_near_poop:
            self.warned_near_poop = True
            self.show_speech(random.choice(DIGEST_QUOTES))
        if self.digestion_progress >= 100.0:
            self.digestion_progress = 0.0
            self.warned_near_poop = False
            self.spawn_poop()

    def spawn_poop(self):
        if len(self.poops) >= 3:
            return
        rx = random.choice([-105, -82, 82, 105])
        ry = random.randint(92, 112)
        self.poops.append({"rx": rx, "ry": ry})
        self.trigger_click_bounce()
        self.show_speech(random.choice(POOP_QUOTES))
        self.save_state()
        self.update_window_mask()

    def action_clean_poop(self):
        self.food_menu_open = False
        if not self.poops:
            self.show_speech("地板干干净净的，吃饱消化满 100% 才会拉便便哦～")
            return
        cx, cy, _, _ = self._fox_anchor()
        for p in self.poops:
            pt = QPointF(cx + p["rx"] * self.scale_factor, cy + p["ry"] * self.scale_factor)
            self.spawn_gentle_particles(count=3, kind="star", origin=pt)
        self.poops.clear()
        self.fun = min(100.0, self.fun + 10.0)
        self.trigger_click_bounce()
        self.show_speech("打扫干净啦，空气都变得香香的～谢谢你！")
        self.save_state()
        self.update_window_mask()

    # ==========================================================================
    # 气泡与低饱和轻盈粒子系统
    # ==========================================================================
    def show_speech(self, text: str, duration: float = 3.6, force: bool = False):
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
        """生成 2~5 个细小、柔和、低饱和的小爱心、四角星或香槟金光点"""
        cx, cy, fw, fh = self._fox_anchor()
        base_pt = origin if origin is not None else QPointF(cx, cy - fh * 0.22)
        s = self.scale_factor

        palette = [
            Theme.CHAMPAGNE_GOLD,
            Theme.ROSE_SOFT,
            Theme.MINT_BORDER,
            Theme.LAVENDER_MAIN,
        ]
        for i in range(count):
            angle = random.uniform(-math.pi * 0.85, -math.pi * 0.15)
            speed = random.uniform(18.0, 34.0) * s
            p_type = kind if kind != "mixed" else random.choice(["heart", "star", "dot"])
            self.particles.append({
                "type": p_type,
                "x": base_pt.x() + random.uniform(-24 * s, 24 * s),
                "y": base_pt.y() + random.uniform(-12 * s, 12 * s),
                "vx": math.cos(angle) * speed * 0.45,
                "vy": -abs(math.sin(angle)) * speed,
                "size": random.uniform(4.5, 7.2) * s,
                "life": 0.0,
                "max_life": random.uniform(0.65, 0.95),
                "color": random.choice(palette),
            })
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    # ==========================================================================
    # 布局坐标与屏幕边缘自动避让（防越界）
    # ==========================================================================
    def _is_near_left_edge(self) -> bool:
        avail = self._current_screen_geometry()
        return (self.x() - avail.left()) < 90

    def _is_near_right_edge(self) -> bool:
        avail = self._current_screen_geometry()
        return (avail.right() - (self.x() + self.width())) < 90

    def _is_near_top_edge(self) -> bool:
        avail = self._current_screen_geometry()
        return (self.y() - avail.top()) < 75

    def _get_circular_button_rects(self) -> dict[str, QRectF]:
        """
        在狐狸身侧弧形排列 5 个精致小圆形图标按钮：
        feed(喂食)、drink(喝水)、play(玩耍)、clean(铲屎)、rename(改名)
        根据屏幕左右边缘自动调整在狐狸左侧或右侧展开，绝不超出屏幕！
        """
        s = self.scale_factor
        cx, cy, fw, fh = self._fox_anchor()
        btn_d = Theme.BTN_CIRCLE_SIZE * s
        place_right = self._is_near_left_edge() and not self._is_near_right_edge()
        side_sign = 1.0 if place_right else -1.0

        keys = ["feed", "drink", "play", "clean", "rename"]
        angles_deg = [-44, -22, 0, 22, 44]
        radius_x = fw * 0.54
        radius_y = fh * 0.46

        # 结合菜单展开动画产生轻微位移与缩放
        slide = (1.0 - ease_out_cubic(self.menu_visible_prog)) * 14.0 * s
        rects: dict[str, QRectF] = {}
        for k, deg in zip(keys, angles_deg):
            rad = math.radians(deg)
            bx = cx + side_sign * (radius_x * math.cos(rad) - slide)
            by = cy + radius_y * math.sin(rad)
            rects[k] = QRectF(bx - btn_d / 2.0, by - btn_d / 2.0, btn_d, btn_d)
        return rects

    def _get_status_strip_rect(self) -> QRectF:
        """狐狸脚下轻盈紧凑的磨砂胶囊状态条"""
        s = self.scale_factor
        cx, cy, fw, fh = self._fox_anchor()
        sw = 228.0 * s
        sh = 22.0 * s
        sy = min(self.height() - sh - 6 * s, cy + fh * 0.47)
        return QRectF(cx - sw / 2.0, sy, sw, sh)

    def _get_food_menu_rect(self) -> QRectF:
        """点击喂食按钮后在狐狸旁边弹出的精致小型食物菜单（自动避让屏幕边缘）"""
        s = self.scale_factor
        cx, cy, fw, _ = self._fox_anchor()
        mw = 136.0 * s
        mh = 148.0 * s
        place_right = not self._is_near_right_edge()
        mx = (cx + fw * 0.28) if place_right else (cx - fw * 0.28 - mw)
        mx = max(6.0, min(self.width() - mw - 6.0, mx))
        my = max(16.0, min(self.height() - mh - 36.0, cy - mh * 0.5))
        return QRectF(mx, my, mw, mh)

    def _get_food_item_rects(self) -> list[tuple[FoodItem, QRectF]]:
        menu_r = self._get_food_menu_rect()
        s = self.scale_factor
        pad_x = 8.0 * s
        pad_top = 28.0 * s
        row_h = 28.0 * s
        out = []
        for idx, item in enumerate(FOOD_MENU_ITEMS):
            r = QRectF(
                menu_r.left() + pad_x,
                menu_r.top() + pad_top + idx * (row_h + 2 * s),
                menu_r.width() - pad_x * 2,
                row_h,
            )
            out.append((item, r))
        return out

    # ==========================================================================
    # 主动画状态机与帧循环 (60FPS 活跃 / 24FPS 空闲节能)
    # ==========================================================================
    def _determine_priority_state(self) -> AnimPriorityState:
        """严格按照优先级确定当前主导动画状态，杜绝多个动画冲突"""
        if self.drag_hover_file or self.rename_bar.isVisible():
            return AnimPriorityState.FILE_DROP
        if self.dragging:
            return AnimPriorityState.DRAGGING
        if self.feeding_active:
            return AnimPriorityState.FEEDING
        if self.click_anim_active:
            return AnimPriorityState.CLICK_REACT
        if self.dock_state != DockState.FREE and self.dock_state != DockState.EXPANDED_HOLD:
            return AnimPriorityState.TUCK_DOCK
        return AnimPriorityState.IDLE

    def _on_frame_tick(self):
        now = time.perf_counter()
        dt = min(0.08, max(0.004, now - self.last_frame_ts))
        self.last_frame_ts = now
        self.elapsed_time += dt

        self.anim_state = self._determine_priority_state()

        # 1. 呼吸相位持续推进（极小幅度）
        self.breath_phase += dt * 2.1

        # 2. 鼠标悬停缓动 (200ms)
        target_hover = 1.0 if (self.is_mouse_inside or self.drag_hover_file) else 0.0
        step_h = dt / AnimConfig.HOVER_DUR
        if self.hover_progress < target_hover:
            self.hover_progress = min(target_hover, self.hover_progress + step_h)
        elif self.hover_progress > target_hover:
            self.hover_progress = max(target_hover, self.hover_progress - step_h)

        # 按钮悬停缩放缓动 (180ms)
        for k in ("feed", "drink", "play", "clean", "rename"):
            t_val = 1.0 if self.hovered_btn_id == k else 0.0
            cur = self.btn_hover_prog.get(k, 0.0)
            if cur < t_val:
                self.btn_hover_prog[k] = min(t_val, cur + dt / 0.18)
            elif cur > t_val:
                self.btn_hover_prog[k] = max(t_val, cur - dt / 0.18)

        # 3. 环绕菜单淡入/淡出与非交互自动隐藏
        should_show_menu = (
            (self.is_mouse_inside or self.food_menu_open or self.menu_hide_countdown > 0.0)
            and not self.dragging
            and self.dock_sink_progress < 0.15
        )
        if self.is_mouse_inside or self.food_menu_open:
            self.menu_hide_countdown = AnimConfig.MENU_HIDE_DELAY
        elif self.menu_hide_countdown > 0.0:
            self.menu_hide_countdown = max(0.0, self.menu_hide_countdown - dt)

        old_menu_vis = self.menu_visible_prog > 0.05
        if should_show_menu:
            self.menu_visible_prog = min(1.0, self.menu_visible_prog + dt / AnimConfig.MENU_FADE_DUR)
        else:
            self.menu_visible_prog = max(0.0, self.menu_visible_prog - dt / AnimConfig.MENU_FADE_DUR)
            if self.menu_visible_prog <= 0.02:
                self.food_menu_open = False
        if (self.menu_visible_prog > 0.05) != old_menu_vis:
            self.update_window_mask()

        # 小型食物菜单弹出缓动
        target_fm = 1.0 if self.food_menu_open else 0.0
        if self.food_menu_prog < target_fm:
            self.food_menu_prog = min(target_fm, self.food_menu_prog + dt / 0.20)
        elif self.food_menu_prog > target_fm:
            self.food_menu_prog = max(target_fm, self.food_menu_prog - dt / 0.18)

        # 4. 单击软弹反馈更新 (160ms)
        if self.click_anim_active:
            self.click_anim_t += dt / AnimConfig.CLICK_DUR
            if self.click_anim_t >= 1.0:
                self.click_anim_t = 0.0
                self.click_anim_active = False

        # 5. 拖拽倾斜回弹阻尼
        if not self.dragging:
            self.drag_tilt_deg *= math.pow(0.001, dt)
            if abs(self.drag_tilt_deg) < 0.05:
                self.drag_tilt_deg = 0.0

        # 6. 顺序喂食动画更新
        if self.feeding_active:
            self._update_feeding_sequence(dt)

        # 7. 屏幕底部探头收纳状态机更新
        self._update_dock_state_machine(dt)

        # 8. 待机随机小动作（仅在 IDLE 优先级且未完全收纳时触发，间隔随机化）
        if self.anim_state == AnimPriorityState.IDLE and self.dock_sink_progress < 0.1:
            if self.idle_quirk_type:
                self.idle_quirk_t += dt / self.idle_quirk_dur
                if self.idle_quirk_t >= 1.0:
                    self.idle_quirk_type = ""
                    self.idle_quirk_t = 0.0
                    self.idle_quirk_timer = random.uniform(5.5, 12.0)
            else:
                self.idle_quirk_timer -= dt
                if self.idle_quirk_timer <= 0.0:
                    self.idle_quirk_type = random.choice(["tilt", "stretch", "hop"])
                    self.idle_quirk_dur = random.uniform(0.75, 1.15)
                    self.idle_tilt_dir = random.choice([-1.0, 1.0])
                    self.idle_quirk_t = 0.0
        else:
            self.idle_quirk_type = ""
            self.idle_quirk_t = 0.0

        # 9. 对话气泡淡入与自动消失
        if self.bubble_hold_timer > 0.0:
            self.bubble_hold_timer -= dt
            self.bubble_alpha_prog = min(1.0, self.bubble_alpha_prog + dt / AnimConfig.BUBBLE_IN_DUR)
        else:
            self.bubble_alpha_prog = max(0.0, self.bubble_alpha_prog - dt / AnimConfig.BUBBLE_OUT_DUR)

        # 10. 粒子更新
        for pt in self.particles[:]:
            pt["life"] += dt
            pt["x"] += pt["vx"] * dt
            pt["y"] += pt["vy"] * dt
            pt["vy"] += 22.0 * dt  # 柔和轻盈阻尼
            if pt["life"] >= pt["max_life"]:
                self.particles.remove(pt)

        # 11. 空闲自动降低刷新频率以节约 CPU
        has_active_motion = (
            self.anim_state != AnimPriorityState.IDLE
            or bool(self.idle_quirk_type)
            or bool(self.particles)
            or self.bubble_alpha_prog > 0.01
            or 0.01 < self.menu_visible_prog < 0.99
            or 0.01 < self.hover_progress < 0.99
        )
        desired_interval = AnimConfig.DT_ACTIVE_MS if has_active_motion else AnimConfig.DT_IDLE_MS
        if self.frame_timer.interval() != desired_interval:
            self.frame_timer.setInterval(desired_interval)

        self.update()

    def _on_bio_tick(self):
        """真实动物生理代谢与消化计算"""
        self.hunger = max(0.0, self.hunger - 0.38)
        self.thirst = max(0.0, self.thirst - 0.44)
        self.fun = max(0.0, self.fun - (0.36 + len(self.poops) * 0.25))

        # 肠胃消化：只有胃里有食物时才逐步转化为便意进度
        if self.food_in_gut > 0.1:
            hydration_mult = 1.22 if self.thirst >= 45.0 else 0.72
            step = min(self.food_in_gut, 2.8 * hydration_mult)
            self.food_in_gut = max(0.0, self.food_in_gut - step)
            self.digestion_progress = min(100.0, self.digestion_progress + step * 1.12)
            self._check_digestion_to_poop()

        # 偶尔自主冒出小气泡（收纳状态下降低频率保持安静陪伴）
        if (
            self.bubble_alpha_prog <= 0.01
            and not self.hide_all_text
            and self.dock_sink_progress < 0.5
            and random.random() < 0.22
        ):
            if self.poops and random.random() < 0.55:
                self.show_speech(random.choice(POOP_QUOTES))
            elif self.hunger < 32.0:
                self.show_speech(random.choice(HUNGRY_QUOTES))
            elif self.thirst < 32.0:
                self.show_speech(random.choice(THIRSTY_QUOTES))
            elif self.fun < 32.0:
                self.show_speech(random.choice(BORED_QUOTES))
            else:
                self.show_speech(random.choice(IDLE_QUOTES))

        self.save_state()

    # ==========================================================================
    # 右键菜单与设置项
    # ==========================================================================
    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #FDFAF3;
                color: #523A42;
                border: 1.5px solid #7CC6B8;
                border-radius: 14px;
                padding: 6px;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background-color: #DAF2EC;
                color: #523A42;
            }
            QMenu::separator {
                height: 1px;
                background: #EAE2D6;
                margin: 4px 8px;
            }
            """
        )

        menu.addAction("🍰 打开小食物菜单投喂", self.toggle_food_menu)
        menu.addAction("🍵 喂星光蜜桃茶 (+水分)", self.action_drink)
        menu.addAction("🎲 陪小狐狸掷骰子 (+心情)", self.action_play_toy)
        menu.addAction(f"🧹 清理小便便 ({len(self.poops)})", self.action_clean_poop)

        menu.addSeparator()

        act_autotuck = QAction(
            "✓ 开启底部自动探头收纳" if self.auto_tuck_enabled else "○ 开启底部自动探头收纳",
            self,
        )
        act_autotuck.triggered.connect(self._toggle_auto_tuck)
        menu.addAction(act_autotuck)

        act_pin = QAction(
            "✓ 固定展开（不自动沉回底部）" if self.pin_expanded else "○ 固定展开（不自动沉回底部）",
            self,
        )
        act_pin.triggered.connect(self._toggle_pin_expanded)
        menu.addAction(act_pin)

        if self.dock_state == DockState.FREE:
            menu.addAction("🐾 立即贴到底部探头收纳", self._manual_tuck_now)
        else:
            menu.addAction("🐾 退出底部收纳回到桌面", self._exit_dock_mode)

        menu.addSeparator()

        act_text = QAction(
            "👁️ 显示气泡与状态胶囊" if self.hide_all_text else "🙈 隐藏所有文本框（纯享模式）",
            self,
        )
        act_text.triggered.connect(self._toggle_hide_text)
        menu.addAction(act_text)

        size_menu = menu.addMenu(f"🔍 调节小狐狸大小 ({int(self.scale_factor * 100)}%)")
        size_menu.addAction("放大 (+15%)", lambda: self.set_pet_scale(self.scale_factor + 0.15))
        size_menu.addAction("缩小 (-15%)", lambda: self.set_pet_scale(self.scale_factor - 0.15))
        size_menu.addSeparator()
        for pct in (75, 90, 100, 115, 135):
            size_menu.addAction(f"设为 {pct}%", lambda p=pct: self.set_pet_scale(p / 100.0))

        menu.addAction("📁 选择文件添加后缀...", self.open_manual_rename_picker)

        menu.addSeparator()
        menu.addAction("🚪 退出小狐狸桌宠", self.quit_pet)
        return menu

    def _toggle_auto_tuck(self):
        self.auto_tuck_enabled = not self.auto_tuck_enabled
        if not self.auto_tuck_enabled and self.dock_state != DockState.FREE:
            self._exit_dock_mode()
        self.show_speech("已开启底部自动收纳～" if self.auto_tuck_enabled else "已关闭底部自动收纳～", force=True)
        self.save_state()

    def _toggle_pin_expanded(self):
        self.pin_expanded = not self.pin_expanded
        if self.pin_expanded and self.dock_state in (DockState.TUCKED, DockState.SINKING):
            self._start_expand_full()
        self.show_speech("已固定展开姿态～" if self.pin_expanded else "已恢复自动沉回底部～", force=True)
        self.save_state()

    def _manual_tuck_now(self):
        self.auto_tuck_enabled = True
        self.pin_expanded = False
        self._start_sink_to_bottom()
        self.show_speech("偷偷藏进屏幕底边观察你～")

    def _exit_dock_mode(self):
        self.dock_state = DockState.FREE
        self.dock_sink_progress = 0.0
        avail = self._current_screen_geometry()
        self.move(self.x(), max(avail.top() + 20, avail.bottom() - self.height() - 65))
        self.update_window_mask()
        self.update()

    def _toggle_hide_text(self):
        self.hide_all_text = not self.hide_all_text
        if self.hide_all_text:
            self.rename_bar.close_bar()
            self.bubble_hold_timer = 0.0
            self.bubble_alpha_prog = 0.0
        else:
            self.show_speech("气泡与状态胶囊已恢复显示～", force=True)
        self.save_state()
        self.update_window_mask()
        self.update()

    def set_pet_scale(self, new_scale: float):
        old_bottom = self.y() + self.height()
        old_cx = self.x() + self.width() // 2
        self.scale_factor = max(0.65, min(1.55, round(new_scale, 2)))
        self._apply_scale_size()
        self.move(old_cx - self.width() // 2, old_bottom - self.height())
        if self.dock_state != DockState.FREE:
            self._align_window_to_screen_bottom()
        self.update_window_mask()
        self.show_speech(f"体型已调整为 {int(self.scale_factor * 100)}%～")
        self.save_state()

    def open_manual_rename_picker(self):
        self.food_menu_open = False
        files, _ = QFileDialog.getOpenFileNames(self, "选择要添加后缀的文件")
        if files:
            self._layout_rename_bar()
            self.rename_bar.open_for_files([Path(f) for f in files])

    def quit_pet(self):
        self.save_state()
        self.tray.hide()
        QApplication.quit()

    # ==========================================================================
    # 鼠标、悬停、拖拽、滚轮与文件拖放事件
    # ==========================================================================
    def enterEvent(self, event):
        self.is_mouse_inside = True
        self.menu_hide_countdown = AnimConfig.MENU_HIDE_DELAY
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

        # 核心需求四.6 & 8：当处于收纳或正在下沉时，鼠标移到露出的脑袋上立即触发探头序列
        if self.dock_state in (DockState.TUCKED, DockState.SINKING):
            self._start_peek_sequence()
        self.update_window_mask()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_mouse_inside = False
        self.hovered_btn_id = ""
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)
        super().leaveEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            step = 0.08 if event.angleDelta().y() > 0 else -0.08
            self.set_pet_scale(self.scale_factor + step)
            event.accept()
        else:
            super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_hide_text()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._build_context_menu().exec(event.globalPosition().toPoint())
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()
        s = self.scale_factor
        cx, cy, _, _ = self._fox_anchor()

        # 1. 若小型食物菜单打开，检查是否点击了某项食物
        if self.food_menu_open and self.food_menu_prog > 0.5:
            for item, rect in self._get_food_item_rects():
                if rect.contains(pos):
                    self.start_feeding_sequence(item, rect.center())
                    return
            if not self._get_food_menu_rect().contains(pos):
                self.food_menu_open = False
                self.update_window_mask()

        # 2. 检查是否点击了圆形功能按钮
        if self.menu_visible_prog > 0.35 and self.dock_sink_progress < 0.25:
            for key, rect in self._get_circular_button_rects().items():
                if rect.contains(pos):
                    if key == "feed":
                        self.toggle_food_menu()
                    elif key == "drink":
                        self.action_drink()
                    elif key == "play":
                        self.action_play_toy()
                    elif key == "clean":
                        self.action_clean_poop()
                    elif key == "rename":
                        self.open_manual_rename_picker()
                    return

        # 3. 检查是否点击了地面上的便便
        for idx, poop in enumerate(self.poops):
            px = cx + poop["rx"] * s
            py = cy + poop["ry"] * s
            if math.hypot(pos.x() - px, pos.y() - py) <= 22 * s:
                self.poops.pop(idx)
                self.spawn_gentle_particles(count=3, kind="star", origin=QPointF(px, py))
                self.show_speech("谢谢你帮我清掉小便便～")
                self.save_state()
                self.update_window_mask()
                return

        # 4. 开始拖动或单击狐狸（若在底部收纳展开状态被拖走，支持直接退出底部吸附状态）
        self.dragging = True
        self.food_menu_open = False
        gpos = event.globalPosition().toPoint()
        self.mouse_down_global = gpos
        self.last_drag_global = gpos
        self.drag_offset = gpos - self.frameGeometry().topLeft()
        self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def mouseMoveEvent(self, event):
        pos = event.position()

        if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            gpos = event.globalPosition().toPoint()
            dx = gpos.x() - self.last_drag_global.x()
            self.last_drag_global = gpos

            # 根据拖动水平方向产生轻微自然的倾斜角（限制在 -9° ~ +9° 内，绝不剧烈变形）
            target_tilt = max(-9.0, min(9.0, dx * 0.65))
            self.drag_tilt_deg = self.drag_tilt_deg * 0.65 + target_tilt * 0.35

            # 若从底部收纳展开状态拖离底部，立即退出底部吸附状态
            if (gpos - self.mouse_down_global).manhattanLength() > 10 and self.dock_state != DockState.FREE:
                self.dock_state = DockState.FREE
                self.dock_sink_progress = 0.0

            new_top_left = gpos - self.drag_offset
            avail = self._current_screen_geometry()
            dist_bottom = avail.bottom() - (new_top_left.y() + self.height())

            # 拖动接近底部 30~50px 时提供轻微的磁吸阻尼反馈
            if self.auto_tuck_enabled and -15 <= dist_bottom <= AnimConfig.SNAP_BOTTOM_DIST:
                self.near_bottom_magnet = True
                magnet_y = avail.bottom() - self.height() + 2
                blended_y = int(new_top_left.y() * 0.55 + magnet_y * 0.45)
                self.move(new_top_left.x(), blended_y)
            else:
                self.near_bottom_magnet = False
                self.move(new_top_left)
            return

        # 非拖拽时检测圆形按钮悬停
        new_hover_btn = ""
        if self.menu_visible_prog > 0.35 and self.dock_sink_progress < 0.25:
            for key, rect in self._get_circular_button_rects().items():
                if rect.contains(pos):
                    new_hover_btn = key
                    break
        if new_hover_btn != self.hovered_btn_id:
            self.hovered_btn_id = new_hover_btn
            self.setCursor(
                QCursor(Qt.CursorShape.PointingHandCursor)
                if new_hover_btn
                else QCursor(Qt.CursorShape.ArrowCursor)
            )
            self.frame_timer.setInterval(AnimConfig.DT_ACTIVE_MS)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.near_bottom_magnet = False
            gpos = event.globalPosition().toPoint()
            move_dist = (gpos - self.mouse_down_global).manhattanLength()

            if move_dist < 6:
                # 单击互动：轻轻压缩回弹 + 2~5 个小爱心/星星/金色粒子 + 互动小气泡
                if self.dock_state in (DockState.TUCKED, DockState.SINKING):
                    self._start_expand_full()
                else:
                    self.trigger_click_bounce()
                    self.spawn_gentle_particles(count=random.randint(3, 5), kind="mixed")
                    self.fun = min(100.0, self.fun + 3.5)
                    self.show_speech(random.choice(CLICK_QUOTES))
            else:
                # 检查是否松开在屏幕底部磁吸区（约 42px 内）
                dist_bottom = self._distance_to_screen_bottom()
                if self.auto_tuck_enabled and -30 <= dist_bottom <= AnimConfig.SNAP_BOTTOM_DIST:
                    if self.pin_expanded:
                        self._align_window_to_screen_bottom()
                        self.dock_state = DockState.EXPANDED_HOLD
                    else:
                        self.show_speech("偷偷躲在屏幕边看你工作～")
                        self._start_sink_to_bottom()
                else:
                    self.dock_state = DockState.FREE
                    self.dock_sink_progress = 0.0
            self.update_window_mask()

    # ------------------ 文件拖放事件（核心需求五） ------------------
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
            self._layout_rename_bar()
            self.rename_bar.open_for_files(paths)
        self.update()

    # ==========================================================================
    # 程序化姿态合成与精致 UI 绘制 (paintEvent)
    # ==========================================================================
    def _compute_fox_transform_params(self) -> tuple[float, float, float, float, float]:
        """
        根据统一动画状态机合成当前帧狐狸的：
        (offset_x, offset_y, scale_x, scale_y, rotate_deg)
        严格保持单张 PNG 原画完整性，仅做轻柔自然的微形变（绝不强制拉伸变形）。
        """
        s = self.scale_factor
        # 1. 基础呼吸浮动（极小幅度上下浮动 2.5px + 0.8% 呼吸缩放）
        breath_sin = math.sin(self.breath_phase)
        ox = 0.0
        oy = breath_sin * 2.4 * s
        sx = 1.0 - breath_sin * 0.006
        sy = 1.0 + breath_sin * 0.008
        rot = math.sin(self.breath_phase * 0.5) * 0.9

        # 2. 鼠标悬停或文件靠近：轻微抬起 (-4px) + 放大 3%（自然缓动）
        hk = ease_out_cubic(self.hover_progress)
        oy += AnimConfig.HOVER_LIFT_PX * s * hk
        hover_scale = 1.0 + (AnimConfig.HOVER_SCALE - 1.0) * hk
        sx *= hover_scale
        sy *= hover_scale

        # 3. 按状态优先级叠加专属动作，互不冲突
        if self.anim_state == AnimPriorityState.FILE_DROP and self.drag_hover_file:
            oy -= 3.5 * s
            rot = math.sin(self.elapsed_time * 5.0) * 2.2

        elif self.anim_state == AnimPriorityState.DRAGGING:
            rot = self.drag_tilt_deg
            oy -= 4.0 * s

        elif self.anim_state == AnimPriorityState.FEEDING:
            t = self.feeding_elapsed
            # 阶段 3 (0.28~0.75s)：狐狸稍微前倾迎接食物
            if 0.22 <= t <= 0.82:
                lean_k = math.sin(((t - 0.22) / 0.60) * math.pi)
                rot -= 5.2 * lean_k
                ox -= 3.5 * s * lean_k
                oy -= 2.5 * s * lean_k
            # 阶段 5 (0.86~1.16s)：吃完后开心轻轻弹跳
            elif 0.86 < t <= 1.16:
                hop_k = math.sin(((t - 0.86) / 0.30) * math.pi)
                oy -= 9.5 * s * hop_k
                sx *= 1.0 - 0.025 * hop_k
                sy *= 1.0 + 0.032 * hop_k

        elif self.anim_state == AnimPriorityState.CLICK_REACT:
            # 单击：轻轻压缩，然后柔软回弹
            p = self.click_anim_t
            wave = math.sin(p * math.pi * 2.0) * math.exp(-p * 2.4)
            sx *= 1.0 + 0.045 * wave
            sy *= 1.0 - 0.045 * wave
            oy += 3.5 * s * wave

        elif self.anim_state == AnimPriorityState.IDLE and self.idle_quirk_type:
            qk = math.sin(self.idle_quirk_t * math.pi)
            if self.idle_quirk_type == "tilt":
                rot += 4.2 * self.idle_tilt_dir * qk
            elif self.idle_quirk_type == "stretch":
                sy *= 1.0 + 0.026 * qk
                sx *= 1.0 - 0.016 * qk
                oy -= 3.0 * s * qk
            elif self.idle_quirk_type == "hop":
                oy -= 6.5 * s * qk

        return ox, oy, sx, sy, rot

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        s = self.scale_factor
        cx, cy, fw, fh = self._fox_anchor()
        ox, oy, sx, sy, rot = self._compute_fox_transform_params()
        draw_cx = cx + ox
        draw_cy = cy + oy

        # 1. 地面柔和阴影（当沉入屏幕底部时自动淡出）
        shadow_vis = max(0.0, 1.0 - self.dock_sink_progress * 1.6)
        if shadow_vis > 0.02:
            sh_w = fw * 0.72 * shadow_vis
            sh_h = 18.0 * s * shadow_vis
            sh_y = cy + fh * 0.42
            grad = QRadialGradient(QPointF(draw_cx, sh_y), sh_w * 0.55)
            grad.setColorAt(0.0, QColor(68, 46, 54, int(56 * shadow_vis)))
            grad.setColorAt(0.65, QColor(68, 46, 54, int(20 * shadow_vis)))
            grad.setColorAt(1.0, QColor(68, 46, 54, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawEllipse(QRectF(draw_cx - sh_w / 2.0, sh_y - sh_h / 2.0, sh_w, sh_h))

        # 2. 拖动接近底部磁吸区时的柔和薄荷金底边提示线
        if self.near_bottom_magnet:
            pen = QPen(Theme.CHAMPAGNE_GOLD, 2.5 * s, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(cx - 85 * s), self.height() - 3, int(cx + 85 * s), self.height() - 3)

        # 3. 文件拖放靠近时的柔和香槟金虚线光环（核心需求五）
        if self.drag_hover_file:
            painter.save()
            halo_r = QRectF(draw_cx - fw * 0.50, draw_cy - fh * 0.48, fw * 1.0, fh * 0.94)
            pen = QPen(Theme.CHAMPAGNE_GOLD, 2.2 * s, Qt.PenStyle.DashLine)
            pen.setDashOffset(self.elapsed_time * 12.0)
            painter.setPen(pen)
            painter.setBrush(QColor(250, 239, 214, 38))
            painter.drawRoundedRect(halo_r, 42 * s, 42 * s)
            painter.restore()

        # 4. 绘制砂金小狐狸本体（保持原画比例完整性）
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

        # 5. 绘制地面便便（仅在未收纳时显示）
        if self.dock_sink_progress < 0.3:
            for poop in self.poops:
                px = cx + poop["rx"] * s
                py = cy + poop["ry"] * s
                self._draw_cute_poop(painter, px, py, s)

        # 6. 绘制 6 阶段顺序贝塞尔喂食动画中的食物轨迹
        if self.feeding_active and self.feeding_food is not None:
            self._draw_feeding_flight(painter, s)

        # 7. 绘制环绕式小圆形图标按钮与底部轻量状态胶囊（带淡入、缩放与位移缓动）
        if self.menu_visible_prog > 0.02 and self.dock_sink_progress < 0.25:
            self._draw_circular_menu_and_status(painter, s)

        # 8. 绘制弹出式小型精致食物菜单
        if self.food_menu_prog > 0.02 and self.dock_sink_progress < 0.25:
            self._draw_food_popup_menu(painter, s)

        # 9. 绘制低饱和柔和粒子特效（小爱心、四角星、香槟金微光）
        self._draw_gentle_particles(painter)

        # 10. 绘制小巧圆角对话气泡（靠近狐狸头顶，自动避让屏幕顶部边缘）
        if not self.hide_all_text and self.bubble_alpha_prog > 0.02 and self.bubble_text:
            self._draw_speech_bubble(painter, draw_cx, draw_cy, fw, fh, s)

    # ==========================================================================
    # 细分矢量绘制方法（统一线条粗细、磨砂质感、无廉价发光）
    # ==========================================================================
    def _draw_circular_menu_and_status(self, painter: QPainter, s: float):
        painter.save()
        prog = ease_out_cubic(self.menu_visible_prog)
        painter.setOpacity(prog)

        # (A) 5 个精致小圆形矢量图标按钮
        rects = self._get_circular_button_rects()
        for key, rect in rects.items():
            h_prog = ease_out_cubic(self.btn_hover_prog.get(key, 0.0))
            scale_k = (0.85 + 0.15 * prog) * (1.0 + 0.08 * h_prog)

            painter.save()
            c = rect.center()
            painter.translate(c)
            painter.scale(scale_k, scale_k)
            r_local = QRectF(-rect.width() / 2.0, -rect.height() / 2.0, rect.width(), rect.height())

            # 柔和阴影
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Theme.SHADOW_SOFT)
            painter.drawEllipse(r_local.translated(0, 2.0 * s))

            # 奶油白磨砂圆底 + 薄荷/香槟描边
            bg_col = Theme.MINT_LIGHT if h_prog > 0.3 else Theme.CREAM_WHITE
            border_col = Theme.MINT_ACCENT if h_prog > 0.3 else Theme.MINT_BORDER
            painter.setBrush(bg_col)
            painter.setPen(QPen(border_col, Theme.PEN_WIDTH_CARD * s))
            painter.drawEllipse(r_local)

            # 统一粗细矢量小图标
            self._draw_button_vector_icon(painter, key, r_local, s)
            painter.restore()

        # (B) 底部紧凑胶囊状态条（饱食 / 水分 / 心情 / 消化便意）
        if not self.hide_all_text and not self.rename_bar.isVisible():
            strip_r = self._get_status_strip_rect()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Theme.SHADOW_SOFT)
            painter.drawRoundedRect(strip_r.translated(0, 1.5 * s), strip_r.height() / 2.0, strip_r.height() / 2.0)

            painter.setBrush(Theme.CREAM_WHITE)
            painter.setPen(QPen(Theme.MINT_BORDER, 1.3 * s))
            painter.drawRoundedRect(strip_r, strip_r.height() / 2.0, strip_r.height() / 2.0)

            items = [
                ("饱食", self.hunger, Theme.MINT_ACCENT),
                ("水分", self.thirst, QColor(118, 178, 224)),
                ("心情", self.fun, Theme.CHAMPAGNE_GOLD),
                ("消化", self.digestion_progress, Theme.LAVENDER_MAIN),
            ]
            seg_w = (strip_r.width() - 16 * s) / len(items)
            painter.setFont(QFont("Microsoft YaHei", max(7, int(7.5 * s)), QFont.Weight.Bold))
            for i, (lbl, val, col) in enumerate(items):
                sx = strip_r.left() + 8 * s + i * seg_w
                sy = strip_r.top() + 4 * s
                # 微型胶囊进度条
                bar_r = QRectF(sx + 24 * s, sy + 4.5 * s, seg_w - 28 * s, 5.5 * s)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(232, 226, 216))
                painter.drawRoundedRect(bar_r, 2.8 * s, 2.8 * s)

                fill_w = max(2.0, bar_r.width() * max(0.0, min(1.0, val / 100.0)))
                painter.setBrush(col)
                painter.drawRoundedRect(QRectF(bar_r.left(), bar_r.top(), fill_w, bar_r.height()), 2.8 * s, 2.8 * s)

                painter.setPen(Theme.TEXT_PRIMARY)
                painter.drawText(QRectF(sx, sy, 24 * s, 14 * s), Qt.AlignmentFlag.AlignVCenter, lbl)

        painter.restore()

    def _draw_button_vector_icon(self, painter: QPainter, key: str, r: QRectF, s: float):
        """使用统一线条粗细绘制 5 个圆形按钮内的精致矢量图标"""
        pen = QPen(Theme.TEXT_PRIMARY, Theme.PEN_WIDTH_ICON * s)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        w = r.width() * 0.24
        if key == "feed":
            # 小糕点/餐盘图标
            painter.setBrush(Theme.CHAMPAGNE_GOLD)
            painter.drawRoundedRect(QRectF(-w, -w * 0.3, w * 2, w * 1.1), 3 * s, 3 * s)
            painter.setBrush(Theme.ROSE_SOFT)
            painter.drawEllipse(QPointF(0, -w * 0.55), w * 0.32, w * 0.32)
        elif key == "drink":
            # 茶杯图标
            painter.setBrush(Theme.MINT_LIGHT)
            painter.drawRoundedRect(QRectF(-w * 0.75, -w * 0.5, w * 1.5, w * 1.4), 2.5 * s, 2.5 * s)
            painter.drawLine(QPointF(w * 0.2, -w * 0.5), QPointF(w * 0.55, -w * 1.0))
        elif key == "play":
            # 小骰子图标
            painter.setBrush(Theme.CHAMPAGNE_SOFT)
            painter.drawRoundedRect(QRectF(-w * 0.85, -w * 0.85, w * 1.7, w * 1.7), 3.5 * s, 3.5 * s)
            painter.setBrush(Theme.TEXT_PRIMARY)
            painter.drawEllipse(QPointF(0, 0), 1.4 * s, 1.4 * s)
        elif key == "clean":
            # 小扫帚/闪光清洁图标
            painter.drawLine(QPointF(-w * 0.6, w * 0.6), QPointF(w * 0.6, -w * 0.6))
            painter.setBrush(Theme.LAVENDER_SOFT)
            painter.drawEllipse(QPointF(-w * 0.4, w * 0.4), w * 0.45, w * 0.45)
        elif key == "rename":
            # 标签/改名图标
            painter.setBrush(Theme.LAVENDER_SOFT)
            painter.drawRoundedRect(QRectF(-w * 0.9, -w * 0.55, w * 1.8, w * 1.1), 3 * s, 3 * s)
            painter.drawLine(QPointF(-w * 0.45, 0), QPointF(w * 0.45, 0))

    def _draw_food_popup_menu(self, painter: QPainter, s: float):
        """绘制狐狸身旁弹出的精致磨砂小型食物菜单"""
        painter.save()
        k = ease_out_back(self.food_menu_prog, overshoot=1.15)
        painter.setOpacity(min(1.0, self.food_menu_prog * 1.15))

        menu_r = self._get_food_menu_rect()
        c = menu_r.center()
        painter.translate(c)
        painter.scale(0.88 + 0.12 * k, 0.88 + 0.12 * k)
        painter.translate(-c)

        # 柔和投影
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Theme.SHADOW_SOFT)
        painter.drawRoundedRect(menu_r.translated(0, 3 * s), Theme.RADIUS_MENU * s, Theme.RADIUS_MENU * s)

        # 奶油白磨砂卡片 + 细腻薄荷描边
        painter.setBrush(Theme.CREAM_WHITE)
        painter.setPen(QPen(Theme.MINT_BORDER, Theme.PEN_WIDTH_CARD * s))
        painter.drawRoundedRect(menu_r, Theme.RADIUS_MENU * s, Theme.RADIUS_MENU * s)

        # 顶部小标题
        painter.setPen(Theme.TEXT_SECONDARY)
        painter.setFont(QFont("Microsoft YaHei", max(7, int(8 * s)), QFont.Weight.Bold))
        painter.drawText(
            QRectF(menu_r.left() + 10 * s, menu_r.top() + 6 * s, menu_r.width() - 20 * s, 18 * s),
            Qt.AlignmentFlag.AlignCenter,
            "点选小点心投喂",
        )

        # 4 个食物选项胶囊行
        painter.setFont(QFont("Microsoft YaHei", max(8, int(8.5 * s)), QFont.Weight.Bold))
        for item, row_r in self._get_food_item_rects():
            painter.setPen(QPen(Theme.CHAMPAGNE_GOLD, 1.1 * s))
            painter.setBrush(Theme.CREAM_WARM)
            painter.drawRoundedRect(row_r, 9 * s, 9 * s)

            # 统一风格的迷你食物图标
            icon_pt = QPointF(row_r.left() + 14 * s, row_r.center().y())
            self._draw_food_mini_icon(painter, item, icon_pt, 7.5 * s)

            painter.setPen(Theme.TEXT_PRIMARY)
            painter.drawText(
                QRectF(row_r.left() + 26 * s, row_r.top(), row_r.width() - 30 * s, row_r.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                item.name,
            )

        painter.restore()

    def _draw_food_mini_icon(self, painter: QPainter, item: FoodItem, center: QPointF, radius: float):
        painter.save()
        painter.setPen(QPen(Theme.TEXT_PRIMARY, 1.3))
        painter.setBrush(item.color_main)
        painter.drawRoundedRect(
            QRectF(center.x() - radius, center.y() - radius * 0.75, radius * 2, radius * 1.5),
            radius * 0.5,
            radius * 0.5,
        )
        painter.setBrush(item.color_sub)
        painter.drawEllipse(QPointF(center.x(), center.y() - radius * 0.55), radius * 0.42, radius * 0.42)
        painter.restore()

    def _draw_feeding_flight(self, painter: QPainter, s: float):
        """
        绘制 6 阶段喂食动画中的食物飞行与被吃掉效果：
        1. 0.00 ~ 0.18s：从菜单位置轻轻浮起；
        2. 0.18 ~ 0.62s：沿柔和二次贝塞尔曲线飞向狐狸嘴边；
        3. 0.62 ~ 0.86s：在嘴边逐渐缩小、淡出（被吃掉）。
        """
        t = self.feeding_elapsed
        if t > 0.86 or self.feeding_food is None:
            return

        p0 = self.feeding_start_pt
        p_float = QPointF(p0.x(), p0.y() - 16.0 * s)
        p_end = self.feeding_mouth_pt
        ctrl = QPointF((p_float.x() + p_end.x()) * 0.5, min(p_float.y(), p_end.y()) - 42.0 * s)

        scale = 1.0
        alpha = 1.0

        if t <= 0.18:
            k = ease_out_cubic(t / 0.18)
            cur_pt = QPointF(p0.x(), p0.y() - 16.0 * s * k)
            scale = 0.85 + 0.25 * k
        elif t <= 0.62:
            k = ease_in_out_cubic((t - 0.18) / 0.44)
            cur_pt = bezier_quad(p_float, ctrl, p_end, k)
            scale = 1.10
        else:
            k = ease_in_out_cubic((t - 0.62) / 0.24)
            cur_pt = p_end
            scale = max(0.1, 1.10 * (1.0 - k))
            alpha = max(0.0, 1.0 - k)

        painter.save()
        painter.setOpacity(alpha)
        self._draw_food_mini_icon(painter, self.feeding_food, cur_pt, 11.5 * s * scale)
        painter.restore()

    def _draw_cute_poop(self, painter: QPainter, px: float, py: float, s: float):
        painter.save()
        painter.setPen(QPen(Theme.TEXT_PRIMARY, 1.4 * s))
        painter.setBrush(QColor(166, 118, 86))
        painter.drawRoundedRect(QRectF(px - 12 * s, py + 2 * s, 24 * s, 8 * s), 4 * s, 4 * s)
        painter.drawRoundedRect(QRectF(px - 9 * s, py - 4 * s, 18 * s, 7.5 * s), 3.5 * s, 3.5 * s)
        painter.drawEllipse(QRectF(px - 4.5 * s, py - 9.5 * s, 9 * s, 6.5 * s))
        painter.restore()

    def _draw_gentle_particles(self, painter: QPainter):
        """绘制细小、柔和、低饱和的小爱心、四角星与香槟金微光点"""
        for pt in self.particles:
            prog = pt["life"] / pt["max_life"]
            alpha = math.sin(prog * math.pi)
            col = QColor(pt["color"])
            col.setAlpha(int(215 * max(0.0, min(1.0, alpha))))

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
        self, painter: QPainter, cx: float, cy: float, fw: float, fh: float, s: float
    ):
        """
        绘制小巧圆角对话气泡：
        - 淡入、微缩放、轻微上浮；
        - 靠近狐狸出现，若靠近屏幕顶部则自动下移，绝不越界。
        """
        painter.save()
        k = ease_out_cubic(self.bubble_alpha_prog)
        painter.setOpacity(k)

        font = QFont("Microsoft YaHei", max(8, int(9 * s)), QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()

        max_bw = int(248 * s)
        text_bound = fm.boundingRect(
            QRect(0, 0, max_bw - int(24 * s), 200),
            Qt.TextFlag.TextWordWrap,
            self.bubble_text,
        )
        bw = max(int(96 * s), min(max_bw, text_bound.width() + int(26 * s)))
        bh = max(int(32 * s), text_bound.height() + int(16 * s))

        bx = max(8.0, min(self.width() - bw - 8.0, cx - bw / 2.0))
        float_up = (1.0 - k) * 6.0 * s
        ideal_by = cy - fh * 0.48 - bh - 6.0 * s + float_up
        # 防止超出窗口/屏幕顶部
        by = max(6.0, min(self.height() - bh - 12.0, ideal_by))

        rect = QRectF(bx, by, bw, bh)
        c = rect.center()
        painter.translate(c)
        painter.scale(0.92 + 0.08 * k, 0.92 + 0.08 * k)
        painter.translate(-c)

        # 柔和投影
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Theme.SHADOW_SOFT)
        painter.drawRoundedRect(rect.translated(0, 2.5 * s), Theme.RADIUS_BUBBLE * s, Theme.RADIUS_BUBBLE * s)

        # 奶油白磨砂气泡底 + 薄荷绿细腻描边
        path = QPainterPath()
        path.addRoundedRect(rect, Theme.RADIUS_BUBBLE * s, Theme.RADIUS_BUBBLE * s)
        tail_x = max(bx + 18 * s, min(bx + bw - 18 * s, cx))
        path.moveTo(tail_x - 6 * s, by + bh)
        path.lineTo(tail_x, by + bh + 6 * s)
        path.lineTo(tail_x + 6 * s, by + bh)
        path.closeSubpath()

        painter.setBrush(Theme.CREAM_WHITE)
        painter.setPen(QPen(Theme.MINT_BORDER, Theme.PEN_WIDTH_CARD * s))
        painter.drawPath(path)

        painter.setPen(Theme.TEXT_PRIMARY)
        painter.drawText(
            rect.adjusted(10 * s, 5 * s, -10 * s, -5 * s),
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
