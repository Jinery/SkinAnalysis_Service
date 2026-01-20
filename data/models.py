from typing import NamedTuple


class Color(NamedTuple):
    red: int
    green: int
    blue: int

    def get_red(self) -> int: return self.red
    def get_green(self) -> int: return self.green
    def get_blue(self) -> int: return self.blue