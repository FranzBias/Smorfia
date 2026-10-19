# 🎭 Smorfia

### A desktop emoji picker for Linux — formerly **GeppEmoji**

<img src="../assets/main.png" width="420" alt="Smorfia main window">

Smorfia is a fast, friendly **emoji picker for Linux desktops** (Cinnamon, GNOME, XFCE, KDE on X11…).
It stays out of the way until you need it, then drops the emoji right where you were typing.

> **Pick. Paste. Done.** All with a single global shortcut.

*Smorfia* is Italian for a facial expression — and every emoji is a tiny one.
Until version 1.0.0 the app was called **GeppEmoji**; from 2.0.0 on it is Smorfia, and your data moves over by itself.

---

## 🚀 Highlights

- 🔍 **Search** by name, English keywords, keywords in your language and **your own tags**
- 🗂️ **Sidebar** with icons: All, Recent, Favorites and every Unicode group
- 🏷️ **Tooltips** that show your tags next to the English keywords
- 📌 **Multi-emoji buffer** and **auto-paste** into the previous window (`xdotool`)
- 👋 **Skin tones**, only where they make sense
- 🎛️ **Preferences**: theme, columns, emoji size, interface language, backup & restore
- 🛠️ **Database update** from the official Unicode `emoji-test.txt`

<img src="../assets/search.png" width="420" alt="Search with custom tags">

---

## 📦 Install

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 xdotool
sudo apt install ./smorfia_2.0.0-1_all.deb     # from the Releases page
smorfia
```

Or, without root:

```bash
git clone https://github.com/FranzBias/Smorfia.git
cd Smorfia
./install_smorfia.sh
```

Full instructions, shortcuts and translations in 10 languages are in the
[README](https://github.com/FranzBias/Smorfia#readme).

---

## ☕ Support

If Smorfia makes your day a bit more expressive:
👉 **[Donate with PayPal](https://www.paypal.com/donate/?hosted_button_id=HUF5MYDG465RY)**

![Donate QR-Code](../assets/DonaQR-Code.png)

---

Made with ❤️ by **Francesco (FranzBias)** · Released under the **MIT License**.
