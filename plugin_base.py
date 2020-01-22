#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = "Marcelo Souza"
__license__ = "GPL"

class PluginBase :
    def __init__(self):
        self.config = []

    def pluginName(self):
        return self.name