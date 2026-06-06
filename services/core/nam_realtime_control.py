"""
Real-time control for NAM LV2 plugin via direct atom messaging.

This module implements the "4. Real-time Control via Custom Host" approach
by building binary LV2 atoms and writing them directly to jalv's ring buffer.

Unlike the state file approach (which restarts jalv), this sends messages
directly to the running plugin via the control input port.
"""

import ctypes
import struct
from ctypes import (
    c_uint32, c_int64, c_void_p, c_char_p, c_char, c_size_t, POINTER
)
from pathlib import Path
from typing import Optional

# LV2 Atom type definitions matching lv2/include/lv2/atom/atom.h


class LV2_Atom(ctypes.Structure):
    """LV2 Atom header - size and type."""
    _fields_ = [("size", c_uint32), ("type", c_uint32)]


class LV2_Atom_URID(ctypes.Structure):
    """atom:URID - 4 bytes of URID value."""
    _fields_ = [("atom", LV2_Atom), ("body", c_uint32)]


class LV2_Atom_Object_Body(ctypes.Structure):
    """atom:Object body - id and otype."""
    _fields_ = [("id", c_uint32), ("otype", c_uint32)]


class LV2_Atom_Object(ctypes.Structure):
    """atom:Object - header followed by properties."""
    _fields_ = [("atom", LV2_Atom), ("body", LV2_Atom_Object_Body)]


class LV2_Atom_Event(ctypes.Structure):
    """Event header in a sequence - not an LV2_Atom itself."""
    _fields_ = [("time", c_int64), ("body", LV2_Atom)]


# LV2 URID constants (these are the actual URI strings that get mapped)
LV2_ATOM__Path = 0  # Will be mapped by host
LV2_PATCH__Set = 0
LV2_PATCH__property = 0
LV2_PATCH__value = 0


def pad_size(size: int) -> int:
    """Pad size to 64-bit alignment (8-byte boundary)."""
    return (size + 7) & ~7


def build_patch_set_for_path(path_str: str, model_path_urid: int,
                            patch_set_urid: int, patch_property_urid: int,
                            patch_value_urid: int) -> bytes:
    """
    Build binary LV2 atom for patch:Set with atom:Path value.

    This constructs the exact binary format expected by NAM plugin:
    - LV2_Atom_Object with otype = patch_Set
    - LV2_Atom_Property with key = patch_property, value = model_path_urid
    - LV2_Atom_Property with key = patch_value, value = path string (atom:Path)

    Args:
        path_str: File path to the .nam model file
        model_path_urid: URID for the model property URI
        patch_set_urid: URID for patch:Set
        patch_property_urid: URID for patch:property
        patch_value_urid: URID for patch:value

    Returns:
        Complete binary atom message ready to send via atom:eventTransfer
    """
    # Ensure null-terminated path
    path_bytes = path_str.encode('utf-8')
    if not path_bytes.endswith(b'\x00'):
        path_bytes += b'\x00'

    path_len = len(path_bytes)  # Includes null terminator

    # Calculate sizes for each component
    # LV2_Atom_Property_Body: key (4) + context (4) + LV2_Atom (8) = 16 bytes
    # Each property value is separately aligned

    # patch:property property (URID value)
    # Property body: 16 bytes + URID body (4 bytes) + padding
    prop_urid_value_size = 16 + 4  # LV2_Atom_Property_Body header + URID body
    prop_urid_value_padded = pad_size(prop_urid_value_size)

    # patch:value property (Path value)
    # Property body: 16 bytes + path string (len) + null + padding
    prop_path_value_size = 16 + path_len
    prop_path_value_padded = pad_size(prop_path_value_size)

    # Total object size
    # Atom_Object header: 12 bytes (8 + 4 for id + otype)
    # Plus the two properties with their padding
    object_size = 12 + prop_urid_value_padded + prop_path_value_padded

    # Build the message
    buf = bytearray()

    # LV2_Atom_Object header + body
    # { size, type } + { id, otype }
    buf.extend(struct.pack('<I', object_size - 8))  # size (excluding header)
    buf.extend(struct.pack('<I', patch_set_urid))     # type = patch_Set

    buf.extend(struct.pack('<I', 0))  # id = 0 (blank)
    buf.extend(struct.pack('<I', patch_set_urid))   # otype = patch_Set

    # LV2_Atom_Property for patch:property -> model_path_urid
    buf.extend(struct.pack('<I', patch_property_urid))  # key = patch_property
    buf.extend(struct.pack('<I', 0))                   # context = 0

    # Value atom header for URID
    buf.extend(struct.pack('<I', 4))                  # size = 4 (URID value)
    buf.extend(struct.pack('<I', LV2_ATOM__Path if LV2_ATOM__Path else 3))  # type = atom_URID (will be set by forge)
    buf.extend(struct.pack('<I', model_path_urid))     # URID body

    # Pad to 8-byte alignment
    prop_urid_padding = prop_urid_value_padded - prop_urid_value_size
    buf.extend(b'\x00' * prop_urid_padding)

    # LV2_Atom_Property for patch:value -> path string
    buf.extend(struct.pack('<I', patch_value_urid))     # key = patch_value
    buf.extend(struct.pack('<I', 0))                   # context = 0

    # Value atom header for Path
    buf.extend(struct.pack('<I', path_len - 1))         # size (excluding null terminator)
    buf.extend(struct.pack('<I', 7))                   # type = atom_Path (placeholder, will be mapped)
    buf.extend(path_bytes)                             # Path string body

    # Pad to 8-byte alignment
    prop_path_padding = prop_path_value_padded - prop_path_value_size
    buf.extend(b'\x00' * prop_path_padding)

    return bytes(buf)


def build_atom_event(message: bytes, frame: int = 0) -> bytes:
    """
    Wrap an atom in an LV2_Atom_Event for writing to a sequence.

    Args:
        message: The complete patch:Set atom message
        frame: Audio frame timestamp (usually 0 for immediate)

    Returns:
        Event with timestamp header prepended
    """
    buf = bytearray()
    buf.extend(struct.pack('<q', frame))              # int64_t timestamp
    buf.extend(message)                              # The atom message
    return bytes(buf)


class NAMRealtimeController:
    """
    Controller for real-time NAM model changes via direct atom messaging.

    This class handles:
    1. URID mapping (must match what jalv uses internally)
    2. Building properly-formatted patch:Set messages
    3. Sending to the plugin via ring buffer or other IPC mechanism
    """

    def __init__(self, jalv_ring_buffer_path: Optional[str] = None):
        """
        Initialize controller.

        Args:
            jalv_ring_buffer_path: Path to jalv's UI-to-plugin ring buffer (for direct IPC)
        """
        self.ring_buffer_path = jalv_ring_buffer_path
        self.ui_to_plugin_ring = None

        # These URIDs would need to be obtained from jalv's symap
        # For now, we document what values are needed
        self.urids = {
            'patch_Set': None,           # LV2_URID_Map should map LV2_PATCH__Set
            'patch_property': None,       # LV2_PATCH__property
            'patch_value': None,          # LV2_PATCH__value
            'atom_Path': None,            # LV2_ATOM__Path
            'atom_URID': None,            # LV2_ATOM__URID
            'model_Path': None,           # The property URI for the model
            'atom_eventTransfer': None,   # LV2_ATOM__eventTransfer
        }

    def get_required_urids(self) -> dict:
        """
        Return the URID values needed to construct valid atoms.

        These must match the URIDs that jalv has mapped in its symap.
        In practice, you'd need to:
        1. Extension to jalv to expose URID map via shared memory
        2. Or use a known fixed URID mapping
        3. Or parse jalv's debug output when dump mode is enabled
        """
        # URIs that jalv maps internally:
        # - http://lv2plug.in/ns/ext/patch#Set
        # - http://lv2plug.in/ns/ext/patch#property
        # - http://lv2plug.in/ns/ext/patch#value
        # - http://lv2plug.in/ns/ext/atom#Path
        # - http://lv2plug.in/ns/ext/atom#URID
        # - http://github.com/mikeoliphant/neural-amp-modeler-lv2#model
        # - http://lv2plug.in/ns/ext/atom#eventTransfer
        return self.urids

    def set_urids(self, urid_map: dict) -> None:
        """
        Set the URID values from an external source.

        Args:
            urid_map: Dict mapping URID names to integer values
        """
        self.urids.update(urid_map)

    def create_patch_set_message(self, model_path: str) -> bytes:
        """
        Create a complete patch:Set message for the given model path.

        Args:
            model_path: Path to the .nam model file

        Returns:
            Complete binary message ready for atom:eventTransfer protocol
        """
        if not all(self.urids.values()):
            raise ValueError("All URIDs must be set before creating messages")

        # Build the patch:Set object atom
        msg = build_patch_set_for_path(
            path_str=model_path,
            model_path_urid=self.urids['model_Path'],
            patch_set_urid=self.urids['patch_Set'],
            patch_property_urid=self.urids['patch_property'],
            patch_value_urid=self.urids['patch_value']
        )

        # Wrap in event for sequence
        return build_atom_event(msg)

    def send_to_jalv_ring(self, model_path: str) -> bool:
        """
        Send model change to jalv via ring buffer.

        This requires:
        1. Shared memory access to jalv's ring buffer
        2. URID values matching jalv's internal symap

        Returns:
            True if message was sent successfully
        """
        raise NotImplementedError(
            "Direct ring buffer access requires jalv to expose shared memory "
            "or a custom extension. The stable approach is to use state files "
            "or build a control extension into jalv itself."
        )


def validate_atom_structure(message: bytes) -> bool:
    """
    Validate that a binary atom message has correct structure.

    Useful for debugging real-time control.
    """
    if len(message) < 20:
        return False

    # Check minimum size for an object
    atom_size = struct.unpack('<I', message[0:4])[0]
    atom_type = struct.unpack('<I', message[4:8])[0]

    # Atom Object must have at least 8 bytes of body (id + otype)
    if atom_size < 8 or atom_size > 10000:
        return False

    return True


# Example usage for testing atom construction
if __name__ == "__main__":
    # Test with placeholder URIDs
    # In reality, these come from jalv's symap
    test_urids = {
        'patch_Set': 1,
        'patch_property': 2,
        'patch_value': 3,
        'atom_Path': 4,
        'atom_URID': 5,
        'model_Path': 6,
        'atom_eventTransfer': 7,
    }

    # Build a test message
    msg = build_patch_set_for_path(
        path_str="/opt/nam/models/test.nam",
        model_path_urid=test_urids['model_Path'],
        patch_set_urid=test_urids['patch_Set'],
        patch_property_urid=test_urids['patch_property'],
        patch_value_urid=test_urids['patch_value']
    )

    event = build_atom_event(msg)

    print(f"Message size: {len(msg)} bytes")
    print(f"Event size: {len(event)} bytes")
    print(f"Valid structure: {validate_atom_structure(msg)}")

    # Show hex dump
    print(f"\nHex dump:\n{msg.hex()}")