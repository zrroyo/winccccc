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

    def get_log_dir(self):
        return self.getSecOption('globals', 'log_dir')

    def get_md_runtime_dir(self):
        return self.getSecOption('globals', 'md_runtime_dir')

    def get_trade_details_dir(self):
        return self.getSecOption('globals', 'trade_details_dir')

    def get_trader_config_dir(self):
        return self.getSecOption('globals', 'trader_config_dir')

    def get_market_data_dir(self):
        return self.getSecOption('globals', 'market_data_dir')

    def get_mdsrv_start_time(self):
        return self.getSecOption('mdsrv', 'start_time')

    def get_mdsrv_stop_time(self):
        return self.getSecOption('mdsrv', 'stop_time')

    def get_mdsrv_debug_level(self):
        level = self.getSecOption('mdsrv', 'debug_level')
        return int(level)
