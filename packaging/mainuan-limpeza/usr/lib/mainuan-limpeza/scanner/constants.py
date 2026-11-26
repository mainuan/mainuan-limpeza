"""Constantes partilhadas pelos módulos de análise (GPL-3+)."""

# Famílias de firmware sempre protegidas, independentemente do hardware detetado.
PROTECTED_FIRMWARE_ALWAYS = [
    'regulatory.db',  # base de dados regulatória Wi-Fi: sempre necessária
]
PROTECTED_FIRMWARE_DIRS = PROTECTED_FIRMWARE_ALWAYS

FIRMWARE_PATH = '/lib/firmware'
APT_CACHE_PATH = '/var/cache/apt/archives'
TEMP_PATHS = ['/tmp', '/var/tmp']
