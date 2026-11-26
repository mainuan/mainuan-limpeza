#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""MAINUAN LIMPEZA - tema, ícones desenhados em código e componentes visuais (Qt).
O visual (cores, barra lateral, cartões, botões) segue o MAINUAN OTIMIZADOR."""
import os
import html
from string import Template

from i18n import _

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Qt, Signal
except ImportError:  # alternativa: PyQt5
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtCore import Qt, pyqtSignal as Signal

# ---- Paletas derivadas do logo Mainuan (gradiente turquesa) ----
THEMES = {
    "dark": dict(BG="#0A1A1E", PANEL="#0F2329", CARD="#133038", BORDER="#1E4650", TEXT="#E8F8F9",
                 MUTED="#8DB8BD", ACCENT="#0CCFD9", ACCENT2="#06ADB7", DEEP="#018993",
                 WARN="#F5B83D", DANGER="#F0604D", OK="#2ED8A0", ONACC="#04262A"),
    "light": dict(BG="#EAF5F6", PANEL="#F7FCFC", CARD="#FFFFFF", BORDER="#C3DEE1", TEXT="#0B2A2E",
                  MUTED="#527C82", ACCENT="#0899A3", ACCENT2="#06ADB7", DEEP="#018993",
                  WARN="#B87400", DANGER="#CF3A2A", OK="#0E8F66", ONACC="#FFFFFF"),
}
T = dict(THEMES["dark"])
FONT = "sans-serif"


def set_theme(dark):
    T.clear()
    T.update(THEMES["dark" if dark else "light"])


def set_font(name):
    global FONT
    FONT = name


def build_qss():
    return Template("""
QWidget { background: $BG; color: $TEXT; font-family: "$FONT"; font-size: 10pt; }
QLabel { background: transparent; }
QLabel#h1 { font-size: 20pt; font-weight: bold; }
QLabel#h2 { font-size: 13pt; font-weight: bold; }
QLabel#muted { color: $MUTED; }
QLabel#kpi { font-size: 19pt; font-weight: bold; color: $ACCENT; }
QLabel#kpilock { font-size: 10pt; color: $MUTED; }
QLabel#cardtitle { font-size: 11pt; font-weight: bold; }
QFrame#sidebar { background: $PANEL; border-right: 1px solid $BORDER; }
QFrame#card { background: $CARD; border: 1px solid $BORDER; border-radius: 14px; }
QFrame#card QLabel { background: transparent; }
QFrame#sumcard { background: $CARD; border: 1px solid $BORDER; border-radius: 16px; }
QFrame#sumcard:hover { border: 1px solid $ACCENT2; background: $PANEL; }
QFrame#sumcard QLabel { background: transparent; }
QFrame#hero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 $ACCENT2, stop:1 $DEEP);
  border: none; border-radius: 18px; }
QFrame#hero QLabel { background: transparent; color: #FFFFFF; }
QFrame#hero QLabel#herosub { color: #D6F6F8; }
QFrame#banner { background: $CARD; border: 1px solid $WARN; border-radius: 12px; }
QFrame#banner QLabel { background: transparent; }
QFrame#statusbar { background: $PANEL; border-top: 1px solid $BORDER; }
QFrame#statusbar QLabel { background: transparent; }
QPushButton { background: $CARD; border: 1px solid $BORDER; border-radius: 8px; padding: 8px 16px; }
QPushButton:hover { border-color: $ACCENT2; }
QPushButton:disabled { color: $MUTED; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 $ACCENT2, stop:1 $DEEP);
  color: $ONACC; font-weight: bold; border: none; }
QPushButton#primary:hover { background: $ACCENT2; }
QPushButton#primary:disabled { background: $BORDER; color: $MUTED; }
QPushButton#herobtn { background: #FFFFFF; color: #016E77; font-weight: bold; border: none; border-radius: 10px; padding: 10px 20px; }
QPushButton#herobtn:hover { background: #E6FBFC; }
QPushButton#herobtn:disabled { background: #7FD3D9; color: #E6FBFC; }
QPushButton#heroghost { background: rgba(255,255,255,0.18); color: #FFFFFF; font-weight: bold; border: 1px solid rgba(255,255,255,0.55); border-radius: 10px; padding: 10px 20px; }
QPushButton#heroghost:hover { background: rgba(255,255,255,0.30); }
QPushButton#heroghost:disabled { color: #BFE9EC; border-color: rgba(255,255,255,0.25); }
QPushButton#danger { border-color: $DANGER; color: $DANGER; }
QPushButton#danger:disabled { border-color: $BORDER; color: $MUTED; }
QPushButton#nav { text-align: left; padding: 8px 14px; border: none; border-radius: 0; background: transparent; }
QPushButton#nav:hover { background: $CARD; }
QPushButton#nav:checked { background: $CARD; color: $ACCENT; border-left: 3px solid $ACCENT; }
QTableWidget { background: $PANEL; alternate-background-color: $BG; border: 1px solid $BORDER;
  border-radius: 8px; selection-background-color: $DEEP; selection-color: white; }
QHeaderView::section { background: $CARD; color: $MUTED; border: none; padding: 6px; font-weight: bold; }
QGroupBox { border: 1px solid $BORDER; border-radius: 10px; margin-top: 14px; padding: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: $ACCENT; }
QComboBox, QSpinBox, QLineEdit { background: $PANEL; border: 1px solid $BORDER; border-radius: 6px; padding: 5px 8px; min-height: 26px; }
QComboBox QAbstractItemView { background: $PANEL; color: $TEXT; selection-background-color: $DEEP;
  border: 1px solid $BORDER; }
QTextBrowser { background: $PANEL; border: 1px solid $BORDER; border-radius: 10px; padding: 6px; }
QScrollArea { border: none; }
QRadioButton, QCheckBox { spacing: 8px; background: transparent; }
QProgressBar { background: $BORDER; border: none; border-radius: 4px; min-height: 8px; max-height: 8px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $ACCENT, stop:1 $DEEP); border-radius: 4px; }
QToolTip { background: $CARD; color: $TEXT; border: 1px solid $ACCENT2; padding: 4px; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: $BORDER; border-radius: 6px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: $ACCENT2; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: $BORDER; border-radius: 6px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: $ACCENT2; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QPushButton#nav[collapsed="true"] { padding: 8px 0px; text-align: center; }
QMessageBox, QDialog { background: $BG; }
""").substitute(FONT=FONT, **T)


def pick_font():
    try:
        fams = set(QtGui.QFontDatabase.families())
    except TypeError:
        fams = set(QtGui.QFontDatabase().families())
    for f in ("Inter", "Noto Sans", "Ubuntu", "Open Sans", "Cantarell", "Segoe UI", "DejaVu Sans"):
        if f in fams:
            return f
    return "sans-serif"


def qt_is_dark():
    try:
        cs = QtGui.QGuiApplication.styleHints().colorScheme()
        if cs == Qt.ColorScheme.Dark:
            return True
        if cs == Qt.ColorScheme.Light:
            return False
    except (AttributeError, TypeError):
        pass
    return QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Window).lightness() < 128


LOGO_PATHS = ["/usr/share/icons/hicolor/256x256/apps/mainuan-limpeza.png",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")]


def logo_pixmap(size):
    for p in LOGO_PATHS:
        if os.path.exists(p):
            pm = QtGui.QPixmap(p)
            return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return QtGui.QPixmap()


# ------------------------------------------------------------------ ícones
def draw_pixmap(kind, color, size=22):
    """Ícone desenhado em código (canvas 44x44, escalado)."""
    px = size * 2
    pm = QtGui.QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    p.scale(px / 44.0, px / 44.0)
    pen = QtGui.QPen(QtGui.QColor(color), 3.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    P, R, PF = QtCore.QPointF, QtCore.QRectF, QtGui.QPolygonF
    s, c = 44.0, 22.0

    def poly(pts, close=False):
        pg = PF([P(x, y) for x, y in pts])
        p.drawPolygon(pg) if close else p.drawPolyline(pg)

    if kind == "gauge":
        p.drawArc(R(5, 5, s - 10, s - 10), 225 * 16, -270 * 16)
        p.drawLine(P(c, c), P(s * 0.70, s * 0.34))
    elif kind == "ram":
        p.drawRoundedRect(R(4, 9, s - 8, s - 22), 3, 3)
        for x in (9, 18, 27):
            p.drawRect(R(x, 15, 8, 8))
        for x in range(10, 36, 7):
            p.drawLine(P(x, s - 13), P(x, s - 7))
    elif kind == "cpu":
        p.drawRoundedRect(R(11, 11, s - 22, s - 22), 4, 4)
        p.drawRect(R(17, 17, s - 34, s - 34))
        for v in (17, 22, 27):
            p.drawLine(P(v, 4), P(v, 11)); p.drawLine(P(v, s - 11), P(v, s - 4))
            p.drawLine(P(4, v), P(11, v)); p.drawLine(P(s - 11, v), P(s - 4, v))
    elif kind == "globe":
        p.drawEllipse(R(5, 5, s - 10, s - 10))
        p.drawEllipse(R(c - 8, 5, 16, s - 10))
        p.drawLine(P(5, c), P(s - 5, c))
        p.drawArc(R(9, 11, s - 18, 14), 0, 180 * 16)
        p.drawArc(R(9, 19, s - 18, 14), 0, -180 * 16)
    elif kind == "menu":
        for y in (12, 22, 32):
            p.drawLine(P(8, y), P(s - 8, y))
    elif kind == "check":
        p.drawEllipse(R(5, 5, s - 10, s - 10))
        p.drawPolyline(PF([P(13, 23), P(20, 30), P(32, 15)]))
    elif kind == "bolt":
        poly([(c + 4, 4), (12, c + 3), (c, c + 3), (c - 4, s - 4), (s - 12, c - 3), (c, c - 3), (c + 4, 4)])
    elif kind == "power":
        p.drawArc(R(8, 9, s - 16, s - 16), 120 * 16, 300 * 16)
        p.drawLine(P(c, 5), P(c, c))
    elif kind == "list":
        for y in (11, 22, 33):
            p.drawPoint(P(10, y)); p.drawLine(P(18, y), P(s - 8, y))
    elif kind == "dash":  # Resumo
        p.drawRoundedRect(R(6, 6, 14, 18), 3, 3)
        p.drawRoundedRect(R(24, 6, 14, 10), 3, 3)
        p.drawRoundedRect(R(24, 20, 14, 18), 3, 3)
        p.drawRoundedRect(R(6, 28, 14, 10), 3, 3)
    elif kind == "apps":
        for x in (7, 19, 31):
            for y in (7, 19, 31):
                p.drawRoundedRect(R(x, y, 6, 6), 2, 2)
    elif kind == "package":
        poly([(22, 4), (38, 12), (38, 32), (22, 40), (6, 32), (6, 12)], True)
        poly([(6, 12), (22, 21), (38, 12)])
        p.drawLine(P(22, 21), P(22, 40))
    elif kind == "folder":
        p.drawRoundedRect(R(5, 13, 34, 24), 4, 4)
        poly([(5, 13), (5, 10), (17, 10), (21, 14)])
    elif kind == "trash":
        p.drawLine(P(8, 13), P(36, 13))
        poly([(17, 13), (17, 8), (27, 8), (27, 13)])
        poly([(11, 13), (13, 37), (31, 37), (33, 13)])
        p.drawLine(P(19, 19), P(19, 31)); p.drawLine(P(25, 19), P(25, 31))
    elif kind == "monitor":
        p.drawRoundedRect(R(4, 7, 36, 24), 3, 3)
        p.drawLine(P(c, 31), P(c, 38)); p.drawLine(P(14, 38), P(30, 38))
    elif kind == "disk":
        p.drawRoundedRect(R(5, 12, 34, 20), 4, 4)
        p.drawLine(P(5, 24), P(39, 24))
        p.drawPoint(P(32, 28)); p.drawPoint(P(26, 28))
    elif kind == "layers":
        poly([(22, 6), (39, 15), (22, 24), (5, 15)], True)
        poly([(5, 22), (22, 31), (39, 22)])
        poly([(5, 29), (22, 38), (39, 29)])
    elif kind == "pkgdown":
        poly([(6, 22), (6, 38), (38, 38), (38, 22)])
        p.drawLine(P(c, 5), P(c, 26))
        poly([(14, 18), (c, 27), (30, 18)])
    elif kind == "clock":
        p.drawEllipse(R(5, 5, s - 10, s - 10))
        poly([(22, 12), (22, 22), (30, 27)])
    elif kind == "doc":
        poly([(10, 4), (26, 4), (34, 12), (34, 40), (10, 40), (10, 4)])
        poly([(26, 4), (26, 12), (34, 12)])
        p.drawLine(P(16, 22), P(28, 22)); p.drawLine(P(16, 29), P(28, 29)); p.drawLine(P(16, 35), P(23, 35))
    elif kind == "sparkle":
        poly([(22, 3), (26.5, 17.5), (41, 22), (26.5, 26.5), (22, 41), (17.5, 26.5), (3, 22), (17.5, 17.5)], True)
    elif kind == "broom":
        p.drawLine(P(35, 7), P(21, 22))
        poly([(15, 20), (27, 26), (24, 31), (12, 25)], True)
        poly([(12, 25), (24, 31), (29, 41), (7, 38)], True)
        p.drawLine(P(14, 31), P(13, 37)); p.drawLine(P(19, 33), P(19, 39))
    elif kind == "lock":
        p.drawRoundedRect(R(9, 20, 26, 19), 4, 4)
        p.drawArc(R(14, 5, 16, 20), 0, 180 * 16)
        p.drawLine(P(14, 15), P(14, 21)); p.drawLine(P(30, 15), P(30, 21))
        p.drawPoint(P(c, 29))
    else:  # info
        p.drawEllipse(R(6, 6, s - 12, s - 12))
        p.drawPoint(P(c, 15)); p.drawLine(P(c, 21), P(c, 31))
    p.end()
    return pm


def make_icon(kind):
    """Ícone de navegação: cor normal e cor de destaque quando selecionado."""
    ic = QtGui.QIcon()
    ic.addPixmap(draw_pixmap(kind, T["TEXT"]), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    ic.addPixmap(draw_pixmap(kind, T["ACCENT"]), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
    return ic


def badge_pixmap(kind, size=48, glass=False):
    """Ícone dentro de um círculo com o gradiente turquesa do logótipo Mainuan."""
    px = size * 2
    pm = QtGui.QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    if glass:
        p.setBrush(QtGui.QColor(255, 255, 255, 46))
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 140), 2))
        p.drawEllipse(QtCore.QRectF(2, 2, px - 4, px - 4))
    else:
        g = QtGui.QLinearGradient(0, 0, 0, px)
        g.setColorAt(0.0, QtGui.QColor(T["ACCENT"]))
        g.setColorAt(0.5, QtGui.QColor(T["ACCENT2"]))
        g.setColorAt(1.0, QtGui.QColor(T["DEEP"]))
        p.setBrush(QtGui.QBrush(g))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QtCore.QRectF(0, 0, px, px))
    inner = int(size * 0.56)
    glyph = draw_pixmap(kind, "#FFFFFF", inner)
    off = (px - glyph.width()) // 2
    p.drawPixmap(off, off, glyph)
    p.end()
    pm.setDevicePixelRatio(2.0)
    return pm


# ------------------------------------------------------------------ widgets
def label(text, name=None, wrap=False):
    l = QtWidgets.QLabel(text)
    if name:
        l.setObjectName(name)
    l.setWordWrap(wrap)
    return l


def card():
    f = QtWidgets.QFrame()
    f.setObjectName("card")
    return f


def button(text, name=None, icon=None):
    b = QtWidgets.QPushButton(text)
    if name:
        b.setObjectName(name)
    if icon:
        b.setIcon(QtGui.QIcon(draw_pixmap(icon, "#FFFFFF" if name in ("primary",) else T["TEXT"], 18)))
        b.setIconSize(QtCore.QSize(18, 18))
    return b


def ask(parent, title, text, detail=None):
    mb = QtWidgets.QMessageBox(parent)
    mb.setWindowTitle(title)
    mb.setText(text)
    if detail:
        mb.setInformativeText(detail)
    yes = mb.addButton(_("Sim"), QtWidgets.QMessageBox.ButtonRole.YesRole)
    mb.addButton(_("Não"), QtWidgets.QMessageBox.ButtonRole.NoRole)
    mb.exec()
    return mb.clickedButton() == yes


def fit_dialog(dlg, w, h):
    a = QtWidgets.QApplication.primaryScreen().availableGeometry()
    dlg.resize(max(360, min(w, a.width() - 60)), max(300, min(h, a.height() - 110)))


def notify(parent, title, message, ok=True):
    """Janela de resultado com botão Fechar (igual à do Otimizador)."""
    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle(title)
    fit_dialog(dlg, 540, 340)
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(30, 26, 30, 22)
    lay.setSpacing(12)
    ic = QtWidgets.QLabel()
    ic.setPixmap(draw_pixmap("check" if ok else "info", T["OK"] if ok else T["WARN"], 56))
    ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(ic)
    h = label(title.upper(), "h2")
    h.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(h)
    m = label(message, None, True)
    m.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(m)
    lay.addStretch(1)
    b = QtWidgets.QPushButton(_("Fechar"))
    b.setObjectName("primary")
    b.setMinimumWidth(170)
    b.clicked.connect(dlg.accept)
    lay.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
    dlg.exec()


def scroll_wrap(page, min_h=0, min_w=640):
    """Coloca uma página dentro de uma área com barra de deslocamento."""
    page.setMinimumSize(min_w, min_h)
    sa = QtWidgets.QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    sa.setWidget(page)
    return sa


def esc(s):
    return html.escape(str(s))


class Task(QtCore.QThread):
    done = Signal(object, object)

    def __init__(self, fn, args, cb, parent=None):
        super().__init__(parent)
        self.fn, self.args, self.cb = fn, args, cb

    def run(self):
        try:
            res = self.fn(*self.args)
        except Exception as ex:  # noqa: BLE001
            res = {"success": False, "error": str(ex), "error_exc": True}
        self.done.emit(self, res)


class CheckTable(QtWidgets.QTableWidget):
    """Tabela com caixas de seleção. Cada linha: dict(key, cells=[...], enabled, tooltip, checks).
    Colunas de texto a partir da 1; a coluna 0 é a caixa principal (omitida se checkable=False)."""
    selection_changed = Signal()

    def __init__(self, headers, checkable=True, stretch_col=1, extra_check_cols=()):
        super().__init__(0, len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(34)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.checkable = checkable
        self.extra = tuple(extra_check_cols)
        hh = self.horizontalHeader()
        hh.setStretchLastSection(False)
        RM = QtWidgets.QHeaderView.ResizeMode
        for i in range(len(headers)):
            hh.setSectionResizeMode(i, RM.Stretch if i == stretch_col else RM.ResizeToContents)
        self._filling = False
        self.itemChanged.connect(self._changed)

    def _changed(self, _it):
        if not self._filling:
            self.selection_changed.emit()

    def fill(self, rows):
        """rows: dict(key, cells=[texto,...], checked=bool (coluna 0), checks={coluna: bool|None},
        enabled=bool, off_cols={colunas sem caixa ativa}, right={colunas alinhadas à direita}, tooltip)."""
        self._filling = True
        self.setRowCount(len(rows))
        box_cols = ({0} if self.checkable else set()) | set(self.extra)
        for r, row in enumerate(rows):
            enabled = row.get("enabled", True)
            for c, text in enumerate(row["cells"]):
                it = QtWidgets.QTableWidgetItem(str(text))
                flags = Qt.ItemFlag.ItemIsEnabled
                if c in box_cols:
                    chk = row.get("checked", False) if c == 0 else row.get("checks", {}).get(c)
                    if chk is None:  # sem caixa nesta célula (ex.: pacote inexistente)
                        it.setText("—")
                        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    else:
                        if enabled and c not in row.get("off_cols", ()):
                            flags |= Qt.ItemFlag.ItemIsUserCheckable
                        it.setCheckState(Qt.CheckState.Checked if chk else Qt.CheckState.Unchecked)
                elif c in row.get("right", ()):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 0 and row.get("key") is not None:
                    it.setData(Qt.ItemDataRole.UserRole, row["key"])
                if not enabled:
                    it.setForeground(QtGui.QBrush(QtGui.QColor(T["MUTED"])))
                if row.get("tooltip"):
                    it.setToolTip(row["tooltip"])
                it.setFlags(flags)
                self.setItem(r, c, it)
        self._filling = False
        self.selection_changed.emit()

    def checked_rows(self, col=0):
        out = []
        for r in range(self.rowCount()):
            it = self.item(r, col)
            if it is not None and it.checkState() == Qt.CheckState.Checked \
                    and bool(it.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                out.append(r)
        return out

    def selected_keys(self, col=0):
        keys = []
        for r in self.checked_rows(col):
            k = self.item(r, 0).data(Qt.ItemDataRole.UserRole)
            if k is not None:
                keys.append(k)
        return keys

    def set_all(self, on, col=0):
        self._filling = True
        for r in range(self.rowCount()):
            it = self.item(r, col)
            if it is not None and bool(it.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
        self._filling = False
        self.selection_changed.emit()

    def filter_text(self, text):
        t = text.strip().lower()
        for r in range(self.rowCount()):
            show = not t or any(
                self.item(r, c) is not None and t in self.item(r, c).text().lower()
                for c in range(self.columnCount()))
            self.setRowHidden(r, not show)
