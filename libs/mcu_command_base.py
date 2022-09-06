from PySide6.QtCore import QObject, Signal


class McuCommand(QObject):
    play_sync_name = Signal(str)
    __directory__ = "./Commands/MCU"

    def __init__(self, sync_name):
        super(McuCommand, self).__init__()
        self.isRunning = False
        self.sync_name = sync_name
        self.postProcess = None

    def start(self, postProcess=None):
        self.writeRow(self.sync_name)
        self.isRunning = True
        self.postProcess = postProcess

    def end(self):
        self.writeRow("end")
        self.isRunning = False
        if self.postProcess is not None:
            self.postProcess()

    def writeRow(self, s):
        self.play_sync_name.emit(s)