"""Unit tests for MockModHostClient - verifies commands are recorded for testing."""

import pytest

NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
NAM_MODEL_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"


class TestMockModHostClientRecordsCommands:
    """Tests verifying MockModHostClient records raw commands correctly."""

    def test_send_command_records_raw_command(self):
        """Test that send_command records the exact command sent."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.connect()

        client.send_command(f'add "{NAM_PLUGIN_URI}" 0')
        assert len(client.commands_sent) == 1
        assert client.commands_sent[0] == f'add "{NAM_PLUGIN_URI}" 0'

    def test_remove_command_recorded(self):
        """Test that remove command is recorded correctly."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.connect()

        client.send_command("remove 1")
        assert len(client.commands_sent) == 1
        assert client.commands_sent[0] == "remove 1"

    def test_param_set_command_recorded(self):
        """Test that param_set command is recorded correctly."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.connect()

        client.send_command("param_set 0/input_level 0.75")
        assert len(client.commands_sent) == 1
        assert client.commands_sent[0] == "param_set 0/input_level 0.75"

    def test_multiple_commands_recorded(self):
        """Test that multiple commands are all recorded."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.connect()

        client.send_command(f'add "{NAM_PLUGIN_URI}" 0')
        client.send_command("param_set 0/input_level 0.5")

        assert len(client.commands_sent) == 2
        assert "add" in client.commands_sent[0]
        assert "param_set" in client.commands_sent[1]


class TestMockModHostClientResponses:
    """Tests verifying MockModHostClient returns configured responses."""

    def test_default_response_returns_zero(self):
        """Test that default response is status 0, None value."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        status, value = client.send_command("any command")
        assert status == 0
        assert value is None

    def test_predefined_exact_response(self):
        """Test that exact predefined responses are used."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.set_response('add "http://test" 0', 1, "test_value")

        status, value = client.send_command('add "http://test" 0')
        assert status == 1
        assert value == "test_value"

    def test_predefined_pattern_response(self):
        """Test that pattern responses work with * suffix."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.set_response('add *', MockModHostClient.ERR_INSTANCE_ALREADY_EXISTS, None)

        status, value = client.send_command(f'add "{NAM_PLUGIN_URI}" 0')
        assert status == MockModHostClient.ERR_INSTANCE_ALREADY_EXISTS
        assert value is None

    def test_custom_default_response(self):
        """Test that custom default response is used."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.set_default_response(-1, "error")

        status, value = client.send_command("unknown command")
        assert status == -1
        assert value == "error"

    def test_response_pattern_matching_multiple(self):
        """Test that * suffix matches various connect commands."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.set_response('connect *', 0, None)

        status1, _ = client.send_command('connect "system:capture_1" "effect_0:input"')
        status2, _ = client.send_command('connect "system:playback_1" "effect_1:output"')

        assert status1 == 0
        assert status2 == 0

    def test_reset_responses_clears_all(self):
        """Test that reset_responses clears predefined responses."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.set_response('add *', MockModHostClient.ERR_INSTANCE_ALREADY_EXISTS)

        client.reset_responses()

        # After reset, should get default response
        status, _ = client.send_command('add "uri" 0')
        assert status == 0  # Default response


class TestRealModHostClient:
    """Tests for real ModHostClient class methods."""

    def test_context_manager_enters_and_exits(self):
        """Test __enter__ calls connect and __exit__ calls close."""
        from unittest.mock import patch, MagicMock
        from mod_api.utils.mod_host_client import ModHostClient

        with patch.object(ModHostClient, 'connect') as mock_connect, \
             patch.object(ModHostClient, 'close') as mock_close:
            with ModHostClient() as client:
                mock_connect.assert_called_once()
            mock_close.assert_called_once()

    def test_close_idempotent_when_socket_none(self):
        """Test close() is safe when socket is None."""
        from mod_api.utils.mod_host_client import ModHostClient

        client = ModHostClient()
        client.socket = None
        # Should not raise
        client.close()
        assert client.socket is None

    def test_send_command_raises_when_not_connected(self):
        """Test send_command raises RuntimeError when not connected."""
        from mod_api.utils.mod_host_client import ModHostClient

        client = ModHostClient()
        client.socket = None

        import pytest
        with pytest.raises(RuntimeError, match="Not connected to mod-host"):
            client.send_command("test")

    def test_send_command_raises_on_unexpected_response(self):
        """Test send_command raises on non-resp format response."""
        from mod_api.utils.mod_host_client import ModHostClient
        from unittest.mock import MagicMock
        import pytest

        client = ModHostClient()
        client.socket = MagicMock()
        client.socket.recv.return_value = b"unexpected_format"

        with pytest.raises(RuntimeError, match="Unexpected response"):
            client.send_command("test")

    def test_send_command_empty_response_raises_runtimeerror(self):
        """Test send_command raises RuntimeError on empty response."""
        from mod_api.utils.mod_host_client import ModHostClient
        from unittest.mock import MagicMock
        import pytest

        client = ModHostClient()
        client.socket = MagicMock()
        client.socket.recv.return_value = b""

        # Empty response raises RuntimeError
        with pytest.raises(RuntimeError, match="Empty response"):
            client.send_command("test")

    def test_preset_save_command_format(self):
        """Test preset_save command format via send_command."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        # preset_save not in mock, test via send_command
        client.send_command('preset_save 1 MyPreset /presets preset.ttl')

        assert len(client.commands_sent) == 1
        assert client.commands_sent[0] == 'preset_save 1 MyPreset /presets preset.ttl'

    def test_bypass_records_correct_command(self):
        """Test bypass records correct command."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.bypass(1, True)
        client.bypass(0, False)

        assert client.commands_sent[0] == "bypass 1 1"
        assert client.commands_sent[1] == "bypass 0 0"

    def test_param_get_returns_zero_when_no_value(self):
        """Test param_get returns 0.0 when no value present."""
        from mock_client import MockModHostClient

        client = MockModHostClient()
        client.set_response('param_get 0 gain', 0, None)

        status, value = client.param_get(0, "gain")
        assert status == 0
        assert value == 0.0

    def test_enumerate_returns_default_ports_when_no_env(self):
        """Test enumerate returns JACK dummy default ports when SYSTEM_PORTS not set."""
        from mock_client import MockModHostClient
        import os
        from unittest.mock import patch

        client = MockModHostClient()
        # Clear SYSTEM_PORTS env var for this test
        with patch.dict(os.environ, {}, clear=True):
            if "SYSTEM_PORTS" in os.environ:
                del os.environ["SYSTEM_PORTS"]
            status, items = client.enumerate()

        assert status == 0
        # Default JACK dummy ports
        assert items == ['system:capture_1', 'system:capture_2',
                         'system:playback_1', 'system:playback_2']

    def test_enumerate_reads_from_environment(self):
        """Test enumerate reads system ports from SYSTEM_PORTS environment variable."""
        from mock_client import MockModHostClient
        import os
        from unittest.mock import patch

        client = MockModHostClient()
        with patch.dict(os.environ, {"SYSTEM_PORTS": "system:capture_1,system:playback_1"}):
            status, items = client.enumerate()

        assert status == 0
        assert items == ['system:capture_1', 'system:playback_1']