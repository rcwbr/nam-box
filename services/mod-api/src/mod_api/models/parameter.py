"""Parameter model definitions with discriminated unions."""

from __future__ import annotations

from typing import Union, Literal

from pydantic import BaseModel


class BaseParameter(BaseModel):
    """Base class for effect parameters.

    All parameters share a name and type, but have different value types.
    The `type` field distinguishes between NUMBER and FILENAME parameters.
    """

    name: str
    type: str


class NumberParameterType(BaseParameter):
    """Numeric parameter type with min/max constraints.

    Represents control parameters like drive, tone, or level values
    that have floating point values within a bounded range.
    """

    type: Literal["number"] = "number"
    min: float
    max: float
    default: float


class FilenameParameterType(BaseParameter):
    """String parameter type representing a file path.

    Represents parameters that accept file paths, such as
    NAM model files or impulse responses.
    """

    type: Literal["filename"] = "filename"
    default: str


# Union type for parameter handling
# Note: Pydantic validates these based on the 'type' literal field
ParameterType = Union[NumberParameterType, FilenameParameterType]

class NumberParameter(NumberParameterType):
    """Numeric parameter instance with a current value.

    Extends NumberParameterType by adding a current value field.
    """

    value: float

class FilenameParameter(FilenameParameterType):
    """Filename parameter instance with a current value.

    Extends FilenameParameterType by adding a current value field.
    """

    value: str

Parameter = Union[NumberParameter, FilenameParameter]
