#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = "Marcelo Souza"
__license__ = "GPL"

_plugin_name = "TIE_Plugin"

from plugin_base import PluginBase
from conf_util import cfg

import logging
logger = logging.getLogger()

import hashlib

from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig

from dxltieclient import TieClient
from dxltieclient.constants import HashType, TrustLevel, FileType, FileProvider, ReputationProp

class TIE_Plugin(PluginBase) :
    def __init__(self):
        logger.info("Plugin " + _plugin_name + " initializing...")
        #
        # Init and connect DXL client
        # 
        logger.info(_plugin_name + " : Connecting OpenDXL client...")
        # DxlClientConfig from DXL configuration file
        logger.debug(_plugin_name + " : Loading DXL config from: %s", cfg['ExportPlugins']['TIE_Plugin']['DXLConfig'])
        self.dxl_config = DxlClientConfig.create_dxl_config_from_file(cfg['ExportPlugins']['TIE_Plugin']['DXLConfig'])

def plugin_name():
    return _plugin_name

def init():
    return TIE_Plugin()