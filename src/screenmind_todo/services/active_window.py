import platform


def get_active_window_title() -> tuple[str, str]:
    if platform.system() != "Windows":
        return "", ""

    from ctypes import create_unicode_buffer, windll, wintypes

    user32 = windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "", ""

    length = user32.GetWindowTextLengthW(hwnd)
    buffer = create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    title = buffer.value or ""

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, pid)

    try:
        import psutil

        process_name = psutil.Process(pid.value).name()
    except Exception:
        process_name = ""

    return title, process_name
