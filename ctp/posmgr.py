# -*- coding:utf-8 -*-


class Position:
    def __init__(self, price, time, volume, direction):
        """
        加仓信息
        :param price: 成交价
        :param time: 时间
        :param volume: 开仓手数
        :param direction: 方向
        """
        self.price = price
        self.time = time
        self.volume = volume
        self.direction = direction


class PositionManager:
    def __init__(self, maxAddPos, logger):
        """
        持仓管理器
        :param maxAddPos: 最大可加仓数
        :param prompt: 调试提示符
        :param logger: 日志接口
        """
        self.logger = logger
        self.maxAddPos = maxAddPos
        # 持仓栈
        self.posStack = []

    def numPositions(self):
        """
        返回当前仓位
        :return: 当前持仓数
        """
        return len(self.posStack)

    def pushPosition(self, time, price, volume=1, direction=None):
        """
        加仓
        :param time: 时间
        :param price: 成交价
        :param volume: 数量
        :param direction: 方向
        :return: 成功为True，否则为False
        """
        if self.numPositions() >= self.maxAddPos:
            self.logger.warn("no more positions are allowed")
            return False

        pos = Position(price, time, volume, direction)
        self.posStack.append(pos)
        self.logger.debug("current %s" % self.numPositions())
        return True

    def popPosition(self, num=None):
        """
        减掉索引对应的仓位
        :param num: 仓位索引（第N次加仓）
        :return: 索引对应的仓位
        """
        try:
            # 标号为None则返回末位仓
            if not num:
                return self.posStack.pop()

            # 否则返回指定仓
            pos = self.posStack.pop(num - 1)
            self.logger.debug("current %s" % self.numPositions())
            return pos
        except IndexError as e:
            self.logger.error("num %s, current %s\n" % (num, self.numPositions()))
            return None

    def valueSum(self, value='price'):
        """
        对所有仓位指定字段求和
        :param value: 指定字段
        :return: 指定字段求和的值
        """
        poses = self.numPositions()
        if poses == 0:
            return 0
        elif poses == 1:
            ret = self.getPosition(1).price
            if value == 'volume':
                ret = self.getPosition(1).volume
            return ret

        # 仓位大于1
        # self.logger.debug("poses: %s" % self.posStack)
        _funcSum = lambda x, y : Position(x.price + y.price, None, 0, None)
        if value == 'volume':
            _funcSum = lambda x, y : Position(0.0, None, x.volume + y.volume, None)

        ret = reduce(_funcSum, self.posStack)
        return ret.price

    def getPosition(self, num):
        """
        返回第num个仓位，num从１开始记。仅返回，不会移除！
        :param num: 仓位索引（第N次加仓）
        :return: 索引对应的仓位
        """
        try:
            return self.posStack[num - 1]
        except IndexError as e:
            self.logger.error("num %s, current %s\n" % (num, self.numPositions()))
            return None

    def empty(self):
        """
        清空持仓
        """
        self.posStack = []

# 测试
def doTest():
    import logging
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('/tmp/test')
    fh.setFormatter(logging.Formatter('%(asctime)s:%(name)s:%(funcName)s:%(lineno)d: <%(levelname)s> %(message)s'))
    logger.addHandler(fh)
    posMgr = PositionManager(3, logger)

    time = '2014-1-13'
    print(posMgr.pushPosition(time, 3666, 2))
    print(posMgr.pushPosition(time, 3677, direction = 0))
    print(posMgr.pushPosition(time, 3688, 3))
    print(posMgr.pushPosition(time, 3699))
    print(posMgr.getPosition(3).price)
    print(posMgr.getPosition(4))

    pos = posMgr.popPosition(1)
    print(pos.price, pos.time, pos.volume, pos.direction)

    while posMgr.numPositions():
        pos = posMgr.popPosition()
        print(pos.price, pos.time, pos.volume, pos.direction)

    pos = posMgr.popPosition()

    # 测试结果
    '''
    True
    True
    True
    False
    3688
    ERR: PositionManager: getPosition: num 4, current 3
     list index out of range
    None
    3666 2014-1-13 2 None
    3688 2014-1-13 3 None
    3677 2014-1-13 1 0
    ERR: PositionManager: getPosition: num None, current 0
     pop from empty list
    '''

if __name__ == '__main__':
    doTest()
