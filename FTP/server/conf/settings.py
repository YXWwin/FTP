#!/usr/bin/env python
# _*_ coding:utf-8 _*_
# Author:Mr.yang
import os
DB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

USERDATA = os.path.join(DB_PATH, 'db') # 服务端储存用户文件
USERINFO = os.path.join(DB_PATH, 'db', 'user_info.ini') # 用户配置文件的绝对路径


