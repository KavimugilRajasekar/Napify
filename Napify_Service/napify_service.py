import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import os
import ctypes
from ctypes import wintypes
import threading

# Constants for power broadcast
PBT_APMQUERYSUSPEND = 0x0000
PBT_APMQUERYSTANDBY = 0x0001

# Constants for session change
WTS_SESSION_LOGOFF = 0x00000007

# Constants for window messages
WM_POWERBROADCAST = 0x0218
WM_WTSSESSION_CHANGE = 0x002B
WM_CREATE = 0x0001
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010

# Constants for window styles
WS_OVERLAPPEDWINDOW = 0x00CF0000
CW_USEDEFAULT = 0x80000000

# Constants for thread execution state
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

# Load necessary libraries
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
powrprof = ctypes.WinDLL('powrprof', use_last_error=True)
wtsapi32 = ctypes.WinDLL('wtsapi32', use_last_error=True)

# Define function prototypes
# RegisterPowerSettingNotification
HPOWERNOTIFY = wintypes.HANDLE
user32.RegisterPowerSettingNotification.argtypes = [wintypes.HWND, ctypes.POINTER(ctypes.GUID), wintypes.DWORD]
user32.RegisterPowerSettingNotification.restype = HPOWERNOTIFY

# PowerCreateRequest
POWER_REQUEST_CONTEXT_VERSION = 0
class POWER_REQUEST_CONTEXT(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.DWORD),
        ("Flags", wintypes.DWORD),
        ("Reason", wintypes.BYTE * 128),  # Simple string buffer
    ]
user32.PowerCreateRequest.argtypes = [ctypes.POINTER(POWER_REQUEST_CONTEXT)]
user32.PowerCreateRequest.restype = wintypes.HANDLE

# PowerSetRequest
user32.PowerSetRequest.argtypes = [wintypes.HANDLE, wintypes.DWORD]
user32.PowerSetRequest.restype = wintypes.BOOL

# PowerClearRequest
user32.PowerClearRequest.argtypes = [wintypes.HANDLE, wintypes.DWORD]
user32.PowerClearRequest.restype = wintypes.BOOL

# SetThreadExecutionState
kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
kernel32.SetThreadExecutionState.restype = wintypes.DWORD

# CreateProcessW
kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,  # lpApplicationName
    wintypes.LPWSTR,   # lpCommandLine
    wintypes.LPVOID,   # lpProcessAttributes
    wintypes.LPVOID,   # lpThreadAttributes
    wintypes.BOOL,     # bInheritHandles
    wintypes.DWORD,    # dwCreationFlags
    wintypes.LPVOID,   # lpEnvironment
    wintypes.LPCWSTR,  # lpCurrentDirectory
    ctypes.POINTER(wintypes.STARTUPINFOW),
    ctypes.POINTER(wintypes.PROCESS_INFORMATION)
]
kernel32.CreateProcessW.restype = wintypes.BOOL

# WaitForSingleObject
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD

# TerminateProcess
kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.TerminateProcess.restype = wintypes.BOOL

# CloseHandle
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

# GetModuleFileNameW
kernel32.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
kernel32.GetModuleFileNameW.restype = wintypes.DWORD

# PathRemoveFileSpecW (from shlwapi)
shlwapi = ctypes.WinDLL('shlwapi', use_last_error=True)
shlwapi.PathRemoveFileSpecW.argtypes = [wintypes.LPWSTR]
shlwapi.PathRemoveFileSpecW.restype = wintypes.BOOL

# WTSRegisterSessionNotification
wtsapi32.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
wtsapi32.WTSRegisterSessionNotification.restype = wintypes.BOOL

# WTSUnRegisterSessionNotification
wtsapi32.WTSUnRegisterSessionNotification.argtypes = [wintypes.HWND]
wtsapi32.WTSUnRegisterSessionNotification.restype = wintypes.BOOL

# Define the GUID for console display state (not used directly for our purpose, but we might register for power settings)
# We are handling WM_POWERBROADCAST directly, so we don't need to register for specific power settings.
# However, to get PBT_APMQUERYSUSPEND and PBT_APMQUERYSTANDBY, we just need to handle WM_POWERBROADCAST.

# Define the window procedure
def window_proc(hwnd, msg, wparam, lparam):
    if msg == WM_POWERBROADCAST:
        if wparam == PBT_APMQUERYSUSPEND or wparam == PBT_APMQUERYSTANDBY:
            # Run Napify.exe
            run_napify_exe()
            # Return TRUE to indicate we can delay (though we are not really delaying the event)
            return True
    elif msg == WM_WTSSESSION_CHANGE:
        if wparam == WTS_SESSION_LOGOFF:
            run_napify_exe()
            return True
    elif msg == WM_DESTROY:
        ctypes.windll.user32.PostQuitMessage(0)
        return 0
    elif msg == WM_CLOSE:
        # We don't destroy the window on close, we hide it or ignore.
        # Return 0 to prevent default handling (which would destroy the window)
        return 0
    # Default window procedure
    return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

# Convert the window procedure to a function pointer
WNDPROCTYPE = ctypes.WINFUNCTYPE(
    wintypes.LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM
)
window_proc_ptr = WNDPROCTYPE(window_proc)

# Global variable to hold the window handle (so we can destroy it on stop)
g_hwnd = None
g_hinstance = None

def run_napify_exe():
    """Launch Napify.exe and wait for it to finish (up to 7 seconds)."""
    try:
        # Get the directory of the current executable
        szPath = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH + 1)
        kernel32.GetModuleFileNameW(None, szPath, ctypes.wintypes.MAX_PATH)
        # Remove the file name
        shlwapi.PathRemoveFileSpecW(szPath)
        # Add Napify.exe
        szNapifyPath = ctypes.create_unicode_buffer(szPath.value + "\\Napify.exe", len(szPath.value) + len("\\Napify.exe") + 1)

        # Prepare startup info
        si = wintypes.STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        pi = wintypes.PROCESS_INFORMATION()

        # Create the process
        if kernel32.CreateProcessW(
            szNapifyPath,  # lpApplicationName
            None,          # lpCommandLine
            None,          # lpProcessAttributes
            None,          # lpThreadAttributes
            False,         # bInheritHandles
            0,             # dwCreationFlags
            None,          # lpEnvironment
            None,          # lpCurrentDirectory
            ctypes.byref(si),
            ctypes.byref(pi)
        ):
            # Wait for up to 7 seconds
            kernel32.WaitForSingleObject(pi.hProcess, 7000)
            # Close handles
            kernel32.CloseHandle(pi.hThread)
            kernel32.CloseHandle(pi.hProcess)
        else:
            # Log error if needed
            pass
    except Exception as e:
        # Log error if needed
        pass

class NapifyService(win32serviceutil.ServiceFramework):
    _svc_name_ = "NapifyService"
    _svc_display_name_ = "Napify Service"
    _svc_description_ = "A background service that monitors system events and runs Napify.exe."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        # Post a quit message to the window to break the message loop
        if g_hwnd:
            ctypes.windll.user32.PostMessageW(g_hwnd, WM_CLOSE, 0, 0)
        self.LogToFile("Service stopped.")

    def SvcDoRun(self):
        global g_hwnd, g_hinstance
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.LogToFile("Service started.")

        # Get the instance handle
        g_hinstance = kernel32.GetModuleHandleW(None)

        # Define the window class
        wc = wintypes.WNDCLASSW()
        wc.lpfnWndProc = window_proc_ptr
        wc.hInstance = g_hinstance
        wc.lpszClassName = "NapifyServiceWindowClass"
        wc.hbrBackground = ctypes.c_int(1 + 5)  # COLOR_WINDOW+1

        # Register the window class
        if not user32.RegisterClassW(ctypes.byref(wc)):
            self.LogToFile("Failed to register window class.")
            return

        # Create the window
        g_hwnd = user32.CreateWindowExW(
            0,                              # dwExStyle
            wc.lpszClassName,               # lpClassName
            "NapifyServiceWindow",          # lpWindowName
            WS_OVERLAPPEDWINDOW,            # dwStyle
            CW_USEDEFAULT, CW_USEDEFAULT,   # x, y
            CW_USEDEFAULT, CW_USEDEFAULT,   # width, height
            None,                           # hWndParent
            None,                           # hMenu
            g_hinstance,                    # hInstance
            None                            # lpParam
        )
        if not g_hwnd:
            self.LogToFile("Failed to create window.")
            return

        # Register for session change notifications
        if not wtsapi32.WTSRegisterSessionNotification(g_hwnd, 0x00000001):  # NOTIFY_FOR_ALL_SESSIONS
            self.LogToFile("Failed to register for session change notifications.")

        # Message loop
        msg = wintypes.MSG()
        while win32event.WaitForSingleObject(self.hWaitStop, 0) != win32event.WAIT_OBJECT_0:
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):  # PM_REMOVE
                if msg.message == 0x0012:  # WM_QUIT
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                # No message, sleep a bit to avoid busy loop
                time.sleep(0.1)

        # Unregister session change notification
        wtsapi32.WTSUnRegisterSessionNotification(g_hwnd)
        # Destroy the window
        user32.DestroyWindow(g_hwnd)
        g_hwnd = None

        self.LogToFile("Service stopped.")

    def SvcShutdown(self):
        self.ReportServiceStatus(win32service.SERVICE_SHUTDOWN_PENDING)
        self.LogToFile("Shutdown event received.")
        run_napify_exe()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def LogToFile(self, message):
        """Write a timestamped message to the log file."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        try:
            # Ensure log directory exists
            log_dir = r"C:\ProgramData\Napify\Logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            log_file = os.path.join(log_dir, "napify_service.log")
            with open(log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            # Fallback to event log if file logging fails
            servicemanager.LogErrorMsg(f"Failed to write to log file: {str(e)}")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(NapifyService)