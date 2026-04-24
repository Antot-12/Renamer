"""Profile management for saving rename templates and settings."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RenameProfile:
    """Stores a rename configuration preset."""
    name: str
    template: str
    prefix: str = ""
    suffix: str = ""
    find_text: str = ""
    replace_text: str = ""
    use_regex: bool = False
    case_mode: str = "none"
    remove_pattern: str = "none"
    trim_spaces: bool = True
    num_start: int = 1
    num_step: int = 1
    num_padding: int = 2
    date_mode: str = "none"
    date_format: str = "YYYY-MM-DD"
    copy_mode: bool = False
    backup_enabled: bool = False
    profile_type: str = "general"  # "audio" or "general"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RenameProfile":
        return cls(
            name=data.get("name", ""),
            template=data.get("template", "{original}"),
            prefix=data.get("prefix", ""),
            suffix=data.get("suffix", ""),
            find_text=data.get("find_text", ""),
            replace_text=data.get("replace_text", ""),
            use_regex=data.get("use_regex", False),
            case_mode=data.get("case_mode", "none"),
            remove_pattern=data.get("remove_pattern", "none"),
            trim_spaces=data.get("trim_spaces", True),
            num_start=data.get("num_start", 1),
            num_step=data.get("num_step", 1),
            num_padding=data.get("num_padding", 2),
            date_mode=data.get("date_mode", "none"),
            date_format=data.get("date_format", "YYYY-MM-DD"),
            copy_mode=data.get("copy_mode", False),
            backup_enabled=data.get("backup_enabled", False),
            profile_type=data.get("profile_type", "general"),
        )


class ProfileManager:
    """Manages saving and loading of rename profiles."""

    DEFAULT_FILE = Path.home() / ".renamer_profiles.json"

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or self.DEFAULT_FILE
        self._profiles: Dict[str, RenameProfile] = {}
        self._load()

    def _load(self) -> None:
        """Load profiles from file."""
        try:
            if self.filepath.exists():
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, profile_data in data.get("profiles", {}).items():
                        self._profiles[name] = RenameProfile.from_dict(profile_data)
        except (json.JSONDecodeError, IOError, KeyError):
            self._profiles = {}

    def _save(self) -> None:
        """Save profiles to file."""
        try:
            data = {
                "profiles": {name: p.to_dict() for name, p in self._profiles.items()}
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def save_profile(self, profile: RenameProfile) -> None:
        """Save a profile."""
        self._profiles[profile.name] = profile
        self._save()

    def delete_profile(self, name: str) -> bool:
        """Delete a profile by name."""
        if name in self._profiles:
            del self._profiles[name]
            self._save()
            return True
        return False

    def get_profile(self, name: str) -> Optional[RenameProfile]:
        """Get a profile by name."""
        return self._profiles.get(name)

    def get_all_profiles(self, profile_type: Optional[str] = None) -> List[RenameProfile]:
        """Get all profiles, optionally filtered by type."""
        profiles = list(self._profiles.values())
        if profile_type:
            profiles = [p for p in profiles if p.profile_type == profile_type]
        return sorted(profiles, key=lambda p: p.name)

    def get_profile_names(self, profile_type: Optional[str] = None) -> List[str]:
        """Get list of profile names."""
        if profile_type:
            return [p.name for p in self._profiles.values() if p.profile_type == profile_type]
        return list(self._profiles.keys())

    def profile_exists(self, name: str) -> bool:
        """Check if profile name exists."""
        return name in self._profiles


# Global instance
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get global profile manager instance."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager
