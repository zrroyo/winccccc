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


class Position:
    """持仓单位（仓位）"""

    # 仓位状态
    POS_STAT_OPEN = 1  # 开仓中
    POS_STAT_CLOSE = 2  # 平仓中
    POS_STAT_FINISH = 0  # 开平仓已完成
    POS_STAT_INVALID = -1  # 无效

    def __init__(self, pos=None, price=None, time=None, volume=None, direction=None, status=-1):
        """加仓信息
        :param pos: 目标持仓数
        :param price: 成交价
        :param time: 时间
        :param volume: 开仓手数
        :param direction: 方向
        :param status: 状态
        """
        self.target_pos = pos
        self.price = price
        self.time = time
        self.volume = volume
        self.direction = direction
        self.status = status

    def __str__(self):
        values = {'target_pos': self.target_pos, 'price': self.price, 'time': self.time,
                  'volume': self.volume, 'direction': self.direction, 'status': self.status}
        return str(values)

    def assign(self, values):
        """赋值
        :param dict values: 赋值数据
        :return True|False
        """
        try:
            passed_fields = values.keys()
        except Exception:
            return False

        if 'target_pos' in passed_fields:
            self.target_pos = values['target_pos']
        if 'price' in passed_fields:
            self.price = values['price']
        if 'time' in passed_fields:
            self.time = values['time']
        if 'volume' in passed_fields:
            self.volume = values['volume']
        if 'direction' in passed_fields:
            self.direction = values['direction']
        if 'status' in passed_fields:
            self.status = values['status']
        return True


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

    def __valid_pos_index(self, num):
        """返回是否为有效的仓位索引
        :param num: 仓位索引
        :return: True|False
        """
        if num < 1 or num > len(self.__positions):
            return False
        return True

    def load_pos_details(self):
        """加载仓位信息
        :return: True|False
        """
        ret = True
        self.__positions.clear()
        pos_details = self.getSecOption(self.defaultSec, 'pos_details')
        if not pos_details:
            # 仓位为空
            return ret

        try:
            pos_details = eval(pos_details)
            for val in pos_details:
                pos = Position()
                if not pos.assign(val):
                    self.logger.error(f"无法解析仓位信息 val: {val}")
                    ret = False
                    break
                self.__positions.append(pos)
        except Exception as e:
            self.logger.error(f"转换时出现错误：pos_details: {pos_details}; "
                              f"exp: {traceback.format_exc(e)}")
            ret = False
        return ret

    def save_pos_details(self):
        """保存仓位信息"""
        pos_details = [str(pos) for pos in self.__positions]
        self.setSecOption(self.defaultSec, 'pos_details', str(pos_details))

    def get_cur_pos_num(self):
        """返回当前仓位"""
        return len(self.__positions)

    def get_position(self, num=None):
        """返回第num个仓位，num从１开始记
        :param num: 仓位索引，默认最后一个仓位
        :return: 索引对应仓位
        """
        # 默认（num为None）返回最后一个仓位
        if num is None:
            num = self.get_cur_pos_num()

        if not self.__valid_pos_index(num):
            self.logger.error(f"仓位超出范围：num {num}, current {len(self.__positions)}")
            return None

        return self.__positions[num-1]

    def set_position(self, num, values):
        """
        更新仓位数据
        :param num: 仓位索引
        :param dict values: 赋值数据
        :return: True|False
        """
        if not self.__valid_pos_index(num):
            self.logger.error(f"仓位超出范围：num {num}, current {len(self.__positions)}")
            return False

        pos = self.__positions[num-1]
        if not pos.assign(values):
            return False
        self.save_pos_details()
        return True

    def add_position(self, pos):
        """添加新仓位
        :param pos: Position class实例
        """
        self.__positions.append(pos)
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

        if not self.__valid_pos_index(num):
            self.logger.error(f"仓位超出范围：num {num}, current {len(self.__positions)}")
            return ret

        ret = self.__positions.pop(num-1)
        self.save_pos_details()
        return ret

    def clear_position(self):
        """清除所有仓位"""
        self.__positions.clear()
        self.save_pos_details()

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
