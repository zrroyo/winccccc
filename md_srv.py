#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
import os
import logging
import traceback
import time
import ctp
sys.path.append(os.path.dirname(__file__))


def get_logger():
    """初始化日志接口"""
    log_file = "%s.log" % time.strftime("%Y%m%d%H%M%S", time.localtime())
    _global_cfg = ctp.GlobalConfig()
    log_dir = _global_cfg.get_log_dir()
    if log_dir:
        log_file = os.path.join(log_dir, 'md', log_file)
    logger = logging.getLogger('ctp_srv')
    dbg_level = _global_cfg.get_mdsrv_debug_level()
    logger.setLevel(dbg_level)
    fh = logging.FileHandler(log_file)
    fh.setFormatter(
        logging.Formatter('%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d: <%(levelname)s> %(message)s')
    )
    logger.addHandler(fh)
    return logger


logger = get_logger()
try:
    srv = ctp.CtpSrvMD(logger)
    srv.run()
except Exception:
    logger.error(traceback.format_exc())
    print(traceback.format_exc())
