#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export DEBEMAIL="${DEBEMAIL:-$(git config user.email || true)}"
export DEBFULLNAME="${DEBFULLNAME:-$(git config user.name || true)}"

if [[ -z "$DEBEMAIL" || -z "$DEBFULLNAME" ]]; then
    echo "Configure Git avec git config user.name et user.email, ou fournis DEBFULLNAME et DEBEMAIL." >&2
    exit 1
fi

VERSION="$(PYTHONPATH=src python -c 'from open_fish_reader.version import APP_VERSION; print(APP_VERSION)')"
ARCH="$(dpkg --print-architecture)"
PACKAGE="open-fish-reader"
STAGE="$ROOT/build/deb/${PACKAGE}_${VERSION}_${ARCH}"
APPDIR="$STAGE/opt/open-fish-reader"
OUTDIR="$ROOT/deb_dist"

if [[ "$ARCH" != "amd64" ]]; then
    echo "Attention : construction pour l'architecture $ARCH."
fi

python -m pip install --upgrade 'pyinstaller>=6.15,<7'
python -m compileall src
ruff format --check .
ruff check .
pytest

rm -rf "$ROOT/build/linux" "$ROOT/dist/open-fish-reader" "$STAGE"
python -m PyInstaller \
    --noconfirm \
    --clean \
    --workpath "$ROOT/build/linux" \
    --distpath "$ROOT/dist" \
    "$ROOT/OpenFishReader-linux.spec"

install -d \
    "$APPDIR" \
    "$STAGE/usr/bin" \
    "$STAGE/usr/share/applications" \
    "$STAGE/usr/share/icons/hicolor/scalable/apps" \
    "$STAGE/usr/share/icons/hicolor/48x48/apps" \
    "$STAGE/usr/share/icons/hicolor/64x64/apps" \
    "$STAGE/usr/share/icons/hicolor/256x256/apps" \
    "$STAGE/usr/share/icons/hicolor/512x512/apps" \
    "$STAGE/usr/share/doc/$PACKAGE" \
    "$STAGE/DEBIAN" \
    "$OUTDIR"

cp -a "$ROOT/dist/open-fish-reader/." "$APPDIR/"
install -m 0755 "$ROOT/debian/open-fish-reader" "$STAGE/usr/bin/open-fish-reader"
install -m 0644 "$ROOT/debian/open-fish-reader.desktop" "$STAGE/usr/share/applications/open-fish-reader.desktop"
install -m 0644 "$ROOT/src/open_fish_reader/resources/icons/open_fish_reader.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/open-fish-reader.svg"
install -m 0644 "$ROOT/src/open_fish_reader/resources/icons/open_fish_reader_48.png" "$STAGE/usr/share/icons/hicolor/48x48/apps/open-fish-reader.png"
install -m 0644 "$ROOT/src/open_fish_reader/resources/icons/open_fish_reader_64.png" "$STAGE/usr/share/icons/hicolor/64x64/apps/open-fish-reader.png"
install -m 0644 "$ROOT/src/open_fish_reader/resources/icons/open_fish_reader_256.png" "$STAGE/usr/share/icons/hicolor/256x256/apps/open-fish-reader.png"
install -m 0644 "$ROOT/src/open_fish_reader/resources/icons/open_fish_reader_512.png" "$STAGE/usr/share/icons/hicolor/512x512/apps/open-fish-reader.png"
install -m 0644 "$ROOT/LICENSE" "$STAGE/usr/share/doc/$PACKAGE/copyright"

INSTALLED_SIZE="$(du -sk "$STAGE" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PACKAGE
Version: $VERSION
Section: science
Priority: optional
Architecture: $ARCH
Maintainer: $DEBFULLNAME <$DEBEMAIL>
Installed-Size: $INSTALLED_SIZE
Depends: libc6, libgl1, libegl1, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0
Description: Dépouillement vidéo et saisie des passages piscicoles
 Open Fish Reader permet de lire les vidéos de stations,
 enregistrer les passages, mesurer les poissons et exporter les données.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF

cat > "$STAGE/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 0755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"
find "$STAGE" -type d -exec chmod 0755 {} +

dpkg-deb --root-owner-group --build "$STAGE" "$OUTDIR/${PACKAGE}_${VERSION}_${ARCH}.deb"

echo
echo "Paquet créé : $OUTDIR/${PACKAGE}_${VERSION}_${ARCH}.deb"
echo "Contrôle : dpkg-deb --info '$OUTDIR/${PACKAGE}_${VERSION}_${ARCH}.deb'"
echo "Installation : sudo apt install ./$OUTDIR/${PACKAGE}_${VERSION}_${ARCH}.deb"
