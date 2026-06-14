import sys
import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QLabel, QPushButton, QFileDialog,
    QMenu, QMessageBox, QLineEdit, QInputDialog, QFrame, QCheckBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage, QIcon, QAction, QColor, QPainter, QFont, QBrush, QPen

from database import GameDB
from scanner import scan_directory

def get_base_dir():
    """兼容源码运行和 PyInstaller 打包后的路径。"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

BASE_DIR = get_base_dir()
COVERS_DIR = BASE_DIR / "covers"


def generate_cover_pixmap(name, size=200):
    """根据游戏名生成一个暗色主题的默认封面（带首字母和彩色圆）。"""
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))

    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)

    # 暗色背景
    bg = QColor(18, 18, 22)
    painter.setBrush(QBrush(bg))
    painter.setPen(Qt.NoPen)
    painter.drawRect(0, 0, size, size)

    # 根据名字 hash 生成一个主色，不同游戏颜色不同
    hue = (hash(name) % 360) / 360.0
    color = QColor.fromHsvF(hue, 0.75, 0.65)

    # 中心圆
    cx = cy = size // 2
    r = int(size * 0.32)
    painter.setBrush(QBrush(color))
    painter.setPen(QPen(QColor(255, 255, 255, 40), 2))
    painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    # 首字母大字
    text = name[0].upper() if name else "?"
    font = QFont("Microsoft YaHei", int(size * 0.35), QFont.Bold)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(img.rect(), Qt.AlignCenter, text)

    # 底部游戏名
    display_name = name if len(name) <= 12 else name[:10] + ".."
    name_font = QFont("Microsoft YaHei", int(size * 0.09), QFont.Normal)
    painter.setFont(name_font)
    painter.setPen(QColor(160, 160, 160))
    painter.drawText(0, int(size * 0.76), size, int(size * 0.2), Qt.AlignCenter | Qt.AlignTop, display_name)

    painter.end()
    return QPixmap.fromImage(img)


def get_default_pixmap(size=200):
    """生成一个暗色占位图（无游戏名版本）。"""
    img = QImage(size, size, QImage.Format_RGB888)
    img.fill(QColor(30, 30, 30))
    return QPixmap.fromImage(img)


class GameCard(QFrame):
    def __init__(self, game, db, on_removed=None, on_selected=None, parent=None):
        super().__init__(parent)
        self.game = game
        self.db = db
        self.on_removed = on_removed
        self.on_selected = on_selected
        self.setFixedSize(220, 280)
        self.setup_ui()
        self.load_cover()
        self._batch_mode = False
        self._selected = False

    def setup_ui(self):
        self.setStyleSheet("""
            GameCard {
                background: #1a1a1a;
                border-radius: 10px;
                border: 2px solid #333;
            }
            GameCard:hover {
                border: 2px solid #555;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 封面图
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setStyleSheet("""
            border: 2px solid #333;
            border-radius: 8px;
            background: #222;
        """)
        self.cover_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)

        # 批量选择复选框
        self.check_box = QCheckBox(self)
        self.check_box.setGeometry(10, 10, 22, 22)
        self.check_box.setStyleSheet("""
            QCheckBox {
                background: rgba(0,0,0,0.7);
                border-radius: 4px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid #888;
                background: #222;
            }
            QCheckBox::indicator:checked {
                background: #4a90d9;
                border: 2px solid #4a90d9;
            }
        """)
        self.check_box.setVisible(False)
        self.check_box.stateChanged.connect(self.on_check_changed)

        # 游戏名
        self.name_label = QLabel(self.game["name"])
        self.name_label.setStyleSheet("""
            color: white;
            font-size: 13px;
            font-weight: bold;
            padding: 5px 8px;
            background: #1a1a1a;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedHeight(40)
        layout.addWidget(self.name_label)

        self.setCursor(Qt.PointingHandCursor)

    def on_check_changed(self, state):
        self._selected = state == Qt.Checked
        self.update_border()
        if self.on_selected:
            self.on_selected(self, self._selected)

    def set_batch_mode(self, active):
        self._batch_mode = active
        self.check_box.setVisible(active)
        if not active:
            self.check_box.setChecked(False)
            self._selected = False
            self.update_border()
        else:
            self.check_box.raise_()

    def set_selected(self, selected):
        self._selected = selected
        self.check_box.setChecked(selected)
        self.update_border()

    def update_border(self):
        if self._selected and self._batch_mode:
            self.setStyleSheet("""
                GameCard {
                    background: #1a1a1a;
                    border-radius: 10px;
                    border: 2px solid #4a90d9;
                }
            """)
        else:
            self.setStyleSheet("""
                GameCard {
                    background: #1a1a1a;
                    border-radius: 10px;
                    border: 2px solid #333;
                }
                GameCard:hover {
                    border: 2px solid #555;
                }
            """)

    def load_cover(self):
        cover_path = self.game.get("cover")
        if cover_path and Path(cover_path).exists():
            pixmap = QPixmap(cover_path)
        else:
            # 先检查用户自定义的全局默认封面
            user_default = COVERS_DIR / "default_cover.png"
            if not user_default.exists():
                user_default = COVERS_DIR / "default_cover.jpg"
            if user_default.exists():
                pixmap = QPixmap(str(user_default))
            else:
                # 生成代码默认封面并保存
                default_path = COVERS_DIR / f"{self.game['id']}_default.png"
                if not default_path.exists():
                    default_path.parent.mkdir(parents=True, exist_ok=True)
                    pixmap = generate_cover_pixmap(self.game["name"], 200)
                    pixmap.save(str(default_path))
                    self.db.update(self.game["id"], cover=str(default_path))
                    self.game["cover"] = str(default_path)
                else:
                    pixmap = QPixmap(str(default_path))

        if not pixmap.isNull():
            pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.cover_label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if self._batch_mode:
            if event.button() == Qt.LeftButton:
                self.set_selected(not self._selected)
                if self.on_selected:
                    self.on_selected(self, self._selected)
            return
        if event.button() == Qt.LeftButton:
            self.launch_game()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())

    def launch_game(self):
        exe_path = self.game.get("exe_path")
        if exe_path and Path(exe_path).exists():
            work_dir = str(Path(exe_path).parent)
            subprocess.Popen([exe_path], cwd=work_dir, shell=False)
        else:
            QMessageBox.warning(self, "错误", "找不到游戏文件！")

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #2a2a2a; color: white; border: 1px solid #444; }
            QMenu::item:selected { background: #444; }
        """)

        menu.addAction("启动游戏", self.launch_game)
        menu.addAction("打开目录", self.open_dir)
        menu.addSeparator()
        menu.addAction("重命名", self.rename_game)
        menu.addAction("更换封面", self.change_cover)
        menu.addSeparator()
        menu.addAction("删除", self.delete_game)

        menu.exec(self.mapToGlobal(pos))

    def change_cover(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择封面图片", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            # 删除旧封面文件（避免占空间），但保留全局默认封面
            old_cover = self.game.get("cover")
            if old_cover:
                old_path = Path(old_cover)
                default_cover = COVERS_DIR / "default_cover.png"
                if old_path.exists() and old_path.resolve() != default_cover.resolve():
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass

            ext = Path(file_path).suffix
            cover_name = f"{self.game['id']}{ext}"
            cover_dest = COVERS_DIR / cover_name
            shutil.copy(file_path, str(cover_dest))
            self.db.update(self.game["id"], cover=str(cover_dest))
            self.game["cover"] = str(cover_dest)
            self.load_cover()

    def rename_game(self):
        new_name, ok = QInputDialog.getText(
            self, "重命名", "新名称:", text=self.game["name"]
        )
        if ok and new_name:
            self.db.update(self.game["id"], name=new_name)
            self.game["name"] = new_name
            self.name_label.setText(new_name)

    def open_dir(self):
        exe_path = self.game.get("exe_path")
        if exe_path:
            dir_path = str(Path(exe_path).parent)
            if Path(dir_path).exists():
                os.startfile(dir_path)

    def delete_game(self):
        reply = QMessageBox.question(
            self, "确认", f"确定要删除 [{self.game['name']}] 吗？\n(不会删除游戏文件，仅从列表移除)"
        )
        if reply == QMessageBox.Yes:
            # 删除该游戏的独立封面文件
            cover_path = self.game.get("cover")
            if cover_path:
                cp = Path(cover_path)
                default_cover = COVERS_DIR / "default_cover.png"
                if cp.exists() and cp.resolve() != default_cover.resolve():
                    try:
                        os.remove(cp)
                    except OSError:
                        pass
            self.db.remove(self.game["id"])
            if self.on_removed:
                self.on_removed(self)
            self.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = GameDB()
        self.cards = []
        self.batch_mode = False
        self.selected_cards = set()
        self.setup_ui()
        self.load_games()
        self.setWindowTitle("Game Launcher")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 顶部工具栏
        top_bar = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索游戏...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background: #151515;
                color: #eee;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
        """)
        self.search_edit.textChanged.connect(self.filter_games)
        top_bar.addWidget(self.search_edit, stretch=1)

        btn_style = """
            QPushButton {
                background: #1f1f1f;
                color: #eee;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover { background: #2a2a2a; border: 1px solid #666; }
        """

        scan_btn = QPushButton("扫描目录")
        scan_btn.setStyleSheet(btn_style)
        scan_btn.clicked.connect(self.scan_custom)
        top_bar.addWidget(scan_btn)

        add_btn = QPushButton("手动添加")
        add_btn.setStyleSheet(btn_style)
        add_btn.clicked.connect(self.manual_add)
        top_bar.addWidget(add_btn)

        # 批量管理按钮
        self.batch_btn = QPushButton("批量管理")
        self.batch_btn.setStyleSheet(btn_style)
        self.batch_btn.clicked.connect(self.toggle_batch_mode)
        top_bar.addWidget(self.batch_btn)

        main_layout.addLayout(top_bar)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #0a0a0a; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(self.grid_widget)
        main_layout.addWidget(scroll)

        # 批量操作栏
        self.batch_bar = QFrame()
        self.batch_bar.setStyleSheet("""
            QFrame {
                background: #151515;
                border-top: 2px solid #333;
                border-bottom: 2px solid #333;
            }
            QLabel { color: white; font-size: 14px; }
            QPushButton {
                background: #1f1f1f;
                color: #eee;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
            }
            QPushButton:hover { background: #2a2a2a; border: 1px solid #666; }
        """)
        batch_layout = QHBoxLayout(self.batch_bar)
        batch_layout.setContentsMargins(15, 8, 15, 8)
        batch_layout.setSpacing(10)

        self.batch_label = QLabel("已选择 0 项")
        self.batch_select_all_btn = QPushButton("全选")
        self.batch_delete_btn = QPushButton("批量删除")
        self.batch_cancel_btn = QPushButton("退出管理")

        self.batch_select_all_btn.clicked.connect(self.batch_select_all)
        self.batch_delete_btn.clicked.connect(self.batch_delete)
        self.batch_cancel_btn.clicked.connect(self.exit_batch_mode)

        batch_layout.addWidget(self.batch_label)
        batch_layout.addStretch()
        batch_layout.addWidget(self.batch_select_all_btn)
        batch_layout.addWidget(self.batch_delete_btn)
        batch_layout.addWidget(self.batch_cancel_btn)

        main_layout.addWidget(self.batch_bar)
        self.batch_bar.setVisible(False)

        # 状态栏
        self.status_label = QLabel("就绪1")
        self.status_label.setStyleSheet("color: #888; font-size: 12px; padding-left: 5px;")
        main_layout.addWidget(self.status_label)

        self.setStyleSheet("""
            QMainWindow { background: #0a0a0a; }
            QWidget { background: #0a0a0a; }
        """)

    def load_games(self):
        self.clear_cards()
        games = self.db.get_all()
        self.create_cards(games)
        self.status_label.setText(f"共 {len(games)} 个游戏")

    def clear_cards(self):
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        self.selected_cards.clear()
        self.update_batch_label()

    def create_cards(self, games):
        self.clear_cards()
        cols = max(1, (self.width() - 60) // 240)
        for i, game in enumerate(games):
            card = GameCard(
                game, self.db,
                on_removed=self.on_card_removed,
                on_selected=self.on_card_selected,
                parent=self.grid_widget
            )
            self.grid_layout.addWidget(card, i // cols, i % cols)
            self.cards.append(card)
            if self.batch_mode:
                card.set_batch_mode(True)

    def on_card_removed(self, card):
        if card in self.cards:
            self.cards.remove(card)
        if card in self.selected_cards:
            self.selected_cards.discard(card)
        self.update_batch_label()
        self.status_label.setText(f"共 {len(self.cards)} 个游戏")

    def filter_games(self, text):
        text = text.lower()
        all_games = self.db.get_all()
        filtered = [g for g in all_games if text in g["name"].lower()]
        self.create_cards(filtered)
        self.status_label.setText(f"显示 {len(filtered)} / {len(all_games)} 个游戏")

    def scan_custom(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择游戏目录")
        if dir_path:
            self._do_scan(dir_path)

    def _do_scan(self, path):
        self.status_label.setText("正在扫描...")
        QApplication.processEvents()

        found = scan_directory(path)
        added = 0
        for exe_path in found:
            exists = any(g["exe_path"] == exe_path for g in self.db.get_all())
            if not exists:
                name = Path(exe_path).stem
                self.db.add(name, exe_path)
                added += 1

        self.load_games()
        self.status_label.setText(f"扫描完成，新增 {added} 个游戏")

    def manual_add(self):
        exe_path, _ = QFileDialog.getOpenFileName(
            self, "选择游戏可执行文件", "", "Executables (*.exe)"
        )
        if exe_path:
            name = Path(exe_path).stem
            self.db.add(name, exe_path)
            self.load_games()
            self.status_label.setText(f"已添加: {name}")

    def toggle_batch_mode(self):
        self.batch_mode = not self.batch_mode
        self.batch_bar.setVisible(self.batch_mode)
        self.batch_btn.setText("退出管理" if self.batch_mode else "批量管理")
        self.selected_cards.clear()
        self.update_batch_label()
        for card in self.cards:
            card.set_batch_mode(self.batch_mode)

    def exit_batch_mode(self):
        self.batch_mode = False
        self.batch_bar.setVisible(False)
        self.batch_btn.setText("批量管理")
        self.selected_cards.clear()
        self.update_batch_label()
        for card in self.cards:
            card.set_batch_mode(False)

    def on_card_selected(self, card, selected):
        if selected:
            self.selected_cards.add(card)
        else:
            self.selected_cards.discard(card)
        self.update_batch_label()

    def update_batch_label(self):
        count = len(self.selected_cards)
        self.batch_label.setText(f"已选择 {count} 项")

    def batch_select_all(self):
        for card in self.cards:
            card.set_selected(True)
            self.selected_cards.add(card)
        self.update_batch_label()

    def batch_delete(self):
        if not self.selected_cards:
            QMessageBox.warning(self, "提示", "请先选择要删除的游戏")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(self.selected_cards)} 个游戏吗？\n(不会删除游戏文件，仅从列表移除)"
        )
        if reply == QMessageBox.Yes:
            to_delete = list(self.selected_cards)
            for card in to_delete:
                # 清理封面文件
                cover_path = card.game.get("cover")
                if cover_path:
                    cp = Path(cover_path)
                    default_cover = COVERS_DIR / "default_cover.png"
                    if cp.exists() and cp.resolve() != default_cover.resolve():
                        try:
                            os.remove(cp)
                        except OSError:
                            pass
                self.db.remove(card.game["id"])
                if card in self.cards:
                    self.cards.remove(card)
                if card.on_removed:
                    card.on_removed(card)
                card.deleteLater()
            self.selected_cards.clear()
            self.exit_batch_mode()
            self.status_label.setText(f"共 {len(self.cards)} 个游戏")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(200, self._relayout)

    def _relayout(self):
        if self.cards:
            games = [card.game for card in self.cards]
            self.create_cards(games)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # 全局对话框暗色样式，防止 QMessageBox / QInputDialog 等黑底黑字
    app.setStyleSheet("""
        QMessageBox {
            background-color: #1a1a1a;
        }
        QMessageBox QLabel {
            color: #eee;
            font-size: 14px;
        }
        QMessageBox QPushButton {
            background: #2a2a2a;
            color: #eee;
            border: 1px solid #555;
            border-radius: 5px;
            padding: 6px 16px;
            font-size: 13px;
            min-width: 60px;
        }
        QMessageBox QPushButton:hover {
            background: #3a3a3a;
            border: 1px solid #777;
        }
        QDialog {
            background-color: #1a1a1a;
        }
        QDialog QLabel {
            color: #eee;
        }
        QInputDialog {
            background-color: #1a1a1a;
        }
        QInputDialog QLabel {
            color: white;
            font-size: 14px;
        }
        QInputDialog QLineEdit {
            background: #2a2a2a;
            color: white;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px;
            font-size: 14px;
        }
        QInputDialog QPushButton {
            background: #2a2a2a;
            color: #eee;
            border: 1px solid #555;
            border-radius: 5px;
            padding: 6px 16px;
            font-size: 13px;
        }
        QInputDialog QPushButton:hover {
            background: #3a3a2a;
            border: 1px solid #777;
        }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
