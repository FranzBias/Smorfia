# Changelog

All notable changes to **Smorfia** (formerly **GeppEmoji**) are documented here.
The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] – 2026-10-19 · *GeppEmoji becomes Smorfia* 🎭

### Changed
- **New name: Smorfia.** The program, the command, the package and the repository are renamed (GeppEmoji → Smorfia). Old GitHub links keep working through GitHub's redirect.
- **Categories in a sidebar.** The category drop-down is gone: All, Recent, Favorites and the Unicode groups now sit in a column on the left of the window, each with its own icon and a localized name.
- **Menu** label is now "☰ Menu".
- User data lives in `~/.config/Smorfia`. On first start Smorfia **copies** your data from `~/.config/GeppEmoji` (recents, favorites, custom tags, settings); the old folder is left untouched.
- `.deb` package renamed to `smorfia` (replaces the `geppemoji` package); command `smorfia`.
- App icon resized and compressed (4.2 MB → about 33 KB).

### Added
- **Richer tooltips:** hovering an emoji shows its name, **your own tags** and the English keywords from the Unicode database.
- Localized category names (Italian, German, English).
- One-time automatic migration from GeppEmoji.

### Fixed
- Fresh installs showed an **empty grid**: the emoji database is now copied to the user folder on first start, with a fallback to the shipped copy.
- **"Update Emoji database"** now works with the `.deb` install too: the database is rebuilt in the user folder instead of the read-only program folder, and the app reloads it.
- Skin tone is applied only to "People & Body" emoji (no more 🍔🏿).
- Choosing a skin tone from the menu refreshes the visible emoji immediately.
- Duplicate "Instructions" and "About" menu entries removed.
- First start on a clean system no longer crashes (missing legacy constants).
- The `.deb` now ships the `locales/` folder.

---

## [1.0.0] – 2025-12-05 · First public release 🎉 (as GeppEmoji)

### Added
- Emoji picker UI with category filtering and search by name or keyword
- Click-to-copy and optional auto-paste (via `xdotool`)
- Recents, favorites, custom keywords per language, skin-tone selector
- Linux Mint / LMDE / Debian compatibility
- Local install script and Debian package builder
- README in Italian and English, GitHub Pages site

---

### Legend
- **Added** = new features · **Changed** = changes in existing behaviour · **Fixed** = bug fixes · **Removed** = removed features
