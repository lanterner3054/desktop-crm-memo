"""桌面备忘录 - 无边框、贴边、置顶的 Qt 容器，内嵌 HTML UI。"""
import os
import sys
import json
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QSize, QUrl, QStandardPaths, Signal, QObject, Slot
from PySide6.QtGui import QGuiApplication, QIcon, QColor, QPainter, QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizeGrip, QFrame,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings, QWebEnginePage


APP_NAME = "桌面备忘录"
DEFAULT_W = 360
MIN_W, MIN_H = 280, 360


def app_data_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not base:
        base = str(Path.home() / ".desktop-memo")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)


class MemoPage(QWebEnginePage):
    """Custom page that captures JS console messages as a save channel.
    JS calls console.log('@@MEMO_SAVE@@' + json) and we persist to disk.
    This sidesteps QWebChannel/qrc loading issues on file:// origins.
    """
    SAVE_TAG = "@@MEMO_SAVE@@"
    LOG_TAG = "@@MEMO_LOG@@"
    BACKUP_KEEP = 5

    def __init__(self, profile, parent, data_file: Path):
        super().__init__(profile, parent)
        self.data_file = data_file
        self.log_file = data_file.parent / "activity.jsonl"

    def javaScriptConsoleMessage(self, level, message, line, source):
        if isinstance(message, str) and message.startswith(self.SAVE_TAG):
            payload = message[len(self.SAVE_TAG):]
            self._save_memos(payload)
            return
        if isinstance(message, str) and message.startswith(self.LOG_TAG):
            payload = message[len(self.LOG_TAG):]
            self._append_log(payload)
            return
        super().javaScriptConsoleMessage(level, message, line, source)

    def _save_memos(self, payload: str):
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            self._rotate_backups()
            tmp = self.data_file.with_suffix(".json.tmp")
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(self.data_file)
        except Exception as e:
            print(f"[memo] save failed: {e}", file=sys.stderr)

    def _rotate_backups(self):
        """Keep the last N copies of memos.json: memos.bak.1..N.json (1 = newest).
        Called before each overwrite; copies (never moves) the current file so the
        live data file is never left missing."""
        if not self.data_file.exists():
            return
        try:
            import shutil
            d, stem = self.data_file.parent, self.data_file.stem
            for i in range(self.BACKUP_KEEP, 1, -1):
                newer = d / f"{stem}.bak.{i-1}.json"
                if newer.exists():
                    newer.replace(d / f"{stem}.bak.{i}.json")
            shutil.copy(self.data_file, d / f"{stem}.bak.1.json")
        except Exception as e:
            print(f"[memo] backup rotate failed: {e}", file=sys.stderr)

    def _append_log(self, line: str):
        """Append-only activity log. Never rewrites existing lines."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8", newline="") as f:
                f.write(line.rstrip("\n") + "\n")
        except Exception as e:
            print(f"[memo] log append failed: {e}", file=sys.stderr)

    def load_initial_data(self) -> str:
        try:
            if self.data_file.exists():
                # utf-8-sig tolerates a BOM if the file was edited externally.
                return self.data_file.read_text(encoding="utf-8-sig")
        except Exception as e:
            print(f"[memo] load failed: {e}", file=sys.stderr)
        return ""

    def load_log_data(self) -> str:
        try:
            if self.log_file.exists():
                return self.log_file.read_text(encoding="utf-8-sig")
        except Exception as e:
            print(f"[memo] log load failed: {e}", file=sys.stderr)
        return ""


class TitleBar(QFrame):
    snap_left = Signal()
    snap_right = Signal()
    snap_free = Signal()
    toggle_top = Signal()
    minimize = Signal()
    close_req = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titlebar")
        self.setFixedHeight(34)
        self._drag_pos = None

        title = QLabel("📝  桌面备忘录")
        title.setObjectName("title")

        def mk(text, tip, slot):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setFixedSize(QSize(26, 22))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            b.setFocusPolicy(Qt.NoFocus)
            return b

        self.btn_left  = mk("⇤", "贴左边", self.snap_left.emit)
        self.btn_free  = mk("◳", "自由窗口", self.snap_free.emit)
        self.btn_right = mk("⇥", "贴右边", self.snap_right.emit)
        self.btn_top   = mk("📌", "切换置顶", self.toggle_top.emit)
        self.btn_min   = mk("—", "最小化", self.minimize.emit)
        self.btn_close = mk("×", "关闭", self.close_req.emit)
        self.btn_close.setObjectName("closebtn")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 6, 0)
        lay.setSpacing(2)
        lay.addWidget(title)
        lay.addStretch(1)
        for b in (self.btn_left, self.btn_free, self.btn_right, self.btn_top, self.btn_min, self.btn_close):
            lay.addWidget(b)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            w = self.window()
            if hasattr(w, "on_drag_move"):
                w.on_drag_move(e.globalPosition().toPoint() - self._drag_pos)
            else:
                w.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        w = self.window()
        if hasattr(w, "on_drag_release"):
            w.on_drag_release()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon())
        self.setMinimumSize(MIN_W, MIN_H)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.Window
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.always_on_top = True
        self.snap_mode = "right"  # left | right | free

        self.titlebar = TitleBar(self)
        self.titlebar.snap_left.connect(lambda: self.apply_snap("left"))
        self.titlebar.snap_right.connect(lambda: self.apply_snap("right"))
        self.titlebar.snap_free.connect(lambda: self.apply_snap("free"))
        self.titlebar.toggle_top.connect(self.toggle_on_top)
        self.titlebar.minimize.connect(self.showMinimized)
        self.titlebar.close_req.connect(self.close)

        # Named (persistent) profile — defaultProfile() is off-the-record in Qt6
        # and would silently lose localStorage on exit.
        self.profile = QWebEngineProfile("DesktopMemo", QApplication.instance())
        self.profile.setPersistentStoragePath(str(app_data_dir() / "web"))
        self.profile.setCachePath(str(app_data_dir() / "cache"))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)

        self.view = QWebEngineView(self)
        self.data_file = app_data_dir() / "memos.json"
        self.page = MemoPage(self.profile, self.view, self.data_file)
        self.view.setPage(self.page)
        s = self.view.settings()
        s.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

        # Inject the file's prior content (if any) into the page before its
        # scripts run, so the UI can pick it up on startup. Encode as JSON so
        # special characters / newlines can't break out of the JS string.
        existed = self.data_file.exists()
        raw = self.page.load_initial_data()
        log_raw = self.page.load_log_data()
        boot_js = (
            "window.__MEMO_INITIAL__ = " + json.dumps(raw) + ";"
            "window.__MEMO_FILE_EXISTED__ = " + ("true" if existed else "false") + ";"
            "window.__MEMO_LOG_INITIAL__ = " + json.dumps(log_raw) + ";"
        )
        from PySide6.QtWebEngineCore import QWebEngineScript
        script = QWebEngineScript()
        script.setName("memo-initial")
        script.setSourceCode(boot_js)
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(False)
        self.page.scripts().insert(script)

        index_path = resource_path("index.html")
        self.view.load(QUrl.fromLocalFile(index_path))

        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(14, 14)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.titlebar)
        root.addWidget(self.view, 1)

        self.setStyleSheet("""
            QWidget { background: #f5f5f7; color: #1d1d1f;
                      font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            #titlebar { background: #ececef; border-bottom: 1px solid #e5e5ea; }
            #title { font-size: 12px; color: #1d1d1f; }
            QPushButton { background: transparent; border: none; color: #1d1d1f;
                          border-radius: 5px; font-size: 13px; }
            QPushButton:hover { background: rgba(0,0,0,.06); }
            #closebtn:hover { background: #ff453a; color: white; }
        """)

        self.load_window_state()
        self.apply_on_top()
        self.apply_snap(self.snap_mode, persist=False)

    def state_file(self) -> Path:
        return app_data_dir() / "window.json"

    def load_window_state(self):
        try:
            data = json.loads(self.state_file().read_text(encoding="utf-8"))
            self.snap_mode = data.get("snap", "right")
            self.always_on_top = bool(data.get("on_top", True))
            w = int(data.get("w", DEFAULT_W))
            h = int(data.get("h", 0)) or self.default_height()
            self.resize(w, h)
            if self.snap_mode == "free":
                x = int(data.get("x", 100))
                y = int(data.get("y", 100))
                self.move(x, y)
        except Exception:
            self.resize(DEFAULT_W, self.default_height())

    def save_window_state(self):
        try:
            data = {
                "snap": self.snap_mode,
                "on_top": self.always_on_top,
                "w": self.width(),
                "h": self.height(),
                "x": self.x(),
                "y": self.y(),
            }
            self.state_file().write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def default_height(self):
        scr = QGuiApplication.primaryScreen().availableGeometry()
        return scr.height()

    def screen_geom(self):
        scr = self.screen() or QGuiApplication.primaryScreen()
        return scr.availableGeometry()

    def apply_on_top(self):
        flags = self.windowFlags()
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def toggle_on_top(self):
        self.always_on_top = not self.always_on_top
        self.apply_on_top()
        self.save_window_state()

    def apply_snap(self, mode, persist=True):
        self.snap_mode = mode
        g = self.screen_geom()
        if mode == "left":
            self.setGeometry(g.x(), g.y(), max(self.width(), MIN_W), g.height())
        elif mode == "right":
            w = max(self.width(), MIN_W)
            self.setGeometry(g.x() + g.width() - w, g.y(), w, g.height())
        # free: keep current geometry
        if persist:
            self.save_window_state()

    def on_drag_move(self, new_top_left: QPoint):
        # When dragging from a snapped state, release into free first
        if self.snap_mode != "free":
            self.snap_mode = "free"
        self.move(new_top_left)

    def on_drag_release(self):
        g = self.screen_geom()
        x = self.x()
        # Snap thresholds
        if x <= g.x() + 18:
            self.apply_snap("left")
        elif x + self.width() >= g.x() + g.width() - 18:
            self.apply_snap("right")
        else:
            self.save_window_state()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "grip"):
            self.grip.move(self.width() - self.grip.width() - 2, self.height() - self.grip.height() - 2)

    def closeEvent(self, e):
        self.save_window_state()
        super().closeEvent(e)


def main():
    QApplication.setApplicationName(APP_NAME)
    QApplication.setOrganizationName("DesktopMemo")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
