from enum import auto, Enum


# noinspection PyArgumentList
class ColorType(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return count

    COLOR = auto()
    GRAY = auto()
    BINARY = auto()