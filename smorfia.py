#!/usr/bin/env python3

######################################################
######################################################
##                     Smorfia                      ##
##           A small desktop emoji picker           ##
##             written in Python + GTK3             ##
##                                                  ##
##       by FranzBias 2025-2026 (ex GeppEmoji)      ##
##           https://github.com/FranzBias           ##
######################################################
######################################################
##          Licensed under the MIT License.         ##
##        See LICENSE file for full license.        ##
######################################################
######################################################

import json
import locale
import logging
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject

logger = logging.getLogger(__name__)


def detect_auto_paste_support():
    """
    Detect whether auto-paste via xdotool is usable in the current session.

    Returns a dict like:
        {
            "session_type": "x11" | "wayland" | "unknown",
            "has_xdotool": bool,
            "auto_paste_available": bool,
        }
    """
    session_type_raw = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()

    if session_type_raw in ("x11", "xorg"):
        session_type = "x11"
    elif session_type_raw == "wayland":
        session_type = "wayland"
    else:
        session_type = "unknown"

    has_xdotool = shutil.which("xdotool") is not None

    # Auto-paste only makes sense on X11 when xdotool is available
    auto_paste_available = (session_type == "x11") and has_xdotool

    logger.debug(
        "Auto-paste env: session_type=%s raw=%r has_xdotool=%s auto_paste_available=%s",
        session_type,
        session_type_raw,
        has_xdotool,
        auto_paste_available,
    )

    return {
        "session_type": session_type,
        "has_xdotool": has_xdotool,
        "auto_paste_available": auto_paste_available,
    }


APP_NAME = "Smorfia"


# -----------------------------------------------------------------------------
# Versioning
# -----------------------------------------------------------------------------
APP_VERSION = "2.0.0"
BUILD = "2026-10-19a"

# Base directory where the app code and default data live (/usr/share/smorfia)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Legacy system-level files (older versions in /usr/share/smorfia)
SYSTEM_CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LEGACY_RECENT_FILE = os.path.join(BASE_DIR, "emoji_recent.json")
LEGACY_FAVORITES_FILE = os.path.join(BASE_DIR, "emoji_favorites.json")

# User-specific configuration and data directories
USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", APP_NAME)
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

# Extra user paths: templates + local README
USER_TEMPLATES_DIR = os.path.join(USER_CONFIG_DIR, "templates")
USER_README_FILE = os.path.join(USER_CONFIG_DIR, "README.md")

# Emoji database: per-user in ~/.config/Smorfia
EMOJI_FILE = os.path.join(USER_CONFIG_DIR, "emoji_data.json")

# emoji_translations.json now lives in the user config directory
TRANSLATIONS_FILE = os.path.join(USER_CONFIG_DIR, "emoji_translations.json")

# Legacy user-data locations (older versions used ~/.local/share/Smorfia)
LEGACY_USER_RECENT_FILE = os.path.join(USER_DATA_DIR, "emoji_recent.json")
LEGACY_USER_FAVORITES_FILE = os.path.join(USER_DATA_DIR, "emoji_favorites.json")

# New user-level paths (final: all in ~/.config/Smorfia)
CONFIG_FILE = os.path.join(USER_CONFIG_DIR, "config.json")
RECENT_FILE = os.path.join(USER_CONFIG_DIR, "emoji_recent.json")
FAVORITES_FILE = os.path.join(USER_CONFIG_DIR, "emoji_favorites.json")

# Pre-2.0 name of the app: user data is migrated from here on first start
LEGACY_APP_NAME = "GeppEmoji"
LEGACY_APP_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", LEGACY_APP_NAME)

# Locales and public URL for the official emoji-test.txt file
LOCALES_DIR = os.path.join(BASE_DIR, "locales")
EMOJI_TEST_URL = "https://unicode.org/Public/emoji/latest/emoji-test.txt"

DEFAULT_CONFIG = {
    "theme": "system",          # "system", "light", "dark"
    "columns": 10,
    "max_recent": 40,
    "emoji_font_size": 28,
    "language": "system",       # "system" or "en"/"it"/"de"/...
    "debug": False,
    "remember_window": True,    # remember window size/position between runs

    # Window geometry (nullable: None → no stored geometry yet)
    "window_width": 460,
    "window_height": 580,
    "window_x": None,
    "window_y": None,
}

# Skin tone modifiers (empty = default)
SKIN_TONES = [
    "",                         # 0 = default (no modifier)
    "\U0001F3FB",               # 1 = light
    "\U0001F3FC",               # 2 = medium-light
    "\U0001F3FD",               # 3 = medium
    "\U0001F3FE",               # 4 = medium-dark
    "\U0001F3FF",               # 5 = dark
]

# For preview buttons (hand with different tones)
SKIN_TONE_PREVIEWS = [
    "🖐",      # default
    "🖐🏻",
    "🖐🏼",
    "🖐🏽",
    "🖐🏾",
    "🖐🏿",
]

# ---------------------------------------------------------------------
# Default English UI strings (fallback if no locale file is found)
# ---------------------------------------------------------------------

DEFAULT_I18N = {
    "menu.root": "Menu",
    "menu.instructions": "Instructions",
    "menu.shortcuts": "Shortcuts",
    "menu.about": "About",
    "menu.update_db": "Update Emoji database",
    "menu.preferences": "Preferences",
    "menu.skin_tone": "Skin tone...",

    "category.all": "All",
    "category.recent": "Recent",
    "category.favorites": "Favorites",
    "category.smileys_emotion": "Smileys & Emotion",
    "category.people_body": "People & Body",
    "category.animals_nature": "Animals & Nature",
    "category.food_drink": "Food & Drink",
    "category.travel_places": "Travel & Places",
    "category.activities": "Activities",
    "category.objects": "Objects",
    "category.symbols": "Symbols",
    "category.flags": "Flags",
    "category.component": "Components",
    "category.other": "Other",

    "tooltip.my_tags": "My tags",
    "tooltip.keywords_en": "Keywords",

    "search.placeholder": "Search emoji...",

    "instructions.title": "Instructions",
    "instructions.body": (
        "How to use Smorfia:\n\n"
        "- On startup it shows the 'Recent' category and focuses the search entry.\n"
        "- Choose a category or use 'Recent' to see your last used emoji.\n"
        "- Type in the search box to filter emoji by name or keyword.\n\n"
        "Mouse / Keyboard:\n"
        "- Left click or Enter: insert the emoji (or accumulated emoji) and close.\n"
        "- Shift + left click, right click or Shift + Enter: add the emoji to the buffer without closing.\n"
        "- Middle click or Shift + T: edit custom keywords for the selected emoji.\n"
        "- Ctrl + F: toggle favorite for the selected emoji.\n"
        "- Esc: close the window without doing anything."
    ),

    "shortcuts.title": "Shortcuts",
    "shortcuts.body": (
        "Keyboard and mouse shortcuts in Smorfia:\n\n"
        "- Arrow keys: move between emoji.\n"
        "- Enter: insert and paste the current emoji (plus any emoji already in the buffer).\n"
        "- Shift + Enter: add to buffer, do not paste.\n"
        "- Left click: insert and paste.\n"
        "- Shift + left click: add to buffer, do not paste.\n"
        "- Right click: add to buffer, do not paste.\n"
        "- Middle click: open the keyword editor for that emoji.\n"
        "- Shift + T: open the keyword editor for the selected emoji.\n"
        "- Ctrl + F: toggle favorite for the selected emoji.\n"
        "- Esc: close the window."
    ),

    "about.title": "About",
    "about.body": (
        "{app_name}\n\n"
        "Emoji picker with localized search, categories, favorites and recents.\n\n"
        "Developed by Francesco Bianchi with the help of Geppetto AI."
    ),

    "update.title": "Update Emoji database",
    "update.button.run": "Run import",
    "update.heading": "How to update the Emoji database",
    "update.step1": "1. Open the following link in your browser and save the file:",
    "update.step2": (
        "2. Save the file as <b>emoji-test.txt</b> into the application folder:\n"
        "<tt>{base_dir}</tt>\n\n"
        "3. After copying the file into the correct folder,\n"
        "   press the button below to start the import process\n"
        "   for the new Emoji into the app database."
    ),
    "update.error.title": "Update error",
    "update.error.body": "Error while running build_emoji_db.py:\n{error}",
    "update.success.title": "Updated",
    "update.success.body": (
        "Emoji database updated successfully.\n\n"
        "New emoji should now be visible in the app."
    ),

    "editor.title": "Edit emoji keywords",
    "editor.search_label": "Search key for emoji: {emoji}",
    "editor.desc": "Add your own search keywords here, separated by a comma \",\"",
    "editor.defaults_title": "Default keywords for {emoji} are:",
    "editor.defaults.none": "(none)",

    "msg.error.xdotool_activate": "Error using xdotool (windowactivate): {error}",
    "msg.error.xdotool_key": "Error using xdotool (key ctrl+v): {error}",
    "msg.info.clipboard_only": (
        "Auto-paste is not available in this session. "
        "Emoji have been copied to the clipboard; use Ctrl+V to paste."
    ),

    # Preferences / config
    "prefs.title": "Preferences",
    "prefs.theme": "Theme",
    "prefs.theme.system": "System",
    "prefs.theme.light": "Light",
    "prefs.theme.dark": "Dark",
    "prefs.columns": "Columns",
    "prefs.max_recent": "Max recent emoji",
    "prefs.font_size": "Emoji font size",
    "prefs.language": "Language",
    "prefs.language.system": "System default",
    "prefs.remember_window": "Remember window size and position",
    "prefs.debug": "Enable debug log (also richer tooltips)",
    "prefs.open_translations": "Open emoji_translations.json",
    "prefs.open_config": "Open config.json",
    "prefs.backup": "Create backup...",
    "prefs.restore": "Restore backup...",

    "prefs.backup_done_title": "Backup created",
    "prefs.backup_done_body": "Backup saved as:\n{path}",
    "prefs.backup_error_title": "Backup error",
    "prefs.backup_error_body": "Error during backup:\n{error}",
    "prefs.restore_done_title": "Backup restored",
    "prefs.restore_done_body": "Backup restored.\nYou may need to restart Smorfia.",
    "prefs.restore_error_title": "Restore error",
    "prefs.restore_error_body": "Error during restore:\n{error}",
    "prefs.language_changed_title": "Language changed",
    "prefs.language_changed_body": "Language will be applied next time you start Smorfia.",

    # Status bar
    "status.results": "{count} emoji shown",
    "status.buffer": "Buffer: {buf}",
    "status.autopaste.enabled": "Auto-paste: enabled",
    "status.autopaste.clipboard_only": "Auto-paste: clipboard only (use Ctrl+V)",
    "status.autopaste.disabled": "Auto-paste: disabled",

    # Skin tone bar
    "skin.label": "Skin tone:",
    "skin.dialog.title": "Choose default skin tone",
}

def make_user_files_writable():
    """Add the owner's write permission to every file in USER_CONFIG_DIR."""
    try:
        for root, _dirs, files in os.walk(USER_CONFIG_DIR):
            for name in files:
                path = os.path.join(root, name)
                mode = os.stat(path).st_mode
                if not mode & 0o200:
                    os.chmod(path, mode | 0o200)
    except Exception as e:
        print(f"[Smorfia] Could not fix permissions in {USER_CONFIG_DIR}: {e}", file=sys.stderr)


def initialize_user_environment():
    """
    Ensure that ~/.config/Smorfia contains all the user files:

    - config.json
    - emoji_translations.json
    - emoji_recent.json
    - emoji_favorites.json
    - README.md
    - templates/ (directory)

    and migrate any legacy files from BASE_DIR or ~/.local/share/Smorfia.
    """
    # 0) One-time migration from the old name (GeppEmoji -> Smorfia):
    #    copy ~/.config/GeppEmoji to ~/.config/Smorfia, never move or delete it.
    try:
        if not os.path.exists(USER_CONFIG_DIR) and os.path.isdir(LEGACY_APP_CONFIG_DIR):
            shutil.copytree(LEGACY_APP_CONFIG_DIR, USER_CONFIG_DIR)
            print(f"[Smorfia] Migrated user data from {LEGACY_APP_CONFIG_DIR}", file=sys.stderr)
    except Exception as e:
        print(f"[Smorfia] Migration from {LEGACY_APP_CONFIG_DIR} failed: {e}", file=sys.stderr)

    # Ensure config dir exists
    try:
        os.makedirs(USER_CONFIG_DIR, exist_ok=True)
    except Exception:
        pass

    # 0b) Seed the per-user emoji database from the shipped copy (first run)
    try:
        shipped_db = os.path.join(BASE_DIR, "emoji_data.json")
        if not os.path.exists(EMOJI_FILE) and os.path.exists(shipped_db):
            shutil.copyfile(shipped_db, EMOJI_FILE)
    except Exception as e:
        print(f"[Smorfia] Could not copy emoji_data.json: {e}", file=sys.stderr)

    # 0c) User files must stay writable even if they were copied from a
    #     read-only system folder (e.g. /usr/share/smorfia with the .deb)
    make_user_files_writable()

    # 1) Migrate legacy recent/favorites from old user-data dir to new config dir
    try:
        if os.path.exists(LEGACY_USER_RECENT_FILE) and not os.path.exists(RECENT_FILE):
            os.makedirs(os.path.dirname(RECENT_FILE), exist_ok=True)
            shutil.move(LEGACY_USER_RECENT_FILE, RECENT_FILE)
    except Exception:
        pass

    try:
        if os.path.exists(LEGACY_USER_FAVORITES_FILE) and not os.path.exists(FAVORITES_FILE):
            os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
            shutil.move(LEGACY_USER_FAVORITES_FILE, FAVORITES_FILE)
    except Exception:
        pass

    # 2) Migrate legacy emoji_translations.json from BASE_DIR to user config
    try:
        legacy_translations = os.path.join(BASE_DIR, "emoji_translations.json")
        if os.path.exists(legacy_translations) and not os.path.exists(TRANSLATIONS_FILE):
            os.makedirs(os.path.dirname(TRANSLATIONS_FILE), exist_ok=True)
            shutil.copy2(legacy_translations, TRANSLATIONS_FILE)
    except Exception:
        pass

    # 3) Ensure config.json exists (if not, create from DEFAULT_CONFIG)
    if not os.path.exists(CONFIG_FILE):
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # 4) Ensure emoji_recent.json exists
    if not os.path.exists(RECENT_FILE):
        try:
            os.makedirs(os.path.dirname(RECENT_FILE), exist_ok=True)
            with open(RECENT_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # 5) Ensure emoji_favorites.json exists
    if not os.path.exists(FAVORITES_FILE):
        try:
            os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # 6) Ensure emoji_translations.json exists (if not created above)
    if not os.path.exists(TRANSLATIONS_FILE):
        try:
            os.makedirs(os.path.dirname(TRANSLATIONS_FILE), exist_ok=True)
            with open(TRANSLATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump({"by_char": {}}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # 7) Ensure templates/ directory exists
    try:
        os.makedirs(USER_TEMPLATES_DIR, exist_ok=True)
    except Exception:
        pass

    # 8) Ensure local README.md exists (copy from BASE_DIR if available)
    if not os.path.exists(USER_README_FILE):
        system_readme = os.path.join(BASE_DIR, "README.md")
        try:
            if os.path.exists(system_readme):
                os.makedirs(os.path.dirname(USER_README_FILE), exist_ok=True)
                shutil.copy2(system_readme, USER_README_FILE)
            else:
                os.makedirs(os.path.dirname(USER_README_FILE), exist_ok=True)
                with open(USER_README_FILE, "w", encoding="utf-8") as f:
                    f.write(
                        "# Smorfia\n\n"
                        "This folder contains your personal configuration files\n"
                        "for Smorfia (config, translations, recents, favorites, templates).\n"
                    )
        except Exception:
            pass

def get_system_language():
    """Return the system language (e.g. 'it', 'de', 'en')."""

    # Set locale based on environment vars (LANG, LC_ALL, etc.)
    # This avoids warnings and makes getlocale() reliable
    try:
        locale.setlocale(locale.LC_ALL, '')
    except Exception:
        pass  # Ignore if locale is not correctly configured on the system

    # Query locale safely (replacement for deprecated getdefaultlocale)
    lang_tuple = locale.getlocale()  # e.g. ('it_IT', 'UTF-8')
    lang = lang_tuple[0] if lang_tuple and lang_tuple[0] else None

    if lang:
        return lang.split("_")[0]  # 'it_IT' → 'it'

    # Secondary fallback: try environment LANG variable
    lang_env = os.environ.get("LANG", "")
    if lang_env:
        return lang_env.split("_")[0]

    # Final fallback
    return "en"

def load_locale(lang):
    """
    Load UI translations from locales/<lang>.json.
    If the file is missing or invalid, return an empty dict
    and rely on DEFAULT_I18N.
    """
    if not os.path.isdir(LOCALES_DIR):
        return {}

    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as e:
        print(f"Error loading locale {lang}: {e}", file=sys.stderr)

    return {}

def load_config():
    """Load user config.json from $HOME, overlaying DEFAULT_CONFIG.

    If it does not exist yet, try to migrate from the legacy config.json
    located next to smorfia.py (e.g. /usr/share/smorfia/config.json).
    """
    cfg = DEFAULT_CONFIG.copy()

    # Ensure user config directory exists
    os.makedirs(USER_CONFIG_DIR, exist_ok=True)

    # First run: migrate legacy system-level config.json if present
    if not os.path.exists(CONFIG_FILE) and os.path.exists(SYSTEM_CONFIG_FILE):
        try:
            shutil.copy2(SYSTEM_CONFIG_FILE, CONFIG_FILE)
        except Exception as e:
            print(f"Error migrating config.json from legacy location: {e}", file=sys.stderr)

    # If we still don't have a config file, just return defaults
    if not os.path.exists(CONFIG_FILE):
        return cfg

    # Load user config and overlay defaults
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update(data)
    except Exception as e:
        print(f"Error loading config.json: {e}", file=sys.stderr)

    return cfg

def save_config(cfg):
    """Save user configuration to config.json in $HOME."""
    try:
        os.makedirs(USER_CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving config.json: {e}", file=sys.stderr)


# Icons shown next to each category in the left sidebar.
CATEGORY_ICONS = {
    "All": "🌐",
    "Recent": "🕘",
    "Favorites": "⭐",
    "Smileys & Emotion": "😀",
    "People & Body": "👋",
    "Animals & Nature": "🐻",
    "Food & Drink": "🍔",
    "Travel & Places": "✈️",
    "Activities": "⚽",
    "Objects": "💡",
    "Symbols": "🔣",
    "Flags": "🏁",
    "Component": "🧩",
}


def category_i18n_key(cat):
    """Map a raw category name to its i18n key ('Food & Drink' -> 'category.food_drink')."""
    slug = re.sub(r"[^a-z0-9]+", "_", cat.lower()).strip("_")
    return "category." + slug


class CategorySidebar(Gtk.ScrolledWindow):
    """Vertical list of categories (icon + name) on the left side of the window.

    It deliberately offers the same small API the old Gtk.ComboBoxText had
    (append / remove_all / get_active_id / set_active_id / set_active and a
    "changed" signal), so the rest of the code did not need to change.
    """

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        try:
            self.set_propagate_natural_width(True)
        except AttributeError:
            self.set_size_request(170, -1)
        self.get_style_context().add_class("category-sidebar")

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self._on_row_selected)
        self.add(self.listbox)

    def _on_row_selected(self, listbox, row):
        if row is not None:
            self.emit("changed")

    def append(self, cat_id, label, icon=""):
        row = Gtk.ListBoxRow()
        row.cat_id = cat_id
        row.set_tooltip_text(label)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(6)
        box.set_margin_end(10)
        box.set_margin_top(3)
        box.set_margin_bottom(3)

        icon_label = Gtk.Label(label=icon or "•")
        icon_label.get_style_context().add_class("cat-icon")
        box.pack_start(icon_label, False, False, 0)

        name_label = Gtk.Label(label=label)
        name_label.set_xalign(0)
        box.pack_start(name_label, True, True, 0)

        row.add(box)
        row.show_all()
        self.listbox.add(row)

    def remove_all(self):
        for row in list(self.listbox.get_children()):
            self.listbox.remove(row)

    def get_active_id(self):
        row = self.listbox.get_selected_row()
        return getattr(row, "cat_id", None) if row else None

    def set_active_id(self, cat_id):
        for row in self.listbox.get_children():
            if getattr(row, "cat_id", None) == cat_id:
                self.listbox.select_row(row)
                return True
        return False

    def set_active(self, index):
        row = self.listbox.get_row_at_index(index)
        if row is not None:
            self.listbox.select_row(row)


def escape_markup(text):
    """Escape text for Pango markup."""
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class Smorfia(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title=APP_NAME)
        self.set_border_width(6)
        self.get_style_context().add_class("smorfia-window")

        # Try to set a custom window icon from local file
        icon_path = os.path.join(BASE_DIR, "smorfia.png")
        if os.path.exists(icon_path):
            try:
                self.set_icon_from_file(icon_path)
            except Exception:
                pass  # If it fails, just keep the default icon

        # Load configuration
        self.config = load_config()

        # Apply initial geometry depending on preference
        remember = bool(self.config.get("remember_window", True))
        if remember:
            # Use stored size/position (if available)
            width = int(self.config.get("window_width", DEFAULT_CONFIG["window_width"]) or DEFAULT_CONFIG["window_width"])
            height = int(self.config.get("window_height", DEFAULT_CONFIG["window_height"]) or DEFAULT_CONFIG["window_height"])
            self.set_default_size(width, height)

            x = self.config.get("window_x")
            y = self.config.get("window_y")
            if isinstance(x, int) and isinstance(y, int) and x >= 0 and y >= 0:
                # Restore previous position
                self.move(x, y)
            else:
                # Fallback: center on first run
                self.set_position(Gtk.WindowPosition.CENTER)
        else:
            # Do NOT restore previous geometry → use defaults & center
            self.set_default_size(
                DEFAULT_CONFIG["window_width"],
                DEFAULT_CONFIG["window_height"],
            )
            self.set_position(Gtk.WindowPosition.CENTER)

        # Current skin tone index (0..5)
        self.current_skin_tone = 0

        # Determine effective UI language (system or override)
        system_lang = get_system_language()
        lang_override = self.config.get("language", "system")
        if lang_override and lang_override != "system":
            self.language = lang_override
        else:
            self.language = system_lang

        # Load UI translations
        self.i18n = load_locale(self.language)

        # Load emoji translations/keyword families
        self.translations = self.load_translations()

        # Apply CSS for emoji (size etc.)
        self.apply_emoji_css()

        # Apply theme (light/dark/system)
        self.apply_theme()

        # Detect environment for auto-paste (X11 + xdotool)
        env_info = detect_auto_paste_support()
        self.session_type = env_info["session_type"]
        self.has_xdotool = env_info["has_xdotool"]
        self.auto_paste_available = env_info["auto_paste_available"]

        self.auto_paste_enabled = bool(self.auto_paste_available)
        # Window that had focus before Smorfia was opened (only if auto-paste is available)
        if self.auto_paste_available:
            self.target_window = self.get_previous_window_id()
        else:
            self.target_window = None

        # Load emoji list and apply translations
        self.emoji_list = self.load_emoji_data()
        self.apply_translations_to_emoji_list()

        # Load favorites (persistent)
        self.favorites_set = self.load_favorites()
        self.apply_favorites_to_emoji_list()

        # Load recent list
        self.recent_list = self.load_recent_list()
        self.max_recent = int(self.config.get("max_recent", DEFAULT_CONFIG["max_recent"]))
        self.recent_list = self.recent_list[: self.max_recent]
        self.recent_set = set(self.recent_list)

        # Buffer for multi-emoji paste
        self.buffer_emojis = []

        # Categories (All / Recent / Favorites / per-category)
        self.categories = []

        # Main layout
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add(main_vbox)

        # Menu bar
        menubar = Gtk.MenuBar()
        menu_root = Gtk.MenuItem(label="☰  " + self.tr("menu.root"))
        menubar.append(menu_root)
        menu = Gtk.Menu()
        menu_root.set_submenu(menu)

        mi_instr = Gtk.MenuItem(label=self.tr("menu.instructions"))
        mi_instr.connect("activate", self.on_menu_instructions)
        menu.append(mi_instr)

        menu.append(Gtk.SeparatorMenuItem())

        mi_short = Gtk.MenuItem(label=self.tr("menu.shortcuts"))
        mi_short.connect("activate", self.on_menu_shortcuts)
        menu.append(mi_short)

        mi_info = Gtk.MenuItem(label=self.tr("menu.about"))
        mi_info.connect("activate", self.on_menu_info)
        menu.append(mi_info)

        mi_update = Gtk.MenuItem(label=self.tr("menu.update_db"))
        mi_update.connect("activate", self.on_menu_update_db)
        menu.append(mi_update)

        mi_prefs = Gtk.MenuItem(label=self.tr("menu.preferences"))
        mi_prefs.connect("activate", self.on_menu_preferences)
        menu.append(mi_prefs)

        mi_skin = Gtk.MenuItem(label=self.tr("menu.skin_tone"))
        mi_skin.connect("activate", self.on_menu_skin_tone)
        menu.append(mi_skin)

        menubar.show_all()
        main_vbox.pack_start(menubar, False, False, 0)

        # Top row: search only (categories moved to the left sidebar)
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        main_vbox.pack_start(top_box, False, False, 0)

        # Category sidebar (internal IDs + localized labels, one icon each).
        # The attribute keeps the old name so existing callers keep working.
        self.category_combo = CategorySidebar()
        self.rebuild_category_combo()
        self.category_combo.connect("changed", self.on_filter_changed)

        # Search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(self.tr("search.placeholder"))
        self.search_entry.connect("search-changed", self.on_filter_changed)
        self.search_entry.connect("activate", self.on_activate_first_visible)
        top_box.pack_start(self.search_entry, True, True, 0)

        # FlowBox with emoji
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_max_children_per_line(int(self.config.get("columns", 6)))
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_activate_on_single_click(False)
        self.flowbox.set_row_spacing(0)
        self.flowbox.set_column_spacing(0)
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_halign(Gtk.Align.FILL)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_margin_top(10)  # spazio sopra le emoji
        scrolled.add(self.flowbox)

        # Middle area: sidebar on the left, emoji grid on the right
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content_box.pack_start(self.category_combo, False, False, 0)
        content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        content_box.pack_start(scrolled, True, True, 0)
        main_vbox.pack_start(content_box, True, True, 0)

        # Populate emojis
        for item in self.emoji_list:
            child = self.create_child(item)
            self.flowbox.add(child)

        self.flowbox.show_all()

        # Skin tone selector bar
        self.create_skin_tone_bar(main_vbox)

        # Status bar
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.status_label = Gtk.Label()
        self.status_label.set_xalign(0)
        status_box.pack_start(self.status_label, True, True, 0)
        main_vbox.pack_start(status_box, False, False, 0)

        # Initial filter (Recent) and selection
        GLib.idle_add(self.on_filter_changed, None)
        GLib.idle_add(self.select_first_visible_emoji)

        # Global key handling and window events
        self.connect("key-press-event", self.on_key_press)
        self.connect("configure-event", self.on_configure_event)
        self.connect("destroy", self.on_window_destroy)

    # -------------------------------------------------------------------------
    # Window geometry & application shutdown
    # -------------------------------------------------------------------------

    def save_window_geometry(self):
        """Store current window size/position into self.config (if enabled)."""
        # If user disabled remembering geometry, do nothing
        if not self.config.get("remember_window", True):
            return

        try:
            width, height = self.get_size()
            x, y = self.get_position()
            self.config["window_width"] = int(width)
            self.config["window_height"] = int(height)
            self.config["window_x"] = int(x)
            self.config["window_y"] = int(y)
        except Exception as e:
            self.log("Unable to read window geometry:", e)

    def on_configure_event(self, widget, event):
        """Update window geometry in config whenever the window moves/resizes."""
        self.save_window_geometry()
        return False

    def on_window_destroy(self, widget):
        """Persist configuration (including geometry) when the window is destroyed."""
        try:
            self.save_window_geometry()
            save_config(self.config)
        except Exception as e:
            self.log("Error saving config on destroy:", e)
        Gtk.main_quit()

    def close_app(self):
        """Centralized app shutdown: save config and quit main loop."""
        try:
            self.save_window_geometry()
            save_config(self.config)
        except Exception as e:
            self.log("Error saving config on close:", e)
        Gtk.main_quit()

    # -------------------------------------------------------------------------
    # Utility / logging / translation helpers
    # -------------------------------------------------------------------------

    def tr(self, key, **kwargs):
        """Translate a key using the loaded locale (with fallback)."""
        text = self.i18n.get(key, DEFAULT_I18N.get(key, key))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    def log(self, *args):
        """Debug log (only if enabled in config)."""
        if self.config.get("debug", False):
            print("[Smorfia]", *args, file=sys.stderr)

    # -------------------------------------------------------------------------
    # Data loading / helpers
    # -------------------------------------------------------------------------

    def get_previous_window_id(self):
        """Read the window that was focused before opening Smorfia."""
        try:
            out = subprocess.check_output(["xdotool", "getwindowfocus"], text=True)
            return out.strip()
        except Exception as e:
            self.log("Unable to read focused window:", e)
            return None

    def load_translations(self):
        """Load custom emoji translations/keywords from emoji_translations.json."""
        if not os.path.exists(TRANSLATIONS_FILE):
            return {}
        try:
            with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
        except Exception as e:
            self.log("Error loading emoji_translations.json:", e)
            return {}

    def apply_translations_to_emoji_list(self):
        """Merge translations keywords (emoji_translations.json) into emoji_list items."""
        if not getattr(self, "translations", None):
            return

        by_char = self.translations.get("by_char", {})
        if not isinstance(by_char, dict):
            return

        for item in self.emoji_list:
            ch = item.get("char")
            if not ch or ch not in by_char:
                continue

            t = by_char[ch]
            kw_dict = t.get("keywords", {})
            if not isinstance(kw_dict, dict):
                continue

            base_kw = item.get("keywords")
            if base_kw is None:
                base_kw = {}
                item["keywords"] = base_kw

            # Remember the database keywords, so tooltips can show them apart
            # from the user's own tags.
            if "_base_keywords" not in item:
                item["_base_keywords"] = json.loads(json.dumps(base_kw))

            if isinstance(base_kw, dict):
                for lang, new_list in kw_dict.items():
                    if not isinstance(new_list, list):
                        continue
                    old_list = base_kw.get(lang, [])
                    if not isinstance(old_list, list):
                        old_list = [str(old_list)]
                    merged = sorted(set(old_list + new_list))
                    base_kw[lang] = merged
            elif isinstance(base_kw, list):
                new_list = kw_dict.get(self.language, [])
                if isinstance(new_list, list):
                    merged = sorted(set(base_kw + new_list))
                    item["keywords"] = merged

    def normalize_skin_tones(self, data):
        """
        Collapse multiple skin-tone variants of the same base emoji into one.

        Example: all skin-tone versions of a "thumbs up" become a single entry.
        """
        result = []
        seen = set()

        for item in data:
            ch = item.get("char")
            if not ch:
                continue

            base = self.strip_skin_tones(ch)

            if base in seen:
                continue

            seen.add(base)
            item["char"] = base
            result.append(item)

        return result

    def load_emoji_data(self):
        """Load emoji data from emoji_data.json and unify skin-tone variants."""
        data = []
        for path in (EMOJI_FILE, os.path.join(BASE_DIR, "emoji_data.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    break
            except Exception as e:
                print(f"Error loading {path}:", e, file=sys.stderr)

        for item in data:
            if "favorite" not in item:
                item["favorite"] = False
            if "category" not in item:
                item["category"] = "Other"

        data = self.normalize_skin_tones(data)
        return data

    def save_recent_list(self):
        """Persist the recent emoji list to the user data directory."""
        try:
            os.makedirs(USER_CONFIG_DIR, exist_ok=True)
            with open(RECENT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.recent_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log("Error writing emoji_recent.json:", e)

    def load_recent_list(self):
        """Load the last used emoji list from the user data directory.

        If the user file does not exist yet, try to migrate from the legacy
        emoji_recent.json next to smorfia.py (e.g. /usr/share/smorfia).
        """
        # Ensure user data directory exists
        os.makedirs(USER_CONFIG_DIR, exist_ok=True)

        # First run: migrate legacy file if present
        if not os.path.exists(RECENT_FILE) and os.path.exists(LEGACY_RECENT_FILE):
            try:
                shutil.copy2(LEGACY_RECENT_FILE, RECENT_FILE)
            except Exception as e:
                self.log("Error migrating emoji_recent.json from legacy location:", e)

        if not os.path.exists(RECENT_FILE):
            return []

        try:
            with open(RECENT_FILE, "r", encoding="utf-8") as f:
                arr = json.load(f)
            if isinstance(arr, list):
                return arr
        except Exception as e:
            self.log("Error reading emoji_recent.json:", e)

        return []

    def update_recent(self, char):
        """
        Update the 'Recent' list when an emoji is used.

        This only updates the in-memory list and saves it.
        Visual reordering of the 'Recent' tab happens later
        when the user changes category or re-opens the app.
        """
        if not char:
            return

        # Move char to the front (if already present, remove old position)
        if char in self.recent_list:
            self.recent_list.remove(char)

        self.recent_list.insert(0, char)

        # Enforce max size
        if len(self.recent_list) > self.max_recent:
            self.recent_list = self.recent_list[: self.max_recent]

        # Keep set in sync for fast membership checks
        self.recent_set = set(self.recent_list)

        # Persist to disk
        self.save_recent_list()
        self.log("Updated recent:", self.recent_list[:5], "...")

        # Just refresh status bar, no live reordering of the 'Recent' grid
        self.update_status()

    def collect_categories(self, data):
        """
        Collect all categories from emoji data, ignoring 'Special',
        and prepend the virtual categories All / Recent / Favorites.
        """
        PRIORITY = [
            "Smileys & Emotion",
            "People & Body",
            "Animals & Nature",
            "Food & Drink",
            "Travel & Places",
            "Activities",
            "Objects",
            "Symbols",
            "Flags",
        ]

        cats = set()
        reserved = {"All", "Recent", "Favorites"}

        for item in data:
            cat = item.get("category", "Other")
            if not cat:
                continue
            # Skip virtual / reserved categories and the legacy 'Special'
            if cat in reserved:
                continue
            if cat.lower() == "special":
                continue
            cats.add(cat)

        # Order categories based on PRIORITY; unknown ones go at the bottom
        cat_list = sorted(
            cats,
            key=lambda c: PRIORITY.index(c) if c in PRIORITY else 999,
        )

        return ["All", "Recent", "Favorites"] + cat_list

    def rebuild_category_combo(self):
        """(Re)build the category combo based on the current emoji list."""

        # Recompute categories from data
        self.categories = self.collect_categories(self.emoji_list)

        # Clear existing entries
        self.category_combo.remove_all()

        # Re-add all categories with proper labels
        for cat in self.categories:
            if cat == "All":
                cat_id = "All"
                label = self.tr("category.all")
            elif cat == "Recent":
                cat_id = "Recent"
                label = self.tr("category.recent")
            elif cat == "Favorites":
                cat_id = "Favorites"
                label = self.tr("category.favorites")
            else:
                cat_id = cat
                key = category_i18n_key(cat)
                label = self.tr(key)
                if label == key:
                    label = cat
            self.category_combo.append(cat_id, label, CATEGORY_ICONS.get(cat_id, "•"))

        # Default selection: "Recent" if available, otherwise first category
        if "Recent" in self.categories:
            self.category_combo.set_active_id("Recent")
        elif self.categories:
            self.category_combo.set_active_id(self.categories[0])
        else:
            self.category_combo.set_active(0)

    def clean_name(self, name):
        """Remove prefixes such as 'e0.6 ' from the name."""
        if not isinstance(name, str):
            return ""
        return re.sub(r"^e\d+(\.\d+)?\s+", "", name, flags=re.IGNORECASE)

    def get_display_name(self, item):
        """Return the display name based on the current language."""
        names = item.get("names", {})
        name = None
        if isinstance(names, dict):
            if self.language in names:
                name = names[self.language]
            elif "en" in names:
                name = names["en"]
        if not name:
            name = item.get("shortcode", "")
        return self.clean_name(name)

    def get_all_keywords(self, item):
        """Collect all keywords used for searching this emoji."""
        keywords = []
        kw = item.get("keywords", {})

        if isinstance(kw, dict):
            if self.language in kw:
                keywords += kw[self.language]
            if "en" in kw:
                keywords += kw["en"]
        elif isinstance(kw, list):
            keywords += kw

        extra = item.get("extra", [])
        if isinstance(extra, list):
            keywords += extra

        keywords.append(self.get_display_name(item))

        return [k.lower() for k in keywords if isinstance(k, str)]

    def load_favorites(self):
        """Load favorites from the user emoji_favorites.json or from emoji_data.

        If the user file does not exist yet, try to migrate from the legacy
        emoji_favorites.json next to smorfia.py.
        """
        # Ensure the user config directory exists
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)

        # First run: migrate legacy favorites if present
        if not os.path.exists(FAVORITES_FILE) and os.path.exists(LEGACY_FAVORITES_FILE):
            try:
                shutil.copy2(LEGACY_FAVORITES_FILE, FAVORITES_FILE)
            except Exception as e:
                self.log("Error migrating emoji_favorites.json from legacy location:", e)

        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                if isinstance(arr, list):
                    return set(arr)
            except Exception as e:
                self.log("Error reading emoji_favorites.json:", e)

        # Fallback: derive favorites from emoji_data.json
        favs = set()
        for item in self.emoji_list:
            if item.get("favorite"):
                ch = item.get("char")
                if ch:
                    favs.add(ch)
        return favs

    def save_favorites(self):
        """Save current favorites set to emoji_favorites.json in user config dir."""
        try:
            os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(sorted(self.favorites_set), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log("Error writing emoji_favorites.json:", e)

    def apply_favorites_to_emoji_list(self):
        """Apply favorites_set to emoji_list items."""
        for item in self.emoji_list:
            ch = item.get("char")
            item["favorite"] = bool(ch in self.favorites_set)

    # -------------------------------------------------------------------------
    # CSS / theme
    # -------------------------------------------------------------------------

    def apply_emoji_css(self):
        """Apply CSS for emoji size and minimal spacing."""
        size = int(self.config.get("emoji_font_size", DEFAULT_CONFIG["emoji_font_size"]))
        css = f"""
        flowboxchild {{
            padding: 0;
            margin: 0;
        }}
        label.emoji-label {{
            font-size: {size}px;
            padding: 0;
            margin: 0;
        }}
        label.cat-icon {{
            font-size: 18px;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER,
        )
        self.emoji_css_provider = provider

    def apply_theme(self):
        """Apply light/dark/system theme via CSS."""
        theme = self.config.get("theme", "system")
        if theme == "system":
            return

        if theme == "dark":
            css = """
            .smorfia-window {
                background-color: #222222;
                color: #eeeeee;
            }
            .smorfia-window label {
                color: #eeeeee;
            }
            """
        else:  # light
            css = """
            .smorfia-window {
                background-color: #ffffff;
                color: #000000;
            }
            """

        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        self.theme_css_provider = provider

    # -------------------------------------------------------------------------
    # Skin tone helpers
    # -------------------------------------------------------------------------

    def strip_skin_tones(self, text):
        """Remove any skin tone modifiers from a string."""
        if not text:
            return text
        return "".join(ch for ch in text if ch not in SKIN_TONES[1:])

    def supports_skin_tone(self, item):
        """Return True if this emoji should receive a Fitzpatrick skin-tone modifier.

        Practical rule for Smorfia: only emojis in 'People & Body' get skin tones.
        This prevents outputs like '🍔🏿' for non-human emoji.
        """
        try:
            return (item.get("category") == "People & Body")
        except Exception:
            return False

    def apply_skin_tone_to_char(self, char):
        """
        Apply current skin tone modifier to a base emoji.
        """
        if not char:
            return char
        base = self.strip_skin_tones(char)
        tone_idx = self.current_skin_tone
        if tone_idx <= 0 or tone_idx >= len(SKIN_TONES):
            return base
        return base + SKIN_TONES[tone_idx]

    def create_skin_tone_bar(self, vbox):
        """Create the skin tone selector bar."""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label = Gtk.Label(label=self.tr("skin.label"))
        label.set_xalign(0)
        bar.pack_start(label, False, False, 0)

        self.skin_buttons = []
        for idx, preview in enumerate(SKIN_TONE_PREVIEWS):
            btn = Gtk.ToggleButton(label=preview)
            btn.connect("toggled", self.on_skin_tone_button_toggled, idx)
            if idx == self.current_skin_tone:
                btn.set_active(True)
            bar.pack_start(btn, False, False, 0)
            self.skin_buttons.append(btn)

        vbox.pack_start(bar, False, False, 0)

    def on_skin_tone_button_toggled(self, button, idx):
        """Ensure only one skin tone button is active at a time."""
        if not button.get_active():
            if idx == self.current_skin_tone:
                button.set_active(True)
            return

        self.current_skin_tone = idx
        for i, btn in enumerate(self.skin_buttons):
            if i != idx:
                btn.handler_block_by_func(self.on_skin_tone_button_toggled)
                btn.set_active(False)
                btn.handler_unblock_by_func(self.on_skin_tone_button_toggled)

        self.log("Skin tone set to index:", idx)
        self.refresh_skin_tone_display()

    def on_menu_skin_tone(self, widget):
        """Dialog to choose default skin tone (also syncs bottom bar)."""
        dialog = Gtk.Dialog(
            title=self.tr("skin.dialog.title"),
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )

        box = dialog.get_content_area()
        box.set_border_width(10)
        box.set_spacing(8)

        label = Gtk.Label(label=self.tr("skin.label"))
        label.set_xalign(0)
        box.pack_start(label, False, False, 0)

        group = None
        radio_buttons = []
        for idx, preview in enumerate(SKIN_TONE_PREVIEWS):
            rb = Gtk.RadioButton.new_with_label_from_widget(group, preview)
            if group is None:
                group = rb
            if idx == self.current_skin_tone:
                rb.set_active(True)
            box.pack_start(rb, False, False, 0)
            radio_buttons.append((idx, rb))
        dialog.show_all()
        resp = dialog.run()

        if resp == Gtk.ResponseType.OK:
            for idx, rb in radio_buttons:
                if rb.get_active():
                    self.current_skin_tone = idx
                    break

            if hasattr(self, "skin_buttons"):
                for i, btn in enumerate(self.skin_buttons):
                    btn.handler_block_by_func(self.on_skin_tone_button_toggled)
                    btn.set_active(i == self.current_skin_tone)
                    btn.handler_unblock_by_func(self.on_skin_tone_button_toggled)

            self.refresh_skin_tone_display()

        dialog.destroy()

    # -------------------------------------------------------------------------
    # Emoji children / tooltips
    # -------------------------------------------------------------------------

    def get_custom_keywords(self, item):
        """Return the user's own tags for this emoji (all languages, no duplicates)."""
        by_char = {}
        if isinstance(getattr(self, "translations", None), dict):
            by_char = self.translations.get("by_char", {}) or {}
        entry = by_char.get(item.get("char", ""), {})
        kw_dict = entry.get("keywords", {}) if isinstance(entry, dict) else {}
        result = []
        if isinstance(kw_dict, dict):
            for words in kw_dict.values():
                if isinstance(words, list):
                    for w in words:
                        if isinstance(w, str) and w.strip() and w not in result:
                            result.append(w)
        return result

    def get_english_keywords(self, item, exclude=()):
        """Return the database's English keywords, without the user's own tags."""
        kw = item.get("_base_keywords", item.get("keywords", {}))
        words = kw.get("en", []) if isinstance(kw, dict) else (kw if isinstance(kw, list) else [])
        skip = {e.lower() for e in exclude}
        out = []
        for w in words:
            if not isinstance(w, str) or w.lower() in skip or w in out:
                continue
            # Skip Unicode version fragments such as "e0", "e1", "7", "0".
            if re.fullmatch(r"e?\d+", w.strip().lower()):
                continue
            out.append(w)
        return out

    def build_tooltip_for_item(self, item):
        """Build tooltip text for an emoji (simple or rich, depending on debug)."""
        name = self.get_display_name(item)
        if not self.config.get("debug", False):
            lines = [name]
            mine = self.get_custom_keywords(item)
            if mine:
                lines.append("🏷️ " + self.tr("tooltip.my_tags") + ": " + ", ".join(mine))
            english = self.get_english_keywords(item, exclude=mine)[:12]
            if english:
                lines.append("🔤 " + self.tr("tooltip.keywords_en") + ": " + ", ".join(english))
            return "\n".join(lines)

        cat = item.get("category", "Other")
        kws = self.get_all_keywords(item)
        kws = sorted(set(kws))[:8]
        parts = [name, f"({cat})"]
        if kws:
            parts.append("keywords: " + ", ".join(kws))
        return "\n".join(parts)

    def update_all_tooltips(self):
        """Rebuild tooltips for all emoji (e.g., after toggling debug)."""
        for child in self.flowbox.get_children():
            item = getattr(child, "item", None)
            if not item:
                continue
            event_box = child.get_child()
            tooltip = self.build_tooltip_for_item(item)
            event_box.set_tooltip_text(tooltip)

    def create_child(self, item):
        """Create a FlowBoxChild with compact cell and tooltip."""
        child = Gtk.FlowBoxChild()
        child.set_size_request(32, 32)

        event_box = Gtk.EventBox()
        event_box.set_hexpand(False)
        event_box.set_vexpand(False)
        child.add(event_box)

        base_char = item.get("char", "?")
        display_char = self.apply_skin_tone_to_char(base_char) if self.supports_skin_tone(item) else self.strip_skin_tones(base_char)
        emoji_label = Gtk.Label(label=display_char)

        emoji_label.set_margin_top(0)
        emoji_label.set_margin_bottom(0)
        emoji_label.set_margin_start(0)
        emoji_label.set_margin_end(0)

        try:
            emoji_label.set_xalign(0.5)
            emoji_label.set_yalign(0.5)
        except AttributeError:
            emoji_label.set_alignment(0.5, 0.5)

        emoji_label.get_style_context().add_class("emoji-label")

        tooltip = self.build_tooltip_for_item(item)
        event_box.set_tooltip_text(tooltip)

        event_box.add(emoji_label)
        event_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        event_box.connect(
            "button-press-event",
            self.on_emoji_button_press,
            child,
            item,
        )

        child.item = item
        return child

    def refresh_skin_tone_display(self):
        """Update the emoji glyphs already visible in the grid to reflect the
        currently selected skin tone, without rebuilding the whole FlowBox
        (category/search state is left untouched)."""
        for child in self.flowbox.get_children():
            item = getattr(child, "item", None)
            if not item:
                continue
            event_box = child.get_child()
            if event_box is None:
                continue
            emoji_label = event_box.get_child()
            if emoji_label is None:
                continue
            base_char = item.get("char", "?")
            display_char = (
                self.apply_skin_tone_to_char(base_char)
                if self.supports_skin_tone(item)
                else self.strip_skin_tones(base_char)
            )
            emoji_label.set_text(display_char)

    def select_first_visible_emoji(self):
        """Select the first visible emoji in the grid."""
        for child in self.flowbox.get_children():
            if child.get_visible():
                self.flowbox.select_child(child)
                break

    # -------------------------------------------------------------------------
    # Status bar
    # -------------------------------------------------------------------------

    def update_status(self):
        """Update status bar with visible emoji count, buffer content and auto-paste state."""
        visible_count = 0
        for child in self.flowbox.get_children():
            if child.get_visible():
                visible_count += 1

        text = self.tr("status.results", count=visible_count)

        if self.buffer_emojis:
            buf = "".join(self.buffer_emojis)
            text += "  |  " + self.tr("status.buffer", buf=buf)

        # Auto-paste status (X11 vs Wayland / missing xdotool)
        if hasattr(self, "auto_paste_available"):
            if self.auto_paste_available:
                text += "  |  " + self.tr("status.autopaste.enabled")
            else:
                session_type = getattr(self, "session_type", "")
                if session_type == "wayland":
                    text += "  |  " + self.tr("status.autopaste.clipboard_only")
                else:
                    text += "  |  " + self.tr("status.autopaste.disabled")

        if hasattr(self, "status_label"):
            self.status_label.set_text(text)

    # -------------------------------------------------------------------------
    # Filtering
    # -------------------------------------------------------------------------

    def on_filter_changed(self, *args):
        """Filter the grid based on selected category and search text.

        If there is search text, always search across ALL emoji,
        regardless of the selected category.
        """
        text = self.search_entry.get_text().strip().lower()
        cat_id = self.category_combo.get_active_id()

        if text:
            effective_cat = "All"
        else:
            effective_cat = cat_id

        self.log("Filter changed:", "text=", text, "cat_id=", cat_id, "effective=", effective_cat)

        # 1) Apply visibility based on search text + effective category
        for child in self.flowbox.get_children():
            item = getattr(child, "item", None)
            if not item:
                child.set_visible(False)
                continue

            if text:
                keywords = self.get_all_keywords(item)
                matches_text = any(text in kw for kw in keywords)
            else:
                matches_text = True

            matches_cat = True
            char = item.get("char", "")
            favorite = item.get("favorite", False)
            category = item.get("category", "Other")

            if effective_cat == "Recent":
                matches_cat = char in self.recent_set
            elif effective_cat == "Favorites":
                matches_cat = bool(favorite)
            elif effective_cat == "All" or effective_cat is None:
                matches_cat = True
            else:
                matches_cat = (category == effective_cat)

            visible = matches_text and matches_cat
            child.set_visible(visible)

        # 2) In "Recent" (no search text), order according to self.recent_list
        if effective_cat == "Recent" and not text:
            order_index = {ch: idx for idx, ch in enumerate(self.recent_list)}

            def child_recent_index(c):
                item = getattr(c, "item", None)
                if not isinstance(item, dict):
                    return len(order_index)
                ch = item.get("char", "")
         # The smaller the index, the more recently the emoji was used
                return order_index.get(ch, len(order_index))

            children = list(self.flowbox.get_children())
            children.sort(key=child_recent_index)

        # Rebuild the FlowBox in the desired order
            for c in list(self.flowbox.get_children()):
                self.flowbox.remove(c)
            for c in children:
                self.flowbox.add(c)

        self.select_first_visible_emoji()
        self.update_status()

    def get_selected_item(self):
        """Return the currently selected emoji item, or the first visible one."""
        selected = self.flowbox.get_selected_children()
        if selected:
            return selected[0].item
        for child in self.flowbox.get_children():
            if child.get_visible():
                self.flowbox.select_child(child)
                return child.item
        return None

    def on_activate_first_visible(self, entry):
        """When pressing Enter in the search bar, use the current selection."""
        item = self.get_selected_item()
        if not item:
            return
        self.finalize_and_paste(item)

    # -------------------------------------------------------------------------
    # Mouse handling
    # -------------------------------------------------------------------------

    def on_emoji_button_press(self, widget, event, child, item):
        """Handle left/middle/right mouse clicks on an emoji."""
        self.flowbox.select_child(child)

        state = event.state
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        if event.button == 2:
            self.open_keyword_editor(item)
            return True

        if event.button == 3:
            self.add_to_buffer(item)
            return True

        if event.button == 1:
            if shift:
                self.add_to_buffer(item)
            else:
                self.finalize_and_paste(item)
            return True

        return False

    # -------------------------------------------------------------------------
    # Keyboard handling
    # -------------------------------------------------------------------------

    def on_key_press(self, widget, event):
        keyval = Gdk.keyval_name(event.keyval)
        state = event.state
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)

        alt = bool(state & Gdk.ModifierType.MOD1_MASK)
        if keyval == "Escape":
            # If search is active, clear it; otherwise close.
            if hasattr(self, "search_entry") and self.search_entry.get_text():
                self.search_entry.set_text("")
                self.on_filter_changed(None)
                return True
            self.close_app()
            return True

        
        # App shortcuts (inside Smorfia window)
        if ctrl and alt and keyval in ("e", "E"):
            # Bring Smorfia to front
            try:
                self.present()
            except Exception:
                pass
            return True

        if ctrl and alt and keyval in ("f", "F"):
            # Focus search
            if hasattr(self, "search_entry"):
                self.search_entry.grab_focus()
            return True

        if ctrl and alt and keyval in ("r", "R"):
            # Go to Recent
            if hasattr(self, "category_combo"):
                self.category_combo.set_active_id("Recent")
            return True

        if ctrl and alt and keyval in ("s", "S"):
            # Go to Favorites
            if hasattr(self, "category_combo"):
                self.category_combo.set_active_id("Favorites")
            return True

        if ctrl and alt and keyval in ("p", "P"):
            # Toggle auto-paste (X11 + xdotool availability)
            if getattr(self, "auto_paste_available", False):
                self.auto_paste_enabled = not getattr(self, "auto_paste_enabled", True)
                self.update_status()
                self.log("[Smorfia] Auto-paste toggled:", self.auto_paste_enabled)
            return True

        if keyval in ("Return", "KP_Enter"):
            item = self.get_selected_item()
            if not item:
                return True
            if shift:
                self.add_to_buffer(item)
            else:
                self.finalize_and_paste(item)
            return True

        if keyval in ("t", "T") and shift:
            item = self.get_selected_item()
            if item:
                self.open_keyword_editor(item)
            return True

        if keyval in ("f", "F") and ctrl:
            item = self.get_selected_item()
            if item:
                self.toggle_favorite(item)
            return True

        return False

    # -------------------------------------------------------------------------
    # Favorites toggle
    # -------------------------------------------------------------------------

    def toggle_favorite(self, item):
        """Toggle favorite flag for the given emoji and persist it."""
        ch = item.get("char", "")
        if not ch:
            return
        if ch in self.favorites_set:
            self.favorites_set.remove(ch)
            item["favorite"] = False
            self.log("Removed from favorites:", ch)
        else:
            self.favorites_set.add(ch)
            item["favorite"] = True
            self.log("Added to favorites:", ch)

        self.save_favorites()
        self.on_filter_changed(None)

    # -------------------------------------------------------------------------
    # Buffer logic and paste
    # -------------------------------------------------------------------------

    def add_to_buffer(self, item):
        """Add the emoji (with skin tone) to the buffer without pasting."""
        raw_char = item.get("char", "")
        if not raw_char:
            return
        char = self.apply_skin_tone_to_char(raw_char) if self.supports_skin_tone(item) else self.strip_skin_tones(raw_char)
        self.buffer_emojis.append(char)
        self.update_recent(char)
        self.log("Buffer now:", "".join(self.buffer_emojis))
        self.update_status()

    def finalize_and_paste(self, item):
        """
        Add the selected emoji (with current skin tone) to the buffer,
        update Recents for all buffered emoji, copy the final string
        to the clipboard (and auto-paste if available), then close the app.
        """
        raw_char = item.get("char", "")
        if not raw_char:
            return

        # Add selected emoji (with current skin tone) to the buffer
        char = self.apply_skin_tone_to_char(raw_char) if self.supports_skin_tone(item) else self.strip_skin_tones(raw_char)
        self.buffer_emojis.append(char)

        # Update "Recent" list for all emojis in the buffer
        for ch in self.buffer_emojis:
            self.update_recent(ch)

        # Build final text to copy/paste
        text = "".join(self.buffer_emojis)
        self.log("Pasting text:", text)

        # Clear buffer after use
        self.buffer_emojis = []
        self.update_status()

        # Copy to clipboard
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

        # Try auto-paste (only on X11 + xdotool)
        if getattr(self, "auto_paste_available", False) and getattr(self, "auto_paste_enabled", True) and self.target_window:
            try:
                subprocess.call(
                    ["xdotool", "windowactivate", "--sync", self.target_window]
                )
            except Exception as e:
                self.log(self.tr("msg.error.xdotool_activate", error=e))
            try:
                subprocess.Popen(
                ["xdotool", "key", "--clearmodifiers", "Shift+Insert"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
                )

            except Exception as e:
                self.log(self.tr("msg.error.xdotool_key", error=e))
        else:
            # No auto-paste: text is in the clipboard, user must paste manually
            self.log(self.tr("msg.info.clipboard_only"))

        # Centralized shutdown: save config (including geometry) and quit
        self.close_app()

    # -------------------------------------------------------------------------
    # Custom keywords editor
    # -------------------------------------------------------------------------

    def open_keyword_editor(self, item):
        """Open a dialog to edit custom keywords for this emoji."""
        char = item.get("char", "")
        if not char:
            return

        lang = self.language

        if os.path.exists(TRANSLATIONS_FILE):
            try:
                with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}

        by_char = data.get("by_char", {})
        char_entry = by_char.get(char, {})

        kw_dict = char_entry.get("keywords", {})
        existing_personal = kw_dict.get(lang, [])

        kw_main = item.get("keywords", {})
        default_keywords = []
        if isinstance(kw_main, dict):
            if lang in kw_main:
                default_keywords = kw_main[lang]
            elif "en" in kw_main:
                default_keywords = kw_main["en"]
        elif isinstance(kw_main, list):
            default_keywords = kw_main

        dialog = Gtk.Dialog(
            title=self.tr("editor.title"),
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
        )

        content = dialog.get_content_area()
        content.set_border_width(10)
        content.set_spacing(8)

        label_title = Gtk.Label()
        label_title.set_markup(
            "<span size='large' weight='bold'>{}</span>".format(
                escape_markup(
                    self.tr("editor.search_label", emoji=char)
                )
            )
        )
        label_title.set_xalign(0)
        content.pack_start(label_title, False, False, 0)

        label_desc = Gtk.Label()
        label_desc.set_markup(
            "<span size='small'>{}</span>".format(
                escape_markup(self.tr("editor.desc"))
            )
        )
        label_desc.set_xalign(0)
        content.pack_start(label_desc, False, False, 0)

        entry = Gtk.Entry()
        entry.set_hexpand(True)
        if existing_personal:
            entry.set_text(", ".join(existing_personal))
        content.pack_start(entry, False, False, 0)

        label_defaults_title = Gtk.Label()
        label_defaults_title.set_markup(
            "<span size='medium'>{}</span>".format(
                escape_markup(
                    self.tr("editor.defaults_title", emoji=char)
                )
            )
        )
        label_defaults_title.set_xalign(0)
        content.pack_start(label_defaults_title, False, False, 0)

        label_defaults = Gtk.Label()
        label_defaults.set_xalign(0)
        label_defaults.set_line_wrap(True)
        label_defaults.set_ellipsize(3)
        defaults_text = (
            ", ".join(default_keywords)
            if default_keywords
            else self.tr("editor.defaults.none")
        )
        label_defaults.set_markup(
            "<span size='small'>{}</span>".format(
                escape_markup(defaults_text)
            )
        )
        content.pack_start(label_defaults, False, False, 0)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            raw = entry.get_text()
            parts = [p.strip() for p in raw.split(",") if p.strip()]

            if "by_char" not in data:
                data["by_char"] = {}
            if char not in data["by_char"]:
                data["by_char"][char] = {}
            if "keywords" not in data["by_char"][char]:
                data["by_char"][char]["keywords"] = {}
            data["by_char"][char]["keywords"][lang] = parts

            try:
                with open(TRANSLATIONS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.log("Error saving emoji_translations.json:", e)

            self.translations = data

            if "keywords" not in item:
                item["keywords"] = {}
            existing_lang = item["keywords"].get(lang, [])
            if not isinstance(existing_lang, list):
                existing_lang = [str(existing_lang)]
            merged = sorted(set(existing_lang + parts))
            item["keywords"][lang] = merged

            self.update_all_tooltips()

        dialog.destroy()

    # -------------------------------------------------------------------------
    # Menu actions: Instructions / Shortcuts / About / Update DB
    # -------------------------------------------------------------------------
    def on_menu_instructions(self, widget):
        """Show Instructions."""
        title = self.tr("instructions.title")
        body = self.tr("instructions.body")

        if title == "instructions.title":
            title = "Smorfia – Instructions"
        if body == "instructions.body":
            body = (
                "• Click an emoji to copy it\n"
                "• On X11, emojis are pasted automatically\n"
                "• Recent emojis are remembered\n"
                "• Preferences allow basic customization\n\n"
                "More features are coming."
            )

        self.show_message(title, body, Gtk.MessageType.INFO)


    def on_menu_shortcuts(self, widget):
        """Show available keyboard and mouse shortcuts."""
        self.show_message(
            self.tr("shortcuts.title"),
            self.tr("shortcuts.body"),
        )

    def on_menu_info(self, widget):
        """Show About dialog with app information."""
        self.show_message(
            self.tr("about.title"),
            self.tr("about.body", app_name=APP_NAME),
        )


    def _run_build_emoji_db(self):
        """
        Run build_emoji_db.py in BASE_DIR.

        Returns:
            True  if the script completed successfully.
            False if there was an error (and shows an error dialog).
        """
        # The build runs inside the user config dir: BASE_DIR may be read-only
        # (/usr/share/smorfia with the .deb), and the app reads EMOJI_FILE
        # from there anyway. build_emoji_db.py works next to itself, so we
        # copy it (and emoji-test.txt, if the user saved it in BASE_DIR).
        emoji_test_path = os.path.join(USER_CONFIG_DIR, "emoji-test.txt")
        print("[Smorfia] Running build_emoji_db.py")
        print(f"[Smorfia]   work dir         = {USER_CONFIG_DIR}")
        print(f"[Smorfia]   emoji-test.txt   = {emoji_test_path}")

        try:
            os.makedirs(USER_CONFIG_DIR, exist_ok=True)
            shutil.copyfile(os.path.join(BASE_DIR, "build_emoji_db.py"),
                            os.path.join(USER_CONFIG_DIR, "build_emoji_db.py"))
            base_test = os.path.join(BASE_DIR, "emoji-test.txt")
            if os.path.exists(base_test) and not os.path.exists(emoji_test_path):
                shutil.copyfile(base_test, emoji_test_path)
            make_user_files_writable()
            subprocess.check_call(
                [sys.executable, "build_emoji_db.py"],
                cwd=USER_CONFIG_DIR,
            )
            print("[Smorfia] build_emoji_db.py completed successfully.")
            return True
        except Exception as e:
            print(f"[Smorfia] build_emoji_db.py failed: {e}", file=sys.stderr)
            self.show_message(
                self.tr("update.error.title"),
                self.tr("update.error.body", error=e),
                Gtk.MessageType.ERROR,
            )
            return False

    def _reload_emoji_data_and_ui(self):
        """
        Reload emoji data from disk and rebuild categories and the FlowBox.

        This is called after a successful database update.
        """
        # Reload list, apply translations and favorites
        self.emoji_list = self.load_emoji_data()
        self.apply_translations_to_emoji_list()
        self.apply_favorites_to_emoji_list()

        # Rebuild the category combo
        self.rebuild_category_combo()

        # Rebuild FlowBox children
        for child in list(self.flowbox.get_children()):
            self.flowbox.remove(child)
        for item in self.emoji_list:
            child = self.create_child(item)
            self.flowbox.add(child)
        self.flowbox.show_all()

        # Refresh filter, selection and status
        self.on_filter_changed(None)
        self.select_first_visible_emoji()
        self.update_status()

    def on_menu_update_db(self, widget):
        """Show instructions and trigger build_emoji_db.py once emoji-test.txt is ready."""
        dialog = Gtk.Dialog(
            title=self.tr("update.title"),
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            self.tr("update.button.run"),
            Gtk.ResponseType.OK,
        )

        content = dialog.get_content_area()
        content.set_border_width(10)
        content.set_spacing(8)

        label1 = Gtk.Label()
        label1.set_xalign(0)
        label1.set_line_wrap(True)
        label1.set_markup(
            "<b>{}</b>\n\n{}".format(
                escape_markup(self.tr("update.heading")),
                escape_markup(self.tr("update.step1")),
            )
        )
        content.pack_start(label1, False, False, 0)

        link_label = Gtk.Label()
        link_label.set_xalign(0)
        link_label.set_use_markup(True)
        link_label.set_line_wrap(True)
        link_label.set_markup(
            f'<a href="{EMOJI_TEST_URL}">{EMOJI_TEST_URL}</a>'
        )
        content.pack_start(link_label, False, False, 0)

        label2 = Gtk.Label()
        label2.set_xalign(0)
        label2.set_line_wrap(True)
        label2.set_markup(
            self.tr("update.step2", base_dir=escape_markup(USER_CONFIG_DIR.replace(os.path.expanduser("~"), "~", 1)))
        )
        content.pack_start(label2, False, False, 0)

        dialog.show_all()
        response = dialog.run()

        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        dialog.destroy()

        # Run the external build script; abort on error
        if not self._run_build_emoji_db():
            return

        # Reload emoji data and refresh the UI
        self._reload_emoji_data_and_ui()

        # Inform the user that everything went fine
        self.show_message(
            self.tr("update.success.title"),
            self.tr("update.success.body"),
        )

    # -------------------------------------------------------------------------
    # Preferences / config UI
    # -------------------------------------------------------------------------

    def on_menu_preferences(self, widget):
        """Open Preferences dialog."""
        dialog = Gtk.Dialog(
            title=self.tr("prefs.title"),
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
        )

        content = dialog.get_content_area()
        content.set_border_width(10)
        content.set_spacing(8)

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        content.pack_start(grid, False, False, 0)

        row = 0

        label_theme = Gtk.Label(label=self.tr("prefs.theme"))
        label_theme.set_xalign(0)
        grid.attach(label_theme, 0, row, 1, 1)

        combo_theme = Gtk.ComboBoxText()
        combo_theme.append("system", self.tr("prefs.theme.system"))
        combo_theme.append("light", self.tr("prefs.theme.light"))
        combo_theme.append("dark", self.tr("prefs.theme.dark"))
        current_theme = self.config.get("theme", "system")
        if current_theme not in ("system", "light", "dark"):
            current_theme = "system"
        combo_theme.set_active_id(current_theme)
        grid.attach(combo_theme, 1, row, 1, 1)

        row += 1

        label_cols = Gtk.Label(label=self.tr("prefs.columns"))
        label_cols.set_xalign(0)
        grid.attach(label_cols, 0, row, 1, 1)

        adj_cols = Gtk.Adjustment(
            value=float(self.config.get("columns", 6)),
            lower=3,
            upper=16,
            step_increment=1,
            page_increment=1,
            page_size=0,
        )
        spin_cols = Gtk.SpinButton()
        spin_cols.set_adjustment(adj_cols)
        spin_cols.set_numeric(True)
        grid.attach(spin_cols, 1, row, 1, 1)

        row += 1

        label_recent = Gtk.Label(label=self.tr("prefs.max_recent"))
        label_recent.set_xalign(0)
        grid.attach(label_recent, 0, row, 1, 1)

        adj_recent = Gtk.Adjustment(
            value=float(self.config.get("max_recent", DEFAULT_CONFIG["max_recent"])),
            lower=5,
            upper=200,
            step_increment=1,
            page_increment=5,
            page_size=0,
        )
        spin_recent = Gtk.SpinButton()
        spin_recent.set_adjustment(adj_recent)
        spin_recent.set_numeric(True)
        grid.attach(spin_recent, 1, row, 1, 1)

        row += 1

        label_font = Gtk.Label(label=self.tr("prefs.font_size"))
        label_font.set_xalign(0)
        grid.attach(label_font, 0, row, 1, 1)

        adj_font = Gtk.Adjustment(
            value=float(self.config.get("emoji_font_size", DEFAULT_CONFIG["emoji_font_size"])),
            lower=12,
            upper=72,
            step_increment=1,
            page_increment=4,
            page_size=0,
        )
        spin_font = Gtk.SpinButton()
        spin_font.set_adjustment(adj_font)
        spin_font.set_numeric(True)
        grid.attach(spin_font, 1, row, 1, 1)

        row += 1

        label_lang = Gtk.Label(label=self.tr("prefs.language"))
        label_lang.set_xalign(0)
        grid.attach(label_lang, 0, row, 1, 1)

        combo_lang = Gtk.ComboBoxText()
        combo_lang.append("system", self.tr("prefs.language.system"))

        available_langs = []
        if os.path.isdir(LOCALES_DIR):
            for fname in sorted(os.listdir(LOCALES_DIR)):
                if fname.endswith(".json"):
                    code = fname[:-5]
                    available_langs.append(code)

        for code in available_langs:
            combo_lang.append(code, code)

        current_lang = self.config.get("language", "system")
        if current_lang == "" or current_lang not in (["system"] + available_langs):
            current_lang = "system"
        combo_lang.set_active_id(current_lang)

        grid.attach(combo_lang, 1, row, 1, 1)

        row += 1

        check_remember = Gtk.CheckButton(label=self.tr("prefs.remember_window"))
        check_remember.set_active(bool(self.config.get("remember_window", True)))
        grid.attach(check_remember, 0, row, 2, 1)

        row += 1

        check_debug = Gtk.CheckButton(label=self.tr("prefs.debug"))
        check_debug.set_active(bool(self.config.get("debug", False)))
        grid.attach(check_debug, 0, row, 2, 1)

        row += 1

        box_files = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_open_trans = Gtk.Button(label=self.tr("prefs.open_translations"))
        btn_open_conf = Gtk.Button(label=self.tr("prefs.open_config"))
        box_files.pack_start(btn_open_trans, True, True, 0)
        box_files.pack_start(btn_open_conf, True, True, 0)
        content.pack_start(box_files, False, False, 6)

        box_backup = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_backup = Gtk.Button(label=self.tr("prefs.backup"))
        btn_restore = Gtk.Button(label=self.tr("prefs.restore"))
        box_backup.pack_start(btn_backup, True, True, 0)
        box_backup.pack_start(btn_restore, True, True, 0)
        content.pack_start(box_backup, False, False, 6)

        btn_open_trans.connect("clicked", self.on_open_file_clicked, TRANSLATIONS_FILE)
        btn_open_conf.connect("clicked", self.on_open_file_clicked, CONFIG_FILE)
        btn_backup.connect("clicked", self.on_backup_clicked)
        btn_restore.connect("clicked", self.on_restore_clicked)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            new_theme = combo_theme.get_active_id() or "system"
            new_cols = spin_cols.get_value_as_int()
            new_max_recent = spin_recent.get_value_as_int()
            new_font = spin_font.get_value_as_int()
            new_lang = combo_lang.get_active_id() or "system"
            new_remember = bool(check_remember.get_active())
            new_debug = bool(check_debug.get_active())

            lang_before = self.config.get("language", "system")
            debug_before = bool(self.config.get("debug", False))

            self.config["theme"] = new_theme
            self.config["columns"] = new_cols
            self.config["max_recent"] = new_max_recent
            self.config["emoji_font_size"] = new_font
            self.config["language"] = new_lang
            self.config["remember_window"] = new_remember
            self.config["debug"] = new_debug

            save_config(self.config)

            self.max_recent = new_max_recent
            self.recent_list = self.recent_list[: self.max_recent]
            self.recent_set = set(self.recent_list)
            self.save_recent_list()

            self.flowbox.set_max_children_per_line(new_cols)

            self.apply_emoji_css()
            self.apply_theme()

            if new_debug != debug_before:
                self.update_all_tooltips()

            if new_lang != lang_before:
                self.show_message(
                    self.tr("prefs.language_changed_title"),
                    self.tr("prefs.language_changed_body"),
                )

            self.update_status()

        dialog.destroy()

    # -------------------------------------------------------------------------
    # Preferences helpers: open file / backup / restore
    # -------------------------------------------------------------------------

    def on_open_file_clicked(self, button, path):
        """Open a file with the system default editor (xdg-open)."""
        if not os.path.exists(path):
            try:
                with open(path, "a", encoding="utf-8"):
                    pass
            except Exception as e:
                self.show_message("Error", f"Cannot create file:\n{e}", Gtk.MessageType.ERROR)
                return
        try:
            subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.show_message("Error", f"Cannot open file:\n{e}", Gtk.MessageType.ERROR)

    def on_backup_clicked(self, button):
        """Create a backup zip with config and data files."""
        chooser = Gtk.FileChooserDialog(
            title=self.tr("prefs.backup"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        chooser.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )
        response = chooser.run()
        if response != Gtk.ResponseType.OK:
            chooser.destroy()
            return

        folder = chooser.get_filename()
        chooser.destroy()

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"smorfia-backup-{timestamp}.zip"
        backup_path = os.path.join(folder, backup_name)

        files_to_include = [
            ("emoji_recent.json", RECENT_FILE),
            ("emoji_translations.json", TRANSLATIONS_FILE),
            ("config.json", CONFIG_FILE),
        ]

        try:
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for arcname, real_path in files_to_include:
                    if os.path.exists(real_path):
                        zf.write(real_path, arcname)
            self.show_message(
                self.tr("prefs.backup_done_title"),
                self.tr("prefs.backup_done_body", path=backup_path),
            )
        except Exception as e:
            self.show_message(
                self.tr("prefs.backup_error_title"),
                self.tr("prefs.backup_error_body", error=e),
                Gtk.MessageType.ERROR,
            )

    def on_restore_clicked(self, button):
        """Restore configuration from a backup zip."""
        chooser = Gtk.FileChooserDialog(
            title=self.tr("prefs.restore"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        chooser.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )

        filter_zip = Gtk.FileFilter()
        filter_zip.set_name("ZIP files")
        filter_zip.add_pattern("*.zip")
        chooser.add_filter(filter_zip)

        response = chooser.run()
        if response != Gtk.ResponseType.OK:
            chooser.destroy()
            return

        zip_path = chooser.get_filename()
        chooser.destroy()

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for name in ("emoji_recent.json", "emoji_translations.json", "config.json"):
                    if name not in zf.namelist():
                        continue

                    if name == "emoji_recent.json":
                        dest = RECENT_FILE
                    elif name == "emoji_translations.json":
                        dest = TRANSLATIONS_FILE
                    elif name == "config.json":
                        dest = CONFIG_FILE
                    else:
                        continue

                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with zf.open(name) as src, open(dest, "wb") as dst:
                        dst.write(src.read())

            self.show_message(
                self.tr("prefs.restore_done_title"),
                self.tr("prefs.restore_done_body"),
            )
        except Exception as e:
            self.show_message(
                self.tr("prefs.restore_error_title"),
                self.tr("prefs.restore_error_body", error=e),
                Gtk.MessageType.ERROR,
            )

    # -------------------------------------------------------------------------
    # Generic message dialog helper
    # -------------------------------------------------------------------------

    def show_message(self, title, text, msg_type=Gtk.MessageType.INFO):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            message_format=title,
        )
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    # Create/migrate user files in ~/.config/Smorfia on first run
    initialize_user_environment()

    app = Smorfia()
    app.show_all()
    app.search_entry.grab_focus()
    app.update_status()
    Gtk.main()

