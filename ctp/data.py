# -*- coding:utf-8 -*-

import traceback
import pandas as pd
from ..lib import GenConfig
from .error import TradeDetailsRecordError


class TradeDataComposition:
    """交易数据合成 ---
    将历史交易数据与最新行情数据合成，比如支持计算动态移动平均线、MACD等
    """
    # 数据文件中的字段名称
    F_OPEN = 'Open'
    F_CLOSE = 'Close'
    F_AVG = 'Avg'
    F_HIGH = 'High'
    F_LOW = 'Low'
    F_BUY = 'Buy'
    F_SELL = 'Sell'

    def __init__(self, datafile, logger=None):
        """交易数据接口
        :param datafile: 数据文件名
        :param logger: 是否调试
        """
        self.logger = logger
        self.datafile = datafile
        self.data = pd.read_csv(datafile, header=None, index_col=0)
        self.data.columns = [self.F_OPEN, self.F_CLOSE, self.F_HIGH, self.F_LOW, self.F_BUY, self.F_SELL]
        # 根据邻近性原则建立tick数据缓存区
        self.__mcache = {}

    def __del__(self):
        pass

    def M(self, date, field, count, price):
        """计算移动平均值
        :param date: 交易日
        :param field: 字段
        :param count: 移动单位数
        :param price: 当前价
        :return:
            参数不正确返回None，正常返回移动平均值
        """
        try:
            return self.__mcache[date]['M'][field][count]
        except KeyError:
            ret = None
            dat = self.data[self.data.index <= date].tail(count-1)
            if count <= 1 or price <= 0:
                self.logger.error(f"收到非法参数：count = {count}, price = {price}")
                return ret
            elif len(dat) < count - 1:
                self.logger.error(f"M值无效：len(dat) = {len(dat)}, count - 1 = {count - 1}")
                return ret

            ret = float(sum(dat[field]) + price)/ (len(dat) + 1)

            if date not in self.__mcache.keys():
                # tick日期发生变化，依据邻近原则更新缓存区
                self.__mcache.clear()
                self.__mcache[date] = {}
                self.__mcache[date]['M'] = {}
                self.__mcache[date]['M'][field] = {}
            elif 'M' not in self.__mcache[date].keys():
                self.__mcache[date]['M'] = {}
                self.__mcache[date]['M'][field] = {}
            elif field not in self.__mcache[date]['M'].keys():
                self.__mcache[date]['M'][field] = {}

            self.__mcache[date]['M'][field][count] = ret
            return ret

    def get_field(self, date, field):
        """获取指定交易时间指定字段值
        :param date: 交易时间
        :param field: 字段
        :return: 没有返回None，有则返回值
        """
        try:
            dat = self.data[self.data.index == date]
            return dat[field][0]
        except IndexError:
            # 指定时间不存在
            return None

    def get_open(self, date):
        """
        获取指定交易时间开盘价
        :param date: 交易时间
        :return: 没有返回None，有则返回值
        """
        return self.get_field(date, self.F_OPEN)

    def get_close(self, date):
        """获取指定交易时间收盘价
        :param date: 交易时间
        :return: 没有返回None，有则返回值
        """
        return self.get_field(date, self.F_CLOSE)

    def get_avg(self, date):
        """获取指定交易时间平均价
        :param date: 交易时间
        :return: 没有返回None，有则返回值
        """
        return self.get_field(date, self.F_AVG)

    def get_high(self, date):
        """获取指定交易时间最高价
        :param date: 交易时间
        :return: 没有返回None，有则返回值
        """
        return self.get_field(date, self.F_HIGH)

    def get_low(self, date):
        """获取指定交易时间最低价
        :param date: 交易时间
        :return: 没有返回None，有则返回值
        """
        return self.get_field(date, self.F_LOW)

    def get_lowest_by_ticks(self, date, count, field):
        """获得交易时间前指定个tick中的最小值
        :param date: 交易时间
        :param count: tick数
        :param field: 字段
        :return: 数据不存在则返回np.nan
        """
        dat = self.data[self.data.index <= date].tail(count)
        return dat[field].min()

    def get_highest_by_ticks(self, date, count, field):
        """获得交易时间前指定个tick中的最大值
        :param date: 交易时间
        :param count: tick数
        :param field: 字段
        :return: 数据不存在则返回np.nan
        """
        dat = self.data[self.data.index <= date].tail(count)
        return dat[field].max()


class TradeDetailsRecord(GenConfig):
    def __init__(self, cfgFile, logger):
        """交易策略配置信息接口
        :raise TradeDetailsRecordError: 初始化仓位数据错误，将会抛出异常，调用时需捕获该异常
        """
        super(TradeDetailsRecord, self).__init__(cfgFile)
        self.cfgFile = cfgFile
        self.defaultSec = "all"
        self.logger = logger
        # 初始化仓位信息
        self.__positions = []
        if not self.load_pos_details():
            raise TradeDetailsRecordError(f"加载pos_details出错！")
        # 交易方向
        self.__direction = self.get_property('current_direction', 0)
        if self.__direction is None:
            raise TradeDetailsRecordError(f"加载current_direction出错！")

    def load_pos_details(self):
        """加载仓位信息
        :return: True|False
        """
        ret = True
        pos_details = self.getSecOption(self.defaultSec, 'pos_details')
        try:
            self.__positions = eval(pos_details)
        except Exception as e:
            self.logger.error(f"转换时出现错误：pos_details: {pos_details}; "
                              f"exp: {traceback.format_exc(e)}")
            ret = False
        return ret

    def save_pos_details(self):
        """保存仓位信息"""
        self.setSecOption(self.defaultSec, 'pos_details', str(self.__positions))

    def get_cur_pos_num(self):
        """返回当前仓位"""
        return len(self.__positions)

    def get_position(self, num=None):
        """返回第num个仓位，num从１开始记
        :param num: 仓位索引，默认最后一个仓位
        :return: 索引对应仓位
        """
        ret = None
        # 默认（num为None）返回最后一个仓位
        if num is None:
            num = self.get_cur_pos_num()

        if num < 1 or num > len(self.__positions):
            self.logger.error(f"仓位超出范围：num {num}, current {len(self.__positions)}")
            return ret

        return self.__positions[num-1]

    def add_position(self, pos):
        """添加新仓位"""
        self.__positions += [{'time': pos.time, 'price': pos.price, 'volume': pos.volume}]
        self.save_pos_details()

    def del_position(self, num):
        """删除仓位，num从１开始记
        :param num: 仓位索引，默认最后一个仓位
        :return: 正常返回已删除的仓位信息，否则返回None
        """
        ret = None
        # 默认（num为None）返回最后一个仓位
        if num is None:
            num = self.get_cur_pos_num()

        if num < 1 or num > len(self.__positions):
            self.logger.error(f"仓位超出范围：num {num}, current {len(self.__positions)}")
            return ret

        ret = self.__positions.pop(num-1)
        self.save_pos_details()
        return ret

    def get_direction(self):
        """得到交易方向
        :return: 0 -> 无交易；1 -> 买多；-1 -> 卖空
        """
        return self.__direction

    def save_direction(self, direction):
        self.__direction = direction
        self.setSecOption(self.defaultSec, 'current_direction', str(direction))

    def get_property(self, prop_name, def_ret):
        """从TDR文件读取属性值
        :param prop_name: 属性名称
        :param def_ret: 默认返回值
        :return: 正常返回属性值，错误返回None
        """
        value = self.getSecOption(self.defaultSec, prop_name)
        if value is None:
            return def_ret

        try:
            ret = eval(value)
        except Exception as e:
            self.logger.error(f"转换时出现错误：{prop_name}: {value}; exp: {traceback.format_exc(e)}")
            ret = None
        return ret

    def save_property(self, prop_name, value):
        """保存属性值到TDR
        :param prop_name: 属性名称
        :param value: 属性值
        :return:
        """
        self.setSecOption(self.defaultSec, prop_name, str(value))
