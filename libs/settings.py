import toml


DEFAULT_SETTINGS = {'app': 'VController', 'version': '0.1 beta',
                    'main_window': {'show_camera_realtime': False, 'show_serial': False, 'keyboard_control': False},
                    'must': {'fps': 60, 'com_port': 3, 'com_port_name': '', 'camera_id': 6, 'camera_name': ''},
                    'option': {'window_size_width': 1150, 'window_size_height': 582, 'tab': 'python'},
                    'line': {'token_1': 'ここにLINE通知用のtokenを貼付'}, 'key_config': {},
                    'button': {'Y': 'K_y', 'B': 'K_b', 'A': 'K_a', 'X': 'K_x',
                               'L': 'K_l', 'R': 'K_r', 'ZL': 'K_k', 'ZR': 'K_e',
                               'MINUS': 'K_m', 'PLUS': 'K_p',
                               'LCLICK': 'K_q', 'RCLICK': 'K_w',
                               'HOME': 'K_h', 'CAPTURE': 'K_c'},
                    'direction': {'UP': 'K_UP', 'RIGHT': 'K_RIGHT',
                                  'DOWN': 'K_DOWN', 'LEFT': 'K_LEFT',
                                  'UP_RIGHT': '', 'DOWN_RIGHT': '',
                                  'DOWN_LEFT': '', 'UP_LEFT': ''},
                    'hat': {'TOP': '', 'BTM': '', 'LEFT': '', 'RIGHT': ''}}




class Setting:
    def __init__(self, path="./config/settings.toml"):
        self.setting = None
        self.path = path

    # 別のパスで設定ファイルを構成したい場合のclass-method
    @classmethod
    def alternate(cls, path):
        return cls(path=path)

    def load(self):
        with open(self.path, encoding="utf-8") as setting:
            self.setting = toml.load(setting)
        return True

    def generate(self):
        if self.setting is None:
            self.setting = DEFAULT_SETTINGS
            return True
        else:
            return False

    def save(self):
        if self.setting is not None:
            with open(self.path, 'w', encoding="utf-8") as setting:
                toml.dump(self.setting, setting)
            return True
        else:
            return False
