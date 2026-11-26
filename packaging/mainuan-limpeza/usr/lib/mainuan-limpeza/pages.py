#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""MAINUAN LIMPEZA - páginas (menus) da aplicação.
Visual e disposição dos menus do MAINUAN OTIMIZADOR."""
import os
import re
import shutil
import subprocess
import configparser

import core
from core import fmt_size
from i18n import _
import ui_common as U
from ui_common import (QtCore, QtGui, QtWidgets, Qt, T, label, card, button, badge_pixmap,
                       draw_pixmap, CheckTable, ask, notify)

HOME = os.path.expanduser("~")
CACHE_DIR = os.path.join(HOME, ".cache")
TRASH_DIR = os.path.join(HOME, ".local", "share", "Trash")


def n_items(n):
    return _("{n} item(ns)").format(n=n)


# ------------------------------------------------------------------ utilitários sem privilégios
def safe_delete_under(paths, base):
    """Apaga caminhos que estejam dentro de «base» (nunca a própria pasta base)."""
    base = os.path.realpath(base)
    done, errs = 0, []
    for p in paths:
        parent, name = os.path.split(os.path.normpath(p))
        real = os.path.join(os.path.realpath(parent), name)
        if not real.startswith(base + os.sep):
            errs.append(_("caminho não permitido: {p}").format(p=p))
            continue
        try:
            if os.path.islink(real) or os.path.isfile(real):
                os.remove(real)
            elif os.path.isdir(real):
                shutil.rmtree(real)
            done += 1
        except FileNotFoundError:
            done += 1
        except OSError as e:
            errs.append("%s: %s" % (name, e.strerror or e))
    return done, errs


def user_delete(paths, base):
    done, errs = safe_delete_under(paths, base)
    return {"success": not errs, "error": " | ".join(errs[:5]) or None, "done": done}


def empty_trash():
    paths = []
    for sub in ("files", "info", "expunged"):
        d = os.path.join(TRASH_DIR, sub)
        if os.path.isdir(d):
            paths += [os.path.join(d, e) for e in os.listdir(d)]
    return user_delete(paths, TRASH_DIR)


def flatpak_uninstall(refs):
    try:
        p = subprocess.run(["flatpak", "uninstall", "-y", "--noninteractive"] + list(refs),
                           capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"success": False, "error": str(e)}
    return {"success": p.returncode == 0,
            "error": None if p.returncode == 0 else ((p.stderr or p.stdout).strip()[-800:] or _("Falhou."))}


def _lang_of(code):
    return re.split(r"[_.@\-]", code, maxsplit=1)[0].lower()


def protected_languages():
    """Idiomas em uso (sistema, sessão e ambiente de trabalho) + inglês: nunca removidos."""
    langs = {"en"}

    def add(val):
        for part in re.split(r"[:;,\s]+", str(val or "")):
            part = part.strip().strip("\"'")
            if part and _lang_of(part) not in ("c", "posix"):
                langs.add(_lang_of(part))

    for var in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LC_CTYPE"):
        add(os.environ.get(var))
    for f in ("/etc/default/locale", "/etc/locale.conf"):
        try:
            with open(f, errors="replace") as fh:
                for line in fh:
                    k, _s, v = line.strip().partition("=")
                    if k in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
                        add(v)
        except OSError:
            pass
    for f, sec in ((os.path.join(HOME, ".config", "plasma-localerc"), None),
                   (os.path.join(HOME, ".config", "kdeglobals"), "Translations")):
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        try:
            cp.read(f, encoding="utf-8")
            for s in ([sec] if sec else cp.sections()):
                for k in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "Language"):
                    add(cp.get(s, k, fallback=""))
        except (configparser.Error, OSError):
            pass
    rc, out = core.run(["gsettings", "get", "org.gnome.system.locale", "region"], timeout=3)
    if rc == 0:
        add(out)
    return langs


# ------------------------------------------------------------------ cálculo do resumo
def compute_summary(d, temp_min_days=1.0):
    """Para cada cartão: (texto de contagem, bytes ou None, bloqueado?)."""
    root = "kernels" in d
    out = {}
    uc = d.get("user_cache") or []
    out["user_cache"] = (n_items(len(uc)), sum(e["size_bytes"] for e in uc), "user_cache" not in d)
    tr = d.get("trash") or {}
    out["trash"] = (n_items(tr.get("count", 0)), tr.get("size_bytes", 0), "trash" not in d)
    fa = d.get("flatpak_apps") or []
    fu = d.get("flatpak_unused") or []
    if "flatpak_apps" in d and not d.get("flatpak_available", True):
        out["flatpak"] = (_("Flatpak não instalado"), 0, False)
    else:
        out["flatpak"] = (_("{a} app(s) · {u} runtime(s) sem uso").format(a=len(fa), u=len(fu)),
                          sum(e["size_bytes"] for e in fu), "flatpak_apps" not in d)
    ap = d.get("installed_apps") or []
    out["apps"] = (_("{n} pacote(s)").format(n=len(ap)), sum(a["size_kb"] for a in ap) * 1024,
                   "installed_apps" not in d)
    lock = _("Requer administrador")
    if root:
        pk = d.get("unnecessary_pkgs") or []
        dk = d.get("orphan_dkms") or []
        out["drivers"] = (n_items(len(pk) + len(dk)),
                          (sum(p.get("installed_size", 0) for p in pk) + sum(o.get("size_kb", 0) for o in dk)) * 1024, False)
        fw = d.get("firmware") or []
        free = [f for f in fw if not f["protected"]]
        out["firmware"] = (_("{n} família(s) · {r} removível(eis)").format(n=len(fw), r=len(free)),
                           sum(f["size_kb"] for f in free) * 1024, False)
        ks = d.get("kernels") or []
        old = _removable_kernels(ks)
        out["kernels"] = (_("{n} kernel(s) · {r} removível(eis)").format(n=len(ks), r=len(old)),
                          sum(k["size_kb"] for k in old) * 1024, False)
        prot = protected_languages()
        lc = [l for l in d.get("locales", []) if _lang_of(l["code"]) not in prot]
        dc = d.get("docs") or []
        out["languages"] = (n_items(len(lc) + len(dc)),
                            (sum(l["size_kb"] for l in lc) + sum(x["size_kb"] for x in dc)) * 1024, False)
        ac = d.get("apt_cache") or {}
        out["apt"] = (_("{n} ficheiros .deb").format(n=ac.get("deb_count", 0)), ac.get("size_bytes", 0), False)
        te = [e for e in d.get("temp_entries", []) if e["age_days"] >= temp_min_days]
        out["temp"] = (n_items(len(te)), sum(e["size_bytes"] for e in te), False)
        le = d.get("log_entries") or []
        jn = (d.get("journald") or {}).get("size_bytes", 0)
        out["logs"] = (n_items(len(le)), sum(e["size_bytes"] for e in le) + jn, False)
    else:
        for k in ("drivers", "firmware", "kernels", "languages", "apt", "temp", "logs"):
            out[k] = (lock, None, True)
    total = sum(v[1] or 0 for k, v in out.items() if k not in ("apps", "firmware"))
    return out, total


def _kver(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


def _kernel_protected(ks):
    prot = {k["version"] for k in ks if k["is_active"]}
    if ks:
        prot.add(max(ks, key=lambda k: _kver(k["version"]))["version"])  # o mais recente é mantido
    return prot


def _removable_kernels(ks):
    prot = _kernel_protected(ks)
    return [k for k in ks if k["version"] not in prot]


# ------------------------------------------------------------------ base das páginas
class BasePage(QtWidgets.QWidget):
    needs_root = False

    def __init__(self, win, kind, title, desc):
        super().__init__()
        self.win, self.kind = win, kind
        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.setContentsMargins(28, 22, 28, 18)
        self.lay.setSpacing(14)
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(14)
        self.badge = QtWidgets.QLabel()
        self.badge.setFixedSize(46, 46)
        head.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label(title, "h1"))
        col.addWidget(label(desc, "muted", True))
        head.addLayout(col, 1)
        self.lay.addLayout(head)
        self.banner = None
        if self.needs_root:
            self.banner = QtWidgets.QFrame()
            self.banner.setObjectName("banner")
            bl = QtWidgets.QHBoxLayout(self.banner)
            bl.setContentsMargins(16, 12, 16, 12)
            self.b_icon = QtWidgets.QLabel()
            bl.addWidget(self.b_icon)
            bl.addWidget(label(_("Esta secção precisa de permissões de administrador para analisar o sistema. "
                                 "Será pedida a palavra-passe uma única vez."), None, True), 1)
            self.b_btn = button(_("Analisar como administrador"), "primary")
            self.b_btn.clicked.connect(lambda _c=False: self.win.start_root_scan())
            bl.addWidget(self.b_btn)
            self.lay.addWidget(self.banner)
        self.body = QtWidgets.QVBoxLayout()
        self.body.setSpacing(12)
        self.lay.addLayout(self.body, 1)
        self.on_theme()

    def on_theme(self):
        self.badge.setPixmap(badge_pixmap(self.kind, 46))
        if self.banner is not None:
            self.b_icon.setPixmap(draw_pixmap("lock", T["WARN"], 28))

    def set_root_state(self, ok):
        if self.banner is not None:
            self.banner.setVisible(not ok)

    def populate(self, d):  # sobrepor
        pass


class Section(QtWidgets.QWidget):
    """Barra de informação + tabela com caixas + botão de ação."""

    def __init__(self, win, headers, action_text, on_action, stretch_col=1, search=False,
                 title=None, hint=None, extra_check_cols=(), checkable=True, min_rows=6,
                 select_all=True):
        super().__init__()
        self.win, self.on_action = win, on_action
        self.sizes = {}
        self.extra = tuple(extra_check_cols)
        self.checkable = checkable
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        if title:
            lay.addWidget(label(title, "h2"))
        if hint:
            lay.addWidget(label(hint, "muted", True))
        bar = QtWidgets.QHBoxLayout()
        self.info = label("", "muted")
        bar.addWidget(self.info)
        bar.addStretch(1)
        self.search = None
        if search:
            self.search = QtWidgets.QLineEdit()
            self.search.setPlaceholderText(_("Pesquisar…"))
            self.search.setMinimumWidth(240)
            bar.addWidget(self.search)
        self.chk_all = None
        if select_all and (checkable or extra_check_cols):
            self.chk_all = QtWidgets.QCheckBox(_("Selecionar tudo"))
            self.chk_all.clicked.connect(self._select_all)
            bar.addWidget(self.chk_all)
        lay.addLayout(bar)
        self.table = CheckTable(headers, checkable=checkable, stretch_col=stretch_col,
                                extra_check_cols=extra_check_cols)
        self.table.setMinimumHeight(34 * min_rows)
        self.table.selection_changed.connect(self._refresh)
        if self.search:
            self.search.textChanged.connect(self.table.filter_text)
        self.empty = label("", "muted", True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setMinimumHeight(34 * min_rows)
        self.empty.hide()
        lay.addWidget(self.table, 1)
        lay.addWidget(self.empty, 1)
        self.btns = QtWidgets.QHBoxLayout()
        self.btns.addStretch(1)
        self.action = None
        if action_text:
            self.action = button(action_text, "primary")
            self.action.setEnabled(False)
            self.action.clicked.connect(lambda _c=False: self.on_action())
            self.btns.addWidget(self.action)
        lay.addLayout(self.btns)
        self.empty_text = _("Faça uma análise para ver os resultados.")

    def add_button(self, b, first=True):
        self.btns.insertWidget(1 if first else self.btns.count(), b)

    def _select_all(self, on):
        for c in ([0] if self.checkable else []) + list(self.extra):
            self.table.set_all(on, c)

    def cols(self):
        return ([0] if self.checkable else []) + list(self.extra)

    def has_selection(self):
        return any(self.table.checked_rows(c) for c in self.cols())

    def selected(self, col=0):
        return self.table.selected_keys(col) if col == 0 else \
            [self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in self.table.checked_rows(col)]

    def _refresh(self):
        n = sum(len(self.table.checked_rows(c)) for c in self.cols())
        if self.action is not None:
            self.action.setEnabled(n > 0)
        if self.info.property("fixed"):
            return
        if self.checkable and not self.extra and self.sizes:
            tot = sum(self.sizes.get(k, 0) for k in self.table.selected_keys())
            if n:
                self.info.setText(_("{n} selecionado(s) — {s}").format(n=n, s=fmt_size(tot)))
                return
        if n:
            self.info.setText(_("{n} selecionado(s)").format(n=n))
        else:
            self.info.setText(self.base_info)

    base_info = ""

    def fill(self, rows, sizes=None, info="", empty=None):
        """rows=None → ainda sem dados; rows=[] → nada para limpar."""
        self.sizes = sizes or {}
        self.base_info = info
        if rows is None or not rows:
            self.table.hide()
            self.empty.setText(self.empty_text if rows is None else (empty or _("Nada para limpar nesta secção.")))
            self.empty.show()
            self.table.fill([])
            self.info.setText(info if rows is not None else "")
        else:
            self.empty.hide()
            self.table.show()
            self.table.fill(rows)
            self.info.setText(info)
        if self.chk_all is not None:
            self.chk_all.setChecked(False)
        self._refresh()


# ============================================================================ RESUMO
class SumCard(QtWidgets.QFrame):
    def __init__(self, kind, title, on_click, kpi_name="kpi"):
        super().__init__()
        self.setObjectName("sumcard")
        self.kind, self.on_click = kind, on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(138)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(6)
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(12)
        self.badge = QtWidgets.QLabel()
        self.badge.setFixedSize(44, 44)
        top.addWidget(self.badge)
        self.title = label(title, "cardtitle", True)
        top.addWidget(self.title, 1)
        self.lock = QtWidgets.QLabel()
        top.addWidget(self.lock, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)
        self.count = label("", "muted", True)
        lay.addWidget(self.count)
        self.kpi = label("—", kpi_name)
        lay.addWidget(self.kpi)
        lay.addStretch(1)
        self.locked = False
        self.on_theme()

    def on_theme(self):
        self.badge.setPixmap(badge_pixmap(self.kind, 44))
        self.lock.setPixmap(draw_pixmap("lock", T["MUTED"], 16) if self.locked else QtGui.QPixmap())

    def set_data(self, count, value, locked=False):
        self.count.setText(count)
        self.locked = locked
        self.kpi.setText("—" if value is None else value)
        self.lock.setPixmap(draw_pixmap("lock", T["MUTED"], 16) if locked else QtGui.QPixmap())

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.on_click:
            self.on_click()
        super().mousePressEvent(e)


class SummaryPage(QtWidgets.QWidget):
    # chave, ícone, título, índice do menu
    CARDS = (
        ("sys", "gauge", "Utilização do sistema", None),
        ("apps", "apps", "Aplicações instaladas", 1),
        ("flatpak", "package", "Flatpak", 2),
        ("user_cache", "folder", "Cache do utilizador", 3),
        ("trash", "trash", "Lixo", 4),
        ("drivers", "monitor", "Drivers desnecessários", 5),
        ("firmware", "disk", "Firmwares", 6),
        ("kernels", "layers", "Kernels antigos", 7),
        ("languages", "globe", "Idiomas e documentação", 8),
        ("apt", "pkgdown", "Cache APT", 9),
        ("temp", "clock", "Ficheiros temporários", 10),
        ("logs", "doc", "Registos do sistema", 11),
    )

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.cols = 0
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(16)
        lay.addWidget(label(_("Resumo"), "h1"))
        lay.addWidget(label(_("Veja quanto espaço pode libertar em cada área do sistema. "
                              "Clique numa caixa para abrir a respetiva secção."), "muted", True))

        self.hero = QtWidgets.QFrame()
        self.hero.setObjectName("hero")
        hl = QtWidgets.QHBoxLayout(self.hero)
        hl.setContentsMargins(26, 22, 26, 22)
        hl.setSpacing(20)
        self.hero_badge = QtWidgets.QLabel()
        self.hero_badge.setFixedSize(72, 72)
        hl.addWidget(self.hero_badge)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label(_("Espaço total recuperável"), "herosub"))
        self.total = label("—", None)
        self.total.setStyleSheet("font-size: 30pt; font-weight: bold; color: #FFFFFF; background: transparent;")
        col.addWidget(self.total)
        self.total_sub = label(_("Faça uma análise para ver quanto pode libertar."), "herosub", True)
        col.addWidget(self.total_sub)
        hl.addLayout(col, 1)
        bcol = QtWidgets.QVBoxLayout()
        bcol.setSpacing(8)
        self.b_scan = QtWidgets.QPushButton(_("Analisar agora"))
        self.b_scan.setObjectName("herobtn")
        self.b_scan.clicked.connect(lambda _c=False: self.win.start_scan())
        self.b_root = QtWidgets.QPushButton(_("Analisar como administrador"))
        self.b_root.setObjectName("heroghost")
        self.b_root.clicked.connect(lambda _c=False: self.win.start_root_scan())
        bcol.addWidget(self.b_scan)
        bcol.addWidget(self.b_root)
        hl.addLayout(bcol)
        lay.addWidget(self.hero)

        self.grid_host = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(14)
        lay.addWidget(self.grid_host)
        lay.addStretch(1)

        self.cards = {}
        for key, kind, title, idx in self.CARDS:
            cb = (lambda i=idx: self.win.goto(i)) if idx is not None else None
            c = SumCard(kind, _(title), cb, "h2" if key == "sys" else "kpi")
            self.cards[key] = c
        self.relayout(3)
        self.cards["sys"].set_data(_("CPU: --%   RAM: --%"), _("Disco: --%   Temp: --"))
        self.on_theme()

    def relayout(self, cols):
        if cols == self.cols:
            return
        self.cols = cols
        for c in self.cards.values():
            self.grid.removeWidget(c)
        for i, (key, _k, _t, _i) in enumerate(self.CARDS):
            self.grid.addWidget(self.cards[key], i // cols, i % cols)
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)

    def resizeEvent(self, e):
        w = self.width()
        self.relayout(3 if w >= 940 else 2 if w >= 620 else 1)
        super().resizeEvent(e)

    def on_theme(self):
        self.hero_badge.setPixmap(badge_pixmap("broom", 72, glass=True))
        for c in self.cards.values():
            c.on_theme()

    def update_sys(self, s):
        t = s.get("temp")
        self.cards["sys"].set_data(_("CPU: {c:.0f}%   RAM: {r:.0f}%").format(c=s["cpu"], r=s["ram"]),
                                   _("Disco: {d:.0f}%   Temp: {t}").format(
                                       d=s["disk"], t="--" if t is None else f"{t:.0f} °C"))

    def populate(self, d):
        vals, total = compute_summary(d, self.win.temp_days())
        for key, (count, size, locked) in vals.items():
            c = self.cards.get(key)
            if c is not None:
                c.set_data(count, None if (size is None or locked) else fmt_size(size), locked)
        has_any = any(k in d for k in ("user_cache", "trash", "installed_apps"))
        if has_any:
            self.total.setText(fmt_size(total))
            self.total_sub.setText(_("Pronto para limpar.") if "kernels" in d else
                                   _("Faça a análise como administrador para incluir o resto do sistema."))
        self.b_root.setEnabled(True)


# ============================================================================ APLICAÇÕES
class AppsPage(BasePage):
    def __init__(self, win):
        super().__init__(win, "apps", _("Aplicações instaladas"),
                         _("Pacotes instalados manualmente. Desinstale o que já não usa."))
        self.sec = Section(win, ["", _("Pacote"), _("Descrição"), _("Tamanho")], _("Desinstalar selecionados"),
                           self.remove, stretch_col=2, search=True)
        self.sec.empty_text = _("A analisar… ou nenhum pacote instalado manualmente.")
        self.body.addWidget(self.sec)

    def populate(self, d):
        apps = d.get("installed_apps")
        if apps is None:
            self.sec.fill(None)
            return
        rows = [dict(key=a["name"], cells=["", a["name"], a["summary"], fmt_size(a["size_kb"] * 1024)],
                     right={3}) for a in apps]
        sizes = {a["name"]: a["size_kb"] * 1024 for a in apps}
        self.sec.fill(rows, sizes, _("{n} pacote(s) — {s}").format(
            n=len(apps), s=fmt_size(sum(sizes.values()))), _("Nenhum pacote instalado manualmente."))

    def remove(self):
        sel = self.sec.selected()
        if not sel or not ask(self.win, _("Desinstalar aplicações"), _("Desinstalar os pacotes selecionados?"),
                              _("{n} pacote(s) serão removidos:\n{l}").format(
                                  n=len(sel), l="\n".join(sel[:8]) + ("…" if len(sel) > 8 else ""))):
            return
        self.win.run_root([("apt_remove", {"packages": sel})], _("A desinstalar pacotes…"),
                          _("Pacotes desinstalados com sucesso."), rescan="user")


# ============================================================================ FLATPAK
class FlatpakPage(BasePage):
    def __init__(self, win):
        super().__init__(win, "package", _("Flatpak"),
                         _("Aplicações Flatpak instaladas e runtimes que já ninguém usa."))
        self.apps = Section(win, ["", _("Nome"), _("Identificador"), _("Versão"), _("Tamanho")],
                            _("Desinstalar selecionadas"), self.rm_apps, title=_("Aplicações"),
                            stretch_col=2, min_rows=4)
        self.rt = Section(win, ["", _("Runtime"), _("Referência"), _("Tamanho")], _("Remover selecionados"),
                          self.rm_rt, title=_("Runtimes sem uso"), stretch_col=2, min_rows=4)
        self.body.addWidget(self.apps)
        self.body.addWidget(self.rt)

    def populate(self, d):
        if "flatpak_apps" not in d:
            self.apps.fill(None)
            self.rt.fill(None)
            return
        if not d.get("flatpak_available", True):
            self.apps.fill([], empty=_("O Flatpak não está instalado neste sistema."))
            self.rt.fill([], empty=_("O Flatpak não está instalado neste sistema."))
            return
        apps = d["flatpak_apps"]
        self.apps.fill([dict(key=a["app_id"], cells=["", a["name"], a["app_id"], a["version"],
                                                     fmt_size(a["size_bytes"])], right={4}) for a in apps],
                       {a["app_id"]: a["size_bytes"] for a in apps},
                       _("{n} aplicação(ões) — {s}").format(n=len(apps), s=fmt_size(sum(a["size_bytes"] for a in apps))),
                       _("Nenhuma aplicação Flatpak instalada."))
        un = d.get("flatpak_unused", [])
        self.rt.fill([dict(key=e["ref"], cells=["", e["name"], e["ref"], fmt_size(e["size_bytes"])], right={3})
                      for e in un], {e["ref"]: e["size_bytes"] for e in un},
                     _("{n} runtime(s) — {s}").format(n=len(un), s=fmt_size(sum(e["size_bytes"] for e in un))),
                     _("Não há runtimes Flatpak por limpar."))

    def rm_apps(self):
        sel = self.apps.selected()
        if sel and ask(self.win, _("Desinstalar Flatpak"), _("Desinstalar as aplicações Flatpak selecionadas?"),
                       _("{n} aplicação(ões) serão desinstaladas.").format(n=len(sel))):
            self.win.run_user(flatpak_uninstall, (sel,), _("A desinstalar aplicações Flatpak…"),
                              _("Aplicações Flatpak desinstaladas."))

    def rm_rt(self):
        sel = self.rt.selected()
        if sel and ask(self.win, _("Remover runtimes"), _("Remover os runtimes Flatpak selecionados?"),
                       _("{n} runtime(s) serão removidos.").format(n=len(sel))):
            self.win.run_user(flatpak_uninstall, (sel,), _("A remover runtimes Flatpak…"),
                              _("Runtimes Flatpak removidos."))


# ============================================================================ CACHE DO UTILIZADOR
class UserCachePage(BasePage):
    def __init__(self, win):
        super().__init__(win, "folder", _("Cache do utilizador"),
                         _("Ficheiros temporários das suas aplicações em ~/.cache. São recriados quando necessário."))
        self.sec = Section(win, ["", _("Aplicação"), _("Pasta"), _("Tamanho")], _("Remover selecionados"),
                           self.remove, stretch_col=2)
        self.body.addWidget(self.sec)

    def populate(self, d):
        es = d.get("user_cache")
        if es is None:
            self.sec.fill(None)
            return
        self.sec.fill([dict(key=e["path"], cells=["", e["name"], e["path"], fmt_size(e["size_bytes"])], right={3})
                       for e in es], {e["path"]: e["size_bytes"] for e in es},
                      _("{n} item(ns) — {s}").format(n=len(es), s=fmt_size(sum(e["size_bytes"] for e in es))),
                      _("A cache do utilizador está vazia."))

    def remove(self):
        sel = self.sec.selected()
        if sel and ask(self.win, _("Cache do utilizador"), _("Remover as entradas de cache selecionadas?"),
                       _("{n} item(ns) serão apagados definitivamente.").format(n=len(sel))):
            self.win.run_user(user_delete, (sel, CACHE_DIR), _("A limpar a cache do utilizador…"),
                              _("Cache do utilizador limpa."))


# ============================================================================ LIXO
class TrashPage(BasePage):
    def __init__(self, win):
        super().__init__(win, "trash", _("Lixo"), _("Ficheiros que enviou para o lixo e ainda ocupam espaço."))
        c = card()
        cl = QtWidgets.QVBoxLayout(c)
        cl.setContentsMargins(30, 30, 30, 30)
        cl.setSpacing(10)
        self.big = QtWidgets.QLabel()
        self.big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.big)
        self.count = label("—", "h2")
        self.count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.count)
        self.size = label("", "kpi")
        self.size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.size)
        self.btn = button(_("Esvaziar lixo"), "primary")
        self.btn.setMinimumWidth(200)
        self.btn.setEnabled(False)
        self.btn.clicked.connect(self.empty)
        cl.addWidget(self.btn, 0, Qt.AlignmentFlag.AlignHCenter)
        self.body.addWidget(c)
        self.body.addStretch(1)
        self.on_theme()

    def on_theme(self):
        super().on_theme()
        if hasattr(self, "big"):
            self.big.setPixmap(badge_pixmap("trash", 88))

    def populate(self, d):
        t = d.get("trash")
        if t is None:
            return
        self.count.setText(n_items(t["count"]) if t["count"] else _("O lixo está vazio"))
        self.size.setText(fmt_size(t["size_bytes"]) if t["count"] else "")
        self.btn.setEnabled(t["count"] > 0)

    def empty(self):
        if ask(self.win, _("Lixo"), _("Esvaziar o lixo?"),
               _("Todos os itens do lixo serão apagados definitivamente.")):
            self.win.run_user(empty_trash, (), _("A esvaziar o lixo…"), _("Lixo esvaziado."))


# ============================================================================ DRIVERS
class DriversPage(BasePage):
    needs_root = True

    def __init__(self, win):
        super().__init__(win, "monitor", _("Drivers desnecessários"),
                         _("Drivers e ferramentas de hardware que não existe neste computador."))
        self.hw = label(_("Hardware detetado: —"), "muted")
        self.body.addWidget(self.hw)
        self.sec = Section(win, ["", _("Pacote"), _("Fabricante"), _("Tamanho")], _("Remover selecionados"),
                           self.remove, stretch_col=1)
        self.body.addWidget(self.sec)
        self.dk = {}

    def populate(self, d):
        if "kernels" not in d:
            self.sec.fill(None)
            return
        hw = d.get("hardware_summary") or []
        self.hw.setText(_("Hardware detetado: {h}").format(h=", ".join(hw) if hw else _("Genérico")))
        rows, sizes = [], {}
        for p in d.get("unnecessary_pkgs", []):
            sz = p.get("installed_size", 0) * 1024
            rows.append(dict(key=p["name"], cells=["", p["name"], "[%s]" % p.get("vendor", ""), fmt_size(sz)],
                             right={3}, tooltip=p.get("description", "")))
            sizes[p["name"]] = sz
        self.dk = {}
        for o in d.get("orphan_dkms", []):
            key = "__dkms__%s__%s" % (o["name"], o["version"])
            self.dk[key] = o
            sz = o.get("size_kb", 0) * 1024
            rows.append(dict(key=key, cells=["", "%s %s" % (o["name"], o["version"]), "[DKMS]", fmt_size(sz)],
                             right={3}))
            sizes[key] = sz
        self.sec.fill(rows, sizes, _("{n} item(ns) — {s}").format(n=len(rows), s=fmt_size(sum(sizes.values()))),
                      _("Não foram encontrados drivers desnecessários."))

    def remove(self):
        sel = self.sec.selected()
        if not sel:
            return
        pkgs = [k for k in sel if not k.startswith("__dkms__")]
        dkms = [self.dk[k] for k in sel if k in self.dk]
        if not ask(self.win, _("Remover drivers"), _("Remover os drivers selecionados?"),
                   _("{n} item(ns) serão removidos e o initramfs será regenerado.").format(n=len(sel))):
            return
        steps = []
        if dkms:
            steps.append(("remove_dkms_orphans", {"orphans": dkms}))
        if pkgs:
            steps.append(("apt_purge", {"packages": pkgs, "rebuild_initrd": True}))
        self.win.run_root(steps, _("A remover drivers e a regenerar o initramfs…"),
                          _("Drivers removidos com sucesso."), rescan="root")


# ============================================================================ FIRMWARES
class FirmwarePage(BasePage):
    needs_root = True

    def __init__(self, win):
        super().__init__(win, "disk", _("Firmwares"),
                         _("Os firmwares exigidos pelo hardware detetado ficam bloqueados automaticamente; "
                           "só os não reconhecidos podem ser removidos."))
        self.sec = Section(win, ["", _("Família"), _("Estado"), _("Tamanho")], _("Remover firmwares selecionados"),
                           self.remove, stretch_col=2)
        self.body.addWidget(self.sec)

    def populate(self, d):
        fw = d.get("firmware")
        if fw is None:
            self.sec.fill(None)
            return
        rows, sizes = [], {}
        for f in fw:
            if f["protected"]:
                st = _("Protegido: hardware presente neste sistema")
            elif f["pkg"]:
                st = _("Temporário: faz parte do pacote {p} e reaparece na próxima atualização").format(p=f["pkg"])
            else:
                st = _("Removível")
            rows.append(dict(key=f["name"], cells=["", f["name"], st, fmt_size(f["size_kb"] * 1024)],
                             enabled=not f["protected"], right={3}))
            sizes[f["name"]] = f["size_kb"] * 1024
        self.sec.fill(rows, sizes, _("{n} família(s) de firmware detetadas").format(n=len(fw)),
                      _("Nenhum firmware encontrado."))

    def remove(self):
        sel = self.sec.selected()
        if sel and ask(self.win, _("Remover firmwares"), _("Remover os firmwares selecionados?"),
                       _("{n} família(s) serão removidas de /lib/firmware/ e o initramfs será regenerado.").format(n=len(sel))):
            self.win.run_root([("remove_firmware", {"families": sel})],
                              _("A remover firmwares e a regenerar o initramfs…"),
                              _("Firmwares removidos e initramfs regenerado."), rescan="root")


# ============================================================================ KERNELS
class KernelsPage(BasePage):
    needs_root = True

    def __init__(self, win):
        super().__init__(win, "layers", _("Kernels antigos"),
                         _("Versões antigas do kernel. O kernel em uso e o mais recente ficam sempre protegidos."))
        self.ks = []
        self.sec = Section(win, [_("Versão"), _("Estado"), _("Imagem"), _("Cabeçalhos"), _("Fontes"), "Kbuild",
                                 _("Tamanho")], _("Remover selecionados"), self.remove, stretch_col=1,
                           checkable=False, extra_check_cols=(2, 3, 4, 5), min_rows=5, select_all=False)
        self.body.addWidget(self.sec)
        self.orph = Section(win, ["", _("Pasta órfã")], _("Remover pastas órfãs"), self.remove_orphans,
                            title=_("Pastas de kernel órfãs"),
                            hint=_("Restos em /usr/src e /lib/modules sem pacote instalado."), min_rows=3)
        self.body.addWidget(self.orph)

    def populate(self, d):
        if "kernels" not in d:
            self.sec.fill(None)
            self.orph.fill(None)
            return
        self.ks = d["kernels"]
        prot = _kernel_protected(self.ks)
        rows, orph = [], set()
        for i, k in enumerate(self.ks):
            locked = k["version"] in prot
            if k["is_active"]:
                st = _("Em uso")
            elif locked:
                st = _("Mais recente (mantido)")
            else:
                st = _("Removível")
            rows.append(dict(key=i, enabled=not locked, right={6},
                             cells=[k["version"], st, "", "", "", "", fmt_size(k["size_kb"] * 1024)],
                             checks={2: False if k["image_pkg"] else None, 3: False if k["headers_pkg"] else None,
                                     4: False if k["src_pkg"] else None, 5: False if k["kbuild_pkg"] else None}))
            orph.update(k["orphan_src_dirs"])
            orph.update(k["orphan_modules_dirs"])
        old = _removable_kernels(self.ks)
        self.sec.fill(rows, None, _("{n} kernel(s) instalados, {r} removível(eis)").format(n=len(self.ks), r=len(old)),
                      _("Nenhum kernel encontrado."))
        self.orph.fill([dict(key=p, cells=["", p]) for p in sorted(orph)], None,
                       _("{n} pasta(s)").format(n=len(orph)), _("Não há pastas órfãs."))
        self.orph.setVisible(bool(orph))

    def remove(self):
        pkgs = []
        for col, field in ((2, "image_pkg"), (3, "headers_pkg"), (4, "src_pkg"), (5, "kbuild_pkg")):
            for r in self.sec.table.checked_rows(col):
                k = self.ks[self.sec.table.item(r, 0).data(Qt.ItemDataRole.UserRole)]
                if k.get(field):
                    pkgs.append(k[field])
                if col == 2:  # no Ubuntu os módulos vêm em pacotes próprios
                    from scanner.packages import is_package_installed
                    for extra in ("linux-modules-%s", "linux-modules-extra-%s"):
                        name = extra % k["version"]
                        if is_package_installed(name):
                            pkgs.append(name)
        pkgs = list(dict.fromkeys(pkgs))
        if pkgs and ask(self.win, _("Remover kernels"), _("Remover os pacotes de kernel selecionados?"),
                        _("{n} pacote(s) a remover:\n{l}\n\nO initramfs e o GRUB serão atualizados.").format(
                            n=len(pkgs), l="\n".join(pkgs[:8]) + ("…" if len(pkgs) > 8 else ""))):
            self.win.run_root([("apt_purge", {"packages": pkgs, "update_bootloader": True})],
                              _("A remover kernels e a atualizar o GRUB…"), _("Kernels removidos com sucesso."),
                              rescan="root")

    def remove_orphans(self):
        sel = self.orph.selected()
        if sel and ask(self.win, _("Pastas órfãs"), _("Remover as pastas órfãs selecionadas?"),
                       _("{n} pasta(s) serão apagadas definitivamente.").format(n=len(sel))):
            self.win.run_root([("delete_orphan_dirs", {"paths": sel})], _("A remover pastas órfãs…"),
                              _("Pastas órfãs removidas."), rescan="root")


# ============================================================================ IDIOMAS
class LanguagesPage(BasePage):
    needs_root = True

    def __init__(self, win):
        super().__init__(win, "globe", _("Idiomas e documentação"),
                         _("Traduções que não usa e documentação do sistema. O seu idioma e o inglês ficam protegidos."))
        bar = QtWidgets.QHBoxLayout()
        self.b_smart = button(_("Manter só os meus idiomas"))
        self.b_smart.setToolTip(_("Seleciona todos os idiomas exceto o atual e o inglês"))
        self.b_smart.clicked.connect(self.smart)
        self.b_docs = button(_("Selecionar toda a documentação"))
        self.b_docs.clicked.connect(self.all_docs)
        bar.addWidget(self.b_smart)
        bar.addWidget(self.b_docs)
        bar.addStretch(1)
        self.persist = QtWidgets.QCheckBox(_("Impedir que as atualizações restaurem os idiomas (instala o localepurge)"))
        bar.addWidget(self.persist)
        self.body.addLayout(bar)
        self.loc = Section(win, ["", _("Idioma"), _("Tipo"), _("Tamanho")], _("Remover idiomas selecionados"),
                           self.rm_locales, title=_("Idiomas"), stretch_col=1, min_rows=5)
        self.doc = Section(win, ["", _("Documentação"), _("Pasta"), _("Tamanho")], _("Remover documentação selecionada"),
                           self.rm_docs, title=_("Documentação do sistema"), stretch_col=2, min_rows=4)
        self.body.addWidget(self.loc)
        self.body.addWidget(self.doc)
        self.paths = {}
        self.prot = set()

    def populate(self, d):
        if "kernels" not in d:
            self.loc.fill(None)
            self.doc.fill(None)
            return
        self.prot = protected_languages()
        cat = {"system": _("Idioma do sistema"), "gnome": _("Ajuda GNOME"), "kde": _("Documentação KDE")}
        rows, sizes = [], {}
        self.paths = {}
        for l in sorted(d.get("locales", []), key=lambda x: -x["size_kb"]):
            prot = _lang_of(l["code"]) in self.prot
            key = l["code"] + "|" + l["category"]
            self.paths[key] = l["paths"]
            rows.append(dict(key=key, enabled=not prot, right={3},
                             cells=["", l["code"] + (_("  (protegido)") if prot else ""),
                                    cat.get(l["category"], l["category"]), fmt_size(l["size_kb"] * 1024)],
                             tooltip=_("Protegido: idioma atual ou inglês") if prot else ""))
            sizes[key] = l["size_kb"] * 1024
        self.loc.fill(rows, sizes, _("{n} idioma(s)").format(n=len(rows)), _("Nenhum idioma encontrado."))
        ds = d.get("docs", [])
        self.doc.fill([dict(key=x["path"], cells=["", x["name"], x["path"], fmt_size(x["size_kb"] * 1024)], right={3})
                       for x in ds], {x["path"]: x["size_kb"] * 1024 for x in ds},
                      _("{n} entrada(s) de documentação").format(n=len(ds)), _("Nenhuma documentação encontrada."))

    def smart(self):
        self.loc.table.set_all(True)

    def all_docs(self):
        self.doc.table.set_all(True)

    def rm_locales(self):
        sel = self.loc.selected()
        paths = [p for k in sel for p in self.paths.get(k, [])]
        if paths and ask(self.win, _("Remover idiomas"), _("Remover os idiomas selecionados?"),
                         _("{n} pasta(s) de idioma serão apagadas definitivamente.").format(n=len(paths))):
            keep = sorted(self.prot)
            self.win.run_root([("delete_locales", {"paths": paths, "keep_codes": keep,
                                                   "persist": self.persist.isChecked()})],
                              _("A remover idiomas…"), _("Idiomas removidos com sucesso."), rescan="root")

    def rm_docs(self):
        sel = self.doc.selected()
        if sel and ask(self.win, _("Remover documentação"), _("Remover a documentação selecionada?"),
                       _("{n} pasta(s) de documentação serão apagadas definitivamente.").format(n=len(sel))):
            self.win.run_root([("delete_docs", {"paths": sel})], _("A remover documentação…"),
                              _("Documentação removida com sucesso."), rescan="root")


# ============================================================================ CACHE APT
class AptPage(BasePage):
    needs_root = True

    def __init__(self, win):
        super().__init__(win, "pkgdown", _("Cache APT"),
                         _("Pacotes .deb descarregados e pacotes que já ninguém precisa."))
        self.debs = Section(win, ["", _("Ficheiro .deb"), _("Tamanho")], _("Remover selecionados"), self.rm_debs,
                            title=_("Cache de pacotes APT"), stretch_col=1, min_rows=5)
        self.b_clean = button(_("Limpar tudo"))
        self.b_clean.clicked.connect(self.clean_all)
        self.debs.add_button(self.b_clean)
        self.orph = Section(win, [_("Pacote ou referência órfã")], _("Remover pacotes órfãos"), self.autoremove,
                            title=_("Pacotes órfãos"), stretch_col=0, checkable=False, min_rows=4)
        self.body.addWidget(self.debs)
        self.body.addWidget(self.orph)
        self.refs = []

    def populate(self, d):
        if "kernels" not in d:
            self.debs.fill(None)
            self.orph.fill(None)
            self.b_clean.setEnabled(False)
            return
        ac = d.get("apt_cache", {})
        debs = d.get("apt_cache_debs", [])
        self.debs.fill([dict(key=x["path"], cells=["", x["name"], fmt_size(x["size_bytes"])], right={2}) for x in debs],
                       {x["path"]: x["size_bytes"] for x in debs},
                       _("{n} ficheiros .deb — {s}  |  Listas de pacotes: {l}").format(
                           n=ac.get("deb_count", 0), s=fmt_size(ac.get("size_bytes", 0)),
                           l=fmt_size(ac.get("lists_size_bytes", 0))),
                       _("Não há ficheiros .deb em cache."))
        self.b_clean.setEnabled(bool(debs))
        self.refs = d.get("orphan_module_refs", [])
        rows = [dict(cells=[p]) for p in d.get("autoremove_pkgs", [])]
        rows += [dict(cells=["%s  (%s)" % (r["module"], r["source"])]) for r in self.refs]
        self.orph.fill(rows, None, _("{n} item(ns) órfão(s)").format(n=len(rows)), _("Não há pacotes órfãos."))
        if self.orph.action is not None:
            self.orph.action.setEnabled(bool(rows))

    def rm_debs(self):
        sel = self.debs.selected()
        if sel and ask(self.win, _("Cache APT"), _("Remover os ficheiros .deb selecionados?"),
                       _("{n} ficheiro(s) serão apagados da cache do APT.").format(n=len(sel))):
            self.win.run_root([("delete_paths", {"paths": sel})], _("A remover ficheiros .deb…"),
                              _("Ficheiros .deb removidos."), rescan="root")

    def clean_all(self):
        self.win.run_root([("apt_clean", {})], _("A limpar a cache do APT…"), _("Cache do APT limpa com sucesso."),
                          rescan="root")

    def autoremove(self):
        if not ask(self.win, _("Pacotes órfãos"), _("Remover os pacotes órfãos?"),
                   _("O APT removerá os pacotes que já não são necessários.")):
            return
        steps = []
        if self.refs:
            steps.append(("clean_module_refs", {"refs": self.refs}))
        steps.append(("apt_autoremove", {}))
        self.win.run_root(steps, _("A remover pacotes órfãos…"), _("Pacotes órfãos removidos."), rescan="root")


# ============================================================================ TEMPORÁRIOS
class TempPage(BasePage):
    needs_root = True
    AGES = ((1, "1 dia"), (7, "7 dias"), (30, "30 dias"), (0, "NÃO MANTER (apagar tudo)"))

    def __init__(self, win):
        super().__init__(win, "clock", _("Ficheiros temporários"),
                         _("Conteúdo de /tmp e /var/tmp. Feche as aplicações abertas antes de apagar tudo."))
        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(label(_("Manter ficheiros dos últimos:"), "muted"))
        self.age = QtWidgets.QComboBox()
        for days, txt in self.AGES:
            self.age.addItem(_(txt), days)
        self.age.currentIndexChanged.connect(lambda _i: self.populate(self.win.data))
        bar.addWidget(self.age)
        bar.addStretch(1)
        self.body.addLayout(bar)
        self.sec = Section(win, ["", _("Caminho"), _("Idade"), _("Tamanho")], _("Remover selecionados"),
                           self.remove, stretch_col=1)
        self.body.addWidget(self.sec)

    def min_days(self):
        return float(self.age.currentData() if self.age.currentData() is not None else 1)

    def populate(self, d):
        if "kernels" not in d:
            self.sec.fill(None)
            return
        md = self.min_days()
        es = [e for e in d.get("temp_entries", []) if e["age_days"] >= md]
        self.sec.fill([dict(key=e["path"], cells=["", e["path"], _("{d:.1f} dias").format(d=e["age_days"]),
                                                  fmt_size(e["size_bytes"])], right={2, 3}) for e in es],
                      {e["path"]: e["size_bytes"] for e in es},
                      _("{n} item(ns) — {s}").format(n=len(es), s=fmt_size(sum(e["size_bytes"] for e in es))),
                      _("Não há ficheiros temporários que cumpram este filtro."))

    def remove(self):
        sel = self.sec.selected()
        if sel and ask(self.win, _("Ficheiros temporários"), _("Remover os ficheiros temporários selecionados?"),
                       _("{n} item(ns) a remover.").format(n=len(sel))):
            self.win.run_root([("delete_paths", {"paths": sel})], _("A remover ficheiros temporários…"),
                              _("Ficheiros temporários removidos."), rescan="root")


# ============================================================================ REGISTOS
class LogsPage(BasePage):
    needs_root = True

    def __init__(self, win):
        super().__init__(win, "doc", _("Registos do sistema"),
                         _("Ficheiros de /var/log e o diário do sistema (journald)."))
        c = card()
        cl = QtWidgets.QHBoxLayout(c)
        cl.setContentsMargins(18, 14, 18, 14)
        self.j = label(_("Diário do sistema: —"), "h2")
        cl.addWidget(self.j, 1)
        self.b_size = button(_("Manter últimos 100 MB"))
        self.b_size.clicked.connect(lambda _c=False: self.vacuum("--vacuum-size=100M"))
        self.b_time = button(_("Manter últimas 2 semanas"))
        self.b_time.clicked.connect(lambda _c=False: self.vacuum("--vacuum-time=2weeks"))
        cl.addWidget(self.b_size)
        cl.addWidget(self.b_time)
        self.body.addWidget(c)
        self.sec = Section(win, ["", _("Nome"), _("Caminho"), _("Tamanho")], _("Remover selecionados"),
                           self.remove, stretch_col=2)
        self.body.addWidget(self.sec)
        self.b_size.setEnabled(False)
        self.b_time.setEnabled(False)

    def populate(self, d):
        if "kernels" not in d:
            self.sec.fill(None)
            return
        j = d.get("journald", {})
        self.j.setText(_("{s} usados pelo diário do sistema").format(s=fmt_size(j.get("size_bytes", 0))))
        self.b_size.setEnabled(True)
        self.b_time.setEnabled(True)
        es = d.get("log_entries", [])
        self.sec.fill([dict(key=e["path"], cells=["", e["name"], e["path"], fmt_size(e["size_bytes"])], right={3})
                       for e in es], {e["path"]: e["size_bytes"] for e in es},
                      _("{n} item(ns) — {s}").format(n=len(es), s=fmt_size(sum(e["size_bytes"] for e in es))),
                      _("Não foram encontrados ficheiros de registo."))

    def vacuum(self, flag):
        self.win.run_root([("vacuum_journal", {"flag": flag})], _("A limpar o diário do sistema…"),
                          _("Diário limpo."), rescan="root")

    def remove(self):
        sel = self.sec.selected()
        if sel and ask(self.win, _("Registos do sistema"), _("Remover os registos selecionados?"),
                       _("{n} item(ns) serão apagados definitivamente.").format(n=len(sel))):
            self.win.run_root([("delete_paths", {"paths": sel})], _("A remover registos…"), _("Registos removidos."),
                              rescan="root")


# ============================================================================ ACERCA
class AboutPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        lay = QtWidgets.QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo = QtWidgets.QLabel()
        logo.setPixmap(U.logo_pixmap(128))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        t = label(core.APP_NAME, "h1")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        for txt in (_("Versão {v}").format(v=core.VERSION), _("Autor: {a}").format(a=core.AUTHOR),
                    _("Limpeza do sistema: cache, lixo, Flatpak, kernels, drivers, firmwares,"),
                    _("idiomas, cache APT, ficheiros temporários e registos."),
                    _("Licença: GPL-3+")):
            l = label(txt, "muted")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(l)

    def on_theme(self):
        pass
