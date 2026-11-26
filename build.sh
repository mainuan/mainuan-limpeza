#!/bin/sh
# Constrói o pacote DEB em dist/. Requer: dpkg-deb (pacote dpkg).
set -e
cd "$(dirname "$0")"
SRC=packaging/mainuan-limpeza
VERSION=$(sed -n 's/^Version: //p' "$SRC/DEBIAN/control")
find "$SRC" -name __pycache__ -type d -prune -exec rm -rf {} +
chmod 755 "$SRC/DEBIAN/postinst" "$SRC/DEBIAN/postrm" "$SRC/usr/bin/mainuan-limpeza" \
          "$SRC/usr/lib/mainuan-limpeza/app.py" "$SRC/usr/lib/mainuan-limpeza/helper.py"
mkdir -p dist
dpkg-deb --root-owner-group -Zxz --build "$SRC" "dist/mainuan-limpeza_${VERSION}_all.deb"
echo "Criado: dist/mainuan-limpeza_${VERSION}_all.deb"
