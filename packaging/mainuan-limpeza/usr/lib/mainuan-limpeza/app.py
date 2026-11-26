#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""MAINUAN LIMPEZA - interface gráfica (Qt). Visual e disposição dos menus como o MAINUAN OTIMIZADOR."""
import os
import sys
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n  # noqa: E402

i18n.set_lang(i18n.detect_lang())  # idioma do sistema, detetado automaticamente
from i18n import _  # noqa: E402

import core  # noqa: E402

if "--version" in sys.argv:
    print("%s %s" % (core.APP_NAME, core.VERSION))
    sys.exit(0)

try:
    import ui_common as U  # noqa: E402
except ImportError:
    sys.stderr.write("MAINUAN LIMPEZA: é necessário o PySide6 (python3-pyside6.qtwidgets) ou o PyQt5.\n")
    sys.exit(1)
from ui_common import QtCore, QtGui, QtWidgets, Qt, T, Signal, label, make_icon, logo_pixmap, notify  # noqa: E402
import pages as P  # noqa: E402


class MainWindow(QtWidgets.QMainWindow):
    sig_progress = Signal(str, float)

    def __init__(self, dark):
        super().__init__()
        self.setWindowTitle(core.APP_NAME)
        self.dark = dark
        self.monitor = core.Monitor()
        self.root = core.RootSession()
        self.root_ok = False
        self.scanning_user = False
        self.scanning_root = False
        self.data = {}
        self.tasks = set()
        self.tick_n = 0

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # ---- barra lateral recolhível (igual à do Otimizador)
        self.collapsed = False
        self.side = QtWidgets.QFrame()
        self.side.setObjectName("sidebar")
        sl = QtWidgets.QVBoxLayout(self.side)
        sl.setContentsMargins(0, 10, 0, 12)
        sl.setSpacing(2)
        self.b_toggle = QtWidgets.QPushButton()
        self.b_toggle.setObjectName("nav")
        self.b_toggle.setIconSize(QtCore.QSize(22, 22))
        self.b_toggle.clicked.connect(lambda _c=False: self.set_sidebar(not self.collapsed))
        sl.addWidget(self.b_toggle)
        head = QtWidgets.QHBoxLayout()
        head.setContentsMargins(12, 8, 8, 12)
        lg = QtWidgets.QLabel()
        lg.setPixmap(logo_pixmap(40))
        head.addWidget(lg)
        self.brand = label("", None)
        head.addWidget(self.brand)
        head.addStretch(1)
        sl.addLayout(head)

        self.stack = QtWidgets.QStackedWidget()
        self.p_sum = P.SummaryPage(self)
        self.p_apps = P.AppsPage(self)
        self.p_flat = P.FlatpakPage(self)
        self.p_ucache = P.UserCachePage(self)
        self.p_trash = P.TrashPage(self)
        self.p_drv = P.DriversPage(self)
        self.p_fw = P.FirmwarePage(self)
        self.p_kern = P.KernelsPage(self)
        self.p_lang = P.LanguagesPage(self)
        self.p_apt = P.AptPage(self)
        self.p_temp = P.TempPage(self)
        self.p_logs = P.LogsPage(self)
        self.p_about = P.AboutPage()
        entries = [(_("Resumo"), "dash", self.p_sum), (_("Aplicações"), "apps", self.p_apps),
                   (_("Flatpak"), "package", self.p_flat), (_("Cache do utilizador"), "folder", self.p_ucache),
                   (_("Lixo"), "trash", self.p_trash), (_("Drivers"), "monitor", self.p_drv),
                   (_("Firmwares"), "disk", self.p_fw), (_("Kernels"), "layers", self.p_kern),
                   (_("Idiomas"), "globe", self.p_lang), (_("Cache APT"), "pkgdown", self.p_apt),
                   (_("Temporários"), "clock", self.p_temp), (_("Registos"), "doc", self.p_logs),
                   (_("Acerca"), "info", self.p_about)]
        self.pages = [e[2] for e in entries]

        navbox = QtWidgets.QWidget()
        navbox.setObjectName("navbox")
        nl = QtWidgets.QVBoxLayout(navbox)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(2)
        self.nav = []
        for i, (txt, ic, page) in enumerate(entries):
            b = QtWidgets.QPushButton("  " + txt)
            b.setObjectName("nav")
            b.kind, b.text_label = ic, txt
            b.setIconSize(QtCore.QSize(22, 22))
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.clicked.connect(lambda _c=False, n=i: self.goto(n))
            nl.addWidget(b)
            self.nav.append(b)
            self.stack.addWidget(U.scroll_wrap(page, 0))
        nl.addStretch(1)
        self.nav_scroll = QtWidgets.QScrollArea()
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }"
                                      " QScrollArea > QWidget > QWidget { background: transparent; }")
        self.nav_scroll.setWidget(navbox)
        sl.addWidget(self.nav_scroll, 1)
        self.ver = label(f"v{core.VERSION}", "muted")
        sl.addWidget(self.ver, 0, Qt.AlignmentFlag.AlignHCenter)
        h.addWidget(self.side)

        # ---- área de conteúdo + barra de estado/progresso
        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self.stack, 1)
        self.status = QtWidgets.QFrame()
        self.status.setObjectName("statusbar")
        stl = QtWidgets.QHBoxLayout(self.status)
        stl.setContentsMargins(20, 8, 20, 8)
        stl.setSpacing(14)
        self.st_label = label("", "muted")
        stl.addWidget(self.st_label, 1)
        self.st_bar = QtWidgets.QProgressBar()
        self.st_bar.setRange(0, 100)
        self.st_bar.setTextVisible(False)
        self.st_bar.setFixedWidth(240)
        stl.addWidget(self.st_bar)
        self.status.hide()
        right.addWidget(self.status)
        h.addLayout(right, 1)

        self.pulse = QtCore.QTimer(self)
        self.pulse.timeout.connect(self._pulse)
        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.status.hide)
        self.sig_progress.connect(self._on_progress)

        self.set_sidebar(False)
        self.restyle()
        for p in self.pages:
            if hasattr(p, "set_root_state"):
                p.set_root_state(False)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.goto(0)
        self.tick()
        self.initial_size()
        QtCore.QTimer.singleShot(250, self.start_user_scan)

    # ---- barra lateral recolhível
    def set_sidebar(self, collapsed):
        self.collapsed = collapsed
        self.side.setFixedWidth(64 if collapsed else 232)
        self.brand.setVisible(not collapsed)
        self.ver.setVisible(not collapsed)
        for b in self.nav + [self.b_toggle]:
            b.setProperty("collapsed", collapsed)
            b.style().unpolish(b)
            b.style().polish(b)
        for b in self.nav:
            b.setText("" if collapsed else "  " + b.text_label)
            b.setToolTip(b.text_label)
        self.b_toggle.setIcon(make_icon("menu"))
        self.b_toggle.setText("" if collapsed else "  " + _("Recolher menu"))
        self.b_toggle.setToolTip(_("Expandir menu") if collapsed else _("Recolher menu"))

    # ---- tamanho e posição dentro da área útil do ecrã
    def _avail(self):
        scr = self.screen() or QtWidgets.QApplication.primaryScreen()
        return scr.availableGeometry()

    @staticmethod
    def _margins():
        wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
        return 60, (140 if wayland else 100)

    def initial_size(self):
        a = self._avail()
        mw, mh = self._margins()
        self.setMinimumSize(min(760, a.width() - mw), min(480, a.height() - mh))
        self.resize(min(1240, a.width() - mw), min(820, a.height() - mh))
        self.move(a.left() + (a.width() - self.width()) // 2, a.top() + (a.height() - self.height()) // 2)

    def fit_to_screen(self):
        a = self._avail()
        fg = self.frameGeometry()
        extra_w, extra_h = fg.width() - self.width(), fg.height() - self.height()
        w = min(self.width(), a.width() - 20 - extra_w)
        h = min(self.height(), a.height() - 20 - extra_h)
        if (w, h) != (self.width(), self.height()):
            self.resize(w, h)
            fg = self.frameGeometry()
        x = max(a.left() + 10, min(fg.x(), a.right() - fg.width() - 9))
        y = max(a.top() + 10, min(fg.y(), a.bottom() - fg.height() - 9))
        if (x, y) != (fg.x(), fg.y()):
            self.move(x, y)

    # ---- tema
    def restyle(self):
        QtWidgets.QApplication.instance().setStyleSheet(U.build_qss())
        self.brand.setText("<b>MAINUAN</b><br><span style='color:%s'>LIMPEZA</span>" % T["ACCENT"])
        for b in self.nav:
            b.setIcon(make_icon(b.kind))
        self.b_toggle.setIcon(make_icon("menu"))
        for p in self.pages:
            p.on_theme()

    def check_theme(self):
        dark = core.system_is_dark()
        dark = U.qt_is_dark() if dark is None else dark
        if dark != self.dark:
            self.dark = dark
            U.set_theme(dark)
            self.restyle()

    def goto(self, n):
        self.nav[n].setChecked(True)
        self.stack.setCurrentIndex(n)

    # ---- estado / progresso
    def set_status(self, msg, frac=None, busy=False, hide_ms=0):
        self.hide_timer.stop()
        self.st_label.setText(msg)
        self.status.show()
        if busy:
            if not self.pulse.isActive():
                self.st_bar.setValue(0)
                self.pulse.start(90)
        else:
            self.pulse.stop()
            self.st_bar.setValue(int(frac if frac is not None else 0))
        if hide_ms:
            self.hide_timer.start(hide_ms)

    def _pulse(self):
        self.st_bar.setValue((self.st_bar.value() + 5) % 101)

    def _on_progress(self, msg, frac):
        self.set_status(msg, frac * 100)

    def temp_days(self):
        return self.p_temp.min_days()

    # ---- tarefas em segundo plano
    def run_task(self, fn, args, cb):
        t = U.Task(fn, args, cb, self)
        self.tasks.add(t)
        t.done.connect(self._task_done)
        t.finished.connect(self._task_finished)
        t.start()

    def _task_done(self, task, res):
        task.cb(res)

    def _task_finished(self):
        self.tasks.discard(self.sender())

    # ---- análises
    def start_scan(self):
        self.start_user_scan()
        if self.root.alive() or self.root_ok:
            self.start_root_scan()

    def start_user_scan(self):
        if self.scanning_user:
            return
        self.scanning_user = True
        self.set_status(_("A analisar…"), 0)
        self.run_task(core.scan_user, (self.sig_progress.emit,), self._user_done)

    def _user_done(self, res):
        self.scanning_user = False
        if res.get("error"):
            self.set_status(_("Erro na análise: {e}").format(e=res["error"]), 0, hide_ms=6000)
            return
        self.data.update(res)
        self.apply_data()
        if not self.scanning_root:
            self.set_status(_("Análise concluída"), 100, hide_ms=3000)

    def start_root_scan(self):
        if self.scanning_root:
            return
        self.scanning_root = True
        self.set_status(_("A analisar o sistema como administrador…"), busy=True)
        self.run_task(self.root.call, ("scan",), self._root_done)

    def _root_done(self, res):
        self.scanning_root = False
        if "kernels" not in res:
            if res.get("cancelled"):
                self.set_status(_("Autenticação cancelada."), 0, hide_ms=5000)
            else:
                self.set_status(_("Erro na análise de administrador."), 0, hide_ms=6000)
                notify(self, _("Erro"), str(res.get("error") or _("Erro desconhecido.")), ok=False)
            return
        self.data.update(res)
        self.root_ok = True
        self.apply_data()
        self.set_status(_("Análise concluída"), 100, hide_ms=3000)

    def apply_data(self):
        for p in self.pages:
            if hasattr(p, "set_root_state"):
                p.set_root_state(self.root_ok)
            if hasattr(p, "populate"):
                p.populate(self.data)

    # ---- ações
    def run_root(self, steps, busy, okmsg, rescan="root"):
        """Executa passos (ação, parâmetros) na sessão de administrador."""
        self.set_status(busy, busy=True)

        def work():
            for action, params in steps:
                r = self.root.call(action, **params)
                if not r.get("success", False):
                    return r
            return {"success": True}

        def done(res):
            if res.get("success"):
                self.root_ok = True
                self.set_status(okmsg, 100, hide_ms=4000)
                if rescan == "user":
                    self.start_user_scan()
                    if self.root_ok:
                        self.start_root_scan()
                else:
                    self.start_root_scan()
            else:
                self.set_status(_("A operação falhou."), 0, hide_ms=5000)
                notify(self, _("Erro"), str(res.get("error") or _("Erro desconhecido."))[:700], ok=False)

        self.run_task(work, (), done)

    def run_user(self, fn, args, busy, okmsg):
        """Executa uma ação sem privilégios (Flatpak, cache do utilizador, lixo)."""
        self.set_status(busy, busy=True)

        def done(res):
            if res.get("success"):
                self.set_status(okmsg, 100, hide_ms=4000)
                self.start_user_scan()
            else:
                self.set_status(_("A operação falhou."), 0, hide_ms=5000)
                notify(self, _("Erro"), str(res.get("error") or _("Erro desconhecido."))[:700], ok=False)
                self.start_user_scan()

        self.run_task(fn, args, done)

    def tick(self):
        self.tick_n += 1
        self.p_sum.update_sys(self.monitor.snapshot())
        if self.tick_n % 3 == 0:
            self.check_theme()

    def closeEvent(self, e):
        self.root.stop()
        super().closeEvent(e)


def main():
    QtWidgets.QApplication.setApplicationName("mainuan-limpeza")
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationDisplayName(core.APP_NAME)
    app.setDesktopFileName("mainuan-limpeza")
    U.set_font(U.pick_font())
    dark = core.system_is_dark()
    dark = U.qt_is_dark() if dark is None else dark
    U.set_theme(dark)
    app.setStyleSheet(U.build_qss())
    app.setWindowIcon(QtGui.QIcon(logo_pixmap(256)))
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    w = MainWindow(dark)
    w.show()
    QtCore.QTimer.singleShot(80, w.fit_to_screen)
    QtCore.QTimer.singleShot(400, w.fit_to_screen)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
