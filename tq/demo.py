#! /usr/bin/env python3

import pandas as pd
import asyncio
from datetime import datetime
from tqsdk import TqApi, TqAccount, TqSim, TqAuth, TqKq, TargetPosTask, TqChan, tafunc


class TqSdkDemo(object):
    def __init__(self):
        auth = TqAuth("13286016839", "Good.day$2020")
        self.api = TqApi(TqAccount("H宏源期货", "901207680", "wawj687913"), auth=auth)
        # self.api = TqApi(TqSim(), auth=auth)   # sdk 2.0.4

    def test_get_md_data(self, instrument):
        quote = self.api.get_quote(instrument)
        while True:
            self.api.wait_update()
            print(quote.datetime, quote.last_price, quote.volume)

    async def test_insert_order(self, symbol):
        pos_chan = TqChan(self.api)
        pos = self.api.get_position(symbol)
        target_pos = TargetPosTask(self.api, symbol, offset_priority="今昨,开", trade_chan=pos_chan)
        delta_volume = 10
        dealed = 0
        target_pos.set_target_volume(delta_volume)
        while True:
            print(f"pos.orders: {pos.orders}")
            _pos = await pos_chan.recv()
            print(f"dealed: {pos}")
            dealed += pos
            if dealed == delta_volume:
                break
            print(f"pos {pos.pos}, long {pos.pos_long}, long_his {pos.pos_long_his}, long_today {pos.pos_long_today}, "
                  f"pos_short {pos.pos_short}, pos_short_his {pos.pos_short_his}, pos_short_today {pos.pos_short_today}")

    async def test_kline_serial(self, symbol):
        """测试 K 线"""
        fp = open('kline_store.txt', 'a+')
        try:
            kline = self.api.get_kline_serial(symbol, 60)
            async with self.api.register_update_notify(kline) as update_chan:
                async for _ in update_chan:
                    if self.api.is_changing(kline.iloc[-1], 'datetime'):
                        latest = kline.iloc[-2]   # 新K线已经生成，上一K线已固定，计入
                        _time = tafunc.time_to_datetime(latest['datetime'])
                        _time = datetime.strftime(_time, "%Y/%m/%d %H:%M:%S")
                        # print(f'=> {_time}\n{latest}\n')
                        output = f"{_time},{latest['id']},{latest['open']},{latest['high']},"\
                                 f"{latest['low']},{latest['close']},{latest['volume']},"\
                                 f"{latest['open_oi']},{latest['close_oi']}\n"
                        print(output)
                        fp.write(output)
        except asyncio.CancelledError:
            print(f"task done!")
            fp.close()

    def wait_update(self):
        while True:
            self.api.wait_update()


if __name__ == '__main__':
    demo = TqSdkDemo()
    # symbol = 'DCE.p2105'
    symbol = 'SHFE.ag2112'
    # demo.test_get_md_data(symbol)
    # demo.api.create_task(demo.test_insert_order(symbol))
    demo.api.create_task(demo.test_kline_serial(symbol))
    try:
        demo.wait_update()
    except KeyboardInterrupt:
        demo.api.close()
