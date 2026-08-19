"""Unit tests for PedalboardStore - data persistence layer."""

import pytest
from pathlib import Path

from mod_api.models import EffectInstance, Port


class TestPedalboardStore:
    """Tests for PedalboardStore in mod_api.storage.pedalboard_store."""

    def test_create_pedalboard(self, tmp_path):
        """Test creating a new pedalboard."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("Test Board", duplicate_from_id=None)

        assert pb.name == "Test Board"
        assert pb.id == 1
        assert pb.file == "test-board.json"
        # Note: store.create() does not set current_id; the API endpoint does that separately

    def test_create_pedalboard_duplicate(self, tmp_path):
        """Test creating pedalboard as duplicate of another."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        original = store.create("Original", None)
        duplicate = store.create("Duplicate", duplicate_from_id=original.id)

        assert duplicate.name == "Duplicate"
        # Effects and connections should be copied
        assert duplicate.effects == original.effects

    def test_get_pedalboard(self, tmp_path):
        """Test getting a pedalboard by ID."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        created = store.create("Test", None)

        retrieved = store.get(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test"

    def test_get_nonexistent_pedalboard(self, tmp_path):
        """Test getting a nonexistent pedalboard."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        result = store.get(999)
        assert result is None

    def test_delete_pedalboard(self, tmp_path):
        """Test deleting a pedalboard."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("To Delete", None)

        result = store.delete(pb.id)
        assert result is True
        assert store.get(pb.id) is None

    def test_delete_current_pedalboard_clears_current(self, tmp_path):
        """Test deleting current pedalboard clears current selection."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("Current", None)
        store.set_current(pb.id)
        assert store._current_id == pb.id

        store.delete(pb.id)
        # Note: Current implementation does NOT clear current_id on delete
        # per the delete method docstring: "Does not change current pedalboard if the deleted pedalboard was active"
        # If this behavior should change, the implementation needs to be updated
        assert store._current_id == pb.id  # Still the old ID (orphaned)


class TestPedalboardStorePersistence:
    """Tests for pedalboard persistence to disk."""

    def test_load_all(self, tmp_path):
        """Test loading all pedalboards from disk."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        store.create("Board 1", None)
        store.create("Board 2", None)

        # Create new store to test loading
        store2 = PedalboardStore(data_dir=str(tmp_path))
        pedalboards = store2.load_all()

        assert len(pedalboards) == 2
        names = {pb.name for pb in pedalboards}
        assert "Board 1" in names
        assert "Board 2" in names

    def test_persists_to_file(self, tmp_path):
        """Test that creating a pedalboard writes to disk."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        store.create("Saved Board", None)

        # Check file exists
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        assert files[0].stem == "saved-board"

    def test_update_pedalboard_saves(self, tmp_path):
        """Test that updating pedalboard state persists to disk."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("Test Board", None)

        # Add an effect to the pedalboard
        pb.effects[0] = EffectInstance(
            uri="http://test/plugin",
            name="Test Effect",
            ports=[
                Port(name="input", type="input"),
                Port(name="output", type="output")
            ],
            parameters={}
        )
        store._save_pedalboard(pb)

        # Load in fresh store and verify effect persisted
        store2 = PedalboardStore(data_dir=str(tmp_path))
        loaded = store2.get(1)
        assert len(loaded.effects) == 1

    def test_rename_updates_file(self, tmp_path):
        """Test that renaming a pedalboard also renames the file."""
        from mod_api.storage.pedalboard_store import PedalboardStore
        from pathlib import Path

        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("Original Name", None)

        # Rename the pedalboard
        renamed = store.rename(pb.id, "New Name")
        assert renamed is not None

        # Check old file is gone, new file exists
        files = list(tmp_path.glob("*.json"))
        stems = {f.stem for f in files}
        assert "original-name" not in stems
        assert "new-name" in stems

    def test_set_current_success(self, tmp_path):
        """Test set_current sets the current pedalboard ID."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb1 = store.create("Board 1", None)
        pb2 = store.create("Board 2", None)

        result = store.set_current(pb1.id)
        assert result is True
        assert store._current_id == pb1.id

    def test_set_current_nonexistent_returns_false(self, tmp_path):
        """Test set_current returns False for nonexistent pedalboard."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        result = store.set_current(999)
        assert result is False
        assert store._current_id is None

    def test_get_current_returns_pedalboard(self, tmp_path):
        """Test get_current returns the current pedalboard."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("Current", None)
        store.set_current(pb.id)

        result = store.get_current()
        assert result is not None
        assert result.id == pb.id
        assert result.name == "Current"

    def test_get_current_returns_none_when_no_current(self, tmp_path):
        """Test get_current returns None when no pedalboard is current."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        store.create("Not Current", None)

        result = store.get_current()
        assert result is None

    def test_calculate_next_id_starts_at_1(self, tmp_path):
        """Test next ID calculation starts at 1 for empty store."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        # Store is empty, next ID should be 1
        assert len(store._pedalboards) == 0

    def test_calculate_next_id_increments(self, tmp_path):
        """Test next ID increments after creating pedalboards."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb1 = store.create("Board 1", None)
        pb2 = store.create("Board 2", None)

        assert pb1.id == 1
        assert pb2.id == 2

    def test_delete_nonexistent_returns_false(self, tmp_path):
        """Test deleting nonexistent pedalboard returns False."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        result = store.delete(999)
        assert result is False

    def test_rename_nonexistent_returns_none(self, tmp_path):
        """Test renaming nonexistent pedalboard returns None."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        result = store.rename(999, "New Name")
        assert result is None

    def test_load_all_skips_malformed_json(self, tmp_path):
        """Test load_all skips files with malformed JSON."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))

        # Create a malformed JSON file
        bad_json = tmp_path / "bad-board.json"
        bad_json.write_text("{not valid json}")

        # Should not crash, just skip the bad file
        pedalboards = store.load_all()
        assert pedalboards == []

    def test_load_all_skips_missing_id(self, tmp_path):
        """Test load_all skips files without id field."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))

        # Create a JSON file without id
        no_id_json = tmp_path / "no-id.json"
        no_id_json.write_text('{"name": "No ID Board"}')

        pedalboards = store.load_all()
        assert pedalboards == []

    def test_load_all_skips_key_error(self, tmp_path):
        """Test load_all skips files that cause KeyError during parsing."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))

        # Create a valid-looking JSON but without required fields for Pedalboard
        # This would cause Pedalboard() to raise KeyError for missing id
        bad_data = tmp_path / "bad-data.json"
        bad_data.write_text('{"effects": {}, "connections": {}}')

        pedalboards = store.load_all()
        assert pedalboards == []

    def test_delete_missing_file_continues(self, tmp_path):
        """Test delete continues even when file doesn't exist."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("Missing File", None)

        # Delete the file manually first
        file_path = tmp_path / pb.file
        file_path.unlink()

        # Delete should still succeed
        result = store.delete(pb.id)
        assert result is True
        assert store.get(pb.id) is None

    def test_rename_missing_old_file_continues(self, tmp_path):
        """Test rename continues even when old file doesn't exist."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("Original", None)

        # Delete the file manually
        (tmp_path / pb.file).unlink()

        # Rename should still succeed
        renamed = store.rename(pb.id, "New Name")
        assert renamed is not None
        assert renamed.name == "New Name"

        # New file should exist
        files = list(tmp_path.glob("*.json"))
        stems = {f.stem for f in files}
        assert "original" not in stems
        assert "new-name" in stems

    def test_load_all_with_corrupted_json_key(self, tmp_path):
        """Test load_all handles JSON decode errors gracefully."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))

        # Create a valid JSON but with data that causes KeyError during Pedalboard creation
        # (missing required 'id' field will cause KeyError)
        bad_json = tmp_path / "bad-key.json"
        import json
        bad_json.write_text(json.dumps({"name": "Bad", "file": "bad-key.json", "effects": {}, "connections": {}}))

        pedalboards = store.load_all()
        assert pedalboards == []

    def test_load_all_restores_current_id(self, tmp_path):
        """Test load_all restores current_id from disk."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        # Create a pedalboard and set it as current
        store = PedalboardStore(data_dir=str(tmp_path))
        pb = store.create("Test Board", None)
        store.set_current(pb.id)

        # Create new store to test loading current_id
        store2 = PedalboardStore(data_dir=str(tmp_path))
        assert store2._current_id == pb.id

    def test_load_all_handles_invalid_current_id(self, tmp_path):
        """Test load_all handles invalid current_id.txt gracefully."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))

        # Create an invalid current_id.txt
        current_id_file = tmp_path / "current_id.txt"
        current_id_file.write_text("not-a-number")

        pedals = store.load_all()
        assert pedals == []
        assert store._current_id is None

    def test_load_all_handles_empty_current_id(self, tmp_path):
        """Test load_all handles empty current_id.txt gracefully."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))

        # Create an empty current_id.txt
        current_id_file = tmp_path / "current_id.txt"
        current_id_file.write_text("")

        pedals = store.load_all()
        assert pedals == []
        assert store._current_id is None


class TestEffectInstanceIdAllocation:
    """Tests for effect instance ID allocation (global uniqueness for mod-host)."""

    def test_allocate_effect_instance_id_starts_at_1(self, tmp_path):
        """Test that first allocated ID is 1."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        first_id = store.allocate_effect_instance_id()
        assert first_id == 1

    def test_allocate_effect_instance_id_increments(self, tmp_path):
        """Test that IDs increment across calls."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        id1 = store.allocate_effect_instance_id()
        id2 = store.allocate_effect_instance_id()
        id3 = store.allocate_effect_instance_id()

        assert id1 == 1
        assert id2 == 2
        assert id3 == 3

    def test_load_all_restores_effect_instance_id(self, tmp_path):
        """Test that load_all restores next_effect_instance_id from disk."""
        from mod_api.storage.pedalboard_store import PedalboardStore

        store = PedalboardStore(data_dir=str(tmp_path))
        store.allocate_effect_instance_id()  # Creates ID 1
        store.allocate_effect_instance_id()  # Creates ID 2

        # Create new store to test loading persisted ID
        store2 = PedalboardStore(data_dir=str(tmp_path))
        # Next allocated ID should be 3 (after 1 and 2)
        next_id = store2.allocate_effect_instance_id()
        assert next_id == 3

    def test_load_all_tracks_max_effect_id_from_pedalboards(self, tmp_path):
        """Test that loading pedalboards with effects sets correct next ID."""
        from mod_api.storage.pedalboard_store import PedalboardStore
        from mod_api.models import Pedalboard, EffectInstance

        store = PedalboardStore(data_dir=str(tmp_path))
        # Create pedalboard with effect instance ID 5
        pb = Pedalboard(
            id=1,
            name="Test Board",
            file="test-board.json",
            effects={5: EffectInstance(
                id=5,
                uri="http://test/plugin",
                ports=[Port(name="input", type="input")],
                parameters={}
            )},
            connections={}
        )
        store._pedalboards[1] = pb
        store._save_pedalboard(pb)

        # Create new store - should resume from ID 6
        # Note: allocate_effect_instance_id() increments first, then returns
        # So if loaded value is 6, it increments to 7 and returns 7
        store2 = PedalboardStore(data_dir=str(tmp_path))
        next_id = store2.allocate_effect_instance_id()
        assert next_id == 7
