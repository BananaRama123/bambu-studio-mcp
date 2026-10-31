"""Direct Local Network (LAN) Bambu Lab Printer & AMS Integration via MQTT-TLS (8883) and FTPS (990).

Uses a zero-dependency native Python TLS MQTT 3.1.1 implementation so users do not need
extra third-party MQTT packages to query live printer status, read AMS filaments, or control prints.
"""

from __future__ import annotations

import ftplib
import json
import os
import socket
import ssl
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import discover_environment


SPEED_LEVEL_NAMES = {
    1: "Silent (50%)",
    2: "Standard (100%)",
    3: "Sport (124%)",
    4: "Ludicrous (166%)",
}


def _encode_mqtt_varint(length: int) -> bytes:
    out = bytearray()
    while True:
        encoded_byte = length % 128
        length //= 128
        if length > 0:
            encoded_byte |= 0x80
        out.append(encoded_byte)
        if length == 0:
            break
    return bytes(out)


def _encode_mqtt_utf8(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("!H", len(raw)) + raw


def _build_mqtt_connect(client_id: str, username: str, password: str, keepalive: int = 30) -> bytes:
    var_header = (
        _encode_mqtt_utf8("MQTT")
        + bytes([0x04])  # Protocol Level 4 (MQTT 3.1.1)
        + bytes([0xC2])  # Connect Flags: Username + Password + Clean Session
        + struct.pack("!H", keepalive)
    )
    payload = (
        _encode_mqtt_utf8(client_id)
        + _encode_mqtt_utf8(username)
        + _encode_mqtt_utf8(password)
    )
    rem = var_header + payload
    return bytes([0x10]) + _encode_mqtt_varint(len(rem)) + rem


def _build_mqtt_subscribe(packet_id: int, topic: str, qos: int = 0) -> bytes:
    var_header = struct.pack("!H", packet_id)
    payload = _encode_mqtt_utf8(topic) + bytes([qos])
    rem = var_header + payload
    return bytes([0x82]) + _encode_mqtt_varint(len(rem)) + rem


def _build_mqtt_publish(topic: str, message_bytes: bytes) -> bytes:
    var_header = _encode_mqtt_utf8(topic)
    rem = var_header + message_bytes
    return bytes([0x30]) + _encode_mqtt_varint(len(rem)) + rem


def _read_mqtt_packet(ssl_sock: ssl.SSLSocket) -> Tuple[int, bytes]:
    first = ssl_sock.recv(1)
    if not first:
        raise EOFError("Connection closed by printer")
    packet_type = first[0]

    multiplier = 1
    rem_length = 0
    while True:
        b = ssl_sock.recv(1)
        if not b:
            raise EOFError("Connection closed while reading packet length")
        encoded = b[0]
        rem_length += (encoded & 127) * multiplier
        if (encoded & 128) == 0:
            break
        multiplier *= 128

    body = bytearray()
    while len(body) < rem_length:
        chunk = ssl_sock.recv(rem_length - len(body))
        if not chunk:
            raise EOFError("Connection closed while reading packet body")
        body.extend(chunk)

    return packet_type, bytes(body)


def resolve_printer_credentials(
    ip: Optional[str] = None,
    access_code: Optional[str] = None,
    serial: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """Resolve printer IP, Access Code, and Serial from parameters, env vars, or BambuStudio.conf."""
    resolved_ip = ip or os.environ.get("BAMBU_PRINTER_IP")
    resolved_code = access_code or os.environ.get("BAMBU_ACCESS_CODE")
    resolved_serial = serial or os.environ.get("BAMBU_SERIAL")

    if not (resolved_code and resolved_serial):
        env = discover_environment()
        if env.config_file and env.config_file.exists():
            try:
                raw = json.loads(env.config_file.read_text(encoding="utf-8", errors="replace"))
                codes = raw.get("access_code", {})
                if isinstance(codes, dict) and codes:
                    if resolved_serial and resolved_serial in codes and not resolved_code:
                        resolved_code = str(codes[resolved_serial])
                    elif not resolved_serial:
                        first_ser, first_code = next(iter(codes.items()))
                        resolved_serial = str(first_ser)
                        if not resolved_code:
                            resolved_code = str(first_code)
            except Exception:
                pass

    return {
        "ip": resolved_ip,
        "access_code": resolved_code,
        "serial": resolved_serial,
    }


def query_printer_status(
    ip: Optional[str] = None,
    access_code: Optional[str] = None,
    serial: Optional[str] = None,
    timeout_seconds: float = 6.0,
) -> Dict[str, Any]:
    """Connect to a Bambu Lab printer over local MQTT-TLS (port 8883) and retrieve full live status & AMS trays."""
    creds = resolve_printer_credentials(ip, access_code, serial)
    p_ip = creds["ip"]
    p_code = creds["access_code"]
    p_serial = creds["serial"]

    if not p_ip or not p_code or not p_serial:
        return {
            "connected": False,
            "error": "Missing printer connection details. Provide ip, access_code, and serial (or set BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE, BAMBU_SERIAL).",
            "discovered_from_config": {
                "serial": p_serial,
                "has_access_code": bool(p_code),
                "ip": p_ip,
            },
        }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    report_topic = f"device/{p_serial}/report"
    request_topic = f"device/{p_serial}/request"

    merged_print: Dict[str, Any] = {}

    try:
        with socket.create_connection((p_ip, 8883), timeout=timeout_seconds) as raw_sock:
            with ctx.wrap_socket(raw_sock, server_hostname=p_ip) as tls_sock:
                tls_sock.settimeout(timeout_seconds)

                # 1. CONNECT
                client_id = f"bambu_mcp_{int(time.time()) % 10000}"
                tls_sock.sendall(_build_mqtt_connect(client_id, "bblp", p_code))
                pkt_type, connack = _read_mqtt_packet(tls_sock)
                if (pkt_type >> 4) != 2 or len(connack) < 2 or connack[1] != 0:
                    rc = connack[1] if len(connack) >= 2 else -1
                    return {
                        "connected": False,
                        "error": f"Printer MQTT CONNACK rejected connection (return code {rc}). Check your 8-digit LAN Access Code.",
                    }

                # 2. SUBSCRIBE to device/<serial>/report
                tls_sock.sendall(_build_mqtt_subscribe(1, report_topic, qos=0))

                # 3. Request pushall full state dump
                pushall_payload = json.dumps({
                    "pushing": {
                        "sequence_id": "1",
                        "command": "pushall",
                        "version": 1,
                        "push_target": 1,
                    }
                }).encode("utf-8")
                tls_sock.sendall(_build_mqtt_publish(request_topic, pushall_payload))

                # 4. Read report messages up to timeout or until we receive a full state report
                deadline = time.time() + timeout_seconds
                while time.time() < deadline:
                    try:
                        ptype, body = _read_mqtt_packet(tls_sock)
                    except socket.timeout:
                        break
                    if (ptype >> 4) == 3:  # PUBLISH
                        topic_len = struct.unpack("!H", body[:2])[0]
                        offset = 2 + topic_len
                        qos = (ptype >> 1) & 0x03
                        if qos > 0:
                            offset += 2
                        payload_bytes = body[offset:]
                        try:
                            msg = json.loads(payload_bytes.decode("utf-8", errors="ignore"))
                            if "print" in msg and isinstance(msg["print"], dict):
                                merged_print.update(msg["print"])
                                # If we got gcode_state and nozzle_temper, we have the full pushall report
                                if "gcode_state" in merged_print and "nozzle_temper" in merged_print:
                                    break
                        except Exception:
                            continue
    except Exception as exc:
        return {
            "connected": False,
            "ip": p_ip,
            "serial": p_serial,
            "error": f"Failed to connect to printer at {p_ip}:8883: {exc}",
        }

    return _format_printer_status(p_ip, p_serial, merged_print)


def _format_printer_status(ip: str, serial: str, p: Dict[str, Any]) -> Dict[str, Any]:
    ams_units_out: List[Dict[str, Any]] = []
    ams_root = p.get("ams", {})
    if isinstance(ams_root, dict):
        for ams_unit in ams_root.get("ams", []):
            unit_id = ams_unit.get("id")
            humidity = ams_unit.get("humidity")
            temp = ams_unit.get("temp")
            trays_out = []
            for tray in ams_unit.get("tray", []):
                t_type = tray.get("tray_type")
                if not t_type:
                    continue
                trays_out.append({
                    "slot": f"AMS {int(unit_id or 0) + 1} - Slot {int(tray.get('id', 0)) + 1}",
                    "filament_type": t_type,
                    "sub_brands": tray.get("tray_sub_brands"),
                    "color_hex": tray.get("tray_color"),
                    "remaining_percent": tray.get("remain"),
                    "nozzle_temp_range_c": f"{tray.get('nozzle_temp_min', '?')}-{tray.get('nozzle_temp_max', '?')}",
                })
            ams_units_out.append({
                "ams_id": unit_id,
                "humidity_index_1_to_5": humidity,
                "temperature_c": temp,
                "loaded_trays": trays_out,
            })

    spd_lvl = p.get("spd_lvl")
    return {
        "connected": True,
        "ip": ip,
        "serial": serial,
        "state": p.get("gcode_state", "UNKNOWN"),
        "current_file": p.get("subtask_name") or p.get("gcode_file"),
        "progress_percent": p.get("mc_percent"),
        "remaining_time_minutes": p.get("mc_remaining_time"),
        "current_layer": p.get("layer_num"),
        "total_layers": p.get("total_layer_num"),
        "temperatures_c": {
            "nozzle_current": p.get("nozzle_temper"),
            "nozzle_target": p.get("nozzle_target_temper"),
            "bed_current": p.get("bed_temper"),
            "bed_target": p.get("bed_target_temper"),
            "chamber": p.get("chamber_temper"),
        },
        "speed_level": SPEED_LEVEL_NAMES.get(spd_lvl, str(spd_lvl)) if spd_lvl else None,
        "ams_units": ams_units_out,
        "lights": p.get("lights_report", []),
        "hms_alerts": p.get("hms", []),
    }


def send_printer_command(
    action: str,
    value: Optional[str] = None,
    ip: Optional[str] = None,
    access_code: Optional[str] = None,
    serial: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a control command to a Bambu Lab printer over local MQTT-TLS.

    Supported actions:
    - 'pause': Pause the active print
    - 'resume': Resume a paused print
    - 'stop': Cancel/stop the active print
    - 'light_on' / 'light_off': Toggle chamber light
    - 'speed': Set print speed level ('1'=Silent, '2'=Standard, '3'=Sport, '4'=Ludicrous)
    """
    creds = resolve_printer_credentials(ip, access_code, serial)
    p_ip, p_code, p_serial = creds["ip"], creds["access_code"], creds["serial"]
    if not p_ip or not p_code or not p_serial:
        return {"success": False, "error": "Missing printer IP, Access Code, or Serial."}

    act = action.lower().strip()
    seq = str(int(time.time()) % 100000)

    if act in ("pause", "resume", "stop"):
        payload_dict: Dict[str, Any] = {
            "print": {
                "sequence_id": seq,
                "command": act,
                "param": "",
            }
        }
    elif act in ("light_on", "light_off"):
        mode = "on" if act == "light_on" else "off"
        payload_dict = {
            "system": {
                "sequence_id": seq,
                "command": "ledctrl",
                "led_node": "chamber_light",
                "led_mode": mode,
                "led_on_time": 500,
                "led_off_time": 500,
                "loop_times": 0,
                "interval_time": 0,
            }
        }
    elif act == "speed":
        if str(value) not in ("1", "2", "3", "4"):
            return {
                "success": False,
                "error": "For action='speed', value must be '1' (Silent), '2' (Standard), '3' (Sport), or '4' (Ludicrous).",
            }
        payload_dict = {
            "print": {
                "sequence_id": seq,
                "command": "print_speed",
                "param": str(value),
            }
        }
    else:
        return {
            "success": False,
            "error": f"Unsupported action '{action}'. Use 'pause', 'resume', 'stop', 'light_on', 'light_off', or 'speed'.",
        }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    request_topic = f"device/{p_serial}/request"

    try:
        with socket.create_connection((p_ip, 8883), timeout=5.0) as raw_sock:
            with ctx.wrap_socket(raw_sock, server_hostname=p_ip) as tls_sock:
                tls_sock.settimeout(5.0)
                client_id = f"bambu_mcp_cmd_{int(time.time()) % 10000}"
                tls_sock.sendall(_build_mqtt_connect(client_id, "bblp", p_code))
                pkt_type, connack = _read_mqtt_packet(tls_sock)
                if (pkt_type >> 4) != 2 or len(connack) < 2 or connack[1] != 0:
                    return {"success": False, "error": "Printer rejected MQTT connection."}

                tls_sock.sendall(
                    _build_mqtt_publish(request_topic, json.dumps(payload_dict).encode("utf-8"))
                )
                time.sleep(0.2)
    except Exception as exc:
        return {"success": False, "error": f"Failed to send command: {exc}"}

    return {
        "success": True,
        "action": act,
        "value": value,
        "printer_ip": p_ip,
        "serial": p_serial,
        "sent_payload": payload_dict,
    }
