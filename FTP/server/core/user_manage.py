#!/usr/bin/env python
# _*_ coding:utf-8 _*_
# Author:Mr.yang
from conf.settings import USERINFO
from conf.settings import USERDATA
import configparser
import hashlib
import os

class user_process:
    def __init__(self):
        self.conf = configparser.ConfigParser()
        self.conf.read(USERINFO)

    def pas_md5(self, pas):
        """将用户密码变成MD5值"""
        m = hashlib.md5()
        m.update(bytes(pas, encoding='utf-8'))
        return m.hexdigest()

    def user_add(self, name, pas, disk):
        """将用户的所有信息写入到user_info.ini当中"""
        user_file = 'db\%s' %name
        user_pas = self.pas_md5(pas)
        if name not in self.conf.sections():
            self.conf.add_section(name)
            self.conf[name]['disk_space'] = disk
            self.conf[name]['file_path'] = user_file
            self.conf[name]['password'] = user_pas
            self.conf.write(open(USERINFO, 'w'))
            os.makedirs('%s/%s' %(USERDATA, name))
            print('创建用户%s成功' %name)
        else:
            print('您输入的用户已存在')

    def user_judge(self, name, pas):
        """判断用户的信息是否正确"""
        if name in self.conf.sections():
            if self.pas_md5(pas) == self.conf[name]['password']:
                return 'yes'
            else:
                return 'no'
        else:
            return 'no'


    def user_disk(self, name):
        """返回用户的剩余磁盘空间"""
        size = 0 #服务端用户目录中所有文件的大小
        for root, dirs, files in os.walk('%s/%s' % (USERDATA, name)):
            for f in files:
                size += os.path.getsize(os.path.join(root, f))
        free_space = int(self.conf[name]['disk_space']) - int(size)
        return free_space