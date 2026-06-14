import sys
import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QLabel, QPushButton, QFileDialog,
    QMenu, QMessageBox, QLineEdit, QInputDialog, QFrame
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage, QIcon, QAction, QColor, QPainter, QFont

from database import GameDB
from scanner import scan_directory

BASE_DIR = Path(__file__).parent.parent
COVERS_DIR = BASE_DIR / "covers"


def get_default_pixmap(size=200):
    """生成一个带游戏手柄图标的默认封面占位图。"""
    img = QImage(size, size, QImage.Format_RGB888)
    img.fill(QColor(30, 30, 30))
    pixmap = QPixmap.fromImage(img)
    return pixmap


class GameCard(QFrame):
    def __init__(self, game, db, on_removed=None, parent=None):
        super().__init__(parent)
        self.game = game
        self.db = db
        self.on_removed = on_removed
        self.setFixedSize(220, 280)
        self.setup_ui()
        self.load_cover()

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

    def load_cover(self):
        cover_path = self.game.get("cover")
        if cover_path and Path(cover_path).exists():
            pixmap = QPixmap(cover_path)
        else:
            pixmap = get_default_pixmap(200)

        if not pixmap.isNull():
            pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.cover_label.setPixmap(pixmap)

    def mousePressEvent(self, event):
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
            self.db.remove(self.game["id"])
            if self.on_removed:
                self.on_removed(self)
            self.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = GameDB()
        self.cards = []
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

        # 状态栏
        self.status_label = QLabel("就绪")
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

    def create_cards(self, games):
        self.clear_cards()
        cols = max(1, (self.width() - 60) // 240)
        for i, game in enumerate(games):
            card = GameCard(game, self.db, on_removed=self.on_card_removed, parent=self.grid_widget)
            self.grid_layout.addWidget(card, i // cols, i % cols)
            self.cards.append(card)

    def on_card_removed(self, card):
        if card in self.cards:
            self.cards.remove(card)
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
