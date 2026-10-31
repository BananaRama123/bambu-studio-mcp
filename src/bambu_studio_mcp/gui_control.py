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
        time.sleep(0.05)
    HWND_TOPMOST = ctypes.c_size_t(-1).value
    HWND_NOTOPMOST = ctypes.c_size_t(-2).value
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
    user32.SetForegroundWindow(hwnd)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
    time.sleep(0.03)


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
    """Encode raw BGRA buffer (top-down) into an RGBA PNG file using slice-vectorized pure Python."""
    rgba = bytearray(bgra_bytes)
    rgba[0::4], rgba[2::4] = bgra_bytes[2::4], bgra_bytes[0::4]
    rgba[3::4] = b"\xff" * (width * height)
    mv = memoryview(rgba)
    stride = width * 4
    raw_rows = b"\x00" + b"\x00".join(mv[y * stride : (y + 1) * stride] for y in range(height))

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack("!I", len(data)) + chunk_type + data + struct.pack("!I", crc)

    # Color type 6 = RGBA (8 bits per channel)
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw_rows, level=1)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", idat)
        + make_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)


def _grab_window_bgra_fast(hwnd: int) -> Tuple[int, int, bytes]:
    """Grab raw BGRA bytes of the window in ~3ms without disk I/O for instant before/after change detection."""
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

    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(
        ctypes.c_size_t(hdc_mem), ctypes.c_size_t(hbmp),
        0, height, buf, ctypes.byref(bmi), 0
    )

    gdi32.SelectObject(ctypes.c_size_t(hdc_mem), ctypes.c_size_t(old_obj))
    gdi32.DeleteObject(ctypes.c_size_t(hbmp))
    gdi32.DeleteDC(ctypes.c_size_t(hdc_mem))
    user32.ReleaseDC(0, hdc_screen)
    return width, height, buf.raw


def capture_window_screenshot(hwnd: int, save_path: Path, focus_first: bool = True) -> Dict[str, Any]:
    """Capture Bambu Studio window screen region to a PNG file."""
    if focus_first:
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


def move_cursor_exact(screen_x: int, screen_y: int) -> Tuple[int, int]:
    """Move cursor across multi-DPI monitors reliably by calling SetCursorPos until GetCursorPos matches."""
    target_x, target_y = int(screen_x), int(screen_y)
    pt = wintypes.POINT()
    for _ in range(4):
        user32.SetCursorPos(target_x, target_y)
        user32.GetCursorPos(ctypes.byref(pt))
        if abs(pt.x - target_x) <= 1 and abs(pt.y - target_y) <= 1:
            break
        time.sleep(0.01)
    return pt.x, pt.y


def click_screen_coords(
    screen_x: int,
    screen_y: int,
    activate_point: Optional[ tuple[int, int] ] = None,
) -> None:
    """Move cursor to exact (screen_x, screen_y), allow OpenGL hover picking frame to update, and click."""
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    move_cursor_exact(int(screen_x) - 1, int(screen_y))
    user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)
    time.sleep(0.05)
    move_cursor_exact(int(screen_x), int(screen_y))
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.08)


def send_key_shortcut(vk_code: int, ctrl: bool = False, shift: bool = False) -> None:
    """Send a native Win32 keyboard shortcut to the focused Bambu Studio window."""
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    KEYEVENTF_KEYUP = 0x0002
    if ctrl:
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
    if shift:
        user32.keybd_event(VK_SHIFT, 0, 0, 0)
    time.sleep(0.01)
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.01)
    if shift:
        user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
    if ctrl:
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.06)


def _sample_lum(width: int, height: int, bgra: bytes, x: int, y: int) -> float:
    """Return average RGB luminance (0..255) in a 5x5 patch around (x, y)."""
    stride = width * 4
    total = 0
    cnt = 0
    for dy in (-4, 0, 4):
        for dx in (-4, 0, 4):
            sx = max(0, min(width - 1, x + dx))
            sy = max(0, min(height - 1, y + dy))
            idx = sy * stride + sx * 4
            total += (bgra[idx] + bgra[idx + 1] + bgra[idx + 2]) // 3
            cnt += 1
    return round(total / max(1, cnt), 1)


def detect_canvas_plates(width: int, height: int, bgra_bytes: bytes) -> Dict[str, Any]:
    """Check the luminance of the visible plates on the canvas (active plate is dark ~95, inactive is light ~212)."""
    # Sample empty upper-left grid corners of each plate in Top View (away from centered 3D objects):
    probe_points = {
        1: (410, 395),
        2: (670, 395),
        3: (900, 395),
        4: (410, 615),
        5: (670, 615),
        6: (900, 615),
    }
    plates = []
    active_idx = None
    for p_num, (px, py) in probe_points.items():
        if px < width and py < height:
            lum = _sample_lum(width, height, bgra_bytes, px, py)
            is_active = 60.0 <= lum <= 145.0
            if is_active and active_idx is None:
                active_idx = p_num
            plates.append({
                "plate": p_num,
                "probe_xy": (px, py),
                "luminance": lum,
                "is_selected": is_active,
            })
    return {
        "active_selected_plate": active_idx,
        "plates": plates,
    }


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
    """Inspect or control the currently open Bambu Studio desktop GUI window, or invoke hot-reloaded AI pipelines."""
    raw_action = action.strip()
    if raw_action.startswith(("cielab:", "search_models:", "audit_model:", "repair_mesh:", "claude:")):
        import importlib
        from . import ai_features as _af
        from . import claude_worker as _cw
        from . import model_3mf as _m3
        importlib.reload(_af)
        importlib.reload(_cw)
        importlib.reload(_m3)
        prefix, payload = raw_action.split(":", 1)
        if prefix == "claude":
            return _cw.delegate_to_claude(task_prompt=payload)
        if prefix == "cielab":
            colors = [c.strip() for c in payload.split(";") if c.strip()]
            return _af.match_ams_colors_cielab(target_colors=colors)
        if prefix == "search_models":
            return _af.search_3d_models(query=payload)
        if prefix == "audit_model":
            return _m3.inspect_3d_model(file_path=payload)
        if prefix == "repair_mesh":
            return _af.repair_and_ground_stl(input_stl_path=payload)

    main_win = find_bambu_main_window()
    if not main_win:
        return {
            "found_window": False,
            "error": "No visible Bambu Studio window found on desktop.",
        }

    hwnd = main_win["hwnd"]
    act = action.lower().strip()
    need_canvas = act in ("inspect", "self_test", "add_object", "add_plate", "auto_orient", "auto_arrange", "variable_layer_height")
    children = list_child_windows(hwnd) if need_canvas else []
    canvas_rect = find_gl_canvas_rect(main_win, children) if need_canvas else main_win["rect"]

    clicked_at: Optional[Dict[str, Any]] = None

    bring_window_to_front(hwnd)
    win_w, win_h, bgra_before = _grab_window_bgra_fast(hwnd)

    if act == "self_test":
        initial_plates = detect_canvas_plates(win_w, win_h, bgra_before)
        steps_report = []

        # Test 1: Probe candidate click points on Plate 2 until active_selected_plate == 2
        p2_candidates = [
            ("plate2_interior", (670, 395)),
            ("plate2_object", (731, 445)),
            ("plate2_badge_02", (842, 537)),
            ("plate2_top_tab", (731, 350)),
            ("plate2_settings_icon", (842, 422)),
        ]
        winning_p2 = None
        plates_s1 = initial_plates
        for label, (rx, ry) in p2_candidates:
            click_screen_coords(main_win["rect"]["left"] + rx, main_win["rect"]["top"] + ry)
            time.sleep(0.12)
            _, _, bgra_s1 = _grab_window_bgra_fast(hwnd)
            plates_s1 = detect_canvas_plates(win_w, win_h, bgra_s1)
            if plates_s1.get("active_selected_plate") == 2:
                winning_p2 = (label, (rx, ry))
                break

        steps_report.append({
            "step": "1_select_plate_2",
            "winning_candidate": winning_p2,
            "plate_state_after": plates_s1,
            "passed": plates_s1.get("active_selected_plate") == 2,
        })

        # Test 2: Switch back to Plate 1 and verify active_selected_plate == 1
        p1_candidates = [
            ("plate1_interior", (410, 395)),
            ("plate1_object", (485, 445)),
            ("plate1_badge_01", (594, 537)),
        ]
        winning_p1 = None
        plates_s2 = plates_s1
        for label, (rx, ry) in p1_candidates:
            click_screen_coords(main_win["rect"]["left"] + rx, main_win["rect"]["top"] + ry)
            time.sleep(0.12)
            _, _, bgra_s2 = _grab_window_bgra_fast(hwnd)
            plates_s2 = detect_canvas_plates(win_w, win_h, bgra_s2)
            if plates_s2.get("active_selected_plate") == 1:
                winning_p1 = (label, (rx, ry))
                break

        steps_report.append({
            "step": "2_select_plate_1",
            "winning_candidate": winning_p1,
            "plate_state_after": plates_s2,
            "passed": plates_s2.get("active_selected_plate") == 1,
        })

        return {
            "found_window": True,
            "action": "self_test",
            "all_passed": all(s["passed"] for s in steps_report),
            "initial_plate_scan": initial_plates,
            "self_test_steps": steps_report,
        }

    if act in ("undo", "remove_plate", "delete_empty_plates"):
        sx = main_win["rect"]["left"] + 207
        sy = main_win["rect"]["top"] + 18
        click_screen_coords(sx, sy)
        clicked_at = {"screen_x": sx, "screen_y": sy, "rel_x": 207, "rel_y": 18}

    elif act.startswith("select_plate_"):
        plate_num = int(act.split("_")[-1])
        candidates_by_plate = {
            1: [(410, 395), (472, 464)],
            2: [(670, 395), (731, 464)],
            3: [(900, 395), (910, 464)],
            4: [(410, 615), (472, 703)],
            5: [(670, 615), (731, 703)],
            6: [(900, 615), (910, 703)],
        }
        cands = candidates_by_plate.get(plate_num, [(670, 395)])
        for rx, ry in cands:
            sx = main_win["rect"]["left"] + rx
            sy = main_win["rect"]["top"] + ry
            click_screen_coords(sx, sy)
            _, _, bgra_try = _grab_window_bgra_fast(hwnd)
            after_scan = detect_canvas_plates(win_w, win_h, bgra_try)
            clicked_at = {
                "plate": plate_num,
                "screen_x": sx,
                "screen_y": sy,
                "rel_x": rx,
                "rel_y": ry,
                "active_selected_plate": after_scan.get("active_selected_plate"),
                "plates_luminance": after_scan.get("plates"),
            }
            if after_scan.get("active_selected_plate") == plate_num:
                break

    elif act in ("sidebar_objects", "sidebar_global"):
        rx = 185 if act == "sidebar_objects" else 132
        ry = 497
        sx = main_win["rect"]["left"] + rx
        sy = main_win["rect"]["top"] + ry
        click_screen_coords(sx, sy)
        clicked_at = {"screen_x": sx, "screen_y": sy, "rel_x": rx, "rel_y": ry}

    elif act in (
        "view_iso", "view_bottom", "view_top", "view_front", "view_back", "view_left", "view_right",
        "hotkey_arrange", "hotkey_slice", "hotkey_undo", "hotkey_redo", "hotkey_add_object",
        "tool_move", "tool_scale", "tool_rotate", "tool_lay_on_face", "tool_cut", "tool_paint",
    ):
        # Group 1: Native Win32 Keyboard Shortcuts (100% resolution & camera independent)
        # Focus the 3D canvas first if needed so single-key shortcuts go to GLCanvas3D
        hotkey_map = {
            "view_iso": (0x30, True, False),       # Ctrl+0
            "view_bottom": (0x31, True, False),    # Ctrl+1
            "view_top": (0x32, True, False),       # Ctrl+2
            "view_front": (0x33, True, False),     # Ctrl+3
            "view_back": (0x34, True, False),      # Ctrl+4
            "view_left": (0x35, True, False),      # Ctrl+5
            "view_right": (0x36, True, False),     # Ctrl+6
            "hotkey_arrange": (0x41, False, False),     # A
            "hotkey_slice": (0x52, True, False),        # Ctrl+R
            "hotkey_undo": (0x5A, True, False),         # Ctrl+Z
            "hotkey_redo": (0x59, True, False),         # Ctrl+Y
            "hotkey_add_object": (0x49, True, False),   # Ctrl+I
            "tool_move": (0x4D, False, False),          # M
            "tool_scale": (0x53, False, False),         # S
            "tool_rotate": (0x52, False, False),        # R
            "tool_lay_on_face": (0x46, False, False),   # F
            "tool_cut": (0x43, False, False),           # C
            "tool_paint": (0x50, False, False),         # P
        }
        vk, use_ctrl, use_shift = hotkey_map[act]
        send_key_shortcut(vk, ctrl=use_ctrl, shift=use_shift)
        clicked_at = {"hotkey": act, "vk": hex(vk), "ctrl": use_ctrl, "shift": use_shift}

    elif act == "click_relative" and click_x_offset is not None and click_y_offset is not None:
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
        click_screen_coords(sx, sy)
        clicked_at = {
            "screen_x": sx,
            "screen_y": sy,
            "canvas_rel_x": dx,
            "canvas_rel_y": dy,
        }

    elif act in ("slice_plate", "tab_prepare", "tab_preview", "tab_device", "tab_project"):
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
        click_screen_coords(sx, sy)
        clicked_at = {"screen_x": sx, "screen_y": sy}

    _, _, bgra_after = _grab_window_bgra_fast(hwnd)
    visual_changed = bgra_before != bgra_after

    shot_info = None
    if act == "inspect" or screenshot_path:
        out_png = (
            Path(screenshot_path)
            if screenshot_path
            else Path(__file__).resolve().parent.parent.parent / "examples" / "bambu_gui_state.png"
        )
        shot_info = capture_window_screenshot(hwnd, out_png, focus_first=False)

    res: Dict[str, Any] = {
        "found_window": True,
        "action": act,
        "visual_change_detected": visual_changed,
        "main_window": main_win,
        "gl_canvas_rect": canvas_rect,
        "clicked_at": clicked_at,
        "screenshot": shot_info,
    }
    if act == "inspect":
        res["child_window_count"] = len(children)
        res["children_sample"] = children[:25]
    return res
