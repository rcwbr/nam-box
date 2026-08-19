"""Connection model for audio/MIDI signal routing."""

from pydantic import BaseModel


class Connection(BaseModel):
    """Represents an audio/MIDI connection between ports.

    A connection links an input port to an output port, enabling signal flow
    through the pedalboard.

    Attributes:
        id: Unique identifier for this connection.
        input_port_id: ID of the input port (receiving signal).
        output_port_id: ID of the output port (sending signal).
    """

    id: int = 0
    input_port_id: str
    output_port_id: str