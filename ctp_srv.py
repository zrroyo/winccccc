#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
import os
import logging
import traceback
import time
import ctp
sys.path.append(os.path.dirname(__file__))

LOG_LEVEL = logging.DEBUG


def get_logger(level):
    """初始化日志接口"""
    log_file = time.strftime("%Y%m%d%H%M%S", time.localtime())
    logger = logging.getLogger('ctp_srv')
    logger.setLevel(LOG_LEVEL)
    fh = logging.FileHandler(log_file)
    fh.setFormatter(
        logging.Formatter('%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d: <%(levelname)s> %(message)s')
    )
    logger.addHandler(fh)
    return logger

try:
    logger = get_logger(LOG_LEVEL)
    srv = ctp.CtpSrvDaemon(logger)
    srv.run()
except Exception as e:
    logger.exception(traceback.format_exc(e))
