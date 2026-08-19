"""Unit test configuration - adds fixtures to path for clean imports."""

import json
import sys
from pathlib import Path

import pytest
from unittest.mock import MagicMock

# Add fixtures directory to path for unit tests
fixtures_path = Path(__file__).parent.parent / "fixtures"
sys.path.insert(0, str(fixtures_path))

# Add src directory to path for mod_api import
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from mod_api.models import NumberParameterType, FilenameParameterType, EffectInfo, EffectInstance, Port  # noqa: E402


NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"


def get_json(response):
    """Extract JSON from response (JSONResponse or dict)."""
    if hasattr(response, 'body'):
        return json.loads(response.body.decode())
    return response


@pytest.fixture
def mock_client():
    """Create a mock ModHostClient."""
    from mock_client import MockModHostClient
    client = MockModHostClient()
    client.connect()
    return client


@pytest.fixture
def mock_store():
    """Create a mock PedalboardStore with real Pedalboard objects."""
    from mod_api.models import Pedalboard, EffectInstance, Connection
    from mod_api.storage.pedalboard_store import PedalboardStore

    # Create a real PedalboardStore with in-memory storage for pedalboards
    mock = MagicMock(spec=PedalboardStore)
    mock._pedalboards = {}  # id -> Pedalboard mapping
    mock._current_id = None
    mock._next_pedalboard_id = 1
    mock._next_effect_instance_id = 1

    def mock_create(name, duplicate_from_id=None):
        """Mock create that returns a Pedalboard object."""
        pb_id = mock._next_pedalboard_id
        mock._next_pedalboard_id += 1

        if duplicate_from_id and duplicate_from_id in mock._pedalboards:
            original = mock._pedalboards[duplicate_from_id]
            pb = Pedalboard(
                id=pb_id,
                name=name,
                file=f"{name.lower().replace(' ', '-')}.json",
                effects=original.effects.copy(),
                connections=original.connections.copy()
            )
        else:
            pb = Pedalboard(
                id=pb_id,
                name=name,
                file=f"{name.lower().replace(' ', '-')}.json"
            )

        mock._pedalboards[pb_id] = pb
        mock._current_id = pb_id
        return pb

    def mock_get(pedalboard_id):
        """Mock get that returns a real Pedalboard or None."""
        return mock._pedalboards.get(pedalboard_id)

    def mock_set_current(pedalboard_id):
        """Mock set_current that updates current_id."""
        if pedalboard_id not in mock._pedalboards:
            return False
        mock._current_id = pedalboard_id
        return True

    def mock_rename(pedalboard_id, new_name):
        """Mock rename that updates pedalboard name."""
        pb = mock._pedalboards.get(pedalboard_id)
        if pb is None:
            return None
        pb.name = new_name
        pb.file = f"{new_name.lower().replace(' ', '-')}.json"
        return pb

    def mock_delete(pedalboard_id):
        """Mock delete that removes pedalboard."""
        if pedalboard_id in mock._pedalboards:
            del mock._pedalboards[pedalboard_id]
            if mock._current_id == pedalboard_id:
                mock._current_id = None
            return True
        return False

    def mock_load_all():
        """Mock load_all that returns pedalboards from memory."""
        return list(mock._pedalboards.values())

    def mock_save_pedalboard(pedalboard):
        """Mock save - just a no-op."""
        pass

    def mock_allocate_effect_instance_id():
        """Mock allocate - returns incrementing IDs starting from 1."""
        effect_id = mock._next_effect_instance_id
        mock._next_effect_instance_id += 1
        return effect_id

    # Configure mock methods
    mock.create.side_effect = mock_create
    mock.get.side_effect = mock_get
    mock.set_current.side_effect = mock_set_current
    mock.rename.side_effect = mock_rename
    mock.delete.side_effect = mock_delete
    mock.get_current.side_effect = lambda: mock._pedalboards.get(mock._current_id)
    mock.load_all.side_effect = mock_load_all
    mock._save_pedalboard.side_effect = mock_save_pedalboard
    mock.allocate_effect_instance_id.side_effect = mock_allocate_effect_instance_id

    return mock


@pytest.fixture
def mock_registry():
    """Create a mock EffectsRegistry with NAM plugin info."""
    registry = MagicMock()
    registry.get.return_value = EffectInfo(
        uri=NAM_PLUGIN_URI,
        name="Neural Amp Modeler",
        ports=[
            Port(name="input", type="input"),
            Port(name="output", type="output")
        ],
        parameters={
            "model": FilenameParameterType(
                name="model",
                default=""
            ),
            "input_level": NumberParameterType(
                name="input_level",
                min=0.0,
                max=1.0,
                default=0.5
            ),
            "output_level": NumberParameterType(
                name="output_level",
                min=0.0,
                max=1.0,
                default=0.5
            )
        }
    )
    registry.get_all.return_value = [registry.get.return_value]
    return registry