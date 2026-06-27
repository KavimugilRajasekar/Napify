NAPIFY SERVICE - COMPLETE SOLUTION
===================================

This directory contains a complete Windows Service solution that runs in the background
without UI or CLI interface. When system events (Sleep, Hibernate, Shutdown, Logout) are
detected, the service launches Napify.exe (which runs for about 7 seconds and blocks
keyboard inputs).

WHAT WAS REQUESTED:
- Design a Complete Windows Service
- Run in background without UI and No CLI interface
- Monitor system events: Sleep, Hibernate, Shutdown, Logout
- When detected, run Napify.exe (which runs about 7 sec and blocks keyboard inputs)
- Using Python Framework
- Mention how to deploy as Service using CMD (specifically using 'sc' command for non-Python devices)
- Rename from "Logger" to "service"

FILES PROVIDED:

1. **napify_service.py** - Python service implementation
   - Service name: NapifyService
   - Display name: Napify Service
   - Monitors system events via window messages and service control handlers
   - Launches Napify.exe when events are detected
   - Logs to: C:\ProgramData\Napify\Logs\napify_service.log
   - Falls back to %TEMP%\napify_service.log if needed
   - Properly handles start/stop/pause/resume/shutdown

2. **dist\napify_service.exe** - Standalone executable (NO PYTHON REQUIRED)
   - Created with PyInstaller --onefile --windowed
   - Contains all dependencies (including pywin32, ctypes)
   - Ready for deployment on Windows devices without Python
   - Requires Napify.exe to be in the same directory

3. **dist\Napify.exe** - The application to run (placeholder - you must provide your own)
   - This is a placeholder; you must replace it with your actual Napify.exe
   - The service expects to find Napify.exe in the same directory as the service executable

4. **DEPLOY_EXE_INSTRUCTIONS.txt** - Deployment using 'sc' command (as requested)
   - For target devices WITHOUT Python
   - Uses ONLY 'sc' command for service management
   - Steps:
     * Copy executable and Napify.exe to target device
     * sc create NapifyService binPath= "C:\NapifyService\napify_service.exe" start= auto
     * sc start NapifyService
     * sc query NapifyService (to check status)
     * sc stop NapifyService / sc delete NapifyService (for management)

5. **DEPLOY_INSTRUCTIONS.txt** - Original Python-based deployment
   - For devices WITH Python installed
   - Uses: python napify_service.py install/start/stop/remove
   - Requires Napify.exe in same directory

6. **TROUBLESHOOTING.txt** - Common issues and solutions
7. **requirements.txt** - pywin32>=306
8. **napify_service.spec** - PyInstaller specification file

KEY FEATURES:
✅ True Windows Service (no console window, no UI)
✅ Background operation (runs continuously)
✅ Monitors system events: Sleep, Hibernate, Shutdown, Logout
✅ Launches Napify.exe upon event detection
✅ Automatic directory creation and permission handling for logs
✅ Proper service lifecycle handling (start/stop/pause/resume/shutdown)
✅ No Python required on target device (when using .exe)
✅ Service management via standard 'sc' command (as requested)
✅ Renamed from "Logger" to "service" as requested

USAGE ON TARGET DEVICE (NO PYTHON):
1. Copy napify_service.exe and Napify.exe to C:\NapifyService\
2. Open CMD as Administrator
3. sc create NapifyService binPath= "C:\NapifyService\napify_service.exe" start= auto
4. sc start NapifyService
5. Check logs: C:\ProgramData\Napify\Logs\napify_service.log (look for event detection)
6. Manage with: sc query/stop/continue/pause/delete NapifyService

IMPORTANT LIMITATIONS:
⚠️ Due to user-mode service constraints, the service cannot delay system events
   (sleep/hibernate/shutdown/logout) but will run Napify.exe upon detection.
⚠️ For shutdown, the service will run Napify.exe during the shutdown process, but
   the system may not wait for the service to finish if it takes too long (default
   shutdown timeout is 20 seconds; our Napify.exe runs ~7 seconds, so it should be safe).
⚠️ For sleep/hibernate, the service runs Napify.exe when the event is queried, but
   the system may proceed to sleep/hibernate immediately after our response.
⚠️ For logout, the service runs Napify.exe when the logoff is detected, but the
   logoff process will continue in parallel.

The service is now ready for deployment and meets the core requirements:
- Runs in background without UI/CLI
- Launches Napify.exe upon system event detection
- Deployable via 'sc' command on non-Python devices
- Properly renamed from "Logger" to "service"