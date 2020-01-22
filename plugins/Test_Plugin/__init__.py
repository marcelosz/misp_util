#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = "Marcelo Souza"
__license__ = "GPL"

_plugin_name = "Test_Plugin"

from plugin_base import PluginBase
from conf_util import cfg

import logging
logger = logging.getLogger()

class Test_Plugin(PluginBase) :
    def __init__(self):
        logger.info("Plugin " + _plugin_name + " initializing...")

def plugin_name():
    return _plugin_name

def init():
    return Test_Plugin()