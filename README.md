# Napify

> A lightweight Windows utility that briefly takes over the screen with a calming animation — used to discourage users from yanking the laptop lid / mashing the power button during Sleep, Hibernate, Shutdown, or Logoff events.

Napify is split into two cooperating pieces:

| Component | Role |
|-----------|------|
| **Napify/** | The visible app — a fullscreen, frameless `pywebview` window that plays a Lottie animation and blocks keyboard input for ~7 seconds. |
| **Napify_Service/** | A background Windows Service that watches for system events (Sleep, Hibernate, Shutdown, Logoff) and launches `Napify.exe` when they fire. |

Together they form a "please don't touch your computer right now" shield that fires automatically at exactly the wrong moment to do something destructive.

---

## 📖 About this Project

### The problem
On shared / lab / kiosk Windows machines, a recurring failure mode is users who see the laptop lid closing, the shutdown spinner, or the lock screen and immediately:

- slam the lid back open,
- mash keys to "cancel" the shutdown,
- yank the power cable,
- or sign back in during a logoff.

These actions routinely corrupt in-progress updates, half-written user profiles, and pending BitLocker / Group Policy operations.

### The goal
Inject a brief, calming, **input-blocking** fullscreen animation at the moment a system event begins — long enough for the OS to commit whatever it needs to commit, short enough that nobody's workflow is meaningfully disrupted.

### Design constraints
- **Zero user interaction** — no console window, no tray icon, no prompts.
- **Trigger automatically** on Sleep, Hibernate, Shutdown, and Logoff.
- **Survive without Python** on the target machine — must deploy as a standalone `.exe` Windows Service.
- **Deployed via `sc`** — no MSI, no PowerShell, no third-party installers. Plain `sc create` / `sc start` is enough.
- **Non-destructive to the system event itself** — the service observes events and runs the animation; it does not (and cannot, from user-mode) delay or cancel them.

### How it works (end-to-end)
```
[OS event: Sleep / Hibernate / Shutdown / Logoff]
            │
            ▼
[NapifyService — running as a Windows Service]
  • Window procedure receives WM_POWERBROADCAST or
    WM_WTSSESSION_CHANGE via WTSRegisterSessionNotification
  • Calls CreateProcessW("Napify.exe")
            │
            ▼
[Napify.exe — fullscreen pywebview app]
  • Opens frameless, fullscreen, always-on-top window
  • Plays animation/animation.html (Lottie)
  • Injects JS that swallows keydown / keyup / keypress
  • Waits ~7 seconds, then exits
```

The service continues running and waits for the next event.

---

## 🧩 Repository layout

```
Napify/
├── README.md                  ← you are here
├── .gitignore
│
├── Napify/                    ← The visible app
│   ├── main.py                ← pywebview entrypoint
│   ├── animation/
│   │   ├── animation.html     ← Lottie player host page
│   │   └── lottie.min.js      ← Lottie runtime
│   ├── dist/main.exe          ← PyInstaller-built standalone
│   ├── main.spec              ← PyInstaller spec
│   └── requirements.txt
│
└── Napify_Service/            ← The Windows Service
    ├── napify_service.py      ← pywin32 service implementation
    ├── dist/
    │   ├── napify_service.exe ← standalone service (no Python needed)
    │   └── Napify.exe         ← the app above, renamed
    ├── build/                 ← PyInstaller scratch
    ├── napify_service.spec    ← PyInstaller spec
    ├── requirements.txt
    ├── DEPLOY_INSTRUCTIONS.txt     ← Python-based deployment
    ├── DEPLOY_EXE_INSTRUCTIONS.txt ← 'sc' deployment (no Python)
    ├── TROUBLESHOOTING.txt
    └── README_SUMMARY.txt
```

---

## 🚀 Quick start

### Prerequisites
- Windows 10 / 11
- Either:
  - **No Python on target** — use the prebuilt `dist/napify_service.exe` and `dist/Napify.exe`, **or**
  - **Python 3.9+** on the target machine — for development / source-based deployment.

### Option A — Deploy the prebuilt binaries (recommended, no Python required)

Open an **Administrator** Command Prompt on the target machine:

```bat
:: 1. Place the two executables somewhere stable
mkdir C:\NapifyService
copy Napify_Service\dist\napify_service.exe C:\NapifyService\
copy Napify_Service\dist\Napify.exe            C:\NapifyService\

:: 2. Register the service
sc create NapifyService binPath= "C:\NapifyService\napify_service.exe" start= auto

:: 3. Start it
sc start NapifyService

:: 4. (Optional) verify
sc query NapifyService
```

Logs land in `C:\ProgramData\Napify\Logs\napify_service.log`.

### Option B — Run from source (development)

```bash
# 1. App
cd Napify
pip install -r requirements.txt
python main.py

# 2. Service (in a separate, elevated shell)
cd ../Napify_Service
pip install -r requirements.txt
python napify_service.py install
python napify_service.py start
```

---

## 🛠 Development

### Rebuild the executables

Both components ship with PyInstaller spec files.

```bash
# App
cd Napify
pyinstaller main.spec

# Service
cd ../Napify_Service
pyinstaller napify_service.spec
```

### Edit the animation

The fullscreen animation is a standard Lottie JSON embedded in `Napify/animation/animation.html`. Swap the Lottie JSON for any calming animation you like — keep file size modest so the executable stays small.

### Useful service commands

| Action | Command |
|--------|---------|
| Status | `sc query NapifyService` |
| Stop | `sc stop NapifyService` |
| Start | `sc start NapifyService` |
| Disable autostart | `sc config NapifyService start= demand` |
| Remove | `sc delete NapifyService` |

---

## ⚠️ Known limitations

These come from running as a **user-mode Windows Service** and are by design — the service cannot elevate above the OS:

- **Sleep / Hibernate** — the service fires `Napify.exe` when the event is queried, but the OS may proceed to sleep immediately after. The animation effectively plays in the ~7 s "you're going to sleep" window on supported hardware.
- **Shutdown** — the animation plays during shutdown, but the OS will not wait beyond its default 20 s shutdown timeout. `Napify.exe` is sized to finish well under that.
- **Logoff** — runs in parallel with the logoff process; the user will see both happen.

If you need a hard delay (true "block shutdown until animation finishes"), you would need a kernel-mode filter driver — that is deliberately out of scope here.

---

## 🧰 Troubleshooting

- **Service won't start** → run Command Prompt **as Administrator**, check the log at `C:\ProgramData\Napify\Logs\napify_service.log`.
- **`Napify.exe` not found** → it must sit in the **same directory** as `napify_service.exe`.
- **Animation doesn't appear** → check that the target desktop session is interactive (Session 1+); service runs in Session 0 and uses `CreateProcessW` to spawn the GUI app in the user's session via the standard trigger flow.
- **Want to watch it fire** → trigger Sleep / Logoff and tail the log file.

Full troubleshooting notes live in `Napify_Service/TROUBLESHOOTING.txt`.

---

## 📄 License

No license file is currently committed. Treat this as **All rights reserved** by the project owner until a `LICENSE` file is added.

---

## 🙏 Credits

- [pywebview](https://pywebview.flowrl.com/) — the frameless webview host.
- [Lottie](https://airbnb.io/lottie-web/) — the animation runtime.
- [pywin32](https://github.com/mhammond/pywin32) — Windows Service glue.
- [PyInstaller](https://pyinstaller.org/) — bundles everything into standalone `.exe`s.