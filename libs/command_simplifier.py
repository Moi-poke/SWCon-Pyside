from __future__ import annotations

from os import path

from libs.keys import Button, Direction, Hat
from libs.CommandBase import CommandBase, StopThread
from typing_extensions import Literal

# global TEMPLATE_PATH


class Sequence:
    def __init__(self, sequence: list[Match | Press | Wait]) -> None:
        for i, ops in enumerate(sequence):
            if not isinstance(ops, (Match, Press, Wait)):
                raise TypeError(f"index:{i} invalid type")
        self.__sequence = sequence

    def run(self, command: CommandBase):
        global TEMPLATE_PATH
        TEMPLATE_PATH = command.TEMPLATE_PATH
        for i, ops in enumerate(self.__sequence):
            try:
                ops.run(command)
            except StopThread:
                command.debug(f"index:{i} stop command")
                raise
            except ValueError:
                command.debug(f"index:{i} stop command")



class Press:
    def __init__(self, specifier: Button | Direction | Hat, duration: float = 0.1, wait: float = 0.1) -> None:
        if duration < 0:
            raise ValueError("duration must be a number greater than 0")
        if wait < 0:
            raise ValueError("wait must be a number greater than 0")

        self.__specifier = specifier
        self.__duration = duration
        self.__wait = wait

    def run(self, command: CommandBase):
        command.press(self.__specifier, self.__duration, self.__wait)


class Wait:
    def __init__(self, wait: float, unit: Literal["sec", "frame"] = "sec", fps: float = 60) -> None:
        if wait < 0:
            raise ValueError("wait must be a number greater than 0")
        if unit != "sec" and unit != "frame":
            raise TypeError('unit must be "sec" or "frame"')

        self.__wait = wait if unit == "sec" else wait / fps

    def run(self, command: CommandBase):
        command.wait(self.__wait)


class Match:
    def __init__(self, template: str, threshold: float = 0.7, use_gray: bool = True, show_value: bool = False,
                 show_position: bool = True, show_only_true_rect: bool = True, ms: int = 2000, crop=None):
        temp_path = path.join(TEMPLATE_PATH, template)
        if not path.exists(temp_path):
            raise FileNotFoundError(temp_path)

        self.__template = template
        self.__threshold = threshold
        self.__use_gray = use_gray
        self.__show_value = show_value
        self.__show_only_true_rect = show_only_true_rect
        self.__ms = ms
        self.__crop = crop

    def run(self, command: CommandBase):
        ret = command.is_contain_template(template_path=self.__template,
                                          threshold=self.__threshold,
                                          use_gray=self.__use_gray,
                                          show_value=self.__show_value,
                                          show_only_true_rect=self.__show_only_true_rect,
                                          show_rect_frame=self.__ms // 60,
                                          trim=self.__crop)
        if not ret:
            raise StopThread()
