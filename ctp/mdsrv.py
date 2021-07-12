# -*- coding:utf-8 -*-

import os
import asyncio
import traceback
from datetime import datetime
from tqsdk import TqApi, tafunc
from lib.genconfig import GenConfig
from .globals import GlobalConfig, CTP_CONFIG_DIR
from .error import CtpSrvMDError
from .auth import ApiAuth

MD_CFG = os.path.join(CTP_CONFIG_DIR, "md_tasks")


class MarketDataSaver:
    """存储行情数据至本地"""
    def __init__(self, api, md_file, md_obj, symbol, logger):
        self.logger = logger
        self.api = api
        self.md_obj = md_obj
        self.symbol = symbol
        _global = GlobalConfig()
        filename = os.path.join(_global.get_market_data_dir(), md_file)
        self.md_fp = open(filename, 'a+')

    def __del__(self):
        self.md_fp.close()

    async def save_market_data(self):
        """保存行情数据"""
        try:
            async with self.api.register_update_notify(self.md_obj) as update_chan:
                async for _ in update_chan:
                    if self.api.is_changing(self.md_obj.iloc[-1], 'datetime'):
                        latest = self.md_obj.iloc[-2]  # 新K线已经生成，上一K线已固定，计入
                        _time = tafunc.time_to_datetime(latest['datetime'])
                        _time = datetime.strftime(_time, "%Y/%m/%d %H:%M:%S")
                        output = f"{_time},{latest['open']},{latest['high']},{latest['low']}," \
                                 f"{latest['close']},{latest['volume']},{latest['open_oi']}," \
                                 f"{latest['close_oi']}\n"
                        # print(f"{self.symbol} => {output}")
                        self.md_fp.write(output)
        except asyncio.CancelledError:
            self.logger.info(f"Flushing market data to disk for '{self.symbol}'.")
            self.md_fp.close()


class CtpSrvMD(object):
    """CTP Server for Storing Market data."""
    def __init__(self, logger):
        self.logger = logger
        auth = ApiAuth()
        self.api = TqApi(auth.get_account(), auth=auth.get_auth())
        try:
            md_cfg = MdSrvConfig()
            all_symbols = md_cfg.get_md_symbols()
            for symbol in all_symbols:
                duration = int(md_cfg.get_symbol_duration(symbol))
                kline = self.api.get_kline_serial(symbol, duration)
                dat_file = "%s.csv" % symbol
                md_saver = MarketDataSaver(self.api, dat_file, kline, symbol, self.logger)
                self.api.create_task(md_saver.save_market_data())
        except Exception as e:
            self.api.close()
            self.logger.error(f"CtpSrvMD初始化异常：{traceback.format_exc()}")
            raise CtpSrvMDError(f"CtpSrvMD初始化异常")

    def run(self):
        try:
            while 1:
                self.api.wait_update()
        except KeyboardInterrupt:
            self.logger.info(f"服务被 Ctrl+C 中断！")
        except Exception:
            self.logger.error(f"捕获到未知异常: {traceback.format_exc()}")
            raise CtpSrvMDError(f"捕获到未知异常")
        finally:
            self.api.close()


class MdSrvConfig(GenConfig):
    """CTP Md Server配置信息"""
    def __init__(self):
        super().__init__(MD_CFG)

    def get_md_symbols(self):
        return self.sectionList()

    def get_symbol_duration(self, symbol):
        return self.getSecOption(symbol, 'duration')
