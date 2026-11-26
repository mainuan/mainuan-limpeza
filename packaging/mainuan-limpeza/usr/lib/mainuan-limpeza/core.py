#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""MAINUAN LIMPEZA - lógica partilhada: dados do sistema, análises e sessão com privilégios."""
import os
import sys
import json
import shutil
import threading
import subprocess
import configparser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import _  # noqa: E402

APP_NAME = "MAINUAN LIMPEZA"
APP_ID = "mainuan-limpeza"
VERSION = "1.0.1"
AUTHOR = "David Caixinha"
HELPER = "/usr/lib/mainuan-limpeza/helper.py"
if not os.path.exists(HELPER):  # execução a partir do código-fonte
    HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "helper.py")


def fmt_size(n):
    n = int(n or 0)
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.1f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def read(path, default=""):
    try:
        with open(path, "r", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return default


def run(cmd, timeout=15):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


# ------------------------------------------------------------------ tema
def system_is_dark():
    """True/False consoante o tema do sistema; None se não for possível saber."""
    desk = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    kde = os.path.expanduser("~/.config/kdeglobals")
    if "KDE" in desk or os.path.exists(kde):
        cp = configparser.ConfigParser(interpolation=None, strict=False, delimiters=("=",))
        cp.optionxform = str
        try:
            cp.read(kde, encoding="utf-8")
            r, g, b = [int(x) for x in cp["Colors:Window"]["BackgroundNormal"].split(",")[:3]]
            return (0.299 * r + 0.587 * g + 0.114 * b) < 128
        except (KeyError, ValueError, configparser.Error, OSError):
            pass
    if shutil.which("gsettings"):
        rc, out = run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"], timeout=2)
        if rc == 0 and "prefer-dark" in out:
            return True
        if rc == 0 and "prefer-light" in out:
            return False
        rc, out = run(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"], timeout=2)
        if rc == 0 and out:
            return "dark" in out.lower()
    return None


# ------------------------------------------------------- utilização do sistema
_HWMON_PRIORITY = ("k10temp", "coretemp", "nct6775", "it87", "acpitz")


def _hwmon_temp(path):
    vals = {}
    try:
        for fn in os.listdir(path):
            if fn.startswith("temp") and fn.endswith("_input"):
                try:
                    vals[fn[4:-6]] = int(read(os.path.join(path, fn))) / 1000.0
                except ValueError:
                    pass
    except OSError:
        return None
    if not vals:
        return None
    for idx in sorted(vals):
        lab = read(os.path.join(path, f"temp{idx}_label")).lower()
        if any(k in lab for k in ("tctl", "package", "core 0")):
            return vals[idx]
    return vals[sorted(vals)[0]]


def cpu_temp():
    """Temperatura do CPU em °C ou None."""
    base = "/sys/class/hwmon"
    names = {}
    try:
        for e in os.listdir(base):
            names.setdefault(read(os.path.join(base, e, "name")), []).append(os.path.join(base, e))
    except OSError:
        names = {}
    for drv in _HWMON_PRIORITY:
        for p in names.get(drv, []):
            t = _hwmon_temp(p)
            if t is not None:
                return t
    tz = "/sys/class/thermal"
    try:
        for e in sorted(os.listdir(tz)):
            if e.startswith("thermal_zone"):
                try:
                    return int(read(os.path.join(tz, e, "temp"))) / 1000.0
                except ValueError:
                    continue
    except OSError:
        pass
    return None


class Monitor:
    def __init__(self):
        self.prev = self._cpu()

    @staticmethod
    def _cpu():
        v = [int(x) for x in read("/proc/stat").splitlines()[0].split()[1:9]]
        return sum(v), v[3] + v[4]

    def snapshot(self):
        total, idle = self._cpu()
        pt, pi = self.prev
        self.prev = (total, idle)
        dt, di = total - pt, idle - pi
        cpu = max(0.0, min(100.0, 100.0 * (dt - di) / dt)) if dt > 0 else 0.0
        mem = {}
        for line in read("/proc/meminfo").splitlines():
            k, _s, v = line.partition(":")
            try:
                mem[k] = int(v.split()[0])
            except (ValueError, IndexError):
                pass
        tot = mem.get("MemTotal", 0)
        ram = 100.0 * (tot - mem.get("MemAvailable", 0)) / tot if tot else 0.0
        try:
            st = os.statvfs("/")
            dtot = st.f_blocks * st.f_frsize
            disk = 100.0 * (dtot - st.f_bavail * st.f_frsize) / dtot if dtot else 0.0
        except OSError:
            disk = 0.0
        return {"cpu": cpu, "ram": ram, "disk": disk, "temp": cpu_temp()}


# ------------------------------------------------------------- análise do utilizador
def scan_user(progress=None):
    """Análise sem privilégios: aplicações, Flatpak, cache do utilizador e lixo."""
    def step(msg, frac):
        if progress:
            progress(msg, frac)

    res = {}
    try:
        step(_("A analisar aplicações instaladas…"), 0.10)
        from scanner.installed_apps import get_installed_apps
        res["installed_apps"] = [dict(name=a.name, summary=a.summary, section=a.section,
                                      size_kb=a.size_kb, has_desktop=a.has_desktop)
                                 for a in get_installed_apps()]
        step(_("A analisar a cache do utilizador…"), 0.35)
        from scanner.user_cache import get_user_cache_entries
        res["user_cache"] = [dict(name=e.name, path=e.path, size_bytes=e.size_bytes)
                             for e in get_user_cache_entries()]
        step(_("A analisar o lixo…"), 0.55)
        from scanner.trash import get_trash_info
        t = get_trash_info()
        res["trash"] = dict(count=t.files_count, size_bytes=t.size_bytes, path=t.path)
        step(_("A analisar o Flatpak…"), 0.70)
        from scanner.flatpak import (flatpak_available, get_installed_flatpak_apps,
                                     get_unused_flatpak_entries)
        res["flatpak_available"] = flatpak_available()
        res["flatpak_apps"] = [dict(app_id=a.app_id, name=a.name, version=a.version,
                                    size_bytes=a.size_bytes) for a in get_installed_flatpak_apps()]
        res["flatpak_unused"] = [dict(ref=e.ref, name=e.name, size_bytes=e.size_bytes)
                                 for e in get_unused_flatpak_entries()]
        step(_("Análise concluída"), 1.0)
    except Exception as ex:  # noqa: BLE001
        res["error"] = str(ex)
    return res


# ------------------------------------------------------------- sessão com privilégios
class RootSession:
    """Processo helper persistente iniciado uma única vez com pkexec (uma só autenticação)."""

    def __init__(self):
        self.proc = None
        self.lock = threading.Lock()

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        """Devolve (True, '') ou (False, motivo)."""
        with self.lock:
            if self.alive():
                return True, ""
            # com pkexec o helper tem de ser o próprio executável autorizado pela política polkit
            cmd = [sys.executable, HELPER, "--session"] if os.geteuid() == 0 \
                else ["pkexec", HELPER, "--session"]
            try:
                self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.DEVNULL, text=True, bufsize=1,
                                             env=dict(os.environ, REAL_HOME=os.path.expanduser("~")))
            except OSError as e:
                self.proc = None
                return False, str(e)
            return True, ""

    def call(self, action, **params):
        """Envia um comando e espera a resposta (bloqueia; usar numa thread)."""
        ok, why = self.start()
        if not ok:
            return {"success": False, "error": why}
        with self.lock:
            try:
                self.proc.stdin.write(json.dumps(dict(params, action=action)) + "\n")
                self.proc.stdin.flush()
                line = self.proc.stdout.readline()
            except (OSError, ValueError) as e:
                self.proc = None
                return {"success": False, "error": str(e)}
            if not line:
                rc = self.proc.poll()
                self.proc = None
                if rc in (126, 127):
                    return {"success": False, "cancelled": True,
                            "error": _("Autenticação cancelada ou recusada.")}
                return {"success": False, "error": _("A sessão de administrador terminou.")}
            try:
                return json.loads(line)
            except ValueError:
                return {"success": False, "error": _("Resposta inválida do helper.")}

    def stop(self):
        p, self.proc = self.proc, None
        if p and p.poll() is None:
            try:
                p.stdin.write(json.dumps({"action": "exit"}) + "\n")
                p.stdin.flush()
                p.wait(timeout=3)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                try:
                    p.kill()
                except OSError:
                    pass
