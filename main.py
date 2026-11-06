#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
砂金猫猫桌面宠物 (shajincw) - Windows 桌面宠物 & 拖拽文件快捷重命名工具
功能：
1. 纯透明无边框置顶桌宠（Q弹呼吸、摇晃、跳跃、桌面散步）
2. 养成互动：喂食、喝水、玩玩具（掷骰子/筹码）、拉屎与点击铲屎
3. 状态系统：会饿、会渴、会无聊、会嫌脏，定时自主说话 + 点击随机台词
4. 拖拽文件重命名：把 000.jpg 拖到宠物身上 -> 输入 555 -> 原地重命名为 000（555）.jpg
"""

import json
import math
import os
import random
import sys
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    QUrl,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


def resource_path(rel_path: str) -> Path:
    """支持 PyInstaller 单文件打包后的资源路径解析"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel_path
    return Path(__file__).resolve().parent / rel_path


STATE_FILE = Path.home() / ".shajincw_pet_state.json"

# 砂金猫猫台词库
CLICK_LINES = [
    "喵呜~ 朋友，摸肚皮可是要付筹码的哦！",
    "所有，或者一无所有~ 今天想赌一把大的吗？",
    "别戳啦，墨镜都要被你戳歪了！",
    "这身小青衫好看吧？本总监亲自挑的定制款~",
    "呼噜噜……勉强允许你再挠一下下巴。",
    "朋友，有文件要改名吗？直接拖到我身上就行！",
    "我的尾巴可不是随便给别人摸的，你是例外~",
    "看我这双紫眼睛，是不是写满了『稳赚不赔』？",
    "摇摇晃晃~ 躺在你的桌面上晒太阳真舒服。",
]

SELF_TALK_LINES = [
    "（晃尾巴）今天的桌面风水不错，适合赢一把大的~",
    "盯——朋友，你都盯着屏幕看半天啦，喝口水歇会儿？",
    "把文件拖给我就能秒改后缀，本总监办事效率一流！",
    "呼噜……呼噜……翻个肚皮晒太阳~",
    "点数是三枚『砂金』，看来幸运女神今天也在我这边。",
    "刚才好像看到一只飞虫飞过去了……本喵才不会去扑呢！",
]

HUNGRY_LINES = [
    "咕噜噜……朋友，本总监的肚子在抗议了，快喂点好吃的！",
    "饿扁啦……没有小鱼干和猫条，连骰子都摇不动了……",
    "再不投喂的话，我就要去啃你的桌面图标了哦！",
]

THIRSTY_LINES = [
    "嗓子干得像茨冈尼亚的沙漠……朋友，赏杯冰饮吧？",
    "想喝冰镇苏打水，或者温牛奶也行喵~",
    "渴啦渴啦，水碗都见底了！",
]

BORED_LINES = [
    "好无聊啊朋友……陪我玩把骰子，或者拿逗猫棒晃两下？",
    "发呆中……都没人陪本总监玩玩具，尾巴都要长蘑菇了。",
    "唉，无聊到想自己跟自己的尾巴猜拳了……",
]

POOP_LINES = [
    "噗——咳咳，朋友，我旁边那坨东西……麻烦帮我铲一下？",
    "唔，地板上有点味道了，快点一下便便或者『🧹铲屎』清理掉吧！",
    "本总监可是很爱干净的，快帮我把便便清掉喵！",
]


class RenameDialog(QDialog):
    """拖拽文件到宠物身上时弹出的快捷后缀重命名窗口"""

    def __init__(self, file_paths: list[Path], parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.renamed_results: list[tuple[Path, Path]] = []

        self.setWindowTitle("砂金桌宠 · 快捷文件后缀重命名")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(430)

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        card = QWidget(self)
        card.setObjectName("RenameCard")
        card.setStyleSheet(
            """
            QWidget#RenameCard {
                background-color: #1A2129;
                border: 2px solid #28C3A6;
                border-radius: 16px;
            }
            QLabel {
                color: #ECEFF4;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            }
            QLineEdit {
                background-color: #252E38;
                border: 2px solid #3A4756;
                border-radius: 10px;
                padding: 8px 12px;
                color: #FFD166;
                font-size: 15px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border-color: #28C3A6;
            }
            QCheckBox {
                color: #A3B1C2;
                font-size: 12px;
            }
            QPushButton {
                border-radius: 9px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#BtnOk {
                background-color: #28C3A6;
                color: #10161B;
                border: none;
            }
            QPushButton#BtnOk:hover {
                background-color: #35DFC0;
            }
            QPushButton#BtnCancel {
                background-color: #2B3541;
                color: #CBD5E1;
                border: 1px solid #3E4C5E;
            }
            QPushButton#BtnCancel:hover {
                background-color: #364250;
            }
            """
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = QLabel(f"🎲 收到 {len(self.file_paths)} 个文件，请输入要追加的后缀：")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #28C3A6;")
        layout.addWidget(title)

        first = self.file_paths[0]
        src_info = QLabel(f"原文件：{first.name}" + (f" 等 {len(self.file_paths)} 项" if len(self.file_paths) > 1 else ""))
        src_info.setStyleSheet("font-size: 12px; color: #94A3B8;")
        layout.addWidget(src_info)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("例如输入 555  ➜  自动变成 000（555）.jpg")
        self.input_edit.textChanged.connect(self._update_preview)
        self.input_edit.returnPressed.connect(self._do_rename)
        layout.addWidget(self.input_edit)

        # 括号样式选择（默认中文括号 000（555）.jpg，也可切换英文括号或无括号）
        opt_row = QHBoxLayout()
        self.chk_bracket = QCheckBox("自动包裹括号（如 000（555）.jpg）")
        self.chk_bracket.setChecked(True)
        self.chk_bracket.toggled.connect(self._update_preview)

        self.chk_half_bracket = QCheckBox("使用 000（555).jpg 括号格式")
        self.chk_half_bracket.setChecked(True)
        self.chk_half_bracket.toggled.connect(self._update_preview)

        opt_row.addWidget(self.chk_bracket)
        opt_row.addWidget(self.chk_half_bracket)
        layout.addLayout(opt_row)

        self.preview_lbl = QLabel("")
        self.preview_lbl.setWordWrap(True)
        self.preview_lbl.setStyleSheet(
            "background: #13181E; padding: 8px 10px; border-radius: 8px; font-size: 12px; color: #FFD166;"
        )
        layout.addWidget(self.preview_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("BtnCancel")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("立即重命名 (Enter)")
        btn_ok.setObjectName("BtnOk")
        btn_ok.clicked.connect(self._do_rename)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        root_layout.addWidget(card)
        self._update_preview()

    def _compute_new_name(self, orig_path: Path, raw_suffix: str) -> str:
        s = raw_suffix.strip()
        if not s:
            return orig_path.name
        stem = orig_path.stem
        ext = orig_path.suffix
        # 如果用户自己已经输入了括号（例如 "（555）"、"(555)"、"（555)"），直接使用用户输入
        if s.startswith(("（", "(")) or not self.chk_bracket.isChecked():
            formatted = s
        else:
            if self.chk_half_bracket.isChecked():
                formatted = f"（{s})"
            else:
                formatted = f"（{s}）"
        return f"{stem}{formatted}{ext}"

    def _update_preview(self):
        raw = self.input_edit.text()
        first = self.file_paths[0]
        new_name = self._compute_new_name(first, raw or "555")
        self.preview_lbl.setText(f"预览效果：{first.name}   ➜   {new_name}\n保存位置：{first.parent}")

    def _do_rename(self):
        raw = self.input_edit.text().strip()
        if not raw:
            self.input_edit.setFocus()
            return
        errors = []
        for p in self.file_paths:
            if not p.exists():
                errors.append(f"文件不存在: {p.name}")
                continue
            new_name = self._compute_new_name(p, raw)
            target = p.with_name(new_name)
            try:
                p.rename(target)
                self.renamed_results.append((p, target))
            except Exception as exc:
                errors.append(f"{p.name}: {exc}")

        if errors:
            QMessageBox.warning(self, "部分文件重命名失败", "\n".join(errors))
        self.accept()


class ShajinPetWindow(QWidget):
    """砂金猫猫主桌面宠物窗口"""

    WIN_W = 400
    WIN_H = 510

    def __init__(self, preview_mode: bool = False):
        super().__init__()
        self.preview_mode = preview_mode

        # 宠物核心数值 (0~100)
        self.hunger = 82.0      # 饱食度（低了会饿）
        self.thirst = 85.0      # 水分（低了会渴）
        self.fun = 80.0         # 心情/不无聊度（低了会无聊）
        self.poops: list[dict] = []  # 地面上的便便列表 [{"x": float, "y": float, "scale": float}]

        self.load_pet_state()

        # 动画与交互状态
        self.tick = 0
        self.auto_walk = False
        self.walk_vx = 1.6
        self.facing_right = False
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.mouse_down_pos = QPoint()
        self.drag_hover_file = False
        self.show_panel = True

        # 气泡文字与限时动画特效
        self.bubble_text = "喵呜~ 我是你的桌面总监砂金！把文件拖给我就能秒改后缀哦~"
        self.bubble_timer = 180  # 帧数 (约 6 秒)
        self.active_prop = None  # {"type": "food"|"drink"|"toy", "ttl": int}
        self.particles: list[dict] = []  # 飘字/爱心/闪光粒子
        self.jump_phase = 0.0

        # 加载高清透明立绘
        sprite_file = resource_path("assets/pet_sprite.png")
        self.pet_pixmap = QPixmap(str(sprite_file))

        self._init_window()
        self._init_tray()
        self._init_timers()

    def _init_window(self):
        self.setWindowTitle("砂金桌宠 (shajincw)")
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFixedSize(self.WIN_W, self.WIN_H)

        icon_path = resource_path("assets/pet_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # 默认停靠在屏幕右下角偏左位置
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.WIN_W - 60, geo.bottom() - self.WIN_H - 20)

    def _init_tray(self):
        icon_path = resource_path("assets/pet_icon.ico")
        tray_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon(self.pet_pixmap)
        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip("砂金猫猫桌宠 (shajincw)")

        menu = self._build_context_menu()
        self.tray.setContextMenu(menu)
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
                background-color: #1B222A;
                color: #ECEFF4;
                border: 1px solid #28C3A6;
                border-radius: 8px;
                padding: 6px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #28C3A6;
                color: #10161B;
                font-weight: bold;
            }
            """
        )

        act_feed = QAction("🍖 喂食（黄金猫糕/鱼子酱）", self)
        act_feed.triggered.connect(self.action_feed)
        menu.addAction(act_feed)

        act_drink = QAction("🧋 喝水（冰镇特调/鲜奶）", self)
        act_drink.triggered.connect(self.action_drink)
        menu.addAction(act_drink)

        act_play = QAction("🎲 玩玩具（掷骰子/逗猫棒）", self)
        act_play.triggered.connect(self.action_play)
        menu.addAction(act_play)

        act_clean = QAction("🧹 铲屎清理地板", self)
        act_clean.triggered.connect(self.action_clean_poop)
        menu.addAction(act_clean)

        act_poop_now = QAction("💩 让它现在拉个便便（测试）", self)
        act_poop_now.triggered.connect(self.spawn_poop)
        menu.addAction(act_poop_now)

        menu.addSeparator()

        act_rename = QAction("📁 选择文件加后缀重命名...", self)
        act_rename.triggered.connect(self.open_manual_rename_picker)
        menu.addAction(act_rename)

        act_walk = QAction("🚶 开启/关闭 桌面自由散步", self)
        act_walk.triggered.connect(self.toggle_walk)
        menu.addAction(act_walk)

        act_panel = QAction("🎛️ 显示/隐藏 底部快捷栏", self)
        act_panel.triggered.connect(self.toggle_panel)
        menu.addAction(act_panel)

        menu.addSeparator()

        act_quit = QAction("🚪 退出桌宠", self)
        act_quit.triggered.connect(self.quit_pet)
        menu.addAction(act_quit)

        return menu

    def _init_timers(self):
        # 30 FPS 动画刷新计时器
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start(33)

        # 状态自然衰减与自主行为计时器 (每 5 秒检查一次)
        self.life_timer = QTimer(self)
        self.life_timer.timeout.connect(self._on_life_tick)
        self.life_timer.start(5000)

    def load_pet_state(self):
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.hunger = float(data.get("hunger", 82.0))
                self.thirst = float(data.get("thirst", 85.0))
                self.fun = float(data.get("fun", 80.0))
                self.poops = data.get("poops", [])[:4]
        except Exception:
            pass

    def save_pet_state(self):
        try:
            data = {
                "hunger": round(self.hunger, 1),
                "thirst": round(self.thirst, 1),
                "fun": round(self.fun, 1),
                "poops": self.poops[:4],
            }
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ------------------ 互动功能 ------------------
    def say(self, text: str, duration_frames: int = 160):
        self.bubble_text = text
        self.bubble_timer = duration_frames
        self.update()

    def add_particle(self, text: str, x: float, y: float, color: str = "#FFD166"):
        self.particles.append(
            {"text": text, "x": x, "y": y, "vy": -1.6, "alpha": 255, "color": color}
        )

    def trigger_jump(self):
        self.jump_phase = 1.0

    def action_feed(self):
        self.hunger = min(100.0, self.hunger + 26.0)
        self.active_prop = {"type": "food", "ttl": 75}
        self.trigger_jump()
        self.add_particle("🍖 饱食 +26", 195, 165, "#28C3A6")
        self.add_particle("❤", 145, 180, "#FF6B8B")
        self.say(random.choice([
            "嗷呜！是香喷喷的猫猫糕和顶级鱼子酱，朋友真大方~",
            "吧唧吧唧……吃饱喝足，下一把筹码全押！",
            "唔~ 味道不错！本总监宣布你是最佳合伙人~",
        ]))
        # 吃饱后有一定概率稍后拉便便
        if len(self.poops) < 3 and random.random() < 0.45:
            QTimer.singleShot(4500, self.spawn_poop)
        self.save_pet_state()

    def action_drink(self):
        self.thirst = min(100.0, self.thirst + 28.0)
        self.active_prop = {"type": "drink", "ttl": 75}
        self.trigger_jump()
        self.add_particle("🧋 水分 +28", 200, 165, "#4CC9F0")
        self.add_particle("✨", 240, 185, "#FFD166")
        self.say(random.choice([
            "咕嘟咕嘟……哈~ 冰镇特调就是爽快！",
            "谢谢朋友的水~ 嗓子润好了，继续陪你聊天！",
            "甜度刚好！再来一杯本总监也喝得下~",
        ]))
        self.save_pet_state()

    def action_play(self):
        self.fun = min(100.0, self.fun + 28.0)
        self.hunger = max(5.0, self.hunger - 3.0)
        self.active_prop = {"type": "toy", "ttl": 80}
        self.trigger_jump()
        pts = random.randint(1, 6)
        self.add_particle(f"🎲 骰子 {pts} 点！心情 +28", 195, 160, "#FFD166")
        self.say(random.choice([
            f"看招！骰子掷出了 {pts} 点——朋友，这局算我们双赢！",
            "喵呜！（扑向金色筹码）这玩具深得本总监欢心~",
            "哈哈，再摇一次！跟朋友玩永远不会腻~",
        ]))
        self.save_pet_state()

    def spawn_poop(self):
        if len(self.poops) >= 4:
            return
        px = random.choice([random.randint(45, 105), random.randint(285, 340)])
        py = random.randint(365, 405)
        self.poops.append({"x": px, "y": py})
        self.add_particle("💩 噗~", px, py - 15, "#D4A373")
        self.say(random.choice(POOP_LINES))
        self.save_pet_state()

    def action_clean_poop(self):
        if not self.poops:
            self.say("地板干干净净的，一粒灰尘都没有哦朋友~")
            return
        count = len(self.poops)
        for p in self.poops:
            self.add_particle("✨已清理", p["x"], p["y"] - 10, "#28C3A6")
        self.poops.clear()
        self.fun = min(100.0, self.fun + 10.0)
        self.trigger_jump()
        self.say(f"🧹 呼~ 清理掉 {count} 坨便便，全身舒坦！谢谢铲屎官朋友~")
        self.save_pet_state()

    def toggle_walk(self):
        self.auto_walk = not self.auto_walk
        if self.auto_walk:
            self.say("🚶 出发咯！本总监要在你的任务栏上面巡视领地了~")
        else:
            self.say("📌 已停下脚步，乖乖待在这里陪你办公~")

    def toggle_panel(self):
        self.show_panel = not self.show_panel
        self.update()

    def open_manual_rename_picker(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要加后缀重命名的文件（也可直接将文件拖到桌宠身上）"
        )
        if files:
            paths = [Path(f) for f in files]
            self.run_rename_dialog(paths)

    def run_rename_dialog(self, paths: list[Path]):
        dlg = RenameDialog(paths, self)
        # 弹窗定位在桌宠窗口附近
        pet_geo = self.geometry()
        dlg.move(max(40, pet_geo.x() - 20), max(40, pet_geo.y() + 120))
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.renamed_results:
            _, new_p = dlg.renamed_results[0]
            total = len(dlg.renamed_results)
            self.trigger_jump()
            self.add_particle("📁 改名成功!", 200, 155, "#FFD166")
            if total == 1:
                self.say(f"搞定！已重命名为「{new_p.name}」，保存在原目录啦~")
            else:
                self.say(f"搞定！「{new_p.name}」等 {total} 个文件已全部在原地址重命名完毕~")

    def quit_pet(self):
        self.save_pet_state()
        self.tray.hide()
        QApplication.quit()

    # ------------------ 定时心跳 ------------------
    def _on_anim_tick(self):
        self.tick += 1

        if self.bubble_timer > 0:
            self.bubble_timer -= 1

        if self.jump_phase > 0:
            self.jump_phase = max(0.0, self.jump_phase - 0.08)

        if self.active_prop:
            self.active_prop["ttl"] -= 1
            if self.active_prop["ttl"] <= 0:
                self.active_prop = None

        for pt in self.particles[:]:
            pt["y"] += pt["vy"]
            pt["alpha"] -= 6
            if pt["alpha"] <= 0:
                self.particles.remove(pt)

        # 自由散步逻辑
        if self.auto_walk and not self.dragging:
            screen = QApplication.primaryScreen()
            if screen:
                sgeo = screen.availableGeometry()
                nx = self.x() + int(self.walk_vx)
                if nx <= sgeo.left() + 10:
                    self.walk_vx = abs(self.walk_vx)
                    self.facing_right = True
                elif nx + self.WIN_W >= sgeo.right() - 10:
                    self.walk_vx = -abs(self.walk_vx)
                    self.facing_right = False
                self.move(nx, self.y())

        self.update()

    def _on_life_tick(self):
        # 缓慢消耗饥饿、水分与心情
        self.hunger = max(0.0, self.hunger - 0.45)
        self.thirst = max(0.0, self.thirst - 0.55)
        self.fun = max(0.0, self.fun - 0.50)

        # 随机拉屎概率
        if len(self.poops) < 3 and self.hunger > 40 and random.random() < 0.035:
            self.spawn_poop()
            return

        # 当气泡空闲时，触发饥饿/口渴/无聊/嫌脏提醒或自主说话
        if self.bubble_timer <= 0 and random.random() < 0.35:
            if self.poops and random.random() < 0.55:
                self.say(random.choice(POOP_LINES))
            elif self.hunger < 35:
                self.say(random.choice(HUNGRY_LINES))
            elif self.thirst < 35:
                self.say(random.choice(THIRSTY_LINES))
            elif self.fun < 35:
                self.say(random.choice(BORED_LINES))
            else:
                self.say(random.choice(SELF_TALK_LINES))

        self.save_pet_state()

    # ------------------ 鼠标与文件拖拽事件 ------------------
    def _get_button_rects(self) -> dict[str, QRectF]:
        """底部快捷操作按钮热区"""
        y = 458
        w, h = 56, 30
        gap = 6
        start_x = 18
        keys = ["feed", "drink", "play", "clean", "walk", "rename"]
        return {k: QRectF(start_x + i * (w + gap), y, w, h) for i, k in enumerate(keys)}

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._build_context_menu().exec(event.globalPosition().toPoint())
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()

            # 1. 检查是否点击了地面上的便便（直接点便便即可铲屎）
            for idx, p in enumerate(self.poops):
                if math.hypot(pos.x() - p["x"], pos.y() - p["y"]) <= 24:
                    self.poops.pop(idx)
                    self.add_particle("✨铲除+1", pos.x(), pos.y() - 10, "#28C3A6")
                    self.say("🧹 谢啦朋友！少了一坨便便，空气都清新了~")
                    self.save_pet_state()
                    return

            # 2. 检查是否点击了底部快捷按钮栏
            if self.show_panel:
                for key, rect in self._get_button_rects().items():
                    if rect.contains(pos):
                        if key == "feed":
                            self.action_feed()
                        elif key == "drink":
                            self.action_drink()
                        elif key == "play":
                            self.action_play()
                        elif key == "clean":
                            self.action_clean_poop()
                        elif key == "walk":
                            self.toggle_walk()
                        elif key == "rename":
                            self.open_manual_rename_picker()
                        return

            # 3. 否则进入拖拽或点击宠物主体
            self.dragging = True
            self.mouse_down_pos = event.globalPosition().toPoint()
            self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            dist = (event.globalPosition().toPoint() - self.mouse_down_pos).manhattanLength()
            if dist < 6:
                # 轻点宠物：随机说话 + Q弹跳起 + 飘爱心/筹码
                self.trigger_jump()
                p_icon = random.choice(["❤", "💎", "🎲", "✨"])
                self.add_particle(p_icon, event.position().x(), event.position().y() - 20, "#FFD166")
                self.fun = min(100.0, self.fun + 4.0)
                self.say(random.choice(CLICK_LINES))

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
            if urls:
                self.drag_hover_file = True
                self.say("📂 松开鼠标，把文件交给本总监改名吧！")
                event.acceptProposedAction()
                self.update()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.drag_hover_file = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self.drag_hover_file = False
        self.update()
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            QTimer.singleShot(50, lambda: self.run_rename_dialog(paths))

    # ------------------ 绘制渲染 (60fps QPainter) ------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 预览截图模式下绘制桌面壁纸感底色，实际运行时 100% 全透明
        if self.preview_mode:
            grad = QLinearGradient(0, 0, self.WIN_W, self.WIN_H)
            grad.setColorAt(0.0, QColor(24, 32, 44))
            grad.setColorAt(1.0, QColor(15, 20, 28))
            painter.fillRect(0, 0, self.WIN_W, self.WIN_H, grad)

        # 1. 拖拽文件悬停光环提示
        if self.drag_hover_file:
            pen = QPen(QColor(40, 195, 166, 220), 3, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(40, 195, 166, 40))
            painter.drawRoundedRect(QRectF(25, 95, 350, 320), 24, 24)

        # 2. 地面柔和阴影
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 65))
        painter.drawEllipse(QRectF(95, 382, 210, 28))

        # 3. 绘制砂金猫猫本体（呼吸缩放 + 轻柔摇摆 + 点击跳跃）
        if not self.pet_pixmap.isNull():
            painter.save()
            breath = math.sin(self.tick * 0.08) * 0.022
            sway_deg = math.sin(self.tick * 0.05) * 2.4
            jump_y = -math.sin(self.jump_phase * math.pi) * 28.0

            cx, cy = 200.0, 265.0 + jump_y
            painter.translate(cx, cy)
            painter.rotate(sway_deg)
            sx = (-1.0 if self.facing_right else 1.0) * (1.0 - breath * 0.5)
            sy = 1.0 + breath
            painter.scale(sx, sy)

            pw, ph = 248, 292
            painter.drawPixmap(int(-pw / 2), int(-ph / 2), pw, ph, self.pet_pixmap)
            painter.restore()

        # 4. 绘制地面上的便便 💩（可点击铲除）
        font_emoji = QFont("Segoe UI Emoji", 20)
        painter.setFont(font_emoji)
        for p in self.poops:
            px, py = p["x"], p["y"]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(110, 71, 32, 230))
            # 画三层可爱便便造型（不依赖系统 Emoji 字库，保证任何电脑都清晰好看）
            painter.drawRoundedRect(QRectF(px - 16, py + 2, 32, 11), 5, 5)
            painter.drawRoundedRect(QRectF(px - 12, py - 6, 24, 10), 5, 5)
            painter.drawEllipse(QRectF(px - 6, py - 13, 12, 9))
            # 臭气波浪线
            wiggle = math.sin(self.tick * 0.15 + px) * 2
            painter.setPen(QPen(QColor(168, 218, 100, 190), 2))
            painter.drawLine(int(px - 6 + wiggle), int(py - 17), int(px - 6 - wiggle), int(py - 25))
            painter.drawLine(int(px + 6 - wiggle), int(py - 17), int(px + 6 + wiggle), int(py - 25))

        # 5. 绘制正在进行的互动道具（喂食/喝水/玩具）
        if self.active_prop:
            ptype = self.active_prop["type"]
            bounce = math.sin(self.tick * 0.25) * 6
            px, py = 125, 245 + bounce
            painter.save()
            if ptype == "food":
                # 黄金鱼子酱猫糕盘
                painter.setBrush(QColor(255, 209, 102))
                painter.setPen(QPen(QColor(120, 70, 20), 2))
                painter.drawEllipse(QRectF(px - 22, py + 6, 44, 16))
                painter.setBrush(QColor(244, 162, 97))
                painter.drawRoundedRect(QRectF(px - 15, py - 10, 30, 20), 8, 8)
            elif ptype == "drink":
                # 冰镇特调杯 + 吸管
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.setBrush(QColor(76, 201, 240, 220))
                painter.drawRoundedRect(QRectF(px - 13, py - 12, 26, 32), 5, 5)
                painter.setPen(QPen(QColor(255, 107, 139), 3))
                painter.drawLine(int(px + 4), int(py - 12), int(px + 12), int(py - 24))
            elif ptype == "toy":
                # 砂金金色骰子
                painter.setBrush(QColor(255, 209, 102))
                painter.setPen(QPen(QColor(140, 90, 15), 2))
                painter.drawRoundedRect(QRectF(px - 16, py - 16, 32, 32), 7, 7)
                painter.setBrush(QColor(140, 90, 15))
                for dx, dy in ((-7, -7), (0, 0), (7, 7), (-7, 7), (7, -7)):
                    painter.drawEllipse(QPointF(px + dx, py + dy), 2.5, 2.5)
            painter.restore()

        # 6. 绘制头顶台词气泡
        if self.bubble_timer > 0 and self.bubble_text:
            self._draw_speech_bubble(painter, self.bubble_text)

        # 7. 绘制飘字与爱心粒子
        for pt in self.particles:
            c = QColor(pt["color"])
            c.setAlpha(max(0, min(255, pt["alpha"])))
            painter.setPen(c)
            painter.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
            painter.drawText(QPointF(pt["x"] - 30, pt["y"]), pt["text"])

        # 8. 绘制底部迷你状态条与快捷交互栏
        if self.show_panel:
            self._draw_bottom_dock(painter)

    def _draw_speech_bubble(self, painter: QPainter, text: str):
        painter.save()
        rect = QRectF(24, 14, 352, 68)

        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        # 气泡小尖角指向砂金猫猫头顶
        path.moveTo(185, 82)
        path.lineTo(198, 95)
        path.lineTo(210, 82)
        path.closeSubpath()

        painter.setBrush(QColor(26, 33, 42, 238))
        painter.setPen(QPen(QColor(40, 195, 166, 230), 2))
        painter.drawPath(path)

        painter.setPen(QColor(240, 245, 250))
        font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = rect.adjusted(14, 8, -14, -8)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            text,
        )
        painter.restore()

    def _draw_bottom_dock(self, painter: QPainter):
        painter.save()
        # 背景胶囊底板
        dock_rect = QRectF(10, 422, 380, 74)
        painter.setBrush(QColor(22, 28, 36, 225))
        painter.setPen(QPen(QColor(58, 72, 88, 200), 1.5))
        painter.drawRoundedRect(dock_rect, 14, 14)

        # 第一行：饱食 / 水分 / 心情 三条状态进度条
        stats = [
            ("饱食", self.hunger, QColor(40, 195, 166)),
            ("水分", self.thirst, QColor(76, 201, 240)),
            ("心情", self.fun, QColor(255, 209, 102)),
        ]
        painter.setFont(QFont("Microsoft YaHei", 8, QFont.Weight.Bold))
        for i, (name, val, col) in enumerate(stats):
            bx = 22 + i * 122
            by = 432
            painter.setPen(QColor(200, 210, 222))
            painter.drawText(QRectF(bx, by, 34, 16), Qt.AlignmentFlag.AlignVCenter, name)

            # 进度槽
            bar_bg = QRectF(bx + 32, by + 4, 76, 8)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(45, 55, 68))
            painter.drawRoundedRect(bar_bg, 4, 4)

            fill_w = max(4.0, 76.0 * (max(0.0, min(100.0, val)) / 100.0))
            painter.setBrush(col if val >= 35 else QColor(240, 90, 90))
            painter.drawRoundedRect(QRectF(bx + 32, by + 4, fill_w, 8), 4, 4)

        # 第二行：6 个快捷操作按钮
        btn_labels = {
            "feed": ("喂食", QColor(40, 195, 166)),
            "drink": ("喝水", QColor(76, 201, 240)),
            "play": ("玩耍", QColor(255, 209, 102)),
            "clean": (f"铲屎({len(self.poops)})" if self.poops else "铲屎", QColor(244, 162, 97)),
            "walk": ("散步中" if self.auto_walk else "散步", QColor(168, 130, 255)),
            "rename": ("改名", QColor(255, 120, 150)),
        }
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        for key, rect in self._get_button_rects().items():
            txt, col = btn_labels[key]
            painter.setBrush(QColor(36, 45, 56, 240))
            painter.setPen(QPen(col, 1.3))
            painter.drawRoundedRect(rect, 7, 7)
            painter.setPen(col)
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
