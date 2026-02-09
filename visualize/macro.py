from enum import Enum

NORM_FACTOR = 0.95  # scale factor for normalization to prevent overflow during augmentation

DUMMY_PLANE = {
    "origin": [0.0, 0.0, 0.0],
    "x": [1.0, 0.0, 0.0],
    "normal": [0.0, 0.0, 1.0]
}


class BooleanOp(Enum):
    NEW = "NEW"
    ADD = "ADD"
    REMOVE = "REMOVE"
    INTERSECT = "INTERSECT"


class CapType(Enum):
    START = "START"
    END = "END"
    SWEPT = "SWEPT"
