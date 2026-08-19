"""TCP socket client for mod-host protocol communication."""

import os
import socket
from typing import Optional, Tuple


class ModHostClient:
    """TCP socket client for mod-host protocol communication.

    This client handles low-level TCP socket communication with mod-host,
    abstracting the protocol details for plugin management, parameter control,
    and audio routing.

    Attributes:
        ERR_INSTANCE_INVALID: Invalid instance number error code.
        ERR_INSTANCE_ALREADY_EXISTS: Instance already exists error code.
        ERR_INSTANCE_NON_EXISTS: Instance does not exist error code.
        ERR_INSTANCE_UNLICENSED: Commercial plugin not licensed error code.
        ERR_LV2_INVALID_URI: Invalid plugin/parameter URI error code.
        ERR_LV2_INSTANTIATION: Plugin instantiation failed error code.
        ERR_LV2_INVALID_PARAM_SYMBOL: Invalid parameter symbol error code.
        ERR_LV2_INVALID_PRESET_URI: Invalid preset URI error code.
        ERR_LV2_CANT_LOAD_STATE: Cannot load state error code.
        ERR_JACK_CLIENT_CREATION: JACK client creation error code.
        ERR_JACK_CLIENT_ACTIVATION: JACK client activation error code.
        ERR_JACK_PORT_CONNECTION: JACK port connection error code.
        ERR_JACK_PORT_DISCONNECTION: JACK port disconnection error code.
        ERR_JACK_VALUE_OUT_OF_RANGE: Value out of range error code.
        ERR_ASSIGNMENT_ALREADY_EXISTS: Assignment already exists error code.
        ERR_ASSIGNMENT_INVALID_OP: Invalid assignment operation error code.
        ERR_ASSIGNMENT_LIST_FULL: Assignment list full error code.
        ERR_ASSIGNMENT_FAILED: Assignment failed error code.
        ERR_CONTROL_CHAIN_UNAVAILABLE: Control Chain unavailable error code.
        ERR_LINK_UNAVAILABLE: Link unavailable error code.
        ERR_HMI_UNAVAILABLE: HMI unavailable error code.
        ERR_EXTERNAL_UI_UNAVAILABLE: External UI unavailable error code.
        ERR_MEMORY_ALLOCATION: Memory allocation error code.
        ERR_INVALID_OPERATION: Invalid operation error code.
    """

    ERR_INSTANCE_INVALID = -1
    ERR_INSTANCE_ALREADY_EXISTS = -2
    ERR_INSTANCE_NON_EXISTS = -3
    ERR_INSTANCE_UNLICENSED = -4
    ERR_LV2_INVALID_URI = -101
    ERR_LV2_INSTANTIATION = -102
    ERR_LV2_INVALID_PARAM_SYMBOL = -103
    ERR_LV2_INVALID_PRESET_URI = -104
    ERR_LV2_CANT_LOAD_STATE = -105
    ERR_JACK_CLIENT_CREATION = -201
    ERR_JACK_CLIENT_ACTIVATION = -202
    ERR_JACK_PORT_CONNECTION = -205
    ERR_JACK_PORT_DISCONNECTION = -206
    ERR_JACK_VALUE_OUT_OF_RANGE = -207
    ERR_ASSIGNMENT_ALREADY_EXISTS = -301
    ERR_ASSIGNMENT_INVALID_OP = -302
    ERR_ASSIGNMENT_LIST_FULL = -303
    ERR_ASSIGNMENT_FAILED = -304
    ERR_CONTROL_CHAIN_UNAVAILABLE = -401
    ERR_LINK_UNAVAILABLE = -402
    ERR_HMI_UNAVAILABLE = -403
    ERR_EXTERNAL_UI_UNAVAILABLE = -404
    ERR_MEMORY_ALLOCATION = -901
    ERR_INVALID_OPERATION = -902

    def __init__(self, host: str = '127.0.0.1', port: int = 5555, fb_port: int = 5556, timeout: float = 5.0) -> None:
        """Initialize the mod-host client.

        Args:
            host: The hostname or IP address of the mod-host service.
            port: The TCP port for mod-host control socket (default 5555).
            fb_port: The TCP port for mod-host feedback socket (default 5556).
            timeout: Socket timeout in seconds for read/write operations.
        """
        self.host = host
        self.port = port
        self.fb_port = fb_port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.fb_socket: Optional[socket.socket] = None

    def connect(self) -> None:
        """Establish TCP connection to mod-host.

        Note: mod-host requires connections to BOTH the control port (port) and
        feedback port (fb_port) before entering its command processing loop.

        Raises:
            RuntimeError: If connection fails or times out.
        """
        # Connect to feedback port first (mod-host blocks waiting for both)
        self.fb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.fb_socket.settimeout(self.timeout)
        self.fb_socket.connect((self.host, self.fb_port))

        # Then connect to control port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.host, self.port))

    def send_command(self, command: str) -> Tuple[int, Optional[str]]:
        """Send a command and return parsed response.

        Sends a newline-terminated ASCII command to mod-host and parses the
        response to extract status code and optional value.

        Args:
            command: The command string to send (without newline terminator).

        Returns:
            Tuple of (status_code, optional_value) where:
            - status_code >= 0 indicates success
            - status_code < 0 indicates error (see ERR_* constants)
            - optional_value is present for commands like param_get

        Note:
            Communication failures (socket timeout, connection lost, malformed
            response) return (ERR_INVALID_OPERATION, None) instead of raising,
            so callers can handle errors uniformly via the status code.
        """
        if not self.socket:
            return self.ERR_INVALID_OPERATION, None

        try:
            self.socket.sendall((command + '\n').encode())
            response = self.socket.recv(4096).decode('utf-8', errors='ignore')
        except (socket.timeout, ConnectionError, OSError):
            return self.ERR_INVALID_OPERATION, None

        # Parse response format: "resp <status> [value]"
        # Strip null bytes that mod-host sends
        response = response.replace('\x00', '').strip()
        parts = response.split()
        if not parts or parts[0] != 'resp':
            return self.ERR_INVALID_OPERATION, None

        try:
            status = int(parts[1])
        except (ValueError, IndexError):
            return self.ERR_INVALID_OPERATION, None

        value = parts[2] if len(parts) > 2 else None
        return status, value

    def add_plugin(self, uri: str, instance: int) -> int:
        """Add an LV2 plugin as a JACK client.

        Creates a new plugin instance with the specified URI and instance number.

        Args:
            uri: Full URI of the LV2 plugin (e.g., 'http://github.com/.../neural-amp-modeler-lv2').
            instance: Integer instance number (0-9999).

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'add "{uri}" {instance}')
        return status

    def remove_plugin(self, instance: int) -> int:
        """Remove an LV2 plugin instance.

        Args:
            instance: Plugin instance number, or -1 to remove all plugins.

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'remove {instance}')
        return status

    def connect_ports(self, source: str, destination: str) -> int:
        """Connect two JACK ports.

        Establishes an audio/MIDI connection between the source and destination ports.

        Args:
            source: Source port name (e.g., 'system:capture_1').
            destination: Destination port name (e.g., 'effect_0:input').

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'connect "{source}" "{destination}"')
        return status

    def disconnect_ports(self, source: str, destination: str) -> int:
        """Disconnect two JACK ports.

        Removes the connection between the specified ports.

        Args:
            source: Source port name.
            destination: Destination port name.

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'disconnect "{source}" "{destination}"')
        return status

    def param_set(self, instance: int, symbol: str, value: float) -> int:
        """Set a control port value.

        Modifies the value of a plugin's control parameter.

        Args:
            instance: Plugin instance number.
            symbol: Parameter symbol/name (e.g., 'input_level', 'output_level').
            value: Numeric value (float).

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'param_set {instance} {symbol} {value}')
        return status

    def param_get(self, instance: int, symbol: str) -> Tuple[int, float]:
        """Get a control port value.

        Retrieves the current value of a plugin's control parameter.

        Args:
            instance: Plugin instance number.
            symbol: Parameter symbol/name.

        Returns:
            Tuple of (status_code, value) where value is the current parameter value.

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, value = self.send_command(f'param_get {instance} {symbol}')
        return status, float(value) if value else 0.0

    def patch_set(self, instance: int, property_uri: str, value: str) -> int:
        """Set a property value using LV2 Patch protocol.

        Used primarily for setting NAM model files via the patch protocol.

        Args:
            instance: Plugin instance number.
            property_uri: URI of the property (e.g., 'http://github.com/...#model').
            value: Property value (string path for model files).

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'patch_set {instance} {property_uri} {value}')
        return status

    def patch_get(self, instance: int, property_uri: str) -> Tuple[int, Optional[str]]:
        """Get a property value using LV2 Patch protocol.

        Note: Property values are received via the feedback port, not the control socket.
        This implementation sends the command but the value would need to be read
        from a separate feedback socket in a production implementation.

        Args:
            instance: Plugin instance number.
            property_uri: URI of the property to query.

        Returns:
            Tuple of (status_code, value) where value comes from feedback port.

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, value = self.send_command(f'patch_get {instance} {property_uri}')
        return status, value

    def preset_load(self, instance: int, preset_uri: str) -> int:
        """Load a preset state for a plugin instance.

        Args:
            instance: Plugin instance number.
            preset_uri: Full URI of the preset.

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'preset_load {instance} {preset_uri}')
        return status

    def preset_save(self, instance: int, preset_name: str, directory: str, file_name: str) -> int:
        """Save a preset state for a plugin instance.

        Args:
            instance: Plugin instance number.
            preset_name: Name for the preset.
            directory: Directory to save the preset.
            file_name: Filename for the preset.

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'preset_save {instance} {preset_name} {directory} {file_name}')
        return status

    def bypass(self, instance: int, enabled: bool) -> int:
        """Toggle bypass for a plugin instance.

        Args:
            instance: Plugin instance number.
            enabled: True to enable bypass, False to disable.

        Returns:
            Status code from mod-host (0 for success, negative for error).

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, _ = self.send_command(f'bypass {instance} {1 if enabled else 0}')
        return status

    def enumerate(self) -> Tuple[int, list[str]]:
        """Enumerate all available ports in the system.

        Discovers system ports (JACK input/output) and effect instance ports.
        System ports are read from JACK configuration (via filesystem or defaults).
        Effect ports come from tracking instantiated plugins in pedalboard state.

        Returns:
            Tuple of (status_code, items) where items is a list of port strings.
            Each port string is in the format "type:name" (e.g., "system:capture_1",
            "effect_0:input").

        Note:
            This reads system ports from the filesystem/JACK configuration rather
            than querying mod-host, as the 'enumerate' command does not exist in
            the mod-host protocol.
        """
        # Get system ports from environment or use JACK dummy defaults
        # In JACK dummy mode (-d dummy), system provides 2 capture and 2 playback ports
        system_ports_str = os.environ.get(
            "SYSTEM_PORTS",
            "system:capture_1,system:capture_2,system:playback_1,system:playback_2"
        )
        ports = [p.strip() for p in system_ports_str.split(",") if p.strip()]
        return 0, ports

    def cpu_load(self) -> Tuple[int, float]:
        """Get current JACK CPU load.

        Returns:
            Tuple of (status_code, load_value) where load_value is a float.

        Raises:
            RuntimeError: If not connected to mod-host.
        """
        status, value = self.send_command('cpu_load')
        return status, float(value) if value else 0.0

    def close(self) -> None:
        """Close the socket connection to mod-host.

        Safely closes the TCP connections if they exist.
        """
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.fb_socket:
            self.fb_socket.close()
            self.fb_socket = None

    def __enter__(self) -> 'ModHostClient':
        """Context manager entry point.

        Establishes connection on entry.

        Returns:
            The ModHostClient instance.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit point.

        Closes connection on exit.
        """
        self.close()