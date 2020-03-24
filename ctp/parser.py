# -*- coding:utf-8 -*-

import sys
import ctp.server as server

from optparse import OptionParser


class CtpParser(object):
    def __init__(self):
        pass

    def run(self, options):
        """

        :param options:
        :return:
        """
        cs = server.CtpServer()
        if options.start:
            ret, err = cs.start()
            if ret:
                print("启动服务失败： %s" % err)
            return ret

        if options.insert:
            ret, err = cs.insert(options.param, options.force)
            if ret:
                print("添加合约失败： %s" % err)
                return ret

        if options.list:
            cs.list()

        return 0


def run():
    """
    命令解析入口
    """
    parser = OptionParser()
    parser.add_option('-s', '--start', action="store_true", dest='start',
            help='Start the ctp server.')
    parser.add_option('-i', '--insert', dest='insert',
            help='Add instruments to trade to ctp server.')
    parser.add_option('-f', '--force', dest='force',
            help='Forcibly override the existing instruments on ctp server with the inserted one.')
    parser.add_option('-p', '--param', dest='param',
            help='Parameters for strategy in readable format, or a json file including strategy parameters.')
    parser.add_option('-l', '--list', action="store_true", dest='list',
            help='List the instruments on ctp server.')
    (options, args) = parser.parse_args()

    cp = CtpParser()
    return cp.run(options)

