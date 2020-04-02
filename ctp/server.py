# -*- coding:utf-8 -*-

import socket
import json
import traceback
import logging
import threading
import time
import multiprocessing as mp


class Instrument(object):

    STANDBY = 0
    RUNNING = 1
    EXCEPTION = 2
    FATAL = 3
    FINISHED = 4

    def __init__(self):
        self.lock = threading.Lock()
        self.name = ''
        self.strategy = None
        self.arguments = None
        self.proc = None
        self.status = -1


class CtpServer(object):
    """

    """
    SRV_IP = '127.0.0.1'
    SRV_PORT = 9900
    CMD_BUF_LEN = 4096

    def __init__(self, log_dir):
        """

        :param log_dir:
        """
        self.active = self.getServer()
        self.logger = logging.basicConfig()
        #
        self.active = {}
        self.activeLock = threading.Lock()
        self.suspend = False

    def getServer(self):
        return True

    def __procTrader(self, instrument, strategy, arguments):
        pass

    def __startInstrument(self, instr):
        ret = 1
        instr.lock.acquire()
        if instr.proc:
            self.logger.warn("合约 %s：" % ("运行中" if instr.proc.is_alive() else "未结束"))
            instr.lock.release()
            return ret

        try:
            _proc = mp.Process(target=self.__procTrader, args=(instr.name, instr.strategy, instr.arguments))
            _proc.start()
            instr.proc = _proc
            instr.status = Instrument.RUNNING
            self.logger.log("合约已开始: %s" % instr.name)
            ret = 0
        except Exception as e:
            self.logger.error("出现异常: %s" % traceback.format_exc(e))
        finally:
            instr.lock.release()
        return ret

    def __stopInstrument(self, instr):
        ret = 1
        instr.lock.acquire()
        if not instr.proc:
            self.logger.log("合约未在运行: %s" % instr.name)
            instr.lock.release()
            return ret

        try:
            if instr.proc.is_alive():
                instr.proc.terminate()
            instr.proc.join()
            self.logger.info("合约已停止: %s" % instr.name)
            ret = 0
        except Exception as e:
            self.logger.error("停止合约出错: %s" % traceback.format_exc(e))
        finally:
            instr.proc = None
            instr.status = Instrument.FINISHED
            instr.lock.release()
            return ret

    def reqInsert(self, args, force=False):
        ret = 1
        self.activeLock.acquire()
        if not force and args['INS'] in self.active:
            self.activeLock.release()
            self.logger.error("已有活动合约: %s" % args['INS'])
            return ret, "已有活动合约"

        instr = Instrument()
        instr.name = args['INS']
        instr.strategy = args['STR']
        instr.arguments = args['ARGS']
        instr.status = Instrument.STANDBY
        self.active[instr.name] = instr
        self.activeLock.release()
        self.logger.log("合约已添加: %s" % args['INS'])
        ret = 0
        return ret, "已添加"

    def reqCancel(self, args):
        ret = 1
        self.activeLock.acquire()
        if args['INS'] not in self.active:
            self.activeLock.release()
            self.logger.error("合约不存在: %s" % args['INS'])
            return ret, "合约不存在"

        instr = self.active[args['INS']]
        self.__stopInstrument(instr)
        del self.active[args['INS']]
        self.activeLock.release()
        self.logger.log("合约已取消: %s" % args['INS'])
        ret = 0
        return ret, "已取消"

    def reqQuery(self, args):
        pass

    def reqControl(self, args):
        pass

    def reqSync(self, args):
        pass

    def __execCmd(self, cmd):
        cmd = json.loads(cmd)
        _cmd = cmd['cmd']
        args = cmd['args']

        ret = None
        if _cmd == 'insert':
            ret, reason = self.reqInsert(args)
        elif _cmd == 'cancel':
            ret, reason = self.reqCancel(args)
        elif _cmd == 'query':
            ret, reason = self.reqQuery(args)
        elif _cmd == 'control':
            ret, reason = self.reqControl(args)
        elif _cmd == 'sync':
            ret, reason = self.reqSync(args)
        else:
            reason = "未知的命令"
            self.logger.error("%s '%s'" % (reason, _cmd))
        return ret, reason

    def __thrRspCmd(self, sock, cmd, addr):
        ret, reason = self.__execCmd(cmd)
        response = {'ret': ret, 'reason': reason}
        response = json.dumps(response)
        sock.sendto(response, addr)

    def onRspCmd(self, sock, cmd, addr):
        rsp = threading.Thread(target=self.__thrRspCmd, args=(sock, cmd, addr))
        rsp.start()

    def inTradeSession(self, instr_name=None):
        now = time.localtime()
        _now = time.struct_time((1970, 1, 1, now.tm_hour, now.tm_min, now.tm_sec, 0, 0, 0))
        if time.struct_time(1970, 1, 1, 8, 50, 1, 0, 0, 0) <= _now < time.struct_time((1970, 1, 1, 15, 5, 0, 0, 0, 0)) \
            or time.struct_time(1970, 1, 1, 20, 50, 0, 0, 0, 0) <= _now < time.struct_time(1970, 1, 1, 24, 0, 0, 0, 0, 0) \
            or time.struct_time(1970, 1, 1, 0, 0, 0, 0, 0, 0) <= _now < time.struct_time(1970, 1, 1, 2, 35, 0, 0, 0, 0):
            return True
        else:
            return False

    def inTradingDay(self):
        pass

    def __handleException(self, instr):
        pass

    def __thrFresh(self):
        while 1:
            # 非交易时段
            if not self.inTradeSession():
                if not self.suspend:
                    self.activeLock.acquire()
                    nr_standby = 0
                    for name, instr in self.active.items():
                        if instr.status == Instrument.STANDBY:
                            nr_standby += 1
                        elif instr.status == Instrument.RUNNING:
                            self.__stopInstrument(instr)
                        elif instr.status in [Instrument.EXCEPTION, Instrument.FATAL]:
                            self.__handleException(instr)
                        else: # FINISHED
                            instr.lock.acquire()
                            instr.status = Instrument.STANDBY
                            instr.proc = None
                            instr.lock.release()
                            nr_standby += 1

                    if nr_standby == len(self.active):
                        self.suspend = True
                    self.activeLock.release()

                time.sleep(10)
                continue

            # 交易时段但非交易日
            if not self.inTradingDay():
                time.sleep(10)
                continue

            # 处于交易时段
            self.activeLock.acquire()
            for name, instr in self.active.items():
                if instr.status == Instrument.STANDBY:
                    self.__startInstrument(instr)
                elif instr.status in [Instrument.EXCEPTION, Instrument.FATAL]:
                    self.__handleException(instr)
            self.activeLock.release()

            self.suspend = False  # 确保进入非交易时段后会继续监控合约的结束状态
            time.sleep(1)

    def __daemon(self, fd):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
            sock.bind((CtpServer.SRV_IP, CtpServer.SRV_PORT))
            #
            fresh = threading.Thread(target=self.__thrFresh)
            fresh.start()

            while 1:
                cmd, addr = sock.recvfrom(CtpServer.CMD_BUF_LEN)
                self.logger.debug('received %s cmd %s' % (addr, cmd))
                self.onRspCmd(sock, cmd, addr)

        except Exception as e:
            self.logger.error("error")
            return 1

    def start(self):
        ret = 0
        if self.active:
            return ret, "已启动"

        daemon = mp.Process(target=self.__daemon, args=())
        daemon.start()
        return ret, "启动成功"


class CtpClient(object):
    def __init__(self):
        pass

    def insert(self, param, force=False):
        ret = 1
        if not self.active:
            return ret
        return 0

    def list(self):
        return 0

    def send(self):
        pass