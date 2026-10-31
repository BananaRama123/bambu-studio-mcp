"""Live Desktop GUI Automation for the running Bambu Studio application on Windows."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import struct
import time
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)
user32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_size_t]
user32.EnumWindows.restype = ctypes.c_bool
user32.EnumChildWindows.argtypes = [ctypes.c_size_t, WNDENUMPROC, ctypes.c_size_t]
user32.EnumChildWindows.restype = ctypes.c_bool
user32.IsWindowVisible.argtypes = [ctypes.c_size_t]
user32.IsWindowVisible.restype = ctypes.c_bool
user32.IsIconic.argtypes = [ctypes.c_size_t]
user32.IsIconic.restype = ctypes.c_bool
user32.ShowWindow.argtypes = [ctypes.c_size_t, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [ctypes.c_size_t]
user32.GetWindowTextLengthW.argtypes = [ctypes.c_size_t]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [ctypes.c_size_t, ctypes.c_wchar_p, ctypes.c_int]
user32.GetClassNameW.argtypes = [ctypes.c_size_t, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowRect.argtypes = [ctypes.c_size_t, ctypes.POINTER(wintypes.RECT)]
user32.GetDC.argtypes = [ctypes.c_size_t]
user32.GetDC.restype = ctypes.c_size_t
user32.ReleaseDC.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
user32.SetWindowPos.argtypes = [
    ctypes.c_size_t, ctypes.c_size_t,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint
]
user32.PostMessageW.argtypes = [ctypes.c_size_t, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]


def bring_window_to_front(hwnd: int) -> None:
    """Reliably bring a window to the top of the Z-order even from a background MCP server."""
    SW_RESTORE = 9
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.15)
    HWND_TOPMOST = ctypes.c_size_t(-1).value
    HWND_NOTOPMOST = ctypes.c_size_t(-2).value
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.1)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
    time.sleep(0.15)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def find_bambu_main_window() -> Optional[Dict[str, Any]]:
    """Find the main visible Bambu Studio desktop window."""
    found: List[Dict[str, Any]] = []

    @WNDENUMPROC
    def enum_cb(hwnd: int, lparam: int) -> bool:
        try:
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                if length > 0:
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                cls_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls_buf, 256)
                cls_name = cls_buf.value
                if "wxwindow" in cls_name.lower():
                    if title.strip().lower() == "preferences":
                        # Close open Preferences modal so the main 3D plater window is accessible
                        user32.PostMessageW(hwnd, 0x0010, 0, 0)
                        return True
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top
                    if w > 400 and h > 400:
                        found.append({
                            "hwnd": int(hwnd),
                            "title": title,
                            "class_name": cls_name,
                            "rect": {
                                "left": rect.left,
                                "top": rect.top,
                                "right": rect.right,
                                "bottom": rect.bottom,
                                "width": w,
                                "height": h,
                            },
                        })
        except Exception:
            pass
        return True

    user32.EnumWindows(enum_cb, 0)
    if not found:
        return None
    # Prefer window with "BambuStudio" or ".3mf" or "Untitled" in title, then largest area
    found.sort(
        key=lambda x: (x["rect"]["width"] * x["rect"]["height"]),
        reverse=True,
    )
    return found[0]


def list_child_windows(parent_hwnd: int) -> List[Dict[str, Any]]:
    """List visible child windows of the Bambu Studio main window."""
    children: List[Dict[str, Any]] = []

    @WNDENUMPROC
    def cb(hwnd: int, lparam: int) -> bool:
        try:
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                if length > 0:
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                cls_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls_buf, 256)
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 20 and h > 20:
                    children.append({
                        "hwnd": int(hwnd),
                        "title": buf.value,
                        "class_name": cls_buf.value,
                        "rect": {
                            "left": rect.left,
                            "top": rect.top,
                            "right": rect.right,
                            "bottom": rect.bottom,
                            "width": w,
                            "height": h,
                        },
                    })
        except Exception:
            pass
        return True

    user32.EnumChildWindows(parent_hwnd, cb, 0)
    return children


def _write_png(path: Path, width: int, height: int, bgra_bytes: bytes) -> None:
    """Encode raw BGRA buffer (top-down) into a standard RGB PNG file using pure Python zlib."""
    raw_rows = bytearray()
    stride = width * 4
    for y in range(height):
        raw_rows.append(0)
        row_start = y * stride
        for x in range(width):
            px = row_start + x * 4
            b = bgra_bytes[px]
            g = bgra_bytes[px + 1]
            r = bgra_bytes[px + 2]
            raw_rows.extend((r, g, b))

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack("!I", len(data)) + chunk_type + data + struct.pack("!I", crc)

    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw_rows), level=6)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", idat)
        + make_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)


def capture_window_screenshot(hwnd: int, save_path: Path) -> Dict[str, Any]:
    """Bring Bambu Studio window to front and capture its screen region to a PNG file."""
    bring_window_to_front(hwnd)

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
    width = max(1, right - left)
    height = max(1, bottom - top)

    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(ctypes.c_size_t(hdc_screen))
    hbmp = gdi32.CreateCompatibleBitmap(ctypes.c_size_t(hdc_screen), width, height)
    old_obj = gdi32.SelectObject(ctypes.c_size_t(hdc_mem), ctypes.c_size_t(hbmp))

    SRCCOPY = 0x00CC0020
    gdi32.BitBlt(
        ctypes.c_size_t(hdc_mem), 0, 0, width, height,
        ctypes.c_size_t(hdc_screen), left, top, SRCCOPY
    )

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf_size = width * height * 4
    buf = ctypes.create_string_buffer(buf_size)
    gdi32.GetDIBits(
        ctypes.c_size_t(hdc_mem), ctypes.c_size_t(hbmp),
        0, height, buf, ctypes.byref(bmi), 0
    )

    gdi32.SelectObject(ctypes.c_size_t(hdc_mem), ctypes.c_size_t(old_obj))
    gdi32.DeleteObject(ctypes.c_size_t(hbmp))
    gdi32.DeleteDC(ctypes.c_size_t(hdc_mem))
    user32.ReleaseDC(0, hdc_screen)

    _write_png(save_path, width, height, buf.raw)
    return {
        "screenshot_path": str(save_path),
        "window_rect": {"left": left, "top": top, "right": right, "bottom": bottom, "width": width, "height": height},
    }


def click_screen_coords(
    screen_x: int,
    screen_y: int,
    activate_point: Optional[ tuple[int, int] ] = None,
) -> None:
    """Move cursor to (screen_x, screen_y) and perform a left mouse click."""
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    if activate_point is not None:
        user32.SetCursorPos(int(activate_point[0]), int(activate_point[1]))
        time.sleep(0.06)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.12)
    user32.SetCursorPos(int(screen_x), int(screen_y))
    time.sleep(0.12)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.35)


def find_gl_canvas_rect(main_win: Dict[str, Any], children: List[Dict[str, Any]]) -> Dict[str, int]:
    """Identify the 3D OpenGL canvas child window (largest child on the right side of the window)."""
    main_rect = main_win["rect"]
    candidates = []
    for ch in children:
        r = ch["rect"]
        if r["width"] > main_rect["width"] * 0.35 and r["height"] > main_rect["height"] * 0.50:
            if r["left"] > main_rect["left"] + 150:
                candidates.append(r)

    if candidates:
        candidates.sort(key=lambda r: (r["left"], -r["width"]), reverse=True)
        return candidates[0]

    return main_rect


def control_bambu_gui(
    action: str = "inspect",
    click_x_offset: Optional[int] = None,
    click_y_offset: Optional[int] = None,
    screenshot_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspect or control the currently open Bambu Studio desktop GUI window."""
    main_win = find_bambu_main_window()
    if not main_win:
        return {
            "found_window": False,
            "error": "No visible Bambu Studio window found on desktop.",
        }

    hwnd = main_win["hwnd"]
    children = list_child_windows(hwnd)
    canvas_rect = find_gl_canvas_rect(main_win, children)

    out_png = (
        Path(screenshot_path)
        if screenshot_path
        else Path(__file__).resolve().parent.parent.parent / "examples" / "bambu_gui_state.png"
    )

    act = action.lower().strip()
    clicked_at: Optional[Dict[str, int]] = None

    bring_window_to_front(hwnd)

    if act == "click_relative" and click_x_offset is not None and click_y_offset is not None:
        sx = main_win["rect"]["left"] + int(click_x_offset)
        sy = main_win["rect"]["top"] + int(click_y_offset)
        click_screen_coords(sx, sy)
        clicked_at = {"screen_x": sx, "screen_y": sy, "rel_x": click_x_offset, "rel_y": click_y_offset}

    elif act in ("add_object", "add_plate", "auto_orient", "auto_arrange", "variable_layer_height"):
        icon_offsets = {
            "add_object": (82, 25),
            "add_plate": (128, 25),
            "auto_orient": (174, 25),
            "auto_arrange": (220, 25),
            "variable_layer_height": (266, 25),
        }
        dx, dy = icon_offsets[act]
        sx = canvas_rect["left"] + dx
        sy = canvas_rect["top"] + dy
        titlebar_pt = (main_win["rect"]["left"] + 450, main_win["rect"]["top"] + 15)
        click_screen_coords(sx, sy, activate_point=titlebar_pt)
        time.sleep(0.35)
        clicked_at = {
            "screen_x": sx,
            "screen_y": sy,
            "canvas_rel_x": dx,
            "canvas_rel_y": dy,
        }

    elif act in ("slice_plate", "tab_prepare", "tab_preview", "tab_device", "tab_project"):
        titlebar_pt = (main_win["rect"]["left"] + 450, main_win["rect"]["top"] + 15)
        if act == "slice_plate":
            sx = main_win["rect"]["right"] - 205
            sy = main_win["rect"]["top"] + 56
        else:
            tab_x = {
                "tab_prepare": 102,
                "tab_preview": 194,
                "tab_device": 284,
                "tab_project": 375,
            }[act]
            sx = main_win["rect"]["left"] + tab_x
            sy = main_win["rect"]["top"] + 56
        click_screen_coords(sx, sy, activate_point=titlebar_pt)
        time.sleep(0.35)
        clicked_at = {"screen_x": sx, "screen_y": sy}

    shot_info = capture_window_screenshot(hwnd, out_png)
    return {
        "found_window": True,
        "action": act,
        "main_window": main_win,
        "gl_canvas_rect": canvas_rect,
        "child_window_count": len(children),
        "children_sample": children[:25],
        "clicked_at": clicked_at,
        "screenshot": shot_info,
    }
