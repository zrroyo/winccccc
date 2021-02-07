# -*- coding:utf-8 -*-

import os
import traceback
import numpy as np
from abc import ABCMeta, abstractmethod
from lib import GenConfig
from ..globals import GlobalConfig
from ..error import StrategyError, TradeDetailsRecordError
from ..data import TradeDataComposition as TDC, TradeDetailsRecord as TDR


class Strategy:
    """交易策略基类"""
    __metaclass__ = ABCMeta
    # 交易信号
    SIG_TRADE_SHORT = -1  # 卖空
    SIG_TRADE_LONG = 1  # 买多
    SIG_TRADE_NONE = 0  # 没有行情

    def __init__(self, api, symbol, tsk_cfg, logger):
        """
        :param TqApi api: API接口实例
        :param string symbol: 交易所合约代号
        :param TraderConfig tsk_cfg: 任务参数读取接口
        :param logger: 日志存取接口
        :raise: StrategyError异常
        """
        self.api = api
        self.symbol = symbol
        self.tsk_cfg = tsk_cfg
        self.logger = logger

        self.tdc_file = self.get_history_data_file()
        if not os.path.exists(self.tdc_file):
            raise StrategyError(f"未找到 {self.symbol} 的TDC数据！")
        self.tdc = TDC(self.tdc_file, self.logger)

        self.tdr_file = self.get_trade_details_file()
        if not os.path.exists(self.tdr_file):
            raise StrategyError(f"未找到 {self.symbol} 的TDR数据！")

        self.tdr = self.init_tdr()
        if self.tdr is None:
            raise StrategyError(f"TDR未初始化成功：{self.symbol} ！")

        self.attrs = self.load_tsk_parameters()
        if self.attrs is None:
            raise StrategyError(f"解析 {self.symbol} 策略参数错误！")

        # 子策略必须要初始化自己的监听对象
        self._listener = None

    def init_tdr(self):
        """初始化tdr ---
        策略类可以重载该方法并返回自定义的TDR对象
        :return: 正常返回TDR或其子类，失败则返回None
        """
        try:
            ret = TDR(self.tdr_file, self.logger)
        except TradeDetailsRecordError as e:
            self.logger.error(f"初始化TDR错误：{traceback.format_exc(e)}")
            ret = None
        return ret

    @abstractmethod
    def load_tsk_parameters(self):
        """解析交易参数
        :return dict: 交易任务参数
        """
        pass

    @property
    def active_listener(self):
        """策略需指定一个实例以触发监控交易行为，该实例可以是合约、K线等。该接口用于返回需监控的实例对象"""
        if self._listener is None:
            raise StrategyError("策略未初始化 ‘_listener’ 属性")
        return self._listener

    @abstractmethod
    def target_pos_change(self):
        """计算仓位的变化量
        基本于self._listener的变化来计算持仓的变化量

        :returns int: 以手数为单位的仓位变化量
                    > 0: 增加仓位
                    < 0: 减少仓位
                    = 0: 持仓不变
        """
        pass

    def get_history_data_file(self):
        """得到历史数据文件"""
        _global = GlobalConfig()
        filename = self.symbol.rstrip('.csv')
        return os.path.join(_global.get_md_runtime_dir(), filename)

    def get_trade_details_file(self):
        """得到交易详情文件"""
        _global = GlobalConfig()
        filename = self.symbol.rstrip('.csv')
        return os.path.join(_global.get_trade_details_dir(), filename)

    def get_signal_direction(self, signal):
        """交易信号转换成方向字符串
        :param signal: 交易信号
        :return: 信号字串
        """
        ret = None
        if signal == Strategy.SIG_TRADE_SHORT:
            ret = 'Short'
        elif signal == Strategy.SIG_TRADE_LONG:
            ret = 'Long'
        return ret

    def gen_cfr(self, price, opPrice, direction):
        """计算当前浮动利润率
        :param price: 当前价格
        :param direction: 方向
        :param opPrice: 加仓价格
        :return: 浮动利润率|NaN
        """
        ret = np.nan
        try:
            if direction == Strategy.SIG_TRADE_LONG:
                ret = (price - opPrice) / opPrice
            elif direction == Strategy.SIG_TRADE_SHORT:
                ret = (opPrice - price) / opPrice
            else:
                raise StrategyError(f"未识别的交易信号 {direction}")
        except ZeroDivisionError:
            self.logger.error(f"输入opPrice异常 {opPrice}")
        return ret


class StrategyConfig(GenConfig):
    """交易策略配置信息接口"""
    def __init__(self, cfgFile, task_id):
        """
        :param cfgFile: 配置文件名
        :param task_id: 合约id
        """
        super(StrategyConfig, self).__init__(cfgFile)
        self.cfgFile = cfgFile
        self.defaultSec = task_id

    def get_strategy(self):
        return self.getSecOption(self.defaultSec, 'strategy')
