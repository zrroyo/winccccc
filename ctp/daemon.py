# -*- coding:utf-8 -*-

import os
import signal
import time
from datetime import datetime, timedelta
from tqsdk import TqApi, TqKq, TqAuth
from lib import GenConfig
from .trader import TradeTask
from .globals import GLOBAL_CONFIG, TASKS_CONFIG


class CtpSrvDaemon:
    """CTP服务"""
    def __init__(self, logger):
        self.logger = logger
        self._tasks = {}
        signal.signal(signal.SIGHUP, self._sighup_handler)
        self.global_cfg = DaemonConfig(GLOBAL_CONFIG)
        self._api = TqApi(TqKq(), TqAuth("", ""))   # sdk 2.0.4
        self.__stop_srv = False
        self.__stop_trade = False

    def __exit__(self, exc_type, exc_val, exc_tb):  # Add __enter__、__exit__??
        pass

    def get_peroids(self, peroid_tag, cur_time=None):
        """从配置中读取对应当天的时间区间
        :param string peroid_tag: 时间区间标识
        :param datetime cur_time: datetime时间
        :return list ret: 时间区间
        """
        ret = []
        _time = None
        if peroid_tag == 'trade':
            _time = self.global_cfg.get_trade_time()
        elif peroid_tag == 'replay':
            _time = self.global_cfg.get_replay_time()
        if _time is None:
            return ret

        if cur_time is None:
            cur_time = datetime.now()

        for tm in _time.split(','):
            _start, _end = tm.strip().split('~')
            _start = datetime.strptime(_start, "%H:%M")
            _end = datetime.strptime(_end, "%H:%M")
            _start = _start.replace(year=cur_time.year, month=cur_time.month, day=cur_time.day)
            _end = _end.replace(year=cur_time.year, month=cur_time.month, day=cur_time.day)
            # 夜盘交易时间段跨天
            if _start > _end:
                _end += timedelta(days=1)
            # cur_time为凌晨12点后的夜盘交易时间
            if _start - timedelta(days=1) <= cur_time <= _end - timedelta(days=1):
                _start -= timedelta(days=1)
                _end -= timedelta(days=1)
            ret.append({'start': _start, 'end': _end})
        return ret

    def __in_peroid_of(self, peroid_tag):
        """是否在指定的时间区间
        :param string peroid_tag: 时间区间标识
        :return tuple ret: (开始时间，结束时间)
        """
        cur_time = datetime.now()
        periods = self.get_peroids(peroid_tag, cur_time)
        ret = None, None

        for p in periods:
            if p['start'] <= cur_time <= p['end']:
                ret = p['start'], p['end']
                break
        return ret

    def run(self):
        while not self.__stop_srv:
            tm_start, tm_end = self.__in_peroid_of('trade')
            if tm_end:
                self.__start_trade(tm_end)

            tm_start, tm_end = self.__in_peroid_of('replay')
            if tm_end:
                self.__start_replay(tm_end)
            time.sleep(10)

    def __create_trade_tasks(self):  # Would Better to capture exceptions??
        """从配置文件中读取并创建交易任务"""
        cfg = GenConfig(TASKS_CONFIG)
        for task_id in cfg.sectionList():
            _task = TradeTask(task_id, self._api, self.logger)
            self._tasks[task_id] = _task
            self._api.create_task(_task._run())

    async def __task_stop_trade(self):
        self.__stop_trade = True

    def __start_trade(self, time_stop):
        """创建交易任务，开始交易"""
        self.__stop_trade = False
        timeout = time_stop - datetime.now()
        self._api._loop.call_later(delay=timeout.delta.total_seconds(), callback=self.__task_stop_trade)
        self.__create_trade_tasks()
        while not self.__stop_srv and not self.__stop_trade:
            self._api.wait_update()

    def __start_replay(self, time_stop):
        pass

    def _sighup_handler(self):
        """收到SIGHUP信号，退出服务"""
        self.logger.info("收到SIGHUP信号，退出！")
        for tsk in self._tasks:
            tsk.cancel()
        self._api.close()  # This can cancel tasks too??
        self.__stop_srv = True

    def notify(self, message):
        """发送邮件通知"""
        pass


class DaemonConfig(GenConfig):
    """从global文件中读取daemon配置"""
    def __init__(self, cfgFile):
        super(DaemonConfig, self).__init__(cfgFile)
        self.cfgFile = cfgFile
        self.defaultSec = 'daemon'

    def get_trade_time(self):
        return self.getSecOption(self.defaultSec, 'trade_time')

    def get_replay_time(self):
        return self.getSecOption(self.defaultSec, 'replay_time')
