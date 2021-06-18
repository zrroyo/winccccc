#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import os
import sys
import traceback
sys.path.append(os.path.dirname(__file__))

_help_info = f"""
{os.path.basename(sys.argv[0])} : at least one sub-command listed below is required.
    ctp     --- Start CTP trading.
    md      --- Receive market data.
"""

try:
    ret = 0
    if len(sys.argv) < 2:
        print(_help_info)
        sys.exit(ret)

    _module = '.'.join([sys.argv[1], 'parser'])
    mod = __import__(_module)
    ret = mod.parser.run()
except (ImportError, ModuleNotFoundError) as e:
    print(f"未发现指定命令模块： {sys.argv[1]}")
    ret = 1
except Exception as e:
    print(traceback.format_exc())
    ret = 1
finally:
    sys.exit(ret)
