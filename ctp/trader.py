# -*- coding:utf-8 -*-

import ctp.posmgr as posmgr

import tqsdk
import logging
import abc
import time


class TraderBadParamError(Exception):
    pass


class Trader():
    def __init__(self, instrument, user_info, trade_param, log_file, log_level=logging.DEBUG):
        # 初始化日志接口
        logger = logging.getLogger(instrument)
        logger.setLevel(log_level)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter('%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d: <%(levelname)s> %(message)s'))
        logger.addHandler(fh)
        self.logger = logger

        self.instrument = instrument
        self.user_info = user_info
        self.api = tqsdk.TqApi(tqsdk.TqAccount(user_info.broker_id, user_info.account_id, user_info.password))
        self.tpt = tqsdk.TargetPosTask(self.api, self.instrument)
        self.maxAddPos, self.param = self.parseCtrlParam(trade_param)
        self.posmgr = posmgr.PositionManager(self.maxAddPos, self.logger)
        #
        self.trend = None

    def parseCtrlParam(self, param):
        """

        :return:
        """
        raise TraderBadParamError("customized parameters haven't been parsed.")

    def reqTrade(self, instrument):
        quote = self.api.get_quote(instrument)
        while True:
            self.api.wait_update()
            # 最新价格发生变化
            if self.api.is_changing(quote, "last_price"):
                self.onRspTrade(quote.last_price)

    def onRspTrade(self, price):
        """

        :param price:
        :return:
        """
        if self.reqOpenTrend(price):
            self.onRspOpenTrend(price)
        elif self.reqAddPosition(price):
            self.onRspAddPosition(price)
        elif self.reqCutPosition(price):
            self.onRspCutPosition(price)

    def reqOpenTrend(self, price):
        """

        :param price:
        :return:
        """
        ret = False
        if self.posmgr.numPositions():
            return ret

        direction, offset, volume = self.signalTriggerTrend(price)
        if not volume:
            return ret

        order = self.insertOrder(direction, offset, volume)
        if not order:
            self.logger.error("开仓失败: '%s', '%s', '%s'." % (direction, offset, volume))
            return ret

        _ret = self.posmgr.pushPosition(time.time(), order.trade_price, direction, order.trade_records.get('price'))
        if not _ret:
            self.logger.warn("远程开仓成功但本地入仓失败！")
            return ret

        ret = True
        self.trend = direction
        self.onRspOpenTrend(price)
        return ret

    def reqAddPosition(self, price):
        """

        :param price:
        :return:
        """
        ret = False
        if self.posmgr.numPositions() >= self.maxAddPos:
            return ret

        direction, offset, volume = self.signalAddPos(price)
        if not volume:
            return ret

        order = self.insertOrder(direction, offset, volume)
        if not order:
            self.logger.error("开仓失败: '%s', '%s', '%s'." % (direction, offset, volume))
            return ret

        _ret = self.posmgr.pushPosition(time.time(), order.trade_price, direction, order.trade_records.get('price'))
        if not _ret:
            self.logger.warn("远程开仓成功但本地入仓失败！")
            return ret

        ret = True
        self.logger.log("加仓成功：'%s', '%s', '%s'." % (direction, offset, volume))
        return ret

    def reqCutPosition(self, price):
        """

        :param price:
        :return:
        """
        ret = False
        if self.posmgr.numPositions() <= 0:
            return ret

        direction, offset, volume, posIdx = self.signalCutPos(price)
        if not volume:
            return ret

        order = self.insertOrder(direction, offset, volume)
        if not order:
            self.logger.error("平仓失败: '%s', '%s', '%s'." % (direction, offset, volume))
            return ret

        _ret = self.posmgr.popPosition(posIdx)
        if not _ret:
            self.logger.warn("远程平仓成功但本地平仓失败！")
            return ret

        ret = True
        self.logger.log("平仓成功：'%s', '%s', '%s'." % (direction, offset, volume))
        return ret

    def onRspOpenTrend(self, price):
        pass

    def onRspAddPosition(self, price):
        pass

    def onRspCutPosition(self, price):
        pass

    def insertOrder(self, direction, offset, volume):
        """

        :param direction:
        :param offset:
        :param volume:
        :return: True|False
        """
        order = self.api.insert_order(self.instrument, direction, offset, volume)
        while True:
            self.api.wait_update()
            if self.api.is_changing(order, ["status", "volume_orign", "volume_left"]):
                # Fix me
                pass
        return order

    def signalTriggerTrend(self, price):
        pass

    def signalAddPos(self, price):
        pass

    def signalCutPos(self, price):
        pass