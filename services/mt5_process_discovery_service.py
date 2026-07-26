"""Read-only Windows process discovery for registered MT5 executables."""

import os


class MT5ProcessDiscoveryService:
    def running_terminals(self):
        if os.name != "nt":
            return {}
        import ctypes
        from ctypes import wintypes

        snapshot_flag = 0x00000002
        query_limited = 0x1000
        invalid_handle = ctypes.c_void_p(-1).value

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260),
            ]

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        snapshot = kernel32.CreateToolhelp32Snapshot(snapshot_flag, 0)
        if snapshot == invalid_handle:
            return {}
        found = {}
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        try:
            has_item = kernel32.Process32FirstW(
                snapshot, ctypes.byref(entry)
            )
            while has_item:
                if entry.szExeFile.casefold() == "terminal64.exe":
                    process = kernel32.OpenProcess(
                        query_limited, False, entry.th32ProcessID
                    )
                    if process:
                        try:
                            size = wintypes.DWORD(32768)
                            buffer = ctypes.create_unicode_buffer(size.value)
                            if kernel32.QueryFullProcessImageNameW(
                                process, 0, buffer, ctypes.byref(size)
                            ):
                                path = os.path.normcase(
                                    os.path.abspath(buffer.value)
                                )
                                found[path] = int(entry.th32ProcessID)
                        finally:
                            kernel32.CloseHandle(process)
                has_item = kernel32.Process32NextW(
                    snapshot, ctypes.byref(entry)
                )
        finally:
            kernel32.CloseHandle(snapshot)
        return found

    def find_pid(self, executable_path):
        normalized = os.path.normcase(
            os.path.abspath(os.path.normpath(str(executable_path)))
        )
        return self.running_terminals().get(normalized)


mt5_process_discovery_service = MT5ProcessDiscoveryService()
