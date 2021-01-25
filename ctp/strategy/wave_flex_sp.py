# -*- coding:utf-8 -*-

import json
from .base import Strategy, Position
from ..error import StrategyError
from ..data import TradeDataComposition as TDC


class STR_WaveFlexSP(Strategy):

    LAST_CUT_TYPE_CL = 1
    LAST_CUT_TYPE_SP = 2

    def __init__(self, api, symbol, params, logger):
        super(STR_WaveFlexSP, self).__init__(api, symbol, params, logger)
        # 止赢参数。第一仓不支持止赢，其它不能为None
        self.spThresholds = (
            (None, None, None, None, None),
            (3, -0.003, -0.00803, 0.0180, 0.0361),
            (2, -0.007, -1, 0.04, 0.06),
            (2, 0, -1, 0.04, 0.08),
        )
        #
        self.apThresholds = [None, 0.013, 0.0129, 0.013]
        #
        self.clThresholds = [-0.016, -0.016, -0.025, -0.03]
        #
        self.posStopProfit = self.tdr.get_property('pos_stop_profit', [])
        if self.posStopProfit is None:
            raise StrategyError(f"TDR中posStopProfit数据错误！")
        #
        self.pLastCut = self.tdr.get_property('p_last_cut', ())
        if self.pLastCut is None:
            raise StrategyError(f"TDR中pLastCut数据错误！")
        # 申明交易跟踪变量
        self._listener = self.api.get_quote(symbol)

    def parse_parameters(self, params):
        """解析交易参数
        :param params:
        :return:
        """
        _attrs = json.loads(params)
        return _attrs

    def target_pos_change(self):
        """计算仓位的变化量
        基本于self._listener的变化来计算持仓的变化量

        :returns int: 以手数为单位的仓位变化量
                    > 0: 增加仓位
                    < 0: 减少仓位
                    = 0: 持仓不变
        """
        tick = self._listener.datetime
        price = self._listener.last_price
        ret = 0

        direction = self._signal_start_trading(tick, price)
        if direction:
            self.logger.info("触发进场信号")
            self.tdr.save_direction(direction)
            self.logger.info("更新TDR持仓数据")
            self.tdr.add_position(Position(price, tick, self.attrs.lot_size_pos, direction))
            ret = self.attrs.lot_size_pos
            return ret

        direction = self.tdr.get_direction()
        if self._signal_end_trading(tick, price, direction):
            self.logger.info("触发交易退出信号，结束交易")
            self.tdr.save_direction(Strategy.SIG_TRADE_NONE)
            self.logger.info("清除TDR持仓数据")
            for pos_idx in reversed(range(1, self.tdr.get_cur_pos_num()+1)):
                self.tdr.del_position(pos_idx)
            ret = self.tdr.get_cur_pos_num() * self.attrs.lot_size_pos
            return -ret

        _ret = self._signal_cut_loss(tick, price, direction)
        if _ret is not None:
            self.logger.info("准备止损，清除TDR持仓数据")
            for pos_idx in reversed(range(_ret, self.tdr.get_cur_pos_num() + 1)):
                self.tdr.del_position(pos_idx)
            ret = (self.tdr.get_cur_pos_num() - _ret + 1) * self.attrs.lot_size_pos
            return -ret

        if self._signal_add_position(tick, price, direction):
            self.logger.info("准备加仓，更新TDR持仓数据")
            self.tdr.add_position(Position(price, tick, self.attrs.lot_size_pos, direction))
            ret = self.attrs.lot_size_pos
            return ret

        _ret = self._signal_stop_profit(tick, price, direction)
        if _ret is not None:
            self.logger.info("准备止赢，更新TDR持仓数据")
            for pos_idx in reversed(range(_ret, self.tdr.get_cur_pos_num() + 1)):
                self.tdr.del_position(pos_idx)
            ret = (self.tdr.get_cur_pos_num() - _ret + 1) * self.attrs.lot_size_pos
            return -ret

        return ret

    def _signal_start_trading(self, tick, price):
        """触发开始交易信号
        :param tick: 交易时间
        :param price: 当前价格
        :return: SIG_TRADE_SHORT、SIG_TRADE_LONG、SIG_TRADE_NONE
        """
        ret = Strategy.SIG_TRADE_NONE
        days = 15
        lowest = self.tdc.get_lowest_by_ticks(tick, days, TDC.F_CLOSE)
        if price < lowest:
            self.logger.info(f"{tick} Hit Short Signal: Close {price}, Lowest {lowest}, "
                             f"priceVariation {self.attrs.priceVariation}")
            ret = Strategy.SIG_TRADE_SHORT
            return ret

        highest = self.tdc.get_highest_by_ticks(tick, days, TDC.F_CLOSE)
        if price > highest:
            self.logger.info(f"{tick} Hit Long Signal: Close {price}, Highest {highest}, "
                             f"priceVariation {self.attrs.priceVariation}")
            ret = Strategy.SIG_TRADE_LONG
            return ret

        return ret

    def _signal_end_trading(self, tick, price, direction):
        """触发结束交易信号
        :param tick: 交易时间
        :param price: 当前价格
        :param direction: 多空方向
        """
        ret = False
        days = 10

        highest = self.tdc.get_highest_by_ticks(tick, days, TDC.F_CLOSE)
        if direction == Strategy.SIG_TRADE_SHORT and price > highest:
            # 价格创出10日新高，结束做空
            self.logger.info(f"	[Short] [{tick}] Hit Highest in {days} days: close {price}, highest {highest}")
            ret = True
            return ret

        lowest = self.tdc.get_lowest_by_ticks(tick, days, TDC.F_CLOSE)
        if direction == Strategy.SIG_TRADE_LONG and price < lowest:
            # 价格创出10日新低，结束做多
            self.logger.info(f"	[Long] [{tick}] Hit Lowest in {days} days: close {price}, lowest {lowest}")
            ret = True
            return ret

        return ret

    def _signal_add_position(self,  tick, price, direction):
        """触发加仓信号
        :param tick: 交易时间
        :param price: 当前价格
        :param direction: 多空方向
        """
        ret = False
        try:
            # 当前最高仓位已进入止赢模式，停止加仓（否则止赢模式失效）
            self.posStopProfit[self.tdr.get_cur_pos_num()]
            return ret
        except KeyError:
            pass

        pos = self.tdr.get_position()

        if self.pLastCut:
            _ignore = True
            plc, cutType = self.pLastCut
            # 需保证新开仓价优于最近一次止损价，否则会有止损点无效风险
            if cutType == self.LAST_CUT_TYPE_CL:
                _ignore = (price <= plc * 1.01) if direction == self.SIG_TRADE_LONG \
                    else (price >= plc * 0.99)
                if not _ignore:
                    self.logger.info(f"[{self.get_signal_direction(direction)}] last CL, price {price}, plc {plc}")

            elif cutType == self.LAST_CUT_TYPE_SP:
                cfr = self.gen_cfr(price, plc, direction)
                _thr = self.spThresholds[self.tdr.get_cur_pos_num()][4]
                _ignore = cfr <= _thr
                if not _ignore:
                    self.logger.info(f"[{self.get_signal_direction(direction)}] last SP, cfr {cfr}, _thr {_thr}")

            if _ignore:
                return ret

        try:
            _thr = self.apThresholds[self.tdr.get_cur_pos_num()]
            cfr = self.gen_cfr(price, pos.price, direction)
            # 利润浮动需大于仓位对应阈值，并且需大于该仓位上一次开仓价（否则会导致止损失效）
            if cfr >= _thr:
                self.logger.info(f" Add Position: {tick}, cfr {cfr}")
                ret = True
        except IndexError:
            ret = False

        if ret:
            # 止损后才需设置以预防止损失效
            self.pLastCut = ()
            self.tdr.save_property('p_last_cut', self.pLastCut)

        return ret

    def _signal_cut_loss(self, tick, price, direction):
        """触发止损信号
        :param tick: 交易时间
        :param price: 当前价格
        :param direction: 多空方向
        :return: 未触发止损信号返回None，否则返回自定义参数
        """
        toCut = None
        cfr = list()

        # 从最后一仓开始逆序检查
        posList = list(range(1, self.tdr.get_cur_pos_num() + 1))
        posList.reverse()
        for posIdx in posList:
            pos = self.tdr.get_position(posIdx)
            _cfr = self.gen_cfr(price, pos.price, direction)
            _thr = self.clThresholds[posIdx - 1]
            cfr.append(_cfr)
            if _cfr >= _thr:
                # 如果不满足则之前仓位也不会满足
                break

            toCut = posIdx
            # 记录止损点，作为加仓条件以避免止损无效
            self.pLastCut = (pos.price, self.LAST_CUT_TYPE_CL)
            self.tdr.save_property('p_last_cut', self.pLastCut)

        ret = None
        if toCut:
            self.logger.info(f"	Cut Loss: {tick}, price {price}, cut from {toCut}, cfr {cfr}")
            ret = toCut

        return ret

    def __could_stop_profit(self, price, pos, espType, thrSP, direction):
        """是否能够止赢
        :param price: 当前价
        :param pos: 持仓
        :param espType: esp类型，1或2
        :param thrSP: 止赢阈值
        :param direction: 多空方向
        :return: 能返回True，否则返回False
        """
        ret = False
        if not espType or not thrSP:
            return ret

        cfr = self.gen_cfr(price, pos.price, direction)
        if (espType == 1 and cfr >= thrSP) or (espType == 2 and cfr > 0):
            self.logger.info("signal %s, price (pos %s, cur %s), esp %s, thrSP %s" % (
                self.get_signal_direction(direction), pos.price, price, espType, thrSP if espType == 1 else 0))
            ret = True
        return ret

    def _signal_stop_profit(self, tick, price, direction):
        """触发止赢信号
        :param tick: 交易时间
        :param price: 当前价格
        :param direction: 多空方向
        :return: 未触发止损信号返回None，否则返回自定义参数
        """
        ret = None

        if not self.dayLastTick or self.dayLastTick.date() != tick.date():
            self.dayLastTick = self.tickHelper.dayLastTick(tick)

        toSP = None
        _skipSP = False

        # 从最后一仓开始逆序检查
        posList = list(range(1, self.tdr.get_cur_pos_num() + 1))
        posList.reverse()
        for posIdx in posList:
            pos = self.tdr.get_position(posIdx)
            (thrDL, thrESP1, thrESP2, thrSP) = self.spThresholds[posIdx - 1][0:4]
            try:
                espType = self.posStopProfit[posIdx][2]
                if not _skipSP and self.__could_stop_profit(price, pos, espType, thrSP, direction):
                    toSP = posIdx
                    self.pLastCut = (pos.price, self.LAST_CUT_TYPE_SP)
                    self.tdr.save_property('p_last_cut', self.pLastCut)
                else:
                    # 不允许隔仓SP，否则仓位统计会发生混乱
                    _skipSP = True
            except KeyError:
                # 该仓没有ESP，以下仓位由于隔仓不允许SP
                _skipSP = True
                if tick != self.dayLastTick:
                    # 仅在交易日的最后一个tick检查是否触发ESP
                    break

                if toSP:
                    # 高仓位已经触发止赢，价格必然高于低仓位，ESP条件不可能成立
                    break

                if not thrDL:
                    # 为了避免仓位混乱，除第一个仓位外都必须设置SP相关参数，否则引起仓位混乱
                    break

                espType = 1
                _fr = self.gen_cfr(price, pos.price, direction)
                if _fr > thrESP1:
                    # 低仓位ESP条件仍有可能满足
                    continue
                elif _fr < thrESP2:
                    espType = 2

                _dayLasts = self.tickHelper.dayLasts(pos.time, tick)
                if _dayLasts < thrDL:
                    #
                    continue

                self.logger.info(f"signalStopProfit: pos {posIdx}, cur (tick {tick}, price {price}), "
                                 f"DL {_dayLasts}, FR {_fr}, esp {espType}")
                #
                self.posStopProfit[posIdx] = [True, _fr, espType]

        if toSP:
            ret = toSP
        return ret
