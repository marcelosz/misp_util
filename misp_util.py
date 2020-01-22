#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""misp_util.py - 
  This script can be used to export, tag and delete MISP events.
"""

__author__ = "Marcelo Souza"
__license__ = "GPL"

import sys, logging, argparse, textwrap
import json, time, os#, re, urllib3, time

from pymisp import ExpandedPyMISP

# Enable logging
log_formatter = logging.Formatter('%(asctime)s misp_util (%(name)s) %(levelname)s: %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.addHandler(console_handler)

# Config
from configobj import ConfigObj, ConfigObjError
import conf_util

# MISP global obj
misp = None

def create_arg_parser():
    """
    Parses command line arguments.
    
    Returns:
        An ArgumentParser object.
    """

    epilog = """\
       TODO *** Descriptive text ***
       Actions
       -------
       - export: Export event data. Only published events are included. Output in JSON format only (JSON array).
    """
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=textwrap.dedent(epilog))
    parser.add_argument("action", help="Action to execute on events in the MISP instance. Can be one of: export, delete, tag", metavar="ACTION")
    parser.add_argument("-c", "--configfile", help="Configuration file. Default is misp_util.conf", default="misp_util.conf")
    # TODO
    #parser.add_argument("-d", "--dryrun", help="Dryrun mode. No changes are made to MISP.", action='store_true', default=False)
    parser.add_argument("-i", "--eventids", help="Focus actions on events with specific event IDs. Sample syntax: \"1024||123\".")
    parser.add_argument("-l", "--loglevel", help="Logging level (DEBUG, INFO or ERROR). Default is INFO.", default="INFO")
    parser.add_argument("-p", "--poll", help="Enable polling mode, based on MISP event publish_timestamp and the script's chosen time window.", action='store_true', default=False)
    parser.add_argument("-s", "--searchquery", help="Query used to search for MISP events. When used, the arguments for tags and IDs are ignored.", default=None)
    parser.add_argument("-t", "--eventtags", help="Focus actions on events with specific tags. Sample syntax: \"tlp:green||tlp:white\".")
    parser.add_argument("-w", "--timewindow", help="Set polling time window (in minutes) when 'poll' option is chosen. Default 10 minutes.", default=10)
    return parser

def set_logging_level(lg, level):
    """
    Set the level of verbosity of a logger instance.
    """
    # Configure logging level
    if level == 'DEBUG':
        lg.setLevel(logging.DEBUG)
    elif level == 'INFO':
        lg.setLevel(logging.INFO)
    elif level == 'WARNING':
        lg.setLevel(logging.WARNING)   
    else:
        lg.setLevel(logging.ERROR)

# Plugins subsystem
if sys.version_info[0] < 3:
    import imp
else:
    import importlib

pluginsList = []

def init_export_plugins():
    """
    Get list of plugins, load and initialize them.
    """
    path = conf_util.cfg['ExportPlugins']['Dir']
    PluginsMainModule = "__init__"
    possiblePlugins = os.listdir(path)
    logger.debug("Going to check export plugins we need to load...")
    for i in possiblePlugins:
        module = None
        location = os.path.join(path, i)
        full_file_name = location + os.sep + "/__init__.py"
        logger.debug("Plugin dir %s...", i)
        if not os.path.isdir(location) or not PluginsMainModule + ".py" in os.listdir(location):
            # TODO - add error msg here
            continue
        if sys.version_info[0] < 3:
	        module = imp.load_source(i, full_file_name)
        else:
            spec = importlib.util.spec_from_file_location(i, full_file_name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        # TODO - enhance error handling here            
        # Check if plugin is enabled. First get it's name...
        plugin_name = getattr(module, 'plugin_name')
        # ...and compare to the config file
        if not conf_util.cfg['ExportPlugins'][plugin_name()]['Enabled'] == "True" :
            continue
        # map and call plugin's init() function
        init = getattr(module, 'init')
        global pluginsList
        pluginsList.append(init())
    logger.info("%s plugin(s) enabled and loaded...", len(pluginsList))
    return True

def action_export(timeframe, search_query, event_ids, event_tags):
    logger.debug("EXPORT - Calling MISP search API...")    
    if search_query == None :
        result = misp.search(publish_timestamp=timeframe, eventid=event_ids, tags=event_tags, published=True, pythonify=False)
    else :
        result = misp.search(publish_timestamp=timeframe, searchall=search_query, published=True, pythonify=False)
    if len(result) > 0 :
        logger.info("MISP search executed. %s event(s) found. Exporting...", len(result))
        logger.debug(json.dumps(result, indent=4, sort_keys=True))
        print(result)
    else:
        logger.info("MISP search executed. No events found.")

def main(argv):
    # parse the args
    arg_parser = create_arg_parser()
    args = arg_parser.parse_args()

    # set logging level
    set_logging_level(logger, args.loglevel)
    # configure local logger for requests (Urllib3) and set its level
    set_logging_level(logging.getLogger("urllib3"), args.loglevel)
    
    logger.info("Starting misp_util...")
    # read main cfg file
    conf_util.cfg = conf_util.read_cfg(args.configfile)
    if not conf_util.cfg:
        logger.error("Error reading main config file!")
        exit(1)
    
    # connect to MISP
    try:
        logger.debug("Creating MISP instance object...")        
        logger.info("Connecting to MISP...")        
        global misp
        misp = ExpandedPyMISP(conf_util.cfg['MISP']['URL'], conf_util.cfg['MISP']['Key'], 
                              ssl=True if conf_util.cfg['MISP']['VerifyCert'] == 'True' else False,
                              debug=True if conf_util.cfg['MISP']['Debug'] == 'True' else False,
                              cert=conf_util.cfg['MISP']['ClientCert'])

    except Exception as e:
        logger.error("Could not connect to MISP ({0}).".format(e.message))
        exit(1)
    
    logger.info("Successfully connected to MISP.")
    #
    # Get plugins and execute their initializers
    #
    logger.info("Starting plugin subsystem...")    
    init_export_plugins()

    # 
    # Run script based on chosen action
    #
    # - Check if we are in "one-shot" or "polling" mode
    if args.poll :
        # POLLING
        logger.debug("Mode: polling mode")
        if not args.action == 'export' :
            logger.error("Unrecognized action %s for polling mode. Only 'export' is accepted right now.", args.action)
            exit(1)
        # main polling loop, time based
        timeout = args.timewindow
        while True:
            logger.debug("Starting poll loop...")
            # Our search will retrieve events from last "timeout" minutes (timeout + "m")
            action_export(timeout + "m", args.searchquery, args.eventids, args.eventtags)
            logger.debug("Going to sleep for %s minute(s)...", timeout)
            time.sleep(int(timeout) * 60)

    else :
        # ONE SHOT
        logger.debug("Mode: one-shot")
        if args.action == 'export' :
            action_export(None, args.searchquery, args.eventids, args.eventtags)
        elif args.action == 'delete' :
            logger.info("Action not implemented yet.")
        elif args.action == 'tag' :
            logger.info("Action not implemented yet.")
        else:
            logger.error("Unrecognized action %s.", args.action)
        exit(1)

    exit(0)

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        # TODO - gracefully exit
        logger.info("Caught keyboard interrupt signal. Exiting...")
        exit(0)
