# -*- coding:utf-8 -*-

import tqsdk
from lib import GenConfig
from .strategy import Strategy
from .error import TraderError


class TradeTask:
    """交易"""
    def __init__(self, instrument, api, stra_name, stra_params, logger):
        """
        :param instrument: 合约名称
        :param api: API接口实例
        :param stra_name: 策略名称（类名）
        :param stra_params: 策略参数
        :param logger: 日志记录接口
        :raise TraderError
        """
        self.logger = logger

        if not isinstance(api, tqsdk.TqApi):
            raise TraderError("必须为tq交易接口类型！")
        self.api = api

        if instrument not in self.api._data.get("quotes", {}):
            raise TraderError(f"发现不存在的合约: {instrument} !")
        self.instrument = instrument
        self._quote = self.api.get_quote(self.instrument)

        _strategy_class = getattr(globals()['strategy'], stra_name)
        if not issubclass(_strategy_class, Strategy):
            raise TraderError(f"未找到对应的行政策略: {stra_name} !")
        self.strategy = _strategy_class(stra_params)

    async def _run(self):
        """策略协程的执行入口"""
        with self.api.register_update_notify(self.strategy.active_listener) as update_chan:
            # async for _ in update_chan:
            while True:
                await update_chan.recv_latest()
                order_offset, order_dir, order_volume = self.strategy.target_pos_change()
                if order_volume == 0:
                    continue

                trade_chan = tqsdk.TqChan()
                order_task = tqsdk.InsertOrderUntilAllTradedTask(self.api, self.instrument, order_dir,
                                        offset=order_offset, volume=order_volume, trade_chan=trade_chan)
                await order_task._task


class TraderConfig(GenConfig):
    """从文件中读取交易任务配置"""
    def __init__(self, cfgFile, task_id):
        """
        :param cfgFile: 配置文件名
        :param task_id: 合约id
        """
        super(TraderConfig, self).__init__(cfgFile)
        self.cfgFile = cfgFile
        self.defaultSec = task_id

    def get_strategy(self):
        return self.getSecOption(self.defaultSec, 'strategy')

    def get_params(self):
        return self.getSecOption(self.defaultSec, 'parameter')
