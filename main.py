#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
砂金猫猫桌面宠物 (shajincw) v2.0 - Windows 3D立体感桌宠 & 白圆角胶囊拖拽改名工具
核心特性：
1. 纯透明无边框置顶窗口 + 贴边磁吸吸附 + 上下轻柔悬浮律动
2. 3D立体感渲染：法线体积光影立绘 + 鼠标跟随2.5D透视微倾 + 呼吸动态景深阴影
3. 配色取自砂金猫猫角色本身：香槟奶油金、松石薄荷青、星光紫粉眸、深棕紫轮廓
4. 胶囊标签样式 UI + 纯白圆角胶囊长条输入框（拖拽 000.jpg 输入 555 原地变成 000（555).jpg）
5. 所有文本框/气泡/胶囊标签均支持一键彻底隐藏（双击宠物 / 快捷键 H / 胶囊按钮 / 右键菜单）
6. 体型大小自由无级调节（Ctrl+滚轮缩放 / 菜单档位调节）
7. 真实动物生理代谢与进食消化拉屎机制：进食增加肠胃食物 -> 随时间与水分消化 -> 消化满100%才会排便
"""

import json
import math
import os
import random
import sys
from pathlib import Path

from PyQt6.QtCore import (
    QPoint,
    QPointF,
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
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
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
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel_path
    return Path(__file__).resolve().parent / rel_path


STATE_FILE = Path.home() / ".shajincw_pet_v2.json"

# ==================== 角色提取配色方案 ====================
COL_CREAM_BG     = QColor(255, 250, 238, 244)  # 奶油香槟浅底
COL_CREAM_GOLD   = QColor(246, 218, 158, 255)  # 奶油金毛色
COL_TEAL_MAIN    = QColor(102, 205, 192, 255)  # 小外套松石薄荷青
COL_TEAL_SOFT    = QColor(226, 247, 243, 242)  # 浅松石胶囊底
COL_PURPLE_EYE   = QColor(186, 132, 218, 255)  # 紫粉渐变猫眼色
COL_PURPLE_SOFT  = QColor(244, 232, 252, 242)  # 浅紫粉胶囊底
COL_OUTLINE_DARK = QColor(74, 46, 56, 255)     # 角色深棕紫外轮廓线（文字与描边）
COL_PAW_PINK     = QColor(228, 148, 162, 255)  # 肉垫粉红
COL_WHITE_PURE   = QColor(255, 255, 255, 252)  # 纯白圆角胶囊输入框底色

# ==================== 台词库 ====================
CLICK_LINES = [
    "喵呜~ 朋友，摸肚皮可是要付筹码的哦！",
    "所有，或者一无所有~ 今天想赌一把大的吗？",
    "别戳啦，墨镜都要被你戳歪了！",
    "这身松石青小开衫好看吧？本总监的定制款~",
    "呼噜噜……勉强允许你再挠一下下巴。",
    "有文件要改后缀吗？直接拖到我身上就行！",
    "我的大尾巴可不是随便给别人摸的，你是例外~",
    "双击我或者按 H 键，就能一键隐藏所有文字胶囊哦~",
]

SELF_TALK_LINES = [
    "（晃尾巴）上下飘呀飘~ 今天的桌面风水真不错。",
    "朋友，盯屏幕太久啦，要不要跟我一起喝口水？",
    "把 000.jpg 拖给我，输入 555 就能秒变 000（555).jpg~",
    "呼噜……呼噜……翻个肚皮晒太阳~",
    "点数是三枚『砂金』，幸运女神今天也在我这边！",
]

HUNGRY_LINES = [
    "咕噜噜……朋友，饥饿度见底啦，快喂块奶油猫糕！",
    "饿扁了喵……肚子空空可摇不动骰子呀……",
    "再不投喂的话，本总监就要去啃你的桌面图标了！",
]

THIRSTY_LINES = [
    "嗓子干得像茨冈尼亚的沙漠……赏杯冰饮吧朋友？",
    "渴啦渴啦，喝点水才能顺畅消化食物哦~",
    "想喝冰镇特调，或者温牛奶也行喵~",
]

BORED_LINES = [
    "好无聊啊朋友……陪我掷把骰子，或者拿玩具逗逗我？",
    "发呆中……都没人陪本总监玩，尾巴都要长蘑菇了。",
    "无聊到想自己跟自己的尾巴猜拳了喵……",
]

DIGEST_NEAR_LINES = [
    "唔……刚才吃的东西消化得差不多了，肚子里咕噜噜响……",
    "（捂肚子）朋友，肠胃消化度快满 100% 了，感觉要拉臭臭了……",
]

POOP_LINES = [
    "噗——呼，排出来舒服多了！朋友，快帮我铲一下便便吧~",
    "地板上有便便啦，点一下便便或者点『铲屎』胶囊就能清掉哦！",
]


class WhiteCapsuleRenameBar(QWidget):
    """
    白圆角胶囊长条输入框：
    拖入文件（如 000.jpg）后悬浮显示在桌宠下方，输入 555 回车即原地重命名为 000（555).jpg
    """

    def __init__(self, parent_pet: "ShajinPetWindow"):
        super().__init__(parent_pet)
        self.pet = parent_pet
        self.file_paths: list[Path] = []
        self.hide()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 5)
        layout.setSpacing(6)

        # 左侧角色青色小胶囊标签：显示原文件名
        self.file_tag = QLabel("000.jpg")
        self.file_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.file_tag)

        # 中间纯白无边框输入框
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入后缀如 555 回车变 000（555).jpg")
        self.input_edit.returnPressed.connect(self.confirm_rename)
        layout.addWidget(self.input_edit, 1)

        # 右侧紫粉胶囊确认按钮
        self.btn_ok = QPushButton("改名")
        self.btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ok.clicked.connect(self.confirm_rename)
        layout.addWidget(self.btn_ok)

        # 关闭小圆钮
        self.btn_close = QPushButton("×")
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.clicked.connect(self.close_bar)
        layout.addWidget(self.btn_close)

        self.setStyleSheet(
            """
            QLabel {
                background-color: #76D2C5;
                color: #4A2E38;
                border-radius: 12px;
                padding: 3px 10px;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit {
                background: transparent;
                border: none;
                color: #4A2E38;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                font-size: 13px;
                font-weight: bold;
                selection-background-color: #B884D8;
            }
            QPushButton {
                background-color: #B884D8;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 4px 11px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #A36BC7;
            }
            """
        )
        self.btn_close.setStyleSheet(
            """
            QPushButton {
                background-color: #F2E6D8;
                color: #4A2E38;
                border-radius: 11px;
                padding: 2px 7px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E5D2BC;
            }
            """
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        # 外层柔和投影
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(74, 46, 56, 38))
        painter.drawRoundedRect(rect.translated(0, 2), 20, 20)
        # 纯白圆角胶囊主体 + 松石青描边
        painter.setBrush(COL_WHITE_PURE)
        painter.setPen(QPen(COL_TEAL_MAIN, 2.2))
        painter.drawRoundedRect(rect, 20, 20)

    def open_for_files(self, paths: list[Path]):
        self.file_paths = paths
        first_name = paths[0].name
        if len(first_name) > 14:
            first_name = first_name[:11] + "..."
        if len(paths) > 1:
            self.file_tag.setText(f"{first_name} 等{len(paths)}项")
        else:
            self.file_tag.setText(first_name)
        self.input_edit.clear()
        self.show()
        self.raise_()
        self.input_edit.setFocus()

    def close_bar(self):
        self.hide()
        self.pet.update()

    @staticmethod
    def format_new_filename(orig_path: Path, raw_suffix: str) -> str:
        s = raw_suffix.strip()
        if not s:
            return orig_path.name
        stem = orig_path.stem
        ext = orig_path.suffix
        # 若用户输入 "555" 或 "（555）" 或 "(555)" 或 "（555)"，统一按要求生成 "000（555).jpg"
        inner = s
        if (s.startswith("（") or s.startswith("(")) and (s.endswith("）") or s.endswith(")")):
            inner = s[1:-1].strip()
        elif s.startswith("（") or s.startswith("("):
            inner = s[1:].strip()
        return f"{stem}（{inner}){ext}"

    def confirm_rename(self):
        raw = self.input_edit.text().strip()
        if not raw or not self.file_paths:
            self.input_edit.setFocus()
            return
        renamed = []
        errors = []
        for p in self.file_paths:
            if not p.exists():
                errors.append(f"{p.name} 不存在")
                continue
            new_name = self.format_new_filename(p, raw)
            target = p.with_name(new_name)
            try:
                p.rename(target)
                renamed.append(target.name)
            except Exception as exc:
                errors.append(f"{p.name}: {exc}")

        self.hide()
        if renamed:
            self.pet.trigger_jump()
            self.pet.add_particle(f"✨ {renamed[0]}", 0, -55, "#76D2C5")
            if len(renamed) == 1:
                self.pet.say(f"搞定喵！已原地重命名为「{renamed[0]}」~", force=True)
            else:
                self.pet.say(f"搞定喵！「{renamed[0]}」等 {len(renamed)} 个文件已全部重命名~", force=True)
        elif errors:
            self.pet.say(f"改名遇到问题：{errors[0]}", force=True)


class ShajinPetWindow(QWidget):
    """砂金猫猫 3D 立体感桌面宠物主窗口"""

    BASE_W = 430
    BASE_H = 520

    def __init__(self, preview_mode: bool = False):
        super().__init__()
        self.preview_mode = preview_mode

        # 体型缩放比例 (支持 0.60 ~ 1.60 无级调节)
        self.scale_factor = 1.0

        # 真实动物生理指标 (0 ~ 100)
        self.hunger = 82.0              # 饱食度：随时间自然消耗，喂食增加
        self.thirst = 85.0              # 水分值：随时间自然消耗，喝水增加并加速肠胃蠕动
        self.fun = 84.0                 # 心情值：低了会无聊叹气，玩玩具增加
        self.food_in_gut = 25.0         # 胃内待消化食物量：只有喂食才会增加！
        self.digestion_progress = 30.0  # 肠道便意累积度(0~100%)：由胃内食物逐步转化，满100%自动拉屎！
        self.warned_near_poop = False
        self.poops: list[dict] = []     # 地面便便坐标（相对于宠物中心）

        # 文本框与胶囊隐藏控制
        self.hide_all_text = False      # 一键隐藏所有文本框/气泡/胶囊（纯享3D宠物模式）
        self.show_capsules = True       # 是否显示底部胶囊标签栏
        self.show_bubble = True         # 是否显示头顶说话气泡

        # 贴边吸附与悬浮动画状态
        self.snap_edge = ""             # "" | "left" | "right" | "top" | "bottom"
        self.tick = 0
        self.float_offset_y = 0.0
        self.jump_phase = 0.0
        self.auto_walk = False
        self.walk_vx = 1.5
        self.facing_right = False

        # 鼠标交互与 3D 视差倾斜
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.mouse_down_pos = QPoint()
        self.hover_pos = QPointF(215, 260)
        self.drag_hover_file = False

        # 气泡与特效
        self.bubble_text = "喵呜~ 把文件拖给我秒改后缀！双击我可隐藏所有文字胶囊哦~"
        self.bubble_timer = 190
        self.active_prop = None
        self.particles: list[dict] = []

        self.load_pet_state()

        # 加载 3D 体积光影烘焙立绘
        sprite_path = resource_path("assets/pet_sprite.png")
        self.pet_pixmap = QPixmap(str(sprite_path))

        self._init_window()
        self.rename_bar = WhiteCapsuleRenameBar(self)
        self._layout_rename_bar()
        self._init_tray()
        self._init_timers()

    def _init_window(self):
        self.setWindowTitle("砂金猫猫桌宠 (shajincw)")
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._apply_window_scale()

        icon_path = resource_path("assets/pet_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 36, geo.bottom() - self.height() - 24)

    def _apply_window_scale(self):
        w = int(self.BASE_W * self.scale_factor)
        h = int(self.BASE_H * self.scale_factor)
        self.setFixedSize(w, h)
        if hasattr(self, "rename_bar"):
            self._layout_rename_bar()

    def _layout_rename_bar(self):
        bw = min(self.width() - 16, max(310, int(386 * self.scale_factor)))
        bh = 44
        bx = (self.width() - bw) // 2
        by = int(self.height() - 108 * self.scale_factor)
        self.rename_bar.setGeometry(bx, by, bw, bh)

    def _init_tray(self):
        icon_path = resource_path("assets/pet_icon.ico")
        tray_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon(self.pet_pixmap)
        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip("砂金猫猫桌宠 (shajincw)")
        self.tray.setContextMenu(self._build_context_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()
            self.raise_()

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #FFFDF8;
                color: #4A2E38;
                border: 2px solid #76D2C5;
                border-radius: 14px;
                padding: 6px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
                font-weight: bold;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 9px;
            }
            QMenu::item:selected {
                background-color: #76D2C5;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: #E8DEC8;
                margin: 4px 8px;
            }
            """
        )

        menu.addAction("🍖 喂食（+饱食 & 进入肠胃消化）", self.action_feed)
        menu.addAction("🧋 喝水（+水分 & 促进肠胃蠕动）", self.action_drink)
        menu.addAction("🎲 玩玩具（掷砂金骰子 +心情）", self.action_play)
        menu.addAction(f"🧹 铲屎清理地板 ({len(self.poops)})", self.action_clean_poop)

        menu.addSeparator()

        act_hide_all = QAction(
            "👁️ 显示所有文本框与胶囊" if self.hide_all_text else "🙈 隐藏所有文本框与胶囊（纯享桌宠）",
            self,
        )
        act_hide_all.triggered.connect(self.toggle_hide_all_text)
        menu.addAction(act_hide_all)

        act_caps = QAction(
            "🏷️ 隐藏底部胶囊标签栏" if self.show_capsules else "🏷️ 显示底部胶囊标签栏",
            self,
        )
        act_caps.triggered.connect(self.toggle_capsules)
        menu.addAction(act_caps)

        act_bub = QAction(
            "💬 关闭说话气泡框" if self.show_bubble else "💬 开启说话气泡框",
            self,
        )
        act_bub.triggered.connect(self.toggle_bubble)
        menu.addAction(act_bub)

        menu.addSeparator()

        # 体型大小调节子菜单
        size_menu = menu.addMenu(f"🔍 调节宠物大小 (当前 {int(self.scale_factor*100)}%)")
        size_menu.addAction("➕ 放大 (+15%)", lambda: self.set_pet_scale(self.scale_factor + 0.15))
        size_menu.addAction("➖ 缩小 (-15%)", lambda: self.set_pet_scale(self.scale_factor - 0.15))
        size_menu.addSeparator()
        for pct in (70, 85, 100, 120, 140):
            size_menu.addAction(f"设为 {pct}%", lambda p=pct: self.set_pet_scale(p / 100.0))

        menu.addAction("📁 打开白胶囊输入框改文件名...", self.open_manual_rename_picker)
        menu.addAction(
            "📌 停止自由散步" if self.auto_walk else "🚶 开启桌面散步",
            self.toggle_walk,
        )

        menu.addSeparator()
        menu.addAction("🚪 退出砂金桌宠", self.quit_pet)
        return menu

    def _init_timers(self):
        # 30 FPS 丝滑悬浮与 3D 视差动画计时器
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start(33)

        # 生理代谢与真实进食消化计时器 (每 4 秒推进一次生理循环)
        self.bio_timer = QTimer(self)
        self.bio_timer.timeout.connect(self._on_metabolism_tick)
        self.bio_timer.start(4000)

    def load_pet_state(self):
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.scale_factor = max(0.6, min(1.6, float(data.get("scale_factor", 1.0))))
                self.hunger = float(data.get("hunger", 82.0))
                self.thirst = float(data.get("thirst", 85.0))
                self.fun = float(data.get("fun", 84.0))
                self.food_in_gut = float(data.get("food_in_gut", 25.0))
                self.digestion_progress = float(data.get("digestion_progress", 30.0))
                self.poops = data.get("poops", [])[:4]
                self.hide_all_text = bool(data.get("hide_all_text", False))
                self.show_capsules = bool(data.get("show_capsules", True))
                self.show_bubble = bool(data.get("show_bubble", True))
        except Exception:
            pass

    def save_pet_state(self):
        try:
            data = {
                "scale_factor": round(self.scale_factor, 2),
                "hunger": round(self.hunger, 1),
                "thirst": round(self.thirst, 1),
                "fun": round(self.fun, 1),
                "food_in_gut": round(self.food_in_gut, 1),
                "digestion_progress": round(self.digestion_progress, 1),
                "poops": self.poops[:4],
                "hide_all_text": self.hide_all_text,
                "show_capsules": self.show_capsules,
                "show_bubble": self.show_bubble,
            }
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ------------------ 大小调节与文本框隐藏 ------------------
    def set_pet_scale(self, new_scale: float):
        old_center = self.geometry().center()
        self.scale_factor = max(0.60, min(1.60, round(new_scale, 2)))
        self._apply_window_scale()
        # 保持中心位置稳定
        self.move(old_center.x() - self.width() // 2, old_center.y() - self.height() // 2)
        self._check_edge_snap()
        self.say(f"🔍 体型已调整为 {int(self.scale_factor * 100)}%（按住 Ctrl+滚轮也能随时缩放哦~）")
        self.save_pet_state()
        self.update()

    def toggle_hide_all_text(self):
        self.hide_all_text = not self.hide_all_text
        if self.hide_all_text:
            self.rename_bar.hide()
        else:
            self.say("✨ 胶囊标签与对话框已恢复显示~（双击我可再次隐藏）", force=True)
        self.save_pet_state()
        self.update()

    def toggle_capsules(self):
        self.show_capsules = not self.show_capsules
        self.save_pet_state()
        self.update()

    def toggle_bubble(self):
        self.show_bubble = not self.show_bubble
        self.save_pet_state()
        self.update()

    # ------------------ 贴边磁吸吸附 ------------------
    def _check_edge_snap(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        sgeo = screen.availableGeometry()
        x, y = self.x(), self.y()
        w, h = self.width(), self.height()
        snap_dist = 38
        snapped = ""

        if abs(x - sgeo.left()) <= snap_dist:
            x = sgeo.left() - int(18 * self.scale_factor)
            snapped = "left"
        elif abs((x + w) - sgeo.right()) <= snap_dist:
            x = sgeo.right() - w + int(18 * self.scale_factor)
            snapped = "right"

        if abs(y - sgeo.top()) <= snap_dist:
            y = sgeo.top()
            snapped = snapped or "top"
        elif abs((y + h) - sgeo.bottom()) <= snap_dist:
            y = sgeo.bottom() - h
            snapped = snapped or "bottom"

        self.snap_edge = snapped
        self.move(x, y)

    # ------------------ 养成与生理消化互动 ------------------
    def say(self, text: str, duration_frames: int = 165, force: bool = False):
        if self.hide_all_text and not force:
            return
        self.bubble_text = text
        self.bubble_timer = duration_frames
        self.update()

    def add_particle(self, text: str, rel_x: float, rel_y: float, color: str = "#50B5A6"):
        self.particles.append(
            {"text": text, "rx": rel_x, "ry": rel_y, "vy": -1.4, "alpha": 255, "color": color}
        )

    def trigger_jump(self):
        self.jump_phase = 1.0

    def action_feed(self):
        if self.hunger >= 99.0 and self.food_in_gut >= 85.0:
            self.trigger_jump()
            self.say("嗝~ 肚子里全是猫糕，实在吃不下啦，等消化完拉完臭臭再喂我吧！")
            return

        self.hunger = min(100.0, self.hunger + 28.0)
        # 进食后食物真实进入肠胃，等待后续消化转化为便意
        self.food_in_gut = min(100.0, self.food_in_gut + 38.0)
        self.active_prop = {"type": "food", "ttl": 75}
        self.trigger_jump()
        self.add_particle("🍖 饱食+28 · 肠胃消化中", 0, -95, "#4A2E38")
        self.add_particle("❤", -48, -75, "#E494A2")
        self.say(random.choice([
            "嗷呜！香喷喷的奶油猫糕下肚，肠胃开始努力消化咯~",
            "吧唧吧唧……吃饱啦！等消化完大概就要找地方拉臭臭了喵~",
            "美味！本总监宣布这顿大餐稳赚不赔~",
        ]))
        self.save_pet_state()

    def action_drink(self):
        self.thirst = min(100.0, self.thirst + 30.0)
        # 喝水促进肠胃蠕动：如果胃里有食物，立即推进一部分消化进度
        if self.food_in_gut > 0:
            boost = min(self.food_in_gut, 14.0)
            self.food_in_gut -= boost
            self.digestion_progress = min(100.0, self.digestion_progress + boost * 1.1)
        self.active_prop = {"type": "drink", "ttl": 75}
        self.trigger_jump()
        self.add_particle("🧋 水分+30 · 肠胃顺畅", 0, -95, "#50B5A6")
        self.say(random.choice([
            "咕嘟咕嘟……冰镇特调下肚，肠胃蠕动都变快啦~",
            "谢谢朋友的饮品~ 水分充足，毛色都更有光泽了！",
            "甜度满分！再来一杯本总监也喝得下~",
        ]))
        self._check_digestion_poop()
        self.save_pet_state()

    def action_play(self):
        self.fun = min(100.0, self.fun + 28.0)
        # 运动消耗少量体力（饱食度与水分微降，同时加速消化）
        self.hunger = max(0.0, self.hunger - 3.5)
        self.thirst = max(0.0, self.thirst - 3.5)
        if self.food_in_gut > 0:
            step = min(self.food_in_gut, 8.0)
            self.food_in_gut -= step
            self.digestion_progress = min(100.0, self.digestion_progress + step)

        self.active_prop = {"type": "toy", "ttl": 80}
        self.trigger_jump()
        pts = random.randint(1, 6)
        self.add_particle(f"🎲 掷出 {pts} 点 · 心情+28", 0, -98, "#9A63BE")
        self.say(random.choice([
            f"看招！骰子掷出了 {pts} 点——餐后运动最助消化啦~",
            "喵呜！（扑向筹码）跟朋友玩玩具永远不会无聊~",
            "哈哈，再摇一次！今天的手气旺得挡不住~",
        ]))
        self._check_digestion_poop()
        self.save_pet_state()

    def _check_digestion_poop(self):
        """根据真实肠胃消化进度判断是否排便"""
        if self.digestion_progress >= 82.0 and not self.warned_near_poop:
            self.warned_near_poop = True
            self.say(random.choice(DIGEST_NEAR_LINES))

        if self.digestion_progress >= 100.0:
            self.digestion_progress = 0.0
            self.warned_near_poop = False
            self.spawn_poop()

    def spawn_poop(self):
        if len(self.poops) >= 4:
            return
        rx = random.choice([random.randint(-135, -90), random.randint(90, 135)])
        ry = random.randint(92, 122)
        self.poops.append({"rx": rx, "ry": ry})
        self.trigger_jump()
        self.add_particle("💩 噗~ 消化排便!", rx, ry - 24, "#8D5B4C")
        self.say(random.choice(POOP_LINES))
        self.save_pet_state()

    def action_clean_poop(self):
        if not self.poops:
            self.say("地板干干净净的，目前还没拉便便哦（喂食消化满100%后才会拉）~")
            return
        count = len(self.poops)
        for p in self.poops:
            self.add_particle("✨干净+1", p["rx"], p["ry"] - 15, "#50B5A6")
        self.poops.clear()
        self.fun = min(100.0, self.fun + 12.0)
        self.trigger_jump()
        self.say(f"🧹 呼~ 清理掉 {count} 坨便便，香喷喷！谢谢铲屎官朋友~")
        self.save_pet_state()

    def toggle_walk(self):
        self.auto_walk = not self.auto_walk
        if self.auto_walk:
            self.snap_edge = ""
            self.say("🚶 开启桌面巡游模式~")
        else:
            self.say("📌 已停下脚步乖乖待命~")

    def open_manual_rename_picker(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要加后缀重命名的文件（也可直接拖文件到砂金猫猫身上）"
        )
        if files:
            self.rename_bar.open_for_files([Path(f) for f in files])

    def quit_pet(self):
        self.save_pet_state()
        self.tray.hide()
        QApplication.quit()

    # ------------------ 动画帧与真实生理代谢循环 ------------------
    def _on_anim_tick(self):
        self.tick += 1
        # 上下轻柔正弦波悬浮律动
        self.float_offset_y = math.sin(self.tick * 0.065) * 6.5

        if self.bubble_timer > 0:
            self.bubble_timer -= 1

        if self.jump_phase > 0:
            self.jump_phase = max(0.0, self.jump_phase - 0.08)

        if self.active_prop:
            self.active_prop["ttl"] -= 1
            if self.active_prop["ttl"] <= 0:
                self.active_prop = None

        for pt in self.particles[:]:
            pt["ry"] += pt["vy"]
            pt["alpha"] -= 6
            if pt["alpha"] <= 0:
                self.particles.remove(pt)

        if self.auto_walk and not self.dragging:
            screen = QApplication.primaryScreen()
            if screen:
                sgeo = screen.availableGeometry()
                nx = self.x() + int(self.walk_vx)
                if nx <= sgeo.left() + 8:
                    self.walk_vx = abs(self.walk_vx)
                    self.facing_right = True
                elif nx + self.width() >= sgeo.right() - 8:
                    self.walk_vx = -abs(self.walk_vx)
                    self.facing_right = False
                self.move(nx, self.y())

        self.update()

    def _on_metabolism_tick(self):
        """
        真实动物生理代谢模型：
        1. 饱食度、水分、心情随时间自然缓慢下降（如果有便便未清理，心情下降加快）。
        2. 只有胃里有食物 (food_in_gut > 0) 时，肠胃才会消化食物并将其转化为便意 (digestion_progress)。
        3. 水分充足时消化顺畅；当便意累积满 100% 时自动排便！绝不凭空拉屎。
        """
        self.hunger = max(0.0, self.hunger - 0.45)
        self.thirst = max(0.0, self.thirst - 0.52)
        poop_penalty = len(self.poops) * 0.35
        self.fun = max(0.0, self.fun - (0.45 + poop_penalty))

        # 肠胃消化计算：将已吃下的食物逐步转化为消化进度
        if self.food_in_gut > 0.1:
            hydration_factor = 1.25 if self.thirst >= 50.0 else 0.75
            digest_step = min(self.food_in_gut, 3.2 * hydration_factor)
            self.food_in_gut = max(0.0, self.food_in_gut - digest_step)
            self.digestion_progress = min(100.0, self.digestion_progress + digest_step * 1.15)
            self._check_digestion_poop()

        # 自主说话与状态提醒
        if self.bubble_timer <= 0 and not self.hide_all_text and random.random() < 0.32:
            if self.poops and random.random() < 0.55:
                self.say(random.choice(POOP_LINES))
            elif self.hunger < 35.0:
                self.say(random.choice(HUNGRY_LINES))
            elif self.thirst < 35.0:
                self.say(random.choice(THIRSTY_LINES))
            elif self.fun < 35.0:
                self.say(random.choice(BORED_LINES))
            else:
                self.say(random.choice(SELF_TALK_LINES))

        self.save_pet_state()

    # ------------------ 胶囊按钮坐标计算 ------------------
    def _pet_center(self) -> tuple[float, float]:
        cx = self.width() * 0.5
        cy = self.height() * 0.49 + self.float_offset_y * self.scale_factor
        return cx, cy

    def _get_action_capsules(self) -> dict[str, QRectF]:
        """底部一排角色配色圆角小胶囊按钮"""
        s = self.scale_factor
        y = self.height() - int(42 * s)
        w = int(58 * s)
        h = int(26 * s)
        gap = int(6 * s)
        keys = ["feed", "drink", "play", "clean", "size", "hide"]
        total_w = len(keys) * w + (len(keys) - 1) * gap
        start_x = (self.width() - total_w) / 2.0
        return {k: QRectF(start_x + i * (w + gap), y, w, h) for i, k in enumerate(keys)}

    # ------------------ 鼠标、滚轮、快捷键与拖拽事件 ------------------
    def wheelEvent(self, event: QWheelEvent):
        """支持按住 Ctrl + 鼠标滚轮直接无级缩放桌宠大小"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = 0.08 if event.angleDelta().y() > 0 else -0.08
            self.set_pet_scale(self.scale_factor + delta)
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_H:
            self.toggle_hide_all_text()
        elif event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.set_pet_scale(self.scale_factor + 0.1)
        elif event.key() == Qt.Key.Key_Minus:
            self.set_pet_scale(self.scale_factor - 0.1)
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """双击宠物一键隐藏/恢复所有文本框与胶囊"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_hide_all_text()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._build_context_menu().exec(event.globalPosition().toPoint())
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            cx, cy = self._pet_center()
            s = self.scale_factor

            # 1. 点击地面上的便便直接铲除
            for idx, p in enumerate(self.poops):
                px = cx + p["rx"] * s
                py = cy + p["ry"] * s
                if math.hypot(pos.x() - px, pos.y() - py) <= 24 * s:
                    self.poops.pop(idx)
                    self.add_particle("✨铲除+1", p["rx"], p["ry"] - 14, "#50B5A6")
                    self.say("🧹 谢啦朋友！便便清掉了，心情舒畅~")
                    self.save_pet_state()
                    return

            # 2. 点击底部胶囊标签按钮
            if not self.hide_all_text and self.show_capsules:
                for key, rect in self._get_action_capsules().items():
                    if rect.contains(pos):
                        if key == "feed":
                            self.action_feed()
                        elif key == "drink":
                            self.action_drink()
                        elif key == "play":
                            self.action_play()
                        elif key == "clean":
                            self.action_clean_poop()
                        elif key == "size":
                            # 循环切换常用尺寸档位：100% -> 125% -> 145% -> 75% -> 100%
                            cycle = [1.0, 1.25, 1.45, 0.75]
                            cur_idx = min(range(len(cycle)), key=lambda i: abs(cycle[i] - self.scale_factor))
                            self.set_pet_scale(cycle[(cur_idx + 1) % len(cycle)])
                        elif key == "hide":
                            self.toggle_hide_all_text()
                        return

            # 3. 拖动或轻点宠物
            self.dragging = True
            self.mouse_down_pos = event.globalPosition().toPoint()
            self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        self.hover_pos = event.position()
        if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            dist = (event.globalPosition().toPoint() - self.mouse_down_pos).manhattanLength()
            if dist < 6:
                self.trigger_jump()
                icon = random.choice(["❤", "💎", "🎲", "✨"])
                self.add_particle(icon, random.randint(-35, 35), -80, "#B884D8")
                self.fun = min(100.0, self.fun + 4.0)
                self.say(random.choice(CLICK_LINES))
            else:
                # 拖动释放后检查贴边吸附
                self._check_edge_snap()
                if self.snap_edge:
                    self.add_particle("📌 贴边吸附", 0, -85, "#76D2C5")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
            if urls:
                self.drag_hover_file = True
                self.say("📂 松手即可唤出白圆角胶囊输入框改名~", force=True)
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

    # ------------------ 3D 立体感渲染与角色配色胶囊绘制 ------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        s = self.scale_factor
        cx = self.width() * 0.5
        base_cy = self.height() * 0.49
        jump_y = -math.sin(self.jump_phase * math.pi) * 26.0 * s
        cy = base_cy + self.float_offset_y * s + jump_y

        # 1. 地面动态 3D 景深阴影（随上下浮动距离自动缩放与明暗变化）
        float_factor = 1.0 - (self.float_offset_y - 6.5) / 35.0
        sh_w = 195.0 * s * float_factor
        sh_h = 26.0 * s * float_factor
        sh_x = cx - sh_w / 2.0
        sh_y = base_cy + 115.0 * s
        rad_grad = QRadialGradient(QPointF(cx, sh_y + sh_h / 2.0), sh_w / 1.8)
        rad_grad.setColorAt(0.0, QColor(74, 46, 56, 85))
        rad_grad.setColorAt(0.6, QColor(74, 46, 56, 35))
        rad_grad.setColorAt(1.0, QColor(74, 46, 56, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(rad_grad)
        painter.drawEllipse(QRectF(sh_x, sh_y, sh_w, sh_h))

        # 2. 拖拽文件时的松石青柔和胶囊光环
        if self.drag_hover_file:
            pen = QPen(COL_TEAL_MAIN, 3 * s, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(118, 210, 197, 45))
            painter.drawRoundedRect(
                QRectF(cx - 145 * s, cy - 145 * s, 290 * s, 290 * s), 36 * s, 36 * s
            )

        # 3. 绘制 3D 立体感砂金猫猫（含呼吸弹性形变 + 2.5D 视差微倾 + 贴边偏角）
        if not self.pet_pixmap.isNull():
            painter.save()
            breath = math.sin(self.tick * 0.08) * 0.018
            sway_deg = math.sin(self.tick * 0.045) * 2.2
            if self.snap_edge == "left":
                sway_deg += 8.0
            elif self.snap_edge == "right":
                sway_deg -= 8.0

            # 根据鼠标悬停位置计算 2.5D 立体透视微倾角
            dx_norm = max(-1.0, min(1.0, (self.hover_pos.x() - cx) / (180.0 * s)))
            dy_norm = max(-1.0, min(1.0, (self.hover_pos.y() - cy) / (180.0 * s)))
            tilt_y = dx_norm * 7.5
            tilt_x = -dy_norm * 6.0

            transform = QTransform()
            transform.translate(cx, cy)
            transform.rotate(tilt_x, Qt.Axis.XAxis)
            transform.rotate(tilt_y, Qt.Axis.YAxis)
            transform.rotate(sway_deg, Qt.Axis.ZAxis)
            sx = (-1.0 if self.facing_right else 1.0) * (1.0 - breath * 0.4) * s
            sy = (1.0 + breath) * s
            transform.scale(sx, sy)
            painter.setTransform(transform)

            pw, ph = 266, 310
            painter.drawPixmap(int(-pw / 2), int(-ph / 2), pw, ph, self.pet_pixmap)
            painter.restore()

        # 4. 绘制地面上的 3D 便便（带高光圆润造型，点击可直接铲除）
        for p in self.poops:
            px = cx + p["rx"] * s
            py = base_cy + p["ry"] * s
            painter.save()
            painter.setPen(QPen(COL_OUTLINE_DARK, 1.6 * s))
            painter.setBrush(QColor(156, 102, 68))
            painter.drawRoundedRect(QRectF(px - 15 * s, py + 2 * s, 30 * s, 10 * s), 5 * s, 5 * s)
            painter.drawRoundedRect(QRectF(px - 11 * s, py - 5 * s, 22 * s, 9 * s), 4.5 * s, 4.5 * s)
            painter.drawEllipse(QRectF(px - 6 * s, py - 12 * s, 12 * s, 8 * s))
            # 3D 小高光点
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 235, 215, 160))
            painter.drawEllipse(QRectF(px - 6 * s, py - 3 * s, 5 * s, 3 * s))
            painter.restore()

        # 5. 绘制互动道具动画（喂食/喝水/骰子）
        if self.active_prop:
            ptype = self.active_prop["type"]
            bounce = math.sin(self.tick * 0.28) * 6.0 * s
            px, py = cx - 72 * s, cy - 12 * s + bounce
            painter.save()
            painter.setPen(QPen(COL_OUTLINE_DARK, 1.8 * s))
            if ptype == "food":
                painter.setBrush(COL_CREAM_GOLD)
                painter.drawEllipse(QRectF(px - 20 * s, py + 5 * s, 40 * s, 14 * s))
                painter.setBrush(COL_PAW_PINK)
                painter.drawRoundedRect(QRectF(px - 14 * s, py - 9 * s, 28 * s, 18 * s), 8 * s, 8 * s)
            elif ptype == "drink":
                painter.setBrush(COL_TEAL_MAIN)
                painter.drawRoundedRect(QRectF(px - 12 * s, py - 10 * s, 24 * s, 28 * s), 6 * s, 6 * s)
            elif ptype == "toy":
                painter.setBrush(COL_CREAM_GOLD)
                painter.drawRoundedRect(QRectF(px - 15 * s, py - 15 * s, 30 * s, 30 * s), 7 * s, 7 * s)
                painter.setBrush(COL_PURPLE_EYE)
                for ox, oy in ((-6, -6), (0, 0), (6, 6), (-6, 6), (6, -6)):
                    painter.drawEllipse(QPointF(px + ox * s, py + oy * s), 2.5 * s, 2.5 * s)
            painter.restore()

        # 6. 绘制飘字粒子（胶囊风柔和文字）
        for pt in self.particles:
            c = QColor(pt["color"])
            c.setAlpha(max(0, min(255, pt["alpha"])))
            painter.setPen(c)
            painter.setFont(QFont("Microsoft YaHei", max(8, int(10 * s)), QFont.Weight.Bold))
            painter.drawText(QPointF(cx + pt["rx"] * s - 35 * s, cy + pt["ry"] * s), pt["text"])

        # 如果开启了「一键隐藏所有文本框」，以下所有气泡与胶囊全部隐藏！
        if self.hide_all_text:
            return

        # 7. 绘制头顶角色配色胶囊说话气泡
        if self.show_bubble and self.bubble_timer > 0 and self.bubble_text:
            self._draw_capsule_bubble(painter, cx, cy, s)

        # 8. 绘制底部状态小胶囊 & 快捷操作胶囊标签栏
        if self.show_capsules and not self.rename_bar.isVisible():
            self._draw_status_and_action_capsules(painter, s)

    def _draw_capsule_bubble(self, painter: QPainter, cx: float, cy: float, s: float):
        painter.save()
        bw = min(self.width() - 20, int(340 * s))
        bh = int(54 * s)
        bx = cx - bw / 2.0
        by = max(8.0, cy - 198 * s)
        rect = QRectF(bx, by, bw, bh)

        # 阴影
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(74, 46, 56, 32))
        painter.drawRoundedRect(rect.translated(0, 3 * s), 22 * s, 22 * s)

        # 奶油白胶囊主体 + 松石青边框
        path = QPainterPath()
        path.addRoundedRect(rect, 22 * s, 22 * s)
        path.moveTo(cx - 8 * s, by + bh)
        path.lineTo(cx, by + bh + 9 * s)
        path.lineTo(cx + 8 * s, by + bh)
        path.closeSubpath()

        painter.setBrush(COL_CREAM_BG)
        painter.setPen(QPen(COL_TEAL_MAIN, 2.2 * s))
        painter.drawPath(path)

        # 左上角紫粉小胶囊角标 "砂金喵"
        tag_rect = QRectF(bx + 12 * s, by - 9 * s, 54 * s, 18 * s)
        painter.setBrush(COL_PURPLE_EYE)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(tag_rect, 9 * s, 9 * s)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", max(7, int(8 * s)), QFont.Weight.Bold))
        painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, "砂金喵")

        # 气泡正文（深棕紫轮廓色）
        painter.setPen(COL_OUTLINE_DARK)
        painter.setFont(QFont("Microsoft YaHei", max(8, int(9.5 * s)), QFont.Weight.Bold))
        painter.drawText(
            rect.adjusted(14 * s, 6 * s, -14 * s, -4 * s),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.bubble_text,
        )
        painter.restore()

    def _draw_status_and_action_capsules(self, painter: QPainter, s: float):
        painter.save()

        # 第一排：4 个独立状态小胶囊标签（饱食 / 水分 / 心情 / 肠胃便意）
        pills = [
            (f"饱食 {int(self.hunger)}%", self.hunger, COL_TEAL_MAIN, COL_TEAL_SOFT),
            (f"水分 {int(self.thirst)}%", self.thirst, QColor(112, 182, 238), QColor(230, 243, 255, 240)),
            (f"心情 {int(self.fun)}%", self.fun, COL_CREAM_GOLD, COL_CREAM_BG),
            (f"便意 {int(self.digestion_progress)}%", self.digestion_progress, COL_PURPLE_EYE, COL_PURPLE_SOFT),
        ]
        pw = int(84 * s)
        ph = int(22 * s)
        gap = int(6 * s)
        total_w = len(pills) * pw + (len(pills) - 1) * gap
        sx0 = (self.width() - total_w) / 2.0
        sy0 = self.height() - int(74 * s)

        painter.setFont(QFont("Microsoft YaHei", max(7, int(8 * s)), QFont.Weight.Bold))
        for i, (label, val, bar_col, bg_col) in enumerate(pills):
            rx = sx0 + i * (pw + gap)
            r = QRectF(rx, sy0, pw, ph)
            # 胶囊底板
            painter.setPen(QPen(bar_col, 1.5 * s))
            painter.setBrush(bg_col)
            painter.drawRoundedRect(r, ph / 2.0, ph / 2.0)

            # 胶囊内部进度填充条
            fill_ratio = max(0.0, min(1.0, val / 100.0))
            if fill_ratio > 0.04:
                fill_c = QColor(bar_col)
                fill_c.setAlpha(65)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(fill_c)
                painter.drawRoundedRect(
                    QRectF(rx + 2 * s, sy0 + 2 * s, (pw - 4 * s) * fill_ratio, ph - 4 * s),
                    (ph - 4 * s) / 2.0,
                    (ph - 4 * s) / 2.0,
                )

            painter.setPen(COL_OUTLINE_DARK)
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, label)

        # 第二排：6 个角色配色圆角胶囊按钮
        btn_specs = {
            "feed": ("喂食", COL_TEAL_SOFT, COL_TEAL_MAIN),
            "drink": ("喝水", QColor(232, 245, 255, 245), QColor(102, 178, 235)),
            "play": ("玩耍", COL_CREAM_BG, QColor(228, 182, 100)),
            "clean": (
                f"铲屎({len(self.poops)})" if self.poops else "铲屎",
                COL_PURPLE_SOFT,
                COL_PURPLE_EYE,
            ),
            "size": (f"{int(self.scale_factor*100)}%", COL_CREAM_BG, COL_PAW_PINK),
            "hide": ("隐藏", COL_CREAM_BG, QColor(145, 125, 135)),
        }
        painter.setFont(QFont("Microsoft YaHei", max(7, int(8.5 * s)), QFont.Weight.Bold))
        for key, rect in self._get_action_capsules().items():
            txt, bg_c, border_c = btn_specs[key]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(74, 46, 56, 25))
            painter.drawRoundedRect(rect.translated(0, 2 * s), rect.height() / 2.0, rect.height() / 2.0)

            painter.setBrush(bg_c)
            painter.setPen(QPen(border_c, 1.6 * s))
            painter.drawRoundedRect(rect, rect.height() / 2.0, rect.height() / 2.0)

            painter.setPen(COL_OUTLINE_DARK)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

        painter.restore()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = ShajinPetWindow(preview_mode=("--preview" in sys.argv))
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
