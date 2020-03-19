#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import os
import sys
import traceback
sys.path.append(os.path.dirname(__file__))

try:
    if len(sys.argv) < 2:
        sys.exit(0)

    _module = '.'.join([sys.argv[1], 'parser'])
    mod = __import__(_module)
except (ImportError, ModuleNotFoundError) as e:
    print("未发现指定命令模块： '%s'" % sys.argv[1])
    sys.exit(1)

try:
    ret = mod.parser.run()
except Exception as e:
    print(traceback.format_exc())
    ret = 1
finally:
    sys.exit(ret)