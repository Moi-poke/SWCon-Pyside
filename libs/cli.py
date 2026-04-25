# libs/cli.py
from __future__ import annotations


def main() -> int:
    # 既存の起動処理を呼ぶ
    from swcontroller import main as app_main

    return int(app_main() or 0)
