# QuickShot

QuickShot is a **lightweight screenshot utility for Windows**.  
With a simple hotkey, you can capture any region or screen,  
save it instantly, and copy it to the clipboard — ready to paste into any AI tool.

---

## ✨ Features

- **Hotkey-driven capture**
  - `Ctrl + Shift + A` : Select a region and capture (saves as file)
  - `Ctrl + Shift + S` : Capture full screen — supports multi-monitor selection
  - `Ctrl + Shift + Z` : Pin a region to screen as a floating overlay (no file saved)
  - `Ctrl + Shift + Q` : Quit the app

- **AI-optimized image formats**
  - Saves under `Pictures\QuickShots\YYYY-MM-DD\`
  - Supports **PNG, JPEG, and WEBP** — configurable quality for smaller file sizes

- **Clipboard integration**
  - Captured images are automatically copied to the clipboard → just `Ctrl+V` to paste

- **Toast notification**
  - A subtle popup appears in the bottom-right corner after each save
  - Click the toast to open the save folder instantly

- **Pin to screen**
  - Captured region stays on top as a floating window — perfect for referencing while typing prompts
  - Drag to move, right-click or double-click to close

---

## 📂 Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   python quick_region_screenshot.py
   ```
   The app runs in the background and listens for hotkeys.

---

## 🌱 Philosophy

Coding feels like building a waterwheel.  
Where ancient people turned rivers and winds into steady motion,  
I turn flows of information and AI's knowledge into working tools.  
QuickShot is my first waterwheel.
