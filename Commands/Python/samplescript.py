from libs.CommandBase import CommandBase
from libs.keys import Button


class Test(CommandBase):
    NAME = "ABXY連打"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def do(self):
        # print(self.is_contain_template("a.png"))
        for i in range(30):
            self.press(Button.A, duration=0.025, wait=0.025)
            self.debug("A")
            self.press(Button.B, duration=0.025, wait=0.025)
            self.debug("B")
            self.press(Button.X, duration=0.025, wait=0.025)
            self.debug("X")
            self.press(Button.Y, duration=0.025, wait=0.025)
            self.debug("Y")
