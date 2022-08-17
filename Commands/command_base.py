#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 使っていません
from abc import ABCMeta, abstractmethod


class Command:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.isRunning = False

    @abstractmethod
    def start(self, ser, postProcess=None):
        pass

    @abstractmethod
    def end(self, ser):
        pass
