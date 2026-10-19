#!/usr/bin/env bash
# Smorfia (formerly GeppEmoji) - build a Debian/Ubuntu/Mint/LMDE package.
#
# Why: a system-wide install in /usr/share/smorfia with a `smorfia` command
# and a menu entry. Only program files go in the package: user data lives in
# ~/.config/Smorfia, is created on first start, and is never touched by apt.
# The package replaces the old "geppemoji" package, if installed.
set -e

APP_NAME="smorfia"
VERSION="2.0.0-1"
PKG_NAME="${APP_NAME}_${VERSION}_all"

echo "=============================="
echo "  Building ${PKG_NAME}.deb"
echo "=============================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ROOT="${ROOT_DIR}/build_deb"
PKG_DIR="${BUILD_ROOT}/${PKG_NAME}"
APP_DIR="${PKG_DIR}/usr/share/${APP_NAME}"
BIN_DIR="${PKG_DIR}/usr/bin"
DESKTOP_DIR="${PKG_DIR}/usr/share/applications"
PIXMAP_DIR="${PKG_DIR}/usr/share/pixmaps"
DOC_DIR="${PKG_DIR}/usr/share/doc/${APP_NAME}"

rm -rf "${PKG_DIR}"
mkdir -p "${APP_DIR}/locales" "${BIN_DIR}" "${DESKTOP_DIR}" "${PIXMAP_DIR}" "${DOC_DIR}"

# --- Runtime files -----------------------------------------------------------
install -m 755 "${ROOT_DIR}/smorfia.py"              "${APP_DIR}/"
install -m 755 "${ROOT_DIR}/build_emoji_db.py"       "${APP_DIR}/"
install -m 644 "${ROOT_DIR}/smorfia.png"             "${APP_DIR}/"
install -m 644 "${ROOT_DIR}/emoji_data.json"         "${APP_DIR}/"
install -m 644 "${ROOT_DIR}/emoji_translations.json" "${APP_DIR}/"
install -m 644 "${ROOT_DIR}/README.md"               "${APP_DIR}/"
install -m 644 "${ROOT_DIR}"/locales/*.json          "${APP_DIR}/locales/"
install -m 644 "${ROOT_DIR}/smorfia.png"             "${PIXMAP_DIR}/smorfia.png"
install -m 644 "${ROOT_DIR}/LICENSE"                 "${DOC_DIR}/copyright"
install -m 644 "${ROOT_DIR}/CHANGELOG.md"            "${DOC_DIR}/"

# --- Command -----------------------------------------------------------------
cat > "${BIN_DIR}/${APP_NAME}" << 'EOF'
#!/usr/bin/env bash
exec /usr/bin/env python3 /usr/share/smorfia/smorfia.py "$@"
EOF
chmod 755 "${BIN_DIR}/${APP_NAME}"

# --- Menu entry --------------------------------------------------------------
cat > "${DESKTOP_DIR}/${APP_NAME}.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=Smorfia
GenericName=Emoji Picker
Comment=Desktop emoji picker with search in your language (formerly GeppEmoji)
Exec=smorfia
Icon=smorfia
Terminal=false
Categories=Utility;GTK;
Keywords=emoji;picker;smiley;GeppEmoji;
StartupNotify=false
EOF

# --- Package metadata --------------------------------------------------------
mkdir -p "${PKG_DIR}/DEBIAN"
INSTALLED_SIZE=$(du -sk "${PKG_DIR}/usr" | cut -f1)
cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Installed-Size: ${INSTALLED_SIZE}
Maintainer: Francesco Bianchi (FranzBias) <113999853+FranzBias@users.noreply.github.com>
Homepage: https://github.com/FranzBias/Smorfia
Depends: python3 (>= 3.10), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0
Recommends: xdotool
Conflicts: geppemoji
Replaces: geppemoji
Description: Smorfia - desktop emoji picker (formerly GeppEmoji)
 GTK 3 emoji picker with search in your language, your own tags,
 recents, favorites, skin tones and auto-paste into the previous window.
EOF

# Standard permissions, whatever the builder's umask
find "${PKG_DIR}" -type d -exec chmod 755 {} +
chmod 644 "${DESKTOP_DIR}/${APP_NAME}.desktop"

dpkg-deb --build --root-owner-group "${PKG_DIR}"

echo
echo "Done: ${BUILD_ROOT}/${PKG_NAME}.deb"
echo "Install it with:"
echo "  sudo apt install ./build_deb/${PKG_NAME}.deb"
