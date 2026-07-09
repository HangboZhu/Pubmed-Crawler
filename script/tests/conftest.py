import os
import sys

# 让 tests 能 import script 目录下的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
