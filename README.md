# Napify

### A calm, full-screen animation that briefly takes over shared Windows machines whenever Sleep, Hibernate, Shutdown, or Logoff fires.

[![Language](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](#)
[![Topic](https://img.shields.io/badge/Windows--Service-lightgrey?logo=windows&logoColor=white)](#)
[![Topic](https://img.shields.io/badge/Win32--ctypes-purple?logo=windowsterminal&logoColor=white)](#)
[![Topic](https://img.shields.io/badge/Lottie-Animation-00DDB3?logo=airbnb&logoColor=white)](#)
[![Topic](https://img.shields.io/badge/pywebview-GUI-orange)](#)
[![Topic](https://img.shields.io/badge/PyInstaller-EXE-blueviolet?logo=python&logoColor=white)](#)

## Overview

Napify is a small Windows utility that runs on shared or lab machines. Whenever the system fires a Sleep, Hibernate, Shutdown, or Logoff event, Napify briefly takes over the entire screen with a calming Lottie animation, blocks keyboard input, and only lets the event proceed for about seven seconds. The intent is to give users a clear visual signal that the machine is shutting down and to discourage them from yanking the laptop lid or spamming the power button mid-shutdown.

The project exists because the standard Windows shutdown UI on a lab or shared box is often missed or dismissed in a hurry. A short, full-screen, distraction-free animation gives the user a moment to back away from the lid, the dock, and the keyboard, and it buys the operating system time to commit the shutdown cleanly.

## Key Features

- **Fullscreen, frameless animation**: `pywebview` opens `animation/animation.html` as a frameless, fullscreen, non-resizable window
- **Keyboard blocking**: JavaScript injected via `window.evaluate_js` swallows `keydown`, `keyup`, and `keypress` events at the capture phase
- **~7 second timeout**: the launching service waits up to 7 seconds (`WaitForSingleObject(pi.hProcess, 7000)`) before continuing
- **Windows service that owns the events**: a `win32serviceutil.ServiceFramework` subclass (`NapifyService`) registers for `WM_POWERBROADCAST` and `WM_WTSSESSION_CHANGE`
- **Sleep / Hibernate / Shutdown handling**: `PBT_APMQUERYSUSPEND` and `PBT_APMQUERYSTANDBY` launch the GUI as soon as the OS asks
- **Logoff handling**: `WTS_SESSION_LOGOFF` (via `WTSRegisterSessionNotification` with `NOTIFY_FOR_ALL_SESSIONS`) launches the GUI when the user signs out
- **Native Win32 window procedure**: pure `ctypes` definition of `WNDPROCTYPE`, `WNDCLASSW`, `CreateWindowExW`, message loop, and shutdown via `PostQuitMessage`
- **Power request hooks (optional path)**: `POWER_REQUEST_CONTEXT` struct + `PowerCreateRequest` / `PowerSetRequest` / `PowerClearRequest` declarations and `SetThreadExecutionState` (`ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED`) are wired in for systems that need to suppress sleep during the animation
- **Background logging**: per-event log lines written to `C:\ProgramData\Napify\Logs\napify_service.log`, with a fallback to the Windows event log via `servicemanager.LogErrorMsg`
- **PyInstaller packaging**: `main.spec` and `napify_service.spec` produce standalone `.exe` files that drop straight into `C:\Program Files\Napify\`
- **Lottie animation**: rendered through `lottie.min.js` for smooth, lightweight playback in the webview

## Architecture Overview

Napify is split into two cooperating pieces, each in its own folder:

- `Napify/` — the **GUI**. A small `pywebview` application (`Napify/main.py`) that opens `Napify/animation/animation.html` as a frameless, fullscreen window, runs the Lottie animation, and blocks keyboard input via JavaScript.
- `Napify_Service/` — the **service**. A `pywin32`-based Windows service (`Napify_Service/napify_service.py`) that registers a hidden window class (`NapifyServiceWindowClass`), listens for `WM_POWERBROADCAST` and `WM_WTSSESSION_CHANGE`, and launches `Napify.exe` synchronously for ~7 seconds on every relevant event.

The service is the trigger; the GUI is the visual payload. Communication is one-way: the service spawns the GUI process, the GUI exits on its own, and the service resumes its message loop.

Key pieces in `napify_service.py`:

- `window_proc` — the `ctypes`-defined `WNDPROCTYPE` that handles `WM_POWERBROADCAST`, `WM_WTSSESSION_CHANGE`, `WM_DESTROY`, and `WM_CLOSE`
- `run_napify_exe` — uses `kernel32.CreateProcessW` to launch `Napify.exe` (resolved via `kernel32.GetModuleFileNameW` + `shlwapi.PathRemoveFileSpecW`), then waits up to 7 seconds with `WaitForSingleObject`
- `NapifyService.SvcDoRun` — registers the window class, creates the window, registers for session-change notifications, and runs a `PeekMessageW` + `WaitForSingleObject` loop until the stop event fires
- `NapifyService.SvcStop` — sets the stop event and posts `WM_CLOSE` to the window to break the message loop
- `NapifyService.SvcShutdown` — fires the GUI when Windows asks the service to shut down

Key pieces in `Napify/main.py`:

- `webview.create_window` with `frameless=True`, `easy_drag=False`, `resizable=False`, `fullscreen=True`
- `block_keyboard_input(window)` — injects the `keydown`/`keyup`/`keypress` blockers at the capture phase
- `webview.start(..., debug=False)` — entry point that runs the blocker callback on window creation

## Tech Stack

| Component | Choice | Purpose |
|-----------|--------|---------|
| Language | Python 3.9+ | Service + GUI |
| Windows service | `pywin32` (>=306) | `win32serviceutil`, `servicemanager`, `win32service`, `win32event` |
| GUI runtime | `pywebview` (>=4.0) | Frameless, fullscreen browser surface |
| Animation | Lottie via `lottie.min.js` | Smooth, lightweight fullscreen playback |
| Typography | Playwrite US Modern variable font | Calm, hand-drawn feel inside the webview |
| Native interop | `ctypes` (`WinDLL`) | `user32`, `kernel32`, `powrprof`, `wtsapi32`, `shlwapi` |
| Native types | `ctypes.wintypes` (`HWND`, `MSG`, `WNDCLASSW`, `STARTUPINFOW`, `PROCESS_INFORMATION`, `POWER_REQUEST_CONTEXT`) | Strongly-typed Win32 calls |
| Service framework | `win32serviceutil.ServiceFramework` | `NapifyService` base |
| Logging | Plain file logging under `C:\ProgramData\Napify\Logs\` + `servicemanager.LogErrorMsg` fallback | Per-event audit trail |
| Packaging | PyInstaller (`main.spec`, `napify_service.spec`) | Standalone `.exe` files |

## Folder Structure

```
Napify/
├── Napify/                       # GUI application (spawned by the service)
│   ├── main.py                   # pywebview fullscreen window + keyboard blocker
│   ├── main.spec                 # PyInstaller spec for Napify.exe
│   ├── requirements.txt          # pywebview>=4.0
│   ├── animation/
│   │   ├── animation.html        # Webview entry, hosts the Lottie animation
│   │   ├── lottie.min.js         # Lottie web player
│   │   └── PlaywriteUSModern-VariableFont_wght.ttf
│   └── dist/                     # PyInstaller output (Napify.exe)
├── Napify_Service/               # Windows service (event listener + launcher)
│   ├── napify_service.py         # pywin32 service with ctypes Win32 window proc
│   ├── napify_service.spec       # PyInstaller spec for the service exe
│   ├── requirements.txt          # pywin32>=306
│   ├── README_SUMMARY.txt        # Deployment summary
│   ├── DEPLOY_INSTRUCTIONS.txt   # End-to-end deployment notes
│   ├── DEPLOY_EXE_INSTRUCTIONS.txt
│   ├── TROUBLESHOOTING.txt       # Common deployment gotchas
│   └── dist/                     # PyInstaller output
└── README.md
```

## Installation / Setup

### Prerequisites

- Windows 10 / 11 or Windows Server 2019+
- Python 3.9 or newer
- Administrator privileges (required to install a Windows service)
- PyInstaller if you want to produce standalone `.exe` files

### Install dependencies

```bash
# GUI
cd Napify
pip install -r requirements.txt

# Service
cd ../Napify_Service
pip install -r requirements.txt
```

### Run the GUI standalone (smoke test)

```bash
cd Napify
python main.py
```

A fullscreen, frameless window should appear with the Lottie animation. Keyboard input (any key) should not affect the underlying desktop. Close the window with the mouse via the OS shortcut if needed; for a quick test the GUI can be killed from Task Manager.

### Build the executables (recommended)

```bash
# GUI exe
cd Napify
pyinstaller main.spec

# Service exe
cd ../Napify_Service
pyinstaller napify_service.spec
```

Drop the resulting `Napify.exe` and `NapifyService.exe` into `C:\Program Files\Napify\`. Both `.spec` files expect a sibling layout so the service can find the GUI by relative path.

### Install the Windows service

From an Administrator `cmd.exe`:

```bash
cd "C:\Program Files\Napify"
napify_service.exe install
napify_service.exe start
```

Use `napify_service.exe stop` and `napify_service.exe remove` for teardown. See `Napify_Service/DEPLOY_INSTRUCTIONS.txt` for the full sequence.

## Usage / Examples

### Trigger the animation by hand

1. Open **Settings -> System -> Power**.
2. Click **Shut down** — Napify intercepts via `WM_POWERBROADCAST` / `PBT_APMQUERYSUSPEND` and pops the fullscreen animation.
3. The animation runs for ~7 seconds; the GUI process is then reaped.

### Trigger via logoff

1. Press **Ctrl+Alt+Del** and choose **Sign out**.
2. The service receives `WM_WTSSESSION_CHANGE` with `WTS_SESSION_LOGOFF` and launches the GUI.

### Check the service log

```text
C:\ProgramData\Napify\Logs\napify_service.log
```

Example entries:

```text
[2026-06-28 09:00:01] Service started.
[2026-06-28 09:14:22] Shutdown event received.
[2026-06-28 17:42:08] Service stopped.
```

### Tail the Windows event log on failures

If the file logger fails (permissions, full disk, etc.), `servicemanager.LogErrorMsg` records the error in the **Application** event log under the source **NapifyService**.

## Configuration

Napify is configuration-light by design. The knobs that matter live as constants near the top of `napify_service.py`:

| Constant | Default | Meaning |
|----------|---------|---------|
| `PBT_APMQUERYSUSPEND` | `0x0000` | Sleep query power broadcast |
| `PBT_APMQUERYSTANDBY` | `0x0001` | Hibernate query power broadcast |
| `WTS_SESSION_LOGOFF` | `0x00000007` | Session logoff |
| `WM_POWERBROADCAST` | `0x0218` | Window message for power events |
| `WM_WTSSESSION_CHANGE` | `0x002B` | Window message for session changes |
| `WM_QUIT` | `0x0012` | Message loop break |
| `WM_CLOSE` | `0x0010` | Window close |
| `WM_DESTROY` | `0x0002` | Window destruction |
| `ES_CONTINUOUS` | `0x80000000` | `SetThreadExecutionState` flag |
| `ES_SYSTEM_REQUIRED` | `0x00000001` | Prevent sleep while the animation runs |
| `ES_AWAYMODE_REQUIRED` | `0x00000040` | Prevent away-mode sleep |
| Wait timeout | `7000` ms | `WaitForSingleObject` budget for the GUI process |
| Service name | `NapifyService` | `_svc_name_` |
| Display name | `Napify Service` | `_svc_display_name_` |
| Window class | `NapifyServiceWindowClass` | Registered at start |
| Log directory | `C:\ProgramData\Napify\Logs` | Created on demand |
| Log file | `napify_service.log` | Append-only, timestamped |

The GUI is configured inside `Napify/main.py`:

| Setting | Value | Source |
|---------|-------|--------|
| Window title | `Napify` | `webview.create_window` |
| Entry URL | `animation/animation.html` | `webview.create_window` |
| Frameless | `True` | `webview.create_window` |
| Fullscreen | `True` | `webview.create_window` |
| Resizable | `False` | `webview.create_window` |
| Easy drag | `False` | `webview.create_window` |
| Keyboard blocker | injected via `evaluate_js` | `block_keyboard_input` |
| Debug | `False` | `webview.start` |

## Learning Outcomes

- Implementing a real Windows service in pure Python with `pywin32` and `ctypes`
- Defining a `WNDCLASSW` and a window procedure entirely in ctypes — no SWIG, no C extension
- Translating Win32 power and session events into a single, well-defined launch trigger
- Spawning a GUI process from a service context using `CreateProcessW` and waiting for it to exit
- Building a distraction-free UX with `pywebview`: frameless, fullscreen, non-resizable, keyboard-blocked
- Hosting a Lottie animation inside a webview for smooth, lightweight playback
- Wiring `WTSRegisterSessionNotification` with `NOTIFY_FOR_ALL_SESSIONS` to catch every logoff on a multi-user box
- Packaging both halves with PyInstaller so the deployment is "copy two `.exe` files and run one install command"

## Challenges Faced

- Two-process deployment: the service has to find the GUI binary next to itself, and the GUI has to be self-contained so it can be launched from a session-zero context
- Window-message routing under ctypes: the `WNDPROCTYPE` signature has to be defined exactly or messages will not arrive
- Power events arrive at unpredictable times, so the service loop cannot block on a single call — `PeekMessageW` plus a 100 ms sleep keeps it responsive without spinning the CPU
- Logs need a real path that survives service restarts; `C:\ProgramData\Napify\Logs` was chosen specifically because it's writable by services
- PyInstaller bundles change working directory at runtime, so resolving the GUI binary uses `kernel32.GetModuleFileNameW` + `shlwapi.PathRemoveFileSpecW` instead of `__file__`

## Future Improvements

- A small installer (Inno Setup or MSI) that drops both `.exe` files into `C:\Program Files\Napify\` and registers the service in one click
- Configurable animation duration (currently hard-coded to 7 seconds)
- A system-tray quick-test that launches the GUI without firing a real shutdown event
- Localization for the (optional) overlay text
- Theming: a small set of calming animations the admin can pick from at install time
- Telemetry counter for how often Napify actually fires per machine per week

## Contribution Guidelines

1. Fork the repository and create a feature branch off `main`.
2. Keep GUI and service responsibilities separate. Cross-process changes should be coordinated in one PR.
3. If you add a new event trigger, document the constants and the message-loop path in this README.
4. Avoid changing the 7-second wait without discussion; it is the project's defining behaviour.
5. Run both halves locally: `python Napify/main.py` for the GUI, and `python Napify_Service/napify_service.py` (with `pywin32` privileges) for the service.
6. Update the deploy and troubleshooting notes in `Napify_Service/DEPLOY_INSTRUCTIONS.txt` and `TROUBLESHOOTING.txt` for any operational change.

## License

This project is licensed under the MIT License.

## Author

**Kavimugil Rajasekar**

- Portfolio: https://KavimugilRajasekar.github.io
- GitHub: https://github.com/KavimugilRajasekar