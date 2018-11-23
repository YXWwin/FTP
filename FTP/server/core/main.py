#!/usr/bin/env python
# _*_ coding:utf-8 _*_
# Author:Mr.yang
from core.user_manage import user_process
from core.serve_side import obj

class main:
    def __init__(self):
        pass

    def create_user(self):
        """创建用户"""
        username = input('Username:').strip()
        password = input('Password:').strip()
        disk_num = input('disk_num:').strip()
        user_obj = user_process()
        user_obj.user_add(username, password, disk_num)

    def start_server(self):
        """启动服务端"""
        obj.server_accept()

    def quit(self):
        """退出"""
        exit()

    def runn(self):
        info = ['1.创建用户', '2.启动服务端', '3.退出']
        function_info = {'1': 'create_user', '2': 'start_server', '3': 'quit'}
        for i in info:print(i)
        while True:
            choise = input('>>:').strip()
            if choise in function_info:
                getattr(self,function_info[choise])()
            else:
                print('您输入有误请重新输入')


