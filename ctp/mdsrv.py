# -*- coding:utf-8 -*-

import os
import asyncio
import traceback
import signal
import time
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
        self.md_file = md_file
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
            self.logger.info(f"Flushing market data to disk for '{os.path.basename(self.md_file)}'.")
            self.md_fp.close()


class CtpSrvMD(object):
    """CTP Server for Storing Market data."""
    def __init__(self, logger):
        self.logger = logger
        self.api = None
        self._recv_sig_stop = False    # Signal to stop and exit service.
        signal.signal(signal.SIGTERM, self._sig_term_handler)
        _global = GlobalConfig()
        self._start_time = datetime.strptime(_global.get_mdsrv_start_time(), "%H:%M")
        self._stop_time = datetime.strptime(_global.get_mdsrv_stop_time(), "%H:%M")
        self._srv_status = -1  # -1：初始化；1：开启服务；0：停止服务
        signal.signal(signal.SIGALRM, self._sig_alarm_handler)
        signal.alarm(1)  # 1秒后唤醒检查交易时间

    def _start_srv(self):
        """启动服务"""
        self.logger.info(f"正在初始化并登录行情数据...")
        auth = ApiAuth()
        self.api = TqApi(auth.get_account(), auth=auth.get_auth())
        self.logger.info(f"登录成功")
        try:
            md_cfg = MdSrvConfig()
            all_symbols = md_cfg.get_md_symbols()
            for symbol in all_symbols:
                durations = md_cfg.get_symbol_duration(symbol)
                durations = list(filter(lambda x: x, durations.split(',')))
                self.logger.debug(f"durations for '{symbol}': {durations}")
                for d in durations:
                    d = d.strip()
                    duration = int(d)
                    kline = self.api.get_kline_serial(symbol, duration)
                    dat_file = f"{symbol}_{d}.csv"
                    md_saver = MarketDataSaver(self.api, dat_file, kline, symbol, self.logger)
                    self.api.create_task(md_saver.save_market_data())
        except Exception:
            self.logger.error(f"CtpSrvMD初始化异常：{traceback.format_exc()}")
            raise CtpSrvMDError(f"CtpSrvMD初始化异常")

    def run(self):
        try:
            while 1:
                if self._recv_sig_stop:
                    raise KeyboardInterrupt  # 接受到外部停止服务信号
                elif self._srv_status == 1:   # 交易时段
                    if self.api is None:
                        self.logger.info(f"启动服务时间到")
                        self._start_srv()
                    self.api.wait_update()
                else:  # 非交易时段
                    if self.api is None:
                        time.sleep(1)
                        continue
                    self.logger.info(f"停止服务时间到")
                    self.api.wait_update()
                    self.api.close()
                    self.api = None
        except KeyboardInterrupt:
            self.logger.info(f"服务被 Ctrl+C 中断！")
        except Exception:
            self.logger.error(f"捕获到未知异常: {traceback.format_exc()}")
        finally:
            if self.api:
                self.api.close()

    def _sig_term_handler(self, sig, frame):
        self.logger.info(f"收到服务退出信号: {sig}")
        self._recv_sig_stop = True

    def _sig_alarm_handler(self, sig, frame):
        now = datetime.now().time()
        if now >= self._start_time.time() or now < self._stop_time.time():
            self._srv_status = 1
        else:
            self._srv_status = 0
        signal.alarm(60)  # 间隔60秒检查一次


class MdSrvConfig(GenConfig):
    """CTP Md Server配置信息"""
    def __init__(self):
        super().__init__(MD_CFG)

    def get_md_symbols(self):
        return self.sectionList()

    def get_symbol_duration(self, symbol):
        return self.getSecOption(symbol, 'duration')
