# -*- coding:utf-8 -*-

from abc import ABCMeta, abstractmethod
from ..error import StrategyError


class Strategy:
    """交易策略基类"""
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, params):
        """
        :param string params: 策略参数字符串，参数间以';'号分隔
        :raise StrategyError: 出错统一抛出 StrategyError 异常
        """
        self._listener = None  # 子策略必须要初始化自己的监听对象

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
