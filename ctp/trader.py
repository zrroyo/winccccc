# -*- coding:utf-8 -*-

import tqsdk
from lib import GenConfig
from .strategy import Strategy  # Fix me
from .error import TraderError
from .daemon import TASKS_CONFIG


class TradeTask:
    """交易"""
    def __init__(self, instrument, api, logger):
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

        self.tsk_cfg = TraderConfig(TASKS_CONFIG, instrument)
        self.strategy_name = self.tsk_cfg.get_param('strategy')
        if self.strategy_name is None:
            raise TraderError(f"未找到合约 {instrument} 的交易策略！")

        _strategy_class = getattr(globals()['strategy'], self.strategy_name)
        if not issubclass(_strategy_class, Strategy):
            raise TraderError(f"发现未知的交易策略: {self.strategy_name}！")
        self.strategy = _strategy_class(self.api, self.instrument, self.tsk_cfg, self.logger)

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

    def get_param(self, name):
        """得到交易参数"""
        return self.getSecOption(self.defaultSec, name)
