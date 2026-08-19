"""Pedalboard persistence layer."""

import json
import os
from pathlib import Path
from typing import Optional

from ..models import Pedalboard


class PedalboardStore:
    """Manages pedalboard persistence to disk.

    Handles loading, saving, creating, and deleting pedalboard configurations.
    Maintains in-memory state of pedalboards and tracks the current pedalboard.

    Attributes:
        data_dir: Directory where pedalboard JSON files are stored.
        _pedalboards: In-memory cache of loaded pedalboards by ID.
        _current_id: ID of the currently active pedalboard.
        _next_effect_instance_id: Next available effect instance ID for mod-host.
    """

    def __init__(self, data_dir: str = "/var/mod/pedalboards") -> None:
        """Initialize the pedalboard store.

        Args:
            data_dir: Directory path for storing pedalboard JSON files.
                      The directory will be created if it doesn't exist.
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._pedalboards: dict[int, Pedalboard] = {}
        self._current_id: Optional[int] = None
        # Track the next available effect instance ID globally (mod-host requires uniqueness)
        self._next_effect_instance_id: int = 0
        self.load_all()

    def _calculate_next_id(self) -> int:
        """Calculate the next available pedalboard ID.

        Uses loaded pedalboards to determine the highest used ID
        and returns the next sequential ID.

        Returns:
            The next available integer ID for a new pedalboard.
        """
        if not self._pedalboards:
            return 1
        return max(self._pedalboards.keys()) + 1

    def load_all(self) -> list[Pedalboard]:
        """Load all pedalboards from disk.

        Reads all JSON files in the data directory and populates the
        in-memory cache. Restores the current pedalboard ID from disk.

        Returns:
            List of all Pedalboard objects loaded from disk.
        """
        # Restore current_id and next_effect_instance_id from persistent storage
        try:
            with open(self.data_dir / "current_id.txt") as f:
                content = f.read().strip()
                if content:
                    self._current_id = int(content)
        except (FileNotFoundError, ValueError):
            pass

        # Restore next effect instance ID (for global uniqueness across pedalboards)
        try:
            with open(self.data_dir / "next_effect_instance_id.txt") as f:
                content = f.read().strip()
                if content:
                    self._next_effect_instance_id = int(content)
        except (FileNotFoundError, ValueError):
            pass

        # Load pedalboards directly into the in-memory cache
        for file in self.data_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                    pedalboard_id = data.get('id')
                    if pedalboard_id is not None:
                        pb = Pedalboard(**data)
                        self._pedalboards[pb.id] = pb
                        # Track max effect instance ID for global uniqueness
                        if pb.effects:
                            max_effect_id = max(pb.effects.keys())
                            self._next_effect_instance_id = max(
                                self._next_effect_instance_id, max_effect_id + 1
                            )
            except (json.JSONDecodeError, KeyError):
                continue

        return list(self._pedalboards.values())

    def allocate_effect_instance_id(self) -> int:
        """Get the next available effect instance ID.

        Returns a globally unique ID for effect instances, tracking the highest
        used ID across all pedalboards. This ensures mod-host doesn't encounter
        duplicate instance IDs.

        Returns:
            The next available integer ID for an effect instance.
        """
        self._next_effect_instance_id += 1
        self._save_effect_instance_id()
        return self._next_effect_instance_id

    def _save_effect_instance_id(self) -> None:
        """Persist the next effect instance ID to disk."""
        with open(self.data_dir / "next_effect_instance_id.txt", 'w') as f:
            f.write(str(self._next_effect_instance_id))

    def get(self, pedalboard_id: int) -> Optional[Pedalboard]:
        """Get a specific pedalboard by ID.

        Args:
            pedalboard_id: The ID of the pedalboard to retrieve.

        Returns:
            The Pedalboard if found, None otherwise.
        """
        return self._pedalboards.get(pedalboard_id)

    def create(self, name: str, duplicate_from_id: Optional[int] = None) -> Pedalboard:
        """Create a new pedalboard, optionally duplicating another.

        Args:
            name: Human-readable name for the new pedalboard.
            duplicate_from_id: Optional ID of an existing pedalboard to copy
                            effects and connections from.

        Returns:
            The newly created Pedalboard object.
        """
        pedalboard_id = self._calculate_next_id()
        file = f"{name.lower().replace(' ', '-')}.json"

        # Create pedalboard
        if duplicate_from_id and duplicate_from_id in self._pedalboards:
            source = self._pedalboards[duplicate_from_id]
            new_pedalboard = Pedalboard(
                id=pedalboard_id,
                name=name,
                file=file,
                effects=source.effects.copy(),
                connections=source.connections.copy()
            )
        else:
            new_pedalboard = Pedalboard(
                id=pedalboard_id,
                name=name,
                file=file
            )

        self._pedalboards[pedalboard_id] = new_pedalboard
        self._save_pedalboard(new_pedalboard)
        return new_pedalboard

    def delete(self, pedalboard_id: int) -> bool:
        """Delete a pedalboard by ID.

        Removes the pedalboard file from disk and clears it from the
        in-memory cache. Does not change current pedalboard if the
        deleted pedalboard was active.

        Args:
            pedalboard_id: The ID of the pedalboard to delete.

        Returns:
            True if deleted successfully, False if pedalboard didn't exist.
        """
        pb = self._pedalboards.get(pedalboard_id)
        if not pb:
            return False

        filepath = self.data_dir / pb.file

        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass

        del self._pedalboards[pedalboard_id]
        return True

    def rename(self, pedalboard_id: int, new_name: str) -> Optional[Pedalboard]:
        """Rename a pedalboard.

        Updates both the in-memory pedalboard and persists the change to disk.
        Also renames the file to match the new name.

        Args:
            pedalboard_id: The ID of the pedalboard to rename.
            new_name: The new human-readable name.

        Returns:
            The renamed Pedalboard if successful, None if not found.
        """
        pb = self._pedalboards.get(pedalboard_id)
        if not pb:
            return None

        old_file = self.data_dir / pb.file
        pb.name = new_name
        pb.file = f"{new_name.lower().replace(' ', '-')}.json"
        new_file = self.data_dir / pb.file

        self._save_pedalboard(pb)

        # Remove old file if it exists and is different from new file
        if old_file != new_file:
            try:
                os.remove(old_file)
            except FileNotFoundError:
                pass

        return pb

    def set_current(self, pedalboard_id: int) -> bool:
        """Set the current active pedalboard.

        Updates the current_id and persists the change.

        Args:
            pedalboard_id: The ID of the pedalboard to set as current.

        Returns:
            True if successful, False if pedalboard doesn't exist.
        """
        if pedalboard_id not in self._pedalboards:
            return False
        self._current_id = pedalboard_id
        self._save_current_id()
        return True

    def get_current(self) -> Optional[Pedalboard]:
        """Get the currently active pedalboard.

        Returns:
            The current Pedalboard if one is selected, None otherwise.
        """
        if not self._current_id:
            return None
        return self._pedalboards.get(self._current_id)

    def _save_pedalboard(self, pedalboard: Pedalboard) -> None:
        """Save a pedalboard to disk.

        Writes the pedalboard as JSON to its associated file, including
        the ID in the output for persistence.

        Args:
            pedalboard: The Pedalboard to save.
        """
        filepath = self.data_dir / pedalboard.file
        data = pedalboard.model_dump()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def _save_current_id(self) -> None:
        """Persist the current pedalboard ID to disk."""
        if self._current_id is not None:
            with open(self.data_dir / "current_id.txt", 'w') as f:
                f.write(str(self._current_id))
