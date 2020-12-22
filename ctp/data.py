# -*- coding:utf-8 -*-

import pandas as pd


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
