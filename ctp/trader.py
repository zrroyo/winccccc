# -*- coding:utf-8 -*-

import traceback
from tqsdk import TqApi, TqChan, TargetPosTask
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

        if not isinstance(api, TqApi):
            raise TraderError("必须为tq交易接口类型！")
        self.api = api

        if instrument not in self.api._data.get("quotes", {}):
            raise TraderError(f"发现不存在的合约: {instrument} !")
        self.instrument = instrument
        self._quote = self.api.get_quote(self.instrument)

        self.tsk_cfg = TraderConfig(TASKS_CONFIG, instrument, logger)
        self.strategy_name = self.tsk_cfg.get_param('strategy')
        if self.strategy_name is None:
            raise TraderError(f"未找到合约 {instrument} 的交易策略！")

        _strategy_class = getattr(globals()['strategy'], self.strategy_name)
        if not issubclass(_strategy_class, Strategy):
            raise TraderError(f"发现未知的交易策略: {self.strategy_name}！")
        self.strategy = _strategy_class(self.api, self.instrument, self.tsk_cfg, self.logger)

        self.pos_chan = TqChan(self.api)  # 接收仓位更新chan
        try:
            _offset_priority = self.tsk_cfg.get_param('offset_priority')
            if _offset_priority is None:
                self.pos_task = TargetPosTask(self.api, self._quote, trade_chan=self.pos_chan)
            else:
                self.pos_task = TargetPosTask(self.api, self._quote, offset_priority=_offset_priority,
                                           trade_chan=self.pos_chan)
        except Exception as e:
            self.logger.error(f"初始化TargetPosTask报错：{traceback.format_exc(e)}")
            raise TraderError(f"初始化TargetPosTask报错: {instrument}！")

    async def req_update_target_pos(self, exp_pos, delta_change, notify=True):
        """

        :param exp_pos:
        :param delta_change:
        :param notify:
        :return:
        """
        if delta_change == 0:
            return

        self.pos_task.set_target_volume(exp_pos)
        dealed_vol = 0
        async for nr_pos_chg in self.pos_chan:
            dealed_vol += nr_pos_chg
            if dealed_vol == delta_change:
                if notify:
                    self.strategy.notify_pos_change(dealed_vol)
                break
        return

    async def _run(self):
        """策略协程的执行入口"""
        # 如果服务器中有未完成的交易单，需先处理完成
        if self.strategy.unhandled_pos is not None:
            exp_pos, delta_change = self.strategy.unhandled_pos
            await self.req_update_target_pos(exp_pos, delta_change, notify=False)
            self.strategy.handle_position_late(delta_change)
            self.strategy.unhandled_pos = None

        async with self.api.register_update_notify(self.strategy.active_listener) as update_chan:
            async for _ in update_chan:
                exp_pos, delta_change = await self.strategy.target_pos_change()
                if exp_pos is None:
                    continue

                # 下单，并等待成交通知
                await self.req_update_target_pos(exp_pos, delta_change)


class TraderConfig(GenConfig):
    """从文件中读取交易任务配置"""
    def __init__(self, cfgFile, task_id, logger):
        """
        :param cfgFile: 配置文件名
        :param task_id: 合约id
        :param logger: 日志记录接口
        """
        super(TraderConfig, self).__init__(cfgFile)
        self.logger = logger
        self.cfgFile = cfgFile
        self.defaultSec = task_id

    def get_param(self, name):
        """得到交易参数"""
        return self.getSecOption(self.defaultSec, name)
