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
    log_file = "%s.log" % time.strftime("%Y%m%d%H%M%S", time.localtime())
    log_dir = os.environ.get('WINCTP_LOG_DIR')
    if log_dir:
        log_file = os.path.join(log_dir, 'md', log_file)
    logger = logging.getLogger('ctp_srv')
    logger.setLevel(level)
    fh = logging.FileHandler(log_file)
    fh.setFormatter(
        logging.Formatter('%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d: <%(levelname)s> %(message)s')
    )
    logger.addHandler(fh)
    return logger


logger = get_logger(LOG_LEVEL)
try:
    srv = ctp.CtpSrvMD(logger)
    srv.run()
except Exception:
    logger.error(f"{traceback.format_exc()}")
    print(traceback.format_exc())


