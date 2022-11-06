import toml

DEFAULT_SETTINGS = {
  'main_window': {
    'show_camera_realtime': False,
    'show_serial': False,
    'keyboard_control': False,
    'tab': 'python',
    'must': {
      'fps': '60',
      'com_port': '',
      'com_port_name': '',
      'camera_id': '',
      'camera_name': ''
    },
    'option': {
      'window_size_width': 948,
      'window_size_height': 796,
      'window_showMaximized': False,
      'show_serial': True
    }
  },
  'line': {
    'token_1': ''
  },
  'command': {
    'py_command': 'A連打',
    'mcu_command': 'A連打'
  },
  'key_config': {
    'keyboard': {
      'button': {
        'Y': 'K_y',
        'B': 'K_b',
        'A': 'K_a',
        'X': 'K_x',
        'L': 'K_l',
        'R': 'K_r',
        'ZL': 'K_k',
        'ZR': 'K_e',
        'MINUS': 'K_m',
        'PLUS': 'K_p',
        'LCLICK': 'K_q',
        'RCLICK': 'K_w',
        'HOME': 'K_h',
        'CAPTURE': 'K_c'
      },
      'direction': {
        'UP': 'K_UP',
        'RIGHT': 'K_RIGHT',
        'DOWN': 'K_DOWN',
        'LEFT': 'K_LEFT',
        'UP_RIGHT': '',
        'DOWN_RIGHT': '',
        'DOWN_LEFT': '',
        'UP_LEFT': ''
      },
      'hat': {
        'TOP': '',
        'BTM': '',
        'LEFT': '',
        'RIGHT': ''
      }
    },
    'joystick': {
      'direction': {
        'LStick': True,
        'RStick': True
      },
      'button': {
        'Y': {
          'state': True,
          'assign': 'button.3'
        },
        'B': {
          'state': True,
          'assign': 'button.1'
        },
        'A': {
          'state': True,
          'assign': 'button.0'
        },
        'X': {
          'state': True,
          'assign': 'button.2'
        },
        'L': {
          'state': True,
          'assign': 'button.9'
        },
        'R': {
          'state': True,
          'assign': 'button.10'
        },
        'ZL': {
          'state': True,
          'assign': 'axis.4'
        },
        'ZR': {
          'state': True,
          'assign': 'axis.5'
        },
        'MINUS': {
          'state': True,
          'assign': 'button.4'
        },
        'PLUS': {
          'state': True,
          'assign': 'button.6'
        },
        'LCLICK': {
          'state': True,
          'assign': 'button.7'
        },
        'RCLICK': {
          'state': True,
          'assign': 'button.8'
        },
        'HOME': {
          'state': True,
          'assign': 'button.5'
        },
        'CAPTURE': {
          'state': True,
          'assign': 'button.15'
        }
      },
      'hat': {
        'TOP': {
          'state': True,
          'assign': 'button.11'
        },
        'BTM': {
          'state': True,
          'assign': 'button.12'
        },
        'LEFT': {
          'state': True,
          'assign': 'button.13'
        },
        'RIGHT': {
          'state': True,
          'assign': 'button.14'
        }
      }
    }
  }
}


class Setting:
    def __init__(self, path: str = "./config/settings.toml"):
        self.setting = None
        self.path = path

    # 別のパスで設定ファイルを構成したい場合のclass-method
    @classmethod
    def alternate(cls, path: str):
        return cls(path=path)

    def load(self) -> bool:
        try:
            with open(self.path, encoding="utf-8") as setting:
                self.setting = toml.load(setting)
            return True
        except:
            self.generate()
            self.save()
            self.load()
            return False

    def generate(self) -> bool:
        if self.setting is None:
            self.setting = DEFAULT_SETTINGS
            return True
        else:
            return False

    def save(self) -> bool:
        if self.setting is not None:
            with open(self.path, 'w', encoding="utf-8") as setting:
                toml.dump(self.setting, setting)
            return True
        else:
            return False


if __name__ == '__main__':
    s = Setting(path="../config/settings.toml")
    s.load()
    print(s.setting)
