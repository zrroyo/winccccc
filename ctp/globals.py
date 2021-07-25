# -*- coding:utf-8 -*-

import os
from lib import GenConfig

# 定义全局变量
# CTP_CONFIG_DIR = os.path.join(os.environ.get('HOME'), '.winctp')
CTP_CONFIG_DIR = "/etc/winctp"
GLOBAL_CONFIG = os.path.join(CTP_CONFIG_DIR, 'global')
TASKS_CONFIG = os.path.join(CTP_CONFIG_DIR, 'trd_tasks')


class GlobalConfig(GenConfig):
    """读取全局配置信息"""
    def __init__(self, cfgFile=GLOBAL_CONFIG):
        super(GlobalConfig, self).__init__(cfgFile)
        self.cfgFile = cfgFile
        self.defaultSec = 'globals'

    def get_md_runtime_dir(self):
        return self.getSecOption(self.defaultSec, 'md_runtime_dir')

    def get_trade_details_dir(self):
        return self.getSecOption(self.defaultSec, 'trade_details_dir')

    def get_trader_config_dir(self):
        return self.getSecOption(self.defaultSec, 'trader_config_dir')

    def get_market_data_dir(self):
        return self.getSecOption(self.defaultSec, 'market_data_dir')

