# -*- coding:utf-8 -*-

import traceback
from .base import Strategy, MarketDataSaver
from ..error import StrategyError
from ..data import TradeDataComposition as TDC, Position as POS


class STR_WaveFlexSP(Strategy):

    LAST_CUT_TYPE_CL = 1
    LAST_CUT_TYPE_SP = 2

    def __init__(self, api, symbol, tsk_cfg, logger):
        super(STR_WaveFlexSP, self).__init__(api, symbol, tsk_cfg, logger)

        #
        self.posStopProfit = self.tdr.get_property('pos_stop_profit', [])
        if self.posStopProfit is None:
            raise StrategyError(f"TDR中posStopProfit数据错误！")
        #
        self.pLastCut = self.tdr.get_property('p_last_cut', ())
        if self.pLastCut is None:
            raise StrategyError(f"TDR中pLastCut数据错误！")
        # 申明交易跟踪变量
        self._listener = self.api.get_kline_serial(self.symbol, 60, data_length=20)
        self._quote = self.api.get_quote(symbol)
        # 使能保存行情数据
        md_saver = MarketDataSaver(api, "%s.csv" % self.symbol, self._listener, self.symbol, logger)
        self.enable_save_market_data(md_saver)

    def load_tsk_parameters(self):
        """解析交易参数"""
        attrs = dict()
        try:
            attrs['lot_size_pos'] = eval(self.tsk_cfg.get_param('lot_size_pos'))
            attrs['signal_start'] = eval(self.tsk_cfg.get_param('signal_start'))
            attrs['signal_end'] = eval(self.tsk_cfg.get_param('signal_end'))
            # 止赢参数。第一仓不支持止赢，其它不能为None
            attrs['spThresholds'] = eval(self.tsk_cfg.get_param('spThresholds'))
            attrs['apThresholds'] = eval(self.tsk_cfg.get_param('apThresholds'))
            attrs['clThresholds'] = eval(self.tsk_cfg.get_param('clThresholds'))
            return attrs
        except Exception as e:
            self.logger.error(f"加载任务参数时出错：{traceback.format_exc(e)}")
            return None

    async def target_pos_change(self):
        """计算仓位的变化量
        基本于self._listener的变化来计算持仓的变化量
        """
        while True:
            if not self.api.is_changing(self._listener.iloc[-1], "datetime"):
                yield None, None
                continue

            tick = self._listener.iloc[-1]['datetime']
            price = self._listener.iloc[-1]['last_price']
            direction = self.tdr.get_direction()

            if direction == Strategy.SIG_TRADE_NONE:
                direction = self._signal_start_trading(tick, price)
                if direction:
                    self.logger.info(f"触发进场信号: {tick}, {price}, {direction}")
                    self.tdr.save_direction(direction)
                    exp_pos, exp_change = self.calculate_target_pos(direction, self.attrs['lot_size_pos'])
                    self.tdr.add_position(POS(exp_pos, price, tick, exp_change, direction, POS.POS_STAT_OPEN))
                    yield exp_pos, exp_change
                    dealed_vol = await self._pos_chg_chan.recv_latest()  # 等待成交
                    self.logger.info(f"进场，更新TDR持仓数据：成交 {dealed_vol}")
                    self.handle_position_late(dealed_vol)
                    continue
                # 新行情未到来
                yield None, None
                continue

            # 在行情中 #

            if self._signal_end_trading(tick, price, direction):
                self.logger.info(f"触发退出信号，结束交易：{tick}, {price}, {direction}")
                exp_pos, exp_change = self.calculate_target_pos(direction, 0)  # 清仓
                # 设置标志...
                for num in range(self.tdr.get_cur_pos_num(), 0, -1):
                    self.tdr.set_position(num, {"target_pos": exp_pos, "status": POS.POS_STAT_CLOSE})
                yield exp_pos, exp_change
                dealed_vol = await self._pos_chg_chan.recv_latest()  # 等待成交
                self.logger.info(f"退场，更新TDR持仓数据：成交 {dealed_vol}")
                self.handle_position_late(dealed_vol)
                self.tdr.save_direction(Strategy.SIG_TRADE_NONE)
                continue

            _ret = self._signal_cut_loss(tick, price, direction)
            if _ret is not None:
                self.logger.info(f"触发止损信号：{tick}, {price}, {direction}")
                pos_change = (self.tdr.get_cur_pos_num() - _ret + 1) * self.attrs['lot_size_pos']
                exp_pos, exp_change = self.calculate_target_pos(direction, -pos_change)  # 减掉(仓位数 * 手数/仓)
                # 设置标志...
                for num in range(self.tdr.get_cur_pos_num(), _ret-1, -1):
                    self.tdr.set_position(num, {"target_pos": exp_pos, "status": POS.POS_STAT_CLOSE})
                yield exp_pos, exp_change
                dealed_vol = await self._pos_chg_chan.recv_latest()  # 等待成交
                self.logger.info(f"止损，更新TDR持仓数据：成交 {dealed_vol}")
                self.handle_position_late(dealed_vol)
                continue

            if self._signal_add_position(tick, price, direction):
                self.logger.info(f"触发加仓信号：{tick}, {price}, {direction}")
                exp_pos, exp_change = self.calculate_target_pos(direction, self.attrs['lot_size_pos'])
                self.tdr.add_position(POS(exp_pos, price, tick, exp_change, direction, POS.POS_STAT_OPEN))
                yield exp_pos, exp_change
                dealed_vol = await self._pos_chg_chan.recv_latest()  # 等待成交
                self.logger.info(f"进场，更新TDR持仓数据：成交 {dealed_vol}")
                self.handle_position_late(dealed_vol)
                continue

            _ret = self._signal_stop_profit(tick, price, direction)
            if _ret is not None:
                self.logger.info(f"触发止赢信号：{tick}, {price}, {direction}")
                pos_change = (self.tdr.get_cur_pos_num() - _ret + 1) * self.attrs['lot_size_pos']
                exp_pos, exp_change = self.calculate_target_pos(direction, -pos_change)  # 减掉(仓位数 * 手数/仓)
                # 设置标志...
                for num in range(self.tdr.get_cur_pos_num(), _ret-1, -1):
                    self.tdr.set_position(num, {"target_pos": exp_pos, "status": POS.POS_STAT_CLOSE})
                yield exp_pos, exp_change
                dealed_vol = await self._pos_chg_chan.recv_latest()  # 等待成交
                self.logger.info(f"止赢，更新TDR持仓数据：成交 {dealed_vol}")
                self.handle_position_late(dealed_vol)

    def _signal_start_trading(self, tick, price):
        """触发开始交易信号
        :param tick: 交易时间
        :param price: 当前价格
        :return: SIG_TRADE_SHORT、SIG_TRADE_LONG、SIG_TRADE_NONE
        """
        ret = Strategy.SIG_TRADE_NONE
        days = self.attrs['signal_start']
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
        days = self.attrs['signal_end']

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
            _ = self.posStopProfit[self.tdr.get_cur_pos_num()]
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
                _thr = self.attrs['spThresholds'][self.tdr.get_cur_pos_num()][4]
                _ignore = cfr <= _thr
                if not _ignore:
                    self.logger.info(f"[{self.get_signal_direction(direction)}] last SP, cfr {cfr}, _thr {_thr}")

            if _ignore:
                return ret

        try:
            _thr = self.attrs['apThresholds'][self.tdr.get_cur_pos_num()]
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
        posList = range(self.tdr.get_cur_pos_num(), 0, -1)
        for posIdx in posList:
            pos = self.tdr.get_position(posIdx)
            _cfr = self.gen_cfr(price, pos.price, direction)
            _thr = self.attrs['clThresholds'][posIdx - 1]
            cfr.append(_cfr)
            if _cfr >= _thr:
                # 如果不满足则之前仓位也不会满足
                break

            toCut = posIdx
            # 记录止损点，作为加仓条件以避免止损无效
            self.pLastCut = (pos.price, self.LAST_CUT_TYPE_CL)
            self.tdr.save_property('p_last_cut', self.pLastCut)
            # Fix ME
            # To move pos from self.posStopProfit

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
        toSP = None
        _skipSP = False

        # 从最后一仓开始逆序检查
        posList = range(self.tdr.get_cur_pos_num(), 0, -1)
        for posIdx in posList:
            pos = self.tdr.get_position(posIdx)
            (thrDL, thrESP1, thrESP2, thrSP) = self.attrs['spThresholds'][posIdx - 1][0:4]
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
                # 仓位未进入ESP，勿须止赢
                break

        if toSP:
            ret = toSP
        return ret
