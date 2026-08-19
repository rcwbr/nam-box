"""Mock ModHostClient for unit testing - records commands and returns predefined responses."""

import os


class MockModHostClient:
    """Mock client that records commands and returns configured responses.

    Use for testing API endpoints - verify correct mod-host protocol commands are sent.
    """

    ERR_INSTANCE_INVALID = -1
    ERR_INSTANCE_ALREADY_EXISTS = -2
    ERR_INSTANCE_NON_EXISTS = -3
    ERR_INSTANCE_UNLICENSED = -4
    ERR_LV2_INVALID_URI = -101
    ERR_LV2_INSTANTIATION = -102
    ERR_LV2_INVALID_PARAM_SYMBOL = -103
    ERR_JACK_PORT_CONNECTION = -205
    ERR_JACK_PORT_DISCONNECTION = -206
    ERR_INVALID_OPERATION = -999

    def __init__(self):
        # Record all commands sent
        self.commands_sent: list[str] = []
        # Predefined responses: command_pattern -> (status, value)
        self._responses: dict[str, tuple[int, str | None]] = {}
        # Default response for unmatched commands
        self._default_response: tuple[int, str | None] = (0, None)

    def connect(self) -> None:
        """Mock connect - no-op."""
        pass

    def add_plugin(self, uri: str, instance: int) -> int:
        """Mock add_plugin - returns configured response."""
        command = f'add "{uri}" {instance}'
        return self._get_response(command)

    def remove_plugin(self, instance: int) -> int:
        """Mock remove_plugin - returns configured response."""
        command = f'remove {instance}'
        return self._get_response(command)

    def connect_ports(self, source: str, destination: str) -> int:
        """Mock connect_ports - returns configured response."""
        command = f'connect "{source}" "{destination}"'
        return self._get_response(command)

    def disconnect_ports(self, source: str, destination: str) -> int:
        """Mock disconnect_ports - returns configured response."""
        command = f'disconnect "{source}" "{destination}"'
        return self._get_response(command)

    def param_set(self, instance: int, symbol: str, value: float) -> int:
        """Mock param_set - returns configured response."""
        command = f'param_set {instance} {symbol} {value}'
        return self._get_response(command)

    def param_get(self, instance: int, symbol: str) -> tuple[int, float]:
        """Mock param_get - returns configured response."""
        command = f'param_get {instance} {symbol}'
        status, value = self._get_response_with_value(command)
        return status, float(value) if value else 0.0

    def patch_set(self, instance: int, property_uri: str, value: str) -> int:
        """Mock patch_set - returns configured response."""
        command = f'patch_set {instance} {property_uri} {value}'
        return self._get_response(command)

    def patch_get(self, instance: int, property_uri: str) -> tuple[int, str | None]:
        """Mock patch_get - returns configured response."""
        command = f'patch_get {instance} {property_uri}'
        return self._get_response_with_value(command)

    def _get_response(self, command: str) -> int:
        """Get response for a command without recording (used by wrapper methods)."""
        self.commands_sent.append(command)
        status, _ = self._get_response_with_value(command)
        return status

    def _get_response_with_value(self, command: str) -> tuple[int, str | None]:
        """Get response tuple for a command."""
        # Check for exact match first
        if command in self._responses:
            return self._responses[command]

        # Check for pattern matches (e.g., "add *" to match any add command)
        for pattern, response in self._responses.items():
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if command.startswith(prefix):
                    return response

        return self._default_response

    def send_command(self, command: str) -> tuple[int, str | None]:
        """Record command and return configured or default response."""
        self.commands_sent.append(command)
        return self._get_response_with_value(command)

    # === Response configuration methods ===

    def set_response(self, command_pattern: str, status: int, value: str | None = None):
        """Set a response for a specific command or command pattern.

        For patterns, use "*" suffix to match commands starting with the pattern.
        Example: client.set_response('add *', 0) matches any "add" command.
        """
        self._responses[command_pattern] = (status, value)

    def set_default_response(self, status: int, value: str | None = None):
        """Set the default response for unmatched commands."""
        self._default_response = (status, value)

    def reset_responses(self):
        """Clear all predefined responses."""
        self._responses.clear()
        self._default_response = (0, None)

    def bypass(self, instance: int, enabled: bool) -> int:
        """Mock bypass - records command and returns success."""
        self.commands_sent.append(f'bypass {instance} {1 if enabled else 0}')
        return 0

    def enumerate(self) -> 'tuple[int, list[str]]':
        """Mock enumerate - returns list of system ports.

        Reads system ports from SYSTEM_PORTS environment variable (comma-separated)
        or uses JACK dummy defaults (system:capture_1, system:capture_2,
        system:playback_1, system:playback_2).

        Note: This no longer accepts set_response configuration since enumerate
        now reads from the environment instead of mod-host.
        """
        self.commands_sent.append('enumerate')
        # Get system ports from environment or use JACK dummy defaults
        system_ports_str = os.environ.get(
            "SYSTEM_PORTS",
            "system:capture_1,system:capture_2,system:playback_1,system:playback_2"
        )
        ports = [p.strip() for p in system_ports_str.split(",") if p.strip()]
        return 0, ports

    def close(self) -> None:
        """Mock close - no-op."""
        pass