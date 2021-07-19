# -*- coding:utf-8 -*-

import os
from tqsdk import TqAccount, TqAuth
from lib.genconfig import GenConfig
from .globals import CTP_CONFIG_DIR

AUTH_CFG = os.path.join(CTP_CONFIG_DIR, "credentials")


class AuthConfig(GenConfig):
    """账户配置信息"""
    def __init__(self):
        super().__init__(AUTH_CFG)
        self.shinny_sec = "shinnytech"
        self.broker_sec = "broker"

    def get_shinny_account(self):
        return self.getSecOption(self.shinny_sec, 'account')

    def get_shinny_passwd(self):
        return self.getSecOption(self.shinny_sec, 'passwd')

    def get_broker_id(self):
        return self.getSecOption(self.broker_sec, 'broker_id')

    def get_broker_account_id(self):
        return self.getSecOption(self.broker_sec, 'account_id')

    def get_broker_password(self):
        return self.getSecOption(self.broker_sec, 'password')


class ApiAuth(object):
    def __init__(self):
        self.login_cfg = AuthConfig()

    def get_account(self):
        account = TqAccount(self.login_cfg.get_broker_id(), self.login_cfg.get_broker_account_id(),
                            self.login_cfg.get_broker_password())
        return account

    def get_auth(self):
        auth = TqAuth(self.login_cfg.get_shinny_account(), self.login_cfg.get_shinny_passwd())
        return auth
