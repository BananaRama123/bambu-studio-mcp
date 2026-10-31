"""Cross-platform path and configuration discovery for Bambu Studio."""

from __future__ import annotations

import json
import os
import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BambuEnvironment:
    """Represents the discovered Bambu Studio installation and user environment."""

    os_name: str
    executable_path: Optional[Path]
    install_dir: Optional[Path]
    resources_dir: Optional[Path]
    appdata_dir: Optional[Path]
    system_profiles_dirs: List[Path] = field(default_factory=list)
    user_profiles_dirs: List[Path] = field(default_factory=list)
    config_file: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os_name": self.os_name,
            "executable_path": str(self.executable_path) if self.executable_path else None,
            "install_dir": str(self.install_dir) if self.install_dir else None,
            "resources_dir": str(self.resources_dir) if self.resources_dir else None,
            "appdata_dir": str(self.appdata_dir) if self.appdata_dir else None,
            "system_profiles_dirs": [str(p) for p in self.system_profiles_dirs],
            "user_profiles_dirs": [str(p) for p in self.user_profiles_dirs],
            "config_file": str(self.config_file) if self.config_file else None,
            "is_installed": self.executable_path is not None and self.executable_path.exists(),
        }


def discover_environment() -> BambuEnvironment:
    """Auto-discover Bambu Studio executable, resources, and user profile directories."""
    sys_name = platform.system().lower()

    # Allow explicit overrides via environment variables
    env_exe = os.environ.get("BAMBU_STUDIO_EXE")
    env_appdata = os.environ.get("BAMBU_STUDIO_APPDATA")

    exe_candidates: List[Path] = []
    appdata_candidates: List[Path] = []

    if env_exe:
        exe_candidates.append(Path(env_exe))
    if env_appdata:
        appdata_candidates.append(Path(env_appdata))

    if sys_name == "windows":
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        roaming_appdata = os.environ.get("APPDATA", "")

        exe_candidates.extend([
            Path(prog_files) / "Bambu Studio" / "bambu-studio.exe",
            Path(prog_files_x86) / "Bambu Studio" / "bambu-studio.exe",
            Path(local_appdata) / "Programs" / "Bambu Studio" / "bambu-studio.exe",
        ])
        if roaming_appdata:
            appdata_candidates.append(Path(roaming_appdata) / "BambuStudio")

    elif sys_name == "darwin":
        exe_candidates.extend([
            Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"),
            Path.home() / "Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
        ])
        appdata_candidates.append(
            Path.home() / "Library" / "Application Support" / "BambuStudio"
        )

    else:  # Linux
        which_bs = shutil.which("bambu-studio") or shutil.which("BambuStudio")
        if which_bs:
            exe_candidates.append(Path(which_bs))
        exe_candidates.extend([
            Path("/usr/bin/bambu-studio"),
            Path("/usr/local/bin/bambu-studio"),
            Path.home() / ".local/bin/bambu-studio",
        ])
        appdata_candidates.extend([
            Path.home() / ".config" / "BambuStudio",
            Path.home() / ".var/app/com.bambulab.BambuStudio/config/BambuStudio",
        ])

    exe_path: Optional[Path] = None
    for cand in exe_candidates:
        if cand and cand.exists() and cand.is_file():
            exe_path = cand
            break

    install_dir: Optional[Path] = None
    resources_dir: Optional[Path] = None
    if exe_path:
        install_dir = exe_path.parent
        if sys_name == "darwin":
            res_cand = install_dir.parent / "Resources"
        else:
            res_cand = install_dir / "resources"
        if res_cand.exists():
            resources_dir = res_cand

    appdata_dir: Optional[Path] = None
    for cand in appdata_candidates:
        if cand and cand.exists() and cand.is_dir():
            appdata_dir = cand
            break

    system_profiles_dirs: List[Path] = []
    user_profiles_dirs: List[Path] = []
    config_file: Optional[Path] = None

    if appdata_dir:
        sys_dir = appdata_dir / "system"
        if sys_dir.exists():
            for vendor_dir in sorted(sys_dir.iterdir()):
                if vendor_dir.is_dir():
                    system_profiles_dirs.append(vendor_dir)

        usr_dir = appdata_dir / "user"
        if usr_dir.exists():
            for user_sub in sorted(usr_dir.iterdir()):
                if user_sub.is_dir():
                    user_profiles_dirs.append(user_sub)

        conf = appdata_dir / "BambuStudio.conf"
        if conf.exists():
            config_file = conf

    if resources_dir:
        res_prof = resources_dir / "profiles"
        if res_prof.exists():
            for vendor_dir in sorted(res_prof.iterdir()):
                if vendor_dir.is_dir() and vendor_dir not in system_profiles_dirs:
                    system_profiles_dirs.append(vendor_dir)

    return BambuEnvironment(
        os_name=sys_name,
        executable_path=exe_path,
        install_dir=install_dir,
        resources_dir=resources_dir,
        appdata_dir=appdata_dir,
        system_profiles_dirs=system_profiles_dirs,
        user_profiles_dirs=user_profiles_dirs,
        config_file=config_file,
    )


def read_bambu_studio_conf( redact_secrets: bool = True ) -> Dict[str, Any]:
    """Read BambuStudio.conf safely, extracting recent presets and known printers."""
    env = discover_environment()
    if not env.config_file or not env.config_file.exists():
        return {"found": False, "error": "BambuStudio.conf not found"}

    try:
        text = env.config_file.read_text(encoding="utf-8", errors="replace").lstrip()
        raw, _ = json.JSONDecoder().raw_decode(text)
    except Exception as exc:
        return {"found": True, "error": f"Failed to parse BambuStudio.conf: {exc}"}

    app_cfg = raw.get("app", {})
    presets = raw.get("presets", {})
    access_codes = raw.get("access_code", {})
    user_bed_type = raw.get("user_bed_type", {})

    printers_configured = []
    for serial, code in access_codes.items():
        printers_configured.append({
            "serial": serial,
            "access_code": ("***" + str(code)[-3:]) if (redact_secrets and code) else code,
            "has_access_code": bool(code),
        })

    return {
        "found": True,
        "config_path": str(env.config_file),
        "version": app_cfg.get("version"),
        "region": app_cfg.get("region"),
        "active_presets": {
            "machine": presets.get("machine"),
            "process": presets.get("process"),
            "filaments": presets.get("filaments", []),
            "filament_colors": presets.get("filament_colors", []),
        },
        "user_bed_type": user_bed_type,
        "configured_printers": printers_configured,
    }
