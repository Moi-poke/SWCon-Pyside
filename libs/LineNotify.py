import configparser
import cv2
import io
import os
import logging

import numpy as np
import requests
from PIL import Image
from logging import getLogger, DEBUG, NullHandler

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QPainter


class LineNotify(QObject):
    print_strings = Signal(str, type(logging.DEBUG))

    def __init__(self, tokens: dict | str):
        super().__init__()
        self.logger = getLogger(__name__)
        self.logger.addHandler(NullHandler())
        self.logger.setLevel(DEBUG)
        self.logger.propagate = True

        self.res = None
        if isinstance(tokens, dict):
            self.token_list = tokens
        self.token_num = len(self.token_list.keys())
        # self.line_notify_token = self.token_file['LINE'][token_name]
        self.headers = [{'Authorization': f'Bearer {token}'} for key, token in self.token_list.items()]
        self.res = []
        for head in self.headers:
            try:
                requests.get('https://notify-api.line.me/api/status', headers=head)
            except UnicodeEncodeError:
                pass

        self.status = [responses.status_code for responses in self.res]
        self.chk_token_json = [responses.json() for responses in self.res]

    def is_utf8_file_with_bom(self, filename):
        """
        utf-8 ファイルが BOM ありかどうかを判定する
        """
        line_first = open(filename, encoding='utf-8').readline()
        return line_first[0] == '\ufeff'

    def __str__(self):
        for stat in self.status:
            if stat == 401:
                self.print_strings.emit("Invalid token", logging.ERROR)
            elif stat == 200:
                self.print_strings.emit("Valid token", logging.DEBUG)

    @classmethod
    def retrieve_line_instance(cls, token):
        return cls(tokens=token)

    def send_text(self, notification_message, token_key: str):
        """
        LINEにテキストを通知する

        """
        line_notify_api = 'https://notify-api.line.me/api/notify'
        try:
            headers = {'Authorization': f'Bearer {self.token_list[token_key]}'}
            data = {'Message': f'{notification_message}'}
            self.res = requests.post(line_notify_api, headers=headers, data=data)
            if self.res.status_code == 200:
                self.print_strings.emit("[LINE]テキストを送信しました。", logging.DEBUG)
            else:
                self.print_strings.emit("[LINE]テキストの送信に失敗しました。", logging.ERROR)
        except KeyError:
            self.print_strings.emit("token名が間違っています", logging.ERROR)

    def send_text_n_image(self, img: cv2, notification_message: str | int, token_key: str):
        """
        カメラが開いていないときはテキストのみを通知し、
        開いているときはテキストと画像を通知する
        """
        try:
            image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image_rgb)
            png = io.BytesIO()  # 空のio.BytesIOオブジェクトを用意
            image.save(png, format='png')  # 空のio.BytesIOオブジェクトにpngファイルとして書き込み
            b_frame = png.getvalue()  # io.BytesIOオブジェクトをbytes形式で読みとり

            line_notify_api = 'https://notify-api.line.me/api/notify'
            headers = {'Authorization': f'Bearer {self.token_list[token_key]}'}
            data = {'Message': f'{notification_message}'}
            files = {'imageFile': b_frame}
            self.res = requests.post(line_notify_api, headers=headers, params=data, files=files)
            if self.res.status_code == 200:
                self.print_strings.emit("[LINE]テキストと画像を送信しました。", logging.DEBUG)
            else:
                self.print_strings.emit("[LINE]テキストと画像の送信に失敗しました。", logging.ERROR)
        except KeyError:
            self.print_strings.emit("token名が間違っています", logging.ERROR)

    def get_rate_limit(self):
        try:
            for i in range(self.token_num):
                print(f'For: {list(self.token_list.keys())[i]}')
                print('X-RateLimit-Limit: ' + self.res[i].headers['X-RateLimit-Limit'])
                print('X-RateLimit-ImageLimit: ' + self.res[i].headers['X-RateLimit-ImageLimit'])
                print('X-RateLimit-Remaining: ' + self.res[i].headers['X-RateLimit-Remaining'])
                print('X-RateLimit-ImageRemaining: ' + self.res[i].headers['X-RateLimit-ImageRemaining'])
                import datetime
                dt = datetime.datetime.fromtimestamp(int(self.res[i].headers['X-RateLimit-Reset']),
                                                     datetime.timezone(datetime.timedelta(hours=9)))
                print('Reset time:', dt, '\n')

                self.logger.info(f"LINE API - Limit: {self.res[i].headers['X-RateLimit-Limit']}")
                self.logger.info(f"LINE API - Remaining: {self.res[i].headers['X-RateLimit-Remaining']}")
                self.logger.info(f"LINE API - ImageLimit: {self.res[i].headers['X-RateLimit-Limit']}")
                self.logger.info(f"LINE API - ImageRemaining: {self.res[i].headers['X-RateLimit-ImageRemaining']}")
                self.logger.info(f"Reset time: {dt}")
        except AttributeError as e:
            self.logger.error(e)
            pass
        except KeyError as e:
            self.logger.error(e)
            pass


if __name__ == "__main__":
    '''
    単体テスト
    status  HTTPステータスコードに準拠した値
       200  成功時
       401  アクセストークンが無効
    '''

    LINE = LineNotify({"token_1": "paste_your_token_here"})
    print(LINE)
    LINE.get_rate_limit()
    print(LINE.send_text("test", token_key="token_1"))
