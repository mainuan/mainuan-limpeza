#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""MAINUAN LIMPEZA - idiomas: pt-PT (origem), pt-BR, es, fr e en.
O idioma é detetado automaticamente a partir do sistema; qualquer outro idioma usa inglês."""
import os

SUPPORTED = ("pt-PT", "pt-BR", "es", "fr", "en")
_lang = "pt-PT"


def _from_code(code):
    c = code.replace("-", "_").split(".")[0].split("@")[0].lower()
    if c in ("pt_br",):
        return "pt-BR"
    if c.startswith("pt"):
        return "pt-PT"
    if c.startswith("es"):
        return "es"
    if c.startswith("fr"):
        return "fr"
    return "en"


def detect_lang(env=None):
    """Lê LANGUAGE, LC_ALL, LC_MESSAGES e LANG (por esta ordem); sem nada definido, usa inglês."""
    env = os.environ if env is None else env
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        for part in env.get(var, "").split(":"):
            if part and part not in ("C", "POSIX") and not part.startswith("C."):
                return _from_code(part)
    for f in ("/etc/default/locale", "/etc/locale.conf"):  # sem variáveis de ambiente (ex.: serviço)
        try:
            with open(f) as fh:
                for line in fh:
                    k, _s, v = line.strip().partition("=")
                    v = v.strip("\"'")
                    if k == "LANG" and v and v != "C" and not v.startswith("C."):
                        return _from_code(v)
        except OSError:
            pass
    return "en"


def set_lang(lang):
    global _lang
    _lang = lang if lang in SUPPORTED else "en"


def get_lang():
    return _lang


def _(s):
    if _lang == "pt-PT":
        return s
    from translations import T
    return T.get(_lang, {}).get(s, s)
