# -*- coding:utf-8 -*-


class TraderError(Exception):
    """交易错误、异常"""
    pass


class ConfigError(Exception):
    """读写配置文件错误"""
    pass


class StrategyError(Exception):
    """策略相关异常"""
    pass
