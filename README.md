# MDI Auto Refresh

A tiny Chrome extension (Mac) that clicks the ⟳ refresh button on the MD Integrations
**Encounters** list every 30 seconds, even when the tab is in the background.

## 👉 [Step-by-step install guide](https://gabo10101.github.io/mdi-auto-refresh/)

[⬇ Download the latest version](https://github.com/gabo10101/mdi-auto-refresh/releases/latest/download/mdi-auto-refresh.zip),
unzip it, open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, select the folder.

- Only touches `app.mdintegrations.com/tabs/cases/list/*`, never an open case.
- Mac notification on a new assigned encounter, on MDI's inactivity lock, and on logout.
- Keeps the Mac from idle sleep while the list is open; protects the tab from Chrome's Memory Saver.
- **Auto login:** click the extension icon, enter your MDI email + password. If MDI logs you out, it logs back in and returns to the list (max 3 tries, so a wrong password can't lock the account). The password is stored unencrypted on this computer, in Chrome's extension storage.
- Does **not** bypass MDI's 20-minute inactivity lock (a HIPAA safeguard).
- No data leaves the computer.

Not affiliated with or endorsed by MD Integrations.

## Development

`python3 tests/test_extension.py` loads the extension into Chromium (Playwright) against fake MDI pages (~105 s).
`python3 tests/test_extension.py --demo` opens the same setup in a visible window to click around in.
Release zip: `cd .. && zip -r mdi-auto-refresh.zip mdi-auto-refresh/{manifest.json,background.js,popup.html,popup.js,icon.png,LICENSE}`

Made by **Gábor Kiss** · [MIT License](LICENSE)
