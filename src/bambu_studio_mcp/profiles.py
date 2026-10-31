"""100% Printer-Agnostic Profile Discovery, Inheritance Resolution, and Custom Preset Creation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import discover_environment


VALID_CATEGORIES = ("machine", "filament", "process")


class ProfileCatalog:
    """Indexes and resolves Bambu Studio system and user profiles across all vendors and printers."""

    def __init__(self) -> None:
        self.env = discover_environment()
        # category -> profile_name -> metadata + path
        self._index: Dict[str, Dict[str, Dict[str, Any]]] = {
            "machine": {},
            "filament": {},
            "process": {},
        }
        self._scanned = False

    def scan(self, force: bool = False) -> None:
        """Scan all system and user profile directories."""
        if self._scanned and not force:
            return

        self._index = {"machine": {}, "filament": {}, "process": {}}

        # Scan system directories first (resources/profiles first, then appdata/system so newer OTA updates win)
        for sys_dir in reversed(self.env.system_profiles_dirs):
            vendor = sys_dir.name
            for cat in VALID_CATEGORIES:
                cat_dir = sys_dir / cat
                if cat_dir.exists():
                    self._scan_category_dir(cat_dir, cat, source="system", vendor=vendor)

        # Scan user directories (user presets override or extend system presets)
        for usr_dir in self.env.user_profiles_dirs:
            user_id = usr_dir.name
            for cat in VALID_CATEGORIES:
                cat_dir = usr_dir / cat
                if cat_dir.exists():
                    self._scan_category_dir(cat_dir, cat, source=f"user:{user_id}", vendor="user")

        self._scanned = True

    def _scan_category_dir(self, directory: Path, category: str, source: str, vendor: str) -> None:
        for json_path in directory.rglob("*.json"):
            try:
                raw = json.loads(json_path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue

            name = raw.get("name") or json_path.stem
            instantiation = str(raw.get("instantiation", "false")).lower() == "true" or source.startswith("user")
            inherits = raw.get("inherits", "")
            compatible_printers = raw.get("compatible_printers", [])

            self._index[category][name] = {
                "name": name,
                "category": category,
                "source": source,
                "vendor": vendor,
                "path": str(json_path),
                "instantiation": instantiation,
                "inherits": inherits,
                "compatible_printers": compatible_printers if isinstance(compatible_printers, list) else [],
                "nozzle_diameter": raw.get("nozzle_diameter"),
                "filament_type": raw.get("filament_type"),
                "layer_height": raw.get("layer_height"),
            }

    def list_profiles(
        self,
        category: str,
        search: Optional[str] = None,
        printer_filter: Optional[str] = None,
        include_base_templates: bool = False,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List discovered profiles in a category ('machine', 'filament', or 'process')."""
        self.scan()
        cat = category.lower().strip()
        if cat not in VALID_CATEGORIES:
            return {"error": f"Invalid category '{category}'. Must be one of {VALID_CATEGORIES}."}

        items = []
        q = search.lower().strip() if search else None
        p_filt = printer_filter.lower().strip() if printer_filter else None

        for name, info in sorted(self._index[cat].items()):
            if not include_base_templates and not info["instantiation"]:
                continue
            if q and q not in name.lower():
                continue
            if p_filt:
                compat = info.get("compatible_printers", [])
                in_name = p_filt in name.lower()
                in_compat = any(p_filt in c.lower() for c in compat)
                if not (in_name or in_compat):
                    continue

            items.append({
                "name": info["name"],
                "source": info["source"],
                "vendor": info["vendor"],
                "inherits": info["inherits"],
                "path": info["path"],
                "compatible_printers_count": len(info.get("compatible_printers", [])),
            })

        total = len(items)
        return {
            "category": cat,
            "total_matching": total,
            "returned": min(total, limit),
            "profiles": items[:limit],
        }

    def resolve_profile(self, category: str, name_or_path: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """Resolve a profile's full dictionary by walking its 'inherits' hierarchy from root to leaf."""
        self.scan()
        cat = category.lower().strip()
        if cat not in VALID_CATEGORIES:
            return None, []

        # Allow direct file path or profile name
        cand_path = Path(name_or_path)
        if cand_path.exists() and cand_path.is_file():
            try:
                leaf_data = json.loads(cand_path.read_text(encoding="utf-8", errors="replace"))
                leaf_name = leaf_data.get("name", cand_path.stem)
            except Exception:
                return None, []
        else:
            meta = self._find_profile_meta(cat, name_or_path)
            if not meta:
                return None, []
            leaf_name = meta["name"]
            leaf_data = json.loads(Path(meta["path"]).read_text(encoding="utf-8", errors="replace"))

        chain_names: List[str] = [leaf_name]
        chain_dicts: List[Dict[str, Any]] = [leaf_data]

        curr_parent = leaf_data.get("inherits")
        visited = {leaf_name}

        while curr_parent and curr_parent not in visited:
            visited.add(curr_parent)
            parent_meta = self._find_profile_meta(cat, curr_parent)
            if not parent_meta:
                break
            try:
                parent_data = json.loads(
                    Path(parent_meta["path"]).read_text(encoding="utf-8", errors="replace")
                )
            except Exception:
                break
            chain_names.append(parent_meta["name"])
            chain_dicts.append(parent_data)
            curr_parent = parent_data.get("inherits")

        # Merge from root base template down to leaf
        resolved: Dict[str, Any] = {}
        for d in reversed(chain_dicts):
            resolved.update(d)

        return resolved, list(reversed(chain_names))

    def _find_profile_meta(self, category: str, query_name: str) -> Optional[Dict[str, Any]]:
        cat_map = self._index.get(category, {})
        if query_name in cat_map:
            return cat_map[query_name]
        q_low = query_name.lower().strip()
        for k, v in cat_map.items():
            if k.lower() == q_low:
                return v
        # Partial match fallback
        for k, v in cat_map.items():
            if q_low in k.lower() and v.get("instantiation"):
                return v
        return None

    def compare_profiles(
        self,
        category: str,
        profile_a: str,
        profile_b: str,
    ) -> Dict[str, Any]:
        """Compare two profiles in the same category and return all settings that differ."""
        res_a, chain_a = self.resolve_profile(category, profile_a)
        res_b, chain_b = self.resolve_profile(category, profile_b)

        if not res_a:
            return {"error": f"Profile A '{profile_a}' not found in category '{category}'."}
        if not res_b:
            return {"error": f"Profile B '{profile_b}' not found in category '{category}'."}

        ignore_keys = {"name", "inherits", "from", "setting_id", "compatible_printers", "description"}
        all_keys = sorted((set(res_a.keys()) | set(res_b.keys())) - ignore_keys)

        differences = {}
        for k in all_keys:
            va = res_a.get(k)
            vb = res_b.get(k)
            if va != vb:
                differences[k] = {
                    profile_a: va,
                    profile_b: vb,
                }

        return {
            "category": category,
            "profile_a": {"name": res_a.get("name", profile_a), "inheritance_chain": chain_a},
            "profile_b": {"name": res_b.get("name", profile_b), "inheritance_chain": chain_b},
            "difference_count": len(differences),
            "differences": differences,
        }

    def save_custom_preset(
        self,
        category: str,
        base_profile_name: str,
        new_preset_name: str,
        overrides: Dict[str, Any],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a custom Bambu Studio preset (either in user presets folder or at output_path)."""
        resolved, chain = self.resolve_profile(category, base_profile_name)
        if not resolved:
            return {"error": f"Base profile '{base_profile_name}' not found in category '{category}'."}

        # Build standalone merged profile (for CLI slicing) and lightweight inherited preset (for GUI)
        merged_profile = dict(resolved)
        for k, v in overrides.items():
            # Preserve list vs scalar type from base profile if base uses a single-element list
            if k in merged_profile and isinstance(merged_profile[k], list) and not isinstance(v, list):
                merged_profile[k] = [str(v)]
            else:
                merged_profile[k] = str(v) if not isinstance(v, (list, dict)) else v

        merged_profile["name"] = new_preset_name
        merged_profile["from"] = "User"
        merged_profile["instantiation"] = "true"

        if output_path:
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Save in BambuStudio user/default/<category> folder
            if self.env.appdata_dir:
                user_base = self.env.appdata_dir / "user" / "default" / category.lower()
            else:
                user_base = Path.cwd() / "custom_presets" / category.lower()
            user_base.mkdir(parents=True, exist_ok=True)
            safe_filename = "".join(c if c not in r'<>:"/\|?*' else "_" for c in new_preset_name) + ".json"
            dest = user_base / safe_filename

        dest.write_text(json.dumps(merged_profile, indent=4), encoding="utf-8")
        return {
            "saved": True,
            "preset_name": new_preset_name,
            "category": category,
            "base_profile": chain[-1] if chain else base_profile_name,
            "inheritance_chain": chain,
            "applied_overrides": overrides,
            "file_path": str(dest),
        }


# Singleton catalog instance
catalog = ProfileCatalog()
