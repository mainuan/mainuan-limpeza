#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""MAINUAN LIMPEZA - helper executado como root via pkexec.

Sessão persistente: lê um comando JSON por linha em stdin e responde com uma linha JSON em
stdout (uma única autenticação). Nada é executado através de shell; caminhos e nomes de
pacotes são validados antes de qualquer operação.

Licença: GPL-3+.
"""
import os
import re
import sys
import json
import glob
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# --------------------------------------------------------------------------- segurança
# Pastas cujo CONTEÚDO (filhos diretos ou mais fundo) pode ser apagado.
ALLOWED_UNDER = (
    "/tmp", "/var/tmp", "/var/log", "/var/cache/apt/archives",
    "/usr/share/locale", "/usr/share/help", "/usr/share/doc/HTML",
    "/usr/src", "/lib/modules", "/usr/lib/modules", "/lib/firmware", "/usr/lib/firmware",
)
# Pastas de documentação que podem ser apagadas por inteiro (listadas na análise).
ALLOWED_EXACT = (
    "/usr/share/man", "/usr/share/info", "/usr/share/doc", "/usr/share/qt5/doc",
    "/usr/share/qt6/doc", "/usr/share/gtk-doc", "/usr/share/cups/doc-root",
    "/usr/share/xml/docbook", "/usr/share/doc-base", "/usr/share/xfce4/helpers",
    "/usr/share/kf6/kdoctools", "/usr/share/devhelp",
)
NEVER_DELETE = ("/var/log/journal", "/var/log/apt", "/var/log/dpkg.log")
PKG_RE = re.compile(r"^[a-z0-9][a-z0-9+.\-]*(:[a-z0-9]+)?$")
NEVER_TOUCH_DRACUT_CONFS = {"i18n.conf", "local.conf"}


def path_allowed(path):
    """Só aceita caminhos absolutos dentro das zonas permitidas (sem seguir o último link)."""
    if not isinstance(path, str) or not os.path.isabs(path) or "\0" in path:
        return False
    parent, name = os.path.split(os.path.normpath(path))
    real = os.path.join(os.path.realpath(parent), name)
    if real in NEVER_DELETE:
        return False
    if real in ALLOWED_EXACT:
        return True
    return any(real.startswith(base + "/") for base in ALLOWED_UNDER)


def remove_path(path):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def delete_paths_checked(paths):
    errors = []
    for p in paths if isinstance(paths, list) else []:
        if not path_allowed(p):
            errors.append("caminho não permitido: %s" % p)
            continue
        try:
            remove_path(p)
        except FileNotFoundError:
            pass
        except OSError as e:
            errors.append("%s: %s" % (p, e.strerror or e))
    return errors


def valid_pkgs(pkgs):
    if not isinstance(pkgs, list) or not pkgs:
        return None
    out = []
    for p in pkgs:
        if not isinstance(p, str) or not PKG_RE.match(p):
            return None
        out.append(p)
    return out


def run(cmd, timeout=1800, env_extra=None):
    env = dict(os.environ, LC_ALL="C", DEBIAN_FRONTEND="noninteractive")
    if env_extra:
        env.update(env_extra)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, ((p.stderr or "") + (p.stdout or "")).strip()[-1500:]


def result(errors):
    errors = [e for e in errors if e]
    return {"success": not errors, "error": " | ".join(errors) or None}


def rebuild_initramfs():
    """Ubuntu/Debian: update-initramfs; sistemas com dracut: dracut -f."""
    if shutil.which("update-initramfs"):
        rc, out = run(["update-initramfs", "-u", "-k", "all"])
    elif shutil.which("dracut"):
        rc, out = run(["dracut", "-f", "--regenerate-all"])
    else:
        return ""
    return "" if rc == 0 else "initramfs: " + out


def update_grub():
    if shutil.which("update-grub"):
        rc, out = run(["update-grub"])
        return "" if rc == 0 else "update-grub: " + out
    return ""


# --------------------------------------------------------------------------- análise
def do_scan(_p):
    r = {}
    try:
        from scanner.hardware import (
            get_all_hardware, get_firmware_protection_set, get_all_firmware_families,
            get_firmware_sizes, get_unnecessary_hardware_packages, get_firmware_owning_packages,
            get_orphan_dkms_modules, is_firmware_dir_protected)
        hw = get_all_hardware()
        families = get_all_firmware_families()
        sizes = get_firmware_sizes(families)
        owning = get_firmware_owning_packages(families)
        prot = frozenset(get_firmware_protection_set(hw))
        r["firmware"] = [{"name": f, "protected": bool(is_firmware_dir_protected(f, prot)),
                          "size_kb": sizes.get(f, 0), "pkg": owning.get(f) or ""}
                         for f in families]
        r["unnecessary_pkgs"] = get_unnecessary_hardware_packages(
            hw["pci_vendors"], hw["usb_vendors"], hw["kvm_present"],
            gpu_pci_vendors=hw["gpu_pci_vendors"], vm_guest_type=hw.get("vm_guest_type", "none"))
        r["orphan_dkms"] = get_orphan_dkms_modules()
        vm = hw.get("vm_guest_type", "none")
        labels = {"kvm": "KVM/QEMU (guest)", "qemu": "QEMU (guest)", "vmware": "VMware (guest)",
                  "oracle": "VirtualBox (guest)", "microsoft": "Hyper-V (guest)",
                  "xen": "Xen (guest)", "parallels": "Parallels (guest)", "bhyve": "bhyve (guest)"}
        summary = list(hw["gpu_vendors_named"])
        if hw["kvm_present"]:
            summary.append("KVM host")
        if vm in labels and labels[vm] not in summary:
            summary.append(labels[vm])
        r["hardware_summary"] = summary
        r["vm_guest_type"] = vm
    except Exception as e:  # noqa: BLE001
        print("[helper] hardware:", e, file=sys.stderr)
        r.update(firmware=[], unnecessary_pkgs=[], orphan_dkms=[], hardware_summary=[],
                 vm_guest_type="none")

    try:
        from scanner.kernels import get_installed_kernels
        r["kernels"] = [{
            "version": k.version, "is_active": k.is_active, "has_headers": k.has_headers,
            "has_src": k.has_src, "has_kbuild": k.has_kbuild, "image_pkg": k.image_pkg,
            "headers_pkg": k.headers_pkg, "src_pkg": k.src_pkg, "kbuild_pkg": k.kbuild_pkg,
            "metapackage": k.metapackage, "size_kb": k.size_kb,
            "orphan_src_dirs": k.orphan_src_dirs, "orphan_modules_dirs": k.orphan_modules_dirs}
            for k in get_installed_kernels()]
    except Exception as e:  # noqa: BLE001
        print("[helper] kernels:", e, file=sys.stderr)
        r["kernels"] = []

    try:
        from scanner.cache import (get_apt_cache_info, get_apt_cache_debs,
                                   get_autoremove_packages, get_orphan_module_refs)
        r["apt_cache"] = get_apt_cache_info()
        r["apt_cache_debs"] = get_apt_cache_debs()
        r["autoremove_pkgs"] = get_autoremove_packages()
        r["orphan_module_refs"] = get_orphan_module_refs(vm_guest_type=r.get("vm_guest_type", "none"))
    except Exception as e:  # noqa: BLE001
        print("[helper] apt:", e, file=sys.stderr)
        r.update(apt_cache={}, apt_cache_debs=[], autoremove_pkgs=[], orphan_module_refs=[])

    try:
        from scanner.temp_files import get_temp_entries
        r["temp_entries"] = [{"path": e.path, "size_bytes": e.size_bytes, "age_days": e.age_days,
                              "is_dir": e.is_dir} for e in get_temp_entries(min_age_days=0.0)]
    except Exception as e:  # noqa: BLE001
        print("[helper] temp:", e, file=sys.stderr)
        r["temp_entries"] = []

    try:
        from scanner.locales import get_locales_info, get_docs_summary
        desk = os.environ.get("XDG_CURRENT_DESKTOP", "unknown").lower()
        r["locales"] = [{"code": l.code, "name": l.name, "paths": list(l.paths),
                         "size_kb": l.size_kb, "category": l.category}
                        for l in get_locales_info(desk)]
        r["docs"] = [{"name": d.name, "path": d.path, "size_kb": d.size_kb, "type": d.type}
                     for d in get_docs_summary()]
    except Exception as e:  # noqa: BLE001
        print("[helper] locales:", e, file=sys.stderr)
        r.update(locales=[], docs=[])

    try:
        from scanner.logs import get_varlog_entries, get_journald_info
        r["log_entries"] = [{"name": e.name, "path": e.path, "size_bytes": e.size_bytes}
                            for e in get_varlog_entries()]
        j = get_journald_info()
        r["journald"] = {"size_bytes": j.size_bytes, "disk_usage_str": j.disk_usage_str}
    except Exception as e:  # noqa: BLE001
        print("[helper] logs:", e, file=sys.stderr)
        r.update(log_entries=[], journald={"size_bytes": 0, "disk_usage_str": ""})
    return r


# --------------------------------------------------------------------------- ações
def do_delete_paths(p):
    return result(delete_paths_checked(p.get("paths", [])))


def do_apt_clean(_p):
    rc, out = run(["apt-get", "clean"])
    return result([] if rc == 0 else [out])


def do_apt_autoremove(_p):
    rc, out = run(["apt-get", "autoremove", "-y"])
    return result([] if rc == 0 else [out])


def do_apt_remove(p):
    pkgs = valid_pkgs(p.get("packages"))
    if not pkgs:
        return result(["lista de pacotes inválida"])
    rc, out = run(["apt-get", "remove", "-y"] + pkgs)
    return result([] if rc == 0 else [out])


def do_apt_purge(p):
    pkgs = valid_pkgs(p.get("packages"))
    if not pkgs:
        return result(["lista de pacotes inválida"])
    errors = []
    rc, out = run(["apt-get", "purge", "-y"] + pkgs)
    if rc != 0:
        return result([out])
    if p.get("autoremove", True):
        rc, out = run(["apt-get", "autoremove", "-y"])
        if rc != 0:
            errors.append(out)
    if p.get("rebuild_initrd"):
        errors.append(rebuild_initramfs())
        _cleanup_module_references(pkgs)
    if p.get("update_bootloader"):
        errors.append(update_grub())
    return result(errors)


def _remove_module_entries(modules):
    if not modules:
        return

    def clean(path):
        try:
            with open(path) as f:
                lines = f.readlines()
            kept = [l for l in lines if l.strip().lstrip("#").strip() not in modules]
            if len(kept) == len(lines):
                return
            if not [l for l in kept if l.strip() and not l.strip().startswith("#")]:
                os.remove(path)
            else:
                with open(path, "w") as f:
                    f.writelines(kept)
        except OSError:
            pass

    if os.path.isfile("/etc/modules"):
        clean("/etc/modules")
    if os.path.isdir("/etc/modules-load.d"):
        for fn in os.listdir("/etc/modules-load.d"):
            clean(os.path.join("/etc/modules-load.d", fn))


def _cleanup_module_references(pkgs):
    try:
        from scanner.hardware import PKG_MODULES
    except Exception:  # noqa: BLE001
        return
    mods = set()
    for p in pkgs:
        mods.update(PKG_MODULES.get(p, []))
    _remove_module_entries(mods)


def do_vacuum_journal(p):
    flag = p.get("flag", "--vacuum-size=100M")
    if not re.match(r"^--vacuum-(size=\d+[KMG]|time=\d+(s|m|h|days|weeks|months|years|d|w))$", str(flag)):
        return result(["opção inválida"])
    rc, out = run(["journalctl", flag])
    return result([] if rc == 0 else [out])


def do_delete_locales(p):
    errors = delete_paths_checked(p.get("paths", []))
    keep = [c for c in p.get("keep_codes", []) if isinstance(c, str) and re.match(r"^[A-Za-z0-9_.@\-]+$", c)]
    if keep and p.get("persist"):
        if not shutil.which("localepurge"):
            rc, out = run(["apt-get", "install", "-y", "localepurge"])
            if rc != 0:
                errors.append(out)
        conf = ("# Gerado por MAINUAN LIMPEZA\nNEEDSCONFIGUPDATE=0\nVERBOSE=0\n"
                "SHOWFREEDSPACE=1\nDONTBOTHERNEWLOCALE\n" + "".join(c + "\n" for c in sorted(set(keep))))
        try:
            with open("/etc/locale.nopurge", "w") as f:
                f.write(conf)
            lp = shutil.which("localepurge") or ("/usr/sbin/localepurge" if os.path.exists("/usr/sbin/localepurge") else None)
            if lp:
                run([lp])
        except OSError as e:
            errors.append(str(e))
    return result(errors)


def do_remove_firmware(p):
    families = [f for f in p.get("families", []) if isinstance(f, str) and re.match(r"^[A-Za-z0-9_.\-]+$", f)]
    if not families:
        return result(["sem famílias válidas"])
    errors = []
    try:
        from scanner.hardware import PCI_VENDOR_FIRMWARE, PCI_VENDOR_PACKAGES
    except Exception:  # noqa: BLE001
        PCI_VENDOR_FIRMWARE, PCI_VENDOR_PACKAGES = {}, {}

    # Pacote de firmware dedicado a cada família (pacotes genéricos nunca são removidos)
    FIRMWARE_PACKAGES = {
        "amdgpu": "firmware-amd-graphics", "radeon": "firmware-amd-graphics",
        "i915": "firmware-intel-graphics", "iwlwifi": "firmware-iwlwifi", "intel": "firmware-intel-sound",
        "rtlwifi": "firmware-realtek", "rtw88": "firmware-realtek", "rtw89": "firmware-realtek",
        "rtl_bt": "firmware-realtek", "rtl_nic": "firmware-realtek", "brcm": "firmware-brcm80211",
        "ath10k": "firmware-atheros", "ath11k": "firmware-atheros", "ath12k": "firmware-atheros",
        "qca": "firmware-atheros", "mediatek": "firmware-mediatek", "mt76": "firmware-mediatek",
        "libertas": "firmware-libertas", "mwl8k": "firmware-libertas", "mwifiex": "firmware-libertas",
        "nvidia": "firmware-nvidia-graphics",
    }
    GENERIC = {"firmware-linux-nonfree", "firmware-misc-nonfree", "firmware-linux", "firmware-linux-free",
               "linux-firmware"}
    fam_vendor = {}
    for vid, fams in PCI_VENDOR_FIRMWARE.items():
        for fam in fams:
            fam_vendor[fam] = vid
    driver_pkgs = {fam: PCI_VENDOR_PACKAGES[vid] for fam, vid in fam_vendor.items() if vid in PCI_VENDOR_PACKAGES}
    pkg_all = {}
    for fam, pkg in FIRMWARE_PACKAGES.items():
        if pkg not in GENERIC:
            pkg_all.setdefault(pkg, set()).add(fam)
    for fam, pkgs in driver_pkgs.items():
        for pkg in pkgs:
            pkg_all.setdefault(pkg, set()).add(fam)

    def installed(pkg):
        rc, out = run(["dpkg-query", "-W", "-f=${Status}", pkg], timeout=10)
        return rc == 0 and "install ok installed" in out

    selected = set(families)
    cands = set()
    for fam in selected:
        fp = FIRMWARE_PACKAGES.get(fam)
        if fp and fp not in GENERIC:
            cands.add(fp)
        cands.update(driver_pkgs.get(fam, []))
    for pkg in sorted(cands):
        if not installed(pkg):
            continue
        owned = {f for f in pkg_all.get(pkg, set()) if os.path.isdir("/lib/firmware/" + f)}
        if owned and owned.issubset(selected):
            rc, out = run(["apt-get", "purge", "-y", pkg])
            if rc != 0:
                errors.append("apt purge %s: %s" % (pkg, out))
    for fam in sorted(selected):
        path = "/lib/firmware/" + fam
        if path_allowed(path) and os.path.isdir(path) and not os.path.islink(path):
            try:
                shutil.rmtree(path)
            except OSError as e:
                errors.append(str(e))
    errors.append(rebuild_initramfs())
    return result(errors)


def do_clean_module_refs(p):
    refs = [r for r in p.get("refs", []) if isinstance(r, dict)]
    errors = []
    modules = {r["module"] for r in refs if r.get("type") in ("modules-load", "modprobe") and isinstance(r.get("module"), str)}
    _remove_module_entries(modules)
    for r in refs:
        path, kind = r.get("path", ""), r.get("type")
        if kind == "modprobe" and path.startswith("/etc/modprobe.d/"):
            try:
                os.remove(path)
            except OSError:
                pass
        elif kind == "systemd" and re.match(r"^[A-Za-z0-9@_.\-]+\.service$", str(r.get("module", ""))) \
                and path.startswith(("/etc/systemd/", "/lib/systemd/", "/usr/lib/systemd/")):
            run(["systemctl", "disable", "--now", r["module"]], timeout=60)
            try:
                os.remove(path)
            except OSError:
                pass
        elif kind == "autostart" and path.startswith(("/etc/xdg/autostart/", "/etc/X11/Xsession.d/")):
            try:
                os.remove(path)
            except OSError:
                pass
        elif kind == "dracut" and path.startswith("/etc/dracut.conf.d/") \
                and os.path.basename(path) not in NEVER_TOUCH_DRACUT_CONFS:
            try:
                os.remove(path)
            except OSError:
                pass
    if any(r.get("type") == "systemd" for r in refs):
        run(["systemctl", "daemon-reload"], timeout=60)
    errors.append(rebuild_initramfs())
    return result(errors)


def do_remove_dkms_orphans(p):
    errors = []
    for o in p.get("orphans", []):
        if not isinstance(o, dict):
            continue
        name, ver, ddir = str(o.get("name", "")), str(o.get("version", "")), str(o.get("dkms_dir", ""))
        if not re.match(r"^[A-Za-z0-9_.+\-]+$", name) or not re.match(r"^[A-Za-z0-9_.+\-~:]+$", ver):
            continue
        rc, _out = run(["dkms", "remove", "%s/%s" % (name, ver), "--all"], timeout=600)
        base = os.path.join("/var/lib/dkms", name)
        if rc != 0 and os.path.isdir(os.path.join(base, ver)) and ddir.startswith("/var/lib/dkms/"):
            try:
                shutil.rmtree(os.path.join(base, ver))
            except OSError as e:
                errors.append(str(e))
    run(["depmod", "-a"], timeout=300)
    errors.append(rebuild_initramfs())
    return result(errors)


HANDLERS = {
    "scan": do_scan,
    "delete_paths": do_delete_paths,
    "delete_docs": do_delete_paths,
    "delete_orphan_dirs": do_delete_paths,
    "apt_clean": do_apt_clean,
    "apt_autoremove": do_apt_autoremove,
    "apt_remove": do_apt_remove,
    "apt_purge": do_apt_purge,
    "vacuum_journal": do_vacuum_journal,
    "delete_locales": do_delete_locales,
    "remove_firmware": do_remove_firmware,
    "clean_module_refs": do_clean_module_refs,
    "remove_dkms_orphans": do_remove_dkms_orphans,
}


def main():
    if os.geteuid() != 0:
        print("O helper tem de ser executado como administrador.", file=sys.stderr)
        return 1
    if "--session" not in sys.argv:
        print("uso: helper.py --session", file=sys.stderr)
        return 2
    real_out = sys.stdout
    sys.stdout = sys.stderr  # nada de módulos de análise pode poluir o canal de respostas
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
            action = cmd.get("action")
            if action == "exit":
                break
            handler = HANDLERS.get(action)
            res = handler(cmd) if handler else {"success": False, "error": "ação desconhecida: %s" % action}
        except Exception as e:  # noqa: BLE001
            res = {"success": False, "error": str(e)}
        real_out.write(json.dumps(res) + "\n")
        real_out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
