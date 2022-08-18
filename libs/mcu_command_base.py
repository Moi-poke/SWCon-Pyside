
class McuCommand:
    def __init__(self, sync_name):
        super(McuCommand, self).__init__()
        self.isRunning = False
        self.sync_name = sync_name
        self.postProcess = None

    def start(self, ser, postProcess):
        ser.writeRow(self.sync_name)
        self.isRunning = True
        self.postProcess = postProcess

    def end(self, ser):
        ser.writeRow('end')
        self.isRunning = False
        if self.postProcess is not None:
            self.postProcess()
