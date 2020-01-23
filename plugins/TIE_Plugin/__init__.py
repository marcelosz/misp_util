#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = "Marcelo Souza"
__license__ = "GPL"

_plugin_name = "TIE_Plugin"

from plugin_base import PluginBase
from conf_util import cfg

import logging
logger = logging.getLogger()

import hashlib, json

from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig

from dxltieclient import TieClient
from dxltieclient.constants import HashType, TrustLevel, FileType, FileProvider, ReputationProp

# Default TIE Reputation Level to set:
TIE_REPUTATION = TrustLevel.MOST_LIKELY_MALICIOUS

class TIE_Plugin(PluginBase) :
    def __init__(self):
        logger.info("Plugin " + _plugin_name + " initializing...")
        #
        # Init and connect DXL client
        # 
        # DxlClientConfig from DXL configuration file
        logger.debug(_plugin_name + " : Loading DXL config from: %s", cfg['ExportPlugins']['TIE_Plugin']['DXLConfig'])
        self.dxl_config = DxlClientConfig.create_dxl_config_from_file(cfg['ExportPlugins']['TIE_Plugin']['DXLConfig'])
        self.tie_client = None

    def export(self, results_array):
        #logger.debug(results_array)
        #logger.debug(json.dumps(results_array, indent=4, sort_keys=True))

        for event in results_array:
            logger.debug(_plugin_name + " processing event: (Event ID: " + event['Event']['id'] + ", Event Info: " + event['Event']['info'] + ", Event Date: " + event['Event']['date'] + ")")
            with DxlClient(self.dxl_config) as client:
                # Connect to the DXL fabric
                logger.debug(_plugin_name + " : Connecting OpenDXL client...")                
                client.connect()
                # Create the McAfee Threat Intelligence Exchange (TIE) client
                self.tie_client = TieClient(client)                
                for attribute in event['Event']['Attribute']:
                    if attribute['type'] == 'md5' or attribute['type'] == 'sha1' or attribute['type'] == 'sha256':                     
                        logger.debug("Found attribute type {0} = {1} in MISP event {2}.".format(str(attribute['type']),str(attribute['value']),str(event['Event']['id'])))
                        self.set_tie_reputation(TIE_REPUTATION, attribute['type'], attribute['value'], "MISP (Event ID {0}, Info: {1})".format(str(event['Event']['id']), str(event['Event']['info'])))

                for obj in event['Event']['Object']:
                    for attribute in obj['Attribute']:
                        if attribute['type'] == 'md5' or attribute['type'] == 'sha1' or attribute['type'] == 'sha256':                     
                            logger.debug("Found object attribute type {0} = {1} in MISP event {2}.".format(str(attribute['type']),str(attribute['value']),str(event['Event']['id'])))
                            self.set_tie_reputation(TIE_REPUTATION, attribute['type'], attribute['value'], "MISP (Event ID {0}, Info: {1})".format(str(event['Event']['id']), str(event['Event']['info'])))                            
        self.tie_client = None

    def set_tie_reputation(self, trust_level, hash_type, hash_value, comment_str):
        if self.tie_client :
            try:
                self.tie_client.set_external_file_reputation(TIE_REPUTATION, {hash_type: hash_value}, filename='MISP Event-based Reputation', comment=comment_str)
                #self.tie_client.set_external_file_reputation(TIE_REPUTATION, {hash_type: hash_value}, filename='FROM MISP', comment="Test")
                logger.debug(_plugin_name + " : Reputation set (%s)", comment_str)
            except ValueError as e:
                logger.error(_plugin_name + " : Error while trying to set TIE reputation (%s)", str(e))

def plugin_name():
    return _plugin_name

def init():
    return TIE_Plugin()

