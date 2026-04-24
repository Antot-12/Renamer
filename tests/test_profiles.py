"""Tests for profile management."""

import json
import os
import tempfile
import shutil
from pathlib import Path

import pytest

from renamer.profiles import (
    RenameProfile,
    ProfileManager,
    get_profile_manager,
)


class TestRenameProfile:
    """Tests for RenameProfile dataclass."""

    def test_create_profile_defaults(self):
        profile = RenameProfile(
            name="test",
            template="Оригінал",
        )
        assert profile.name == "test"
        assert profile.template == "Оригінал"
        assert profile.prefix == ""
        assert profile.suffix == ""
        assert profile.use_regex is False
        assert profile.case_mode == "none"
        assert profile.num_start == 1
        assert profile.profile_type == "general"

    def test_create_profile_custom(self):
        profile = RenameProfile(
            name="my_profile",
            template="## - Назва",
            prefix="pre_",
            suffix="_suf",
            find_text="old",
            replace_text="new",
            use_regex=True,
            case_mode="title",
            remove_pattern="brackets",
            trim_spaces=False,
            num_start=10,
            num_step=5,
            num_padding=3,
            date_mode="modified",
            date_format="YYYY-MM-DD",
            copy_mode=True,
            backup_enabled=True,
            profile_type="audio",
        )

        assert profile.name == "my_profile"
        assert profile.prefix == "pre_"
        assert profile.use_regex is True
        assert profile.num_start == 10
        assert profile.num_step == 5
        assert profile.profile_type == "audio"

    def test_to_dict(self):
        profile = RenameProfile(
            name="test",
            template="template",
            prefix="pre",
        )

        d = profile.to_dict()

        assert d["name"] == "test"
        assert d["template"] == "template"
        assert d["prefix"] == "pre"
        assert "suffix" in d
        assert "use_regex" in d
        assert "profile_type" in d

    def test_from_dict(self):
        data = {
            "name": "loaded_profile",
            "template": "custom_template",
            "prefix": "X_",
            "suffix": "_Y",
            "find_text": "find",
            "replace_text": "replace",
            "use_regex": True,
            "case_mode": "upper",
            "remove_pattern": "numbers",
            "trim_spaces": True,
            "num_start": 100,
            "num_step": 10,
            "num_padding": 4,
            "date_mode": "created",
            "date_format": "DD.MM.YYYY",
            "copy_mode": False,
            "backup_enabled": True,
            "profile_type": "audio",
        }

        profile = RenameProfile.from_dict(data)

        assert profile.name == "loaded_profile"
        assert profile.template == "custom_template"
        assert profile.prefix == "X_"
        assert profile.use_regex is True
        assert profile.num_start == 100
        assert profile.profile_type == "audio"

    def test_from_dict_with_missing_fields(self):
        data = {
            "name": "minimal",
            "template": "basic",
        }

        profile = RenameProfile.from_dict(data)

        assert profile.name == "minimal"
        assert profile.prefix == ""  # Default
        assert profile.use_regex is False  # Default


class TestProfileManager:
    """Tests for ProfileManager class."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.profile_file = Path(self.tmpdir) / "test_profiles.json"

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_manager(self):
        manager = ProfileManager(self.profile_file)
        assert manager.filepath == self.profile_file

    def test_save_profile(self):
        manager = ProfileManager(self.profile_file)
        profile = RenameProfile(name="test", template="template")

        manager.save_profile(profile)

        assert manager.profile_exists("test")

    def test_get_profile(self):
        manager = ProfileManager(self.profile_file)
        profile = RenameProfile(
            name="myprofile",
            template="mytemplate",
            prefix="PRE_",
        )
        manager.save_profile(profile)

        loaded = manager.get_profile("myprofile")

        assert loaded is not None
        assert loaded.name == "myprofile"
        assert loaded.prefix == "PRE_"

    def test_get_nonexistent_profile(self):
        manager = ProfileManager(self.profile_file)

        result = manager.get_profile("nonexistent")

        assert result is None

    def test_delete_profile(self):
        manager = ProfileManager(self.profile_file)
        profile = RenameProfile(name="to_delete", template="template")
        manager.save_profile(profile)

        result = manager.delete_profile("to_delete")

        assert result is True
        assert not manager.profile_exists("to_delete")

    def test_delete_nonexistent_profile(self):
        manager = ProfileManager(self.profile_file)

        result = manager.delete_profile("nonexistent")

        assert result is False

    def test_get_all_profiles(self):
        manager = ProfileManager(self.profile_file)
        manager.save_profile(RenameProfile(name="profile1", template="t1"))
        manager.save_profile(RenameProfile(name="profile2", template="t2"))
        manager.save_profile(RenameProfile(name="profile3", template="t3"))

        profiles = manager.get_all_profiles()

        assert len(profiles) == 3

    def test_get_all_profiles_filtered_by_type(self):
        manager = ProfileManager(self.profile_file)
        manager.save_profile(RenameProfile(name="audio1", template="t1", profile_type="audio"))
        manager.save_profile(RenameProfile(name="audio2", template="t2", profile_type="audio"))
        manager.save_profile(RenameProfile(name="general1", template="t3", profile_type="general"))

        audio_profiles = manager.get_all_profiles(profile_type="audio")
        general_profiles = manager.get_all_profiles(profile_type="general")

        assert len(audio_profiles) == 2
        assert len(general_profiles) == 1

    def test_get_profile_names(self):
        manager = ProfileManager(self.profile_file)
        manager.save_profile(RenameProfile(name="alpha", template="t"))
        manager.save_profile(RenameProfile(name="beta", template="t"))

        names = manager.get_profile_names()

        assert "alpha" in names
        assert "beta" in names

    def test_get_profile_names_by_type(self):
        manager = ProfileManager(self.profile_file)
        manager.save_profile(RenameProfile(name="audio", template="t", profile_type="audio"))
        manager.save_profile(RenameProfile(name="general", template="t", profile_type="general"))

        audio_names = manager.get_profile_names(profile_type="audio")
        general_names = manager.get_profile_names(profile_type="general")

        assert audio_names == ["audio"]
        assert general_names == ["general"]

    def test_profile_exists(self):
        manager = ProfileManager(self.profile_file)
        manager.save_profile(RenameProfile(name="exists", template="t"))

        assert manager.profile_exists("exists") is True
        assert manager.profile_exists("not_exists") is False

    def test_profiles_sorted_by_name(self):
        manager = ProfileManager(self.profile_file)
        manager.save_profile(RenameProfile(name="charlie", template="t"))
        manager.save_profile(RenameProfile(name="alpha", template="t"))
        manager.save_profile(RenameProfile(name="bravo", template="t"))

        profiles = manager.get_all_profiles()

        assert profiles[0].name == "alpha"
        assert profiles[1].name == "bravo"
        assert profiles[2].name == "charlie"

    def test_persistence_across_instances(self):
        # Save with first instance
        manager1 = ProfileManager(self.profile_file)
        manager1.save_profile(RenameProfile(name="persistent", template="template", prefix="TEST"))

        # Load with new instance
        manager2 = ProfileManager(self.profile_file)
        profile = manager2.get_profile("persistent")

        assert profile is not None
        assert profile.prefix == "TEST"

    def test_overwrite_existing_profile(self):
        manager = ProfileManager(self.profile_file)

        # Save original
        manager.save_profile(RenameProfile(name="profile", template="original", prefix="OLD"))

        # Overwrite
        manager.save_profile(RenameProfile(name="profile", template="updated", prefix="NEW"))

        profile = manager.get_profile("profile")

        assert profile.template == "updated"
        assert profile.prefix == "NEW"

    def test_load_corrupted_file(self):
        # Write invalid JSON
        with open(self.profile_file, "w") as f:
            f.write("not valid json {{{")

        # Should not crash
        manager = ProfileManager(self.profile_file)
        profiles = manager.get_all_profiles()

        assert len(profiles) == 0

    def test_empty_profile_file(self):
        manager = ProfileManager(self.profile_file)
        profiles = manager.get_all_profiles()

        assert len(profiles) == 0

    def test_export_single_profile(self):
        manager = ProfileManager(self.profile_file)
        manager.save_profile(RenameProfile(name="export_test", template="{artist} - {title}", prefix="PRE_"))

        export_file = Path(self.tmpdir) / "exported.json"
        result = manager.export_profile("export_test", str(export_file))

        assert result is True
        assert export_file.exists()

        with open(export_file, "r") as f:
            data = json.load(f)
        assert data.get("renamer_profile") is True
        assert data["profile"]["name"] == "export_test"
        assert data["profile"]["prefix"] == "PRE_"

    def test_export_nonexistent_profile(self):
        manager = ProfileManager(self.profile_file)
        export_file = Path(self.tmpdir) / "exported.json"

        result = manager.export_profile("nonexistent", str(export_file))

        assert result is False
        assert not export_file.exists()

    def test_export_all_profiles(self):
        manager = ProfileManager(self.profile_file)
        manager.save_profile(RenameProfile(name="p1", template="t1"))
        manager.save_profile(RenameProfile(name="p2", template="t2"))

        export_file = Path(self.tmpdir) / "all_exported.json"
        result = manager.export_all_profiles(str(export_file))

        assert result is True
        with open(export_file, "r") as f:
            data = json.load(f)
        assert data.get("renamer_profiles") is True
        assert "p1" in data["profiles"]
        assert "p2" in data["profiles"]

    def test_import_single_profile(self):
        export_file = Path(self.tmpdir) / "to_import.json"
        with open(export_file, "w") as f:
            json.dump({
                "renamer_profile": True,
                "version": "1.0",
                "profile": {
                    "name": "imported",
                    "template": "imported_template",
                    "prefix": "IMP_"
                }
            }, f)

        manager = ProfileManager(self.profile_file)
        success, message = manager.import_profile(str(export_file))

        assert success is True
        assert "1 profile" in message
        profile = manager.get_profile("imported")
        assert profile is not None
        assert profile.prefix == "IMP_"

    def test_import_multiple_profiles(self):
        export_file = Path(self.tmpdir) / "multi_import.json"
        with open(export_file, "w") as f:
            json.dump({
                "renamer_profiles": True,
                "version": "1.0",
                "profiles": {
                    "multi1": {"name": "multi1", "template": "t1"},
                    "multi2": {"name": "multi2", "template": "t2"}
                }
            }, f)

        manager = ProfileManager(self.profile_file)
        success, message = manager.import_profile(str(export_file))

        assert success is True
        assert "2 profile" in message
        assert manager.profile_exists("multi1")
        assert manager.profile_exists("multi2")

    def test_import_invalid_file(self):
        invalid_file = Path(self.tmpdir) / "invalid.json"
        with open(invalid_file, "w") as f:
            json.dump({"some": "data"}, f)

        manager = ProfileManager(self.profile_file)
        success, message = manager.import_profile(str(invalid_file))

        assert success is False
        assert "Invalid" in message

    def test_import_corrupted_file(self):
        corrupt_file = Path(self.tmpdir) / "corrupt.json"
        with open(corrupt_file, "w") as f:
            f.write("not valid json")

        manager = ProfileManager(self.profile_file)
        success, message = manager.import_profile(str(corrupt_file))

        assert success is False
        assert "Error" in message

    def test_export_import_roundtrip(self):
        manager = ProfileManager(self.profile_file)
        original = RenameProfile(
            name="roundtrip",
            template="{title}",
            prefix="A_",
            suffix="_B",
            use_regex=True,
            num_start=5,
            num_step=2,
            profile_type="audio"
        )
        manager.save_profile(original)

        export_file = Path(self.tmpdir) / "roundtrip.json"
        manager.export_profile("roundtrip", str(export_file))

        manager2 = ProfileManager(Path(self.tmpdir) / "new_profiles.json")
        manager2.import_profile(str(export_file))

        imported = manager2.get_profile("roundtrip")
        assert imported.template == original.template
        assert imported.prefix == original.prefix
        assert imported.suffix == original.suffix
        assert imported.use_regex == original.use_regex
        assert imported.num_start == original.num_start
        assert imported.profile_type == original.profile_type


class TestGetProfileManager:
    """Tests for global profile manager accessor."""

    def test_returns_instance(self):
        manager = get_profile_manager()
        assert manager is not None
        assert isinstance(manager, ProfileManager)

    def test_returns_singleton(self):
        manager1 = get_profile_manager()
        manager2 = get_profile_manager()

        assert manager1 is manager2
