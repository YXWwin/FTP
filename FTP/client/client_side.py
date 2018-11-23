#!/usr/bin/env python
# _*_ coding:utf-8 _*_
# Author:Mr.yang
import hashlib
import socket
import struct
import json
import time
import sys
import os

class MYTCPClient:
    address_family = socket.AF_INET

    socket_type = socket.SOCK_STREAM

    max_packet_size = 8096

    request_queue_size = 5

    upload_dir = r'%s\upload' %(os.path.dirname(os.path.abspath(__file__))) # 上传目录的绝对路径

    download_dir = r'%s\download' %(os.path.dirname(os.path.abspath(__file__))) # 上传目录的绝对路径

    def __init__(self, client_address):
        self.client_address = client_address
        self.socket = socket.socket(self.address_family, self.socket_type)
        self.connect()

    def connect(self):
        """与服务端进行双管链接"""
        try:
            self.socket.connect(self.client_address)
        except Exception:
            exit('\033[1;31m服务端还未启动\033[0m')

    def run(self):
        """将用户信息交给服务端，接收结果"""
        print('\033[1;31m最大并发数为2\033[0m')
        print('\033[1;31m用户名：yang 密码：123\033[0m')
        print('\033[1;31m用户名：hang 密码：123\033[0m')
        print('\033[1;31m用户名：liu 密码：123\033[0m')
        while True:
            username = input('Username:').strip()
            password = input('Password:').strip()
            user_data = {
                'username' : username,
                'password' : password
            }
            user_json = json.dumps(user_data)
            user_bytes = user_json.encode('utf-8')
            self.socket.send(user_bytes)
            result = self.socket.recv(self.max_packet_size).decode('utf-8')
            if result == 'yes':
                print('\033[1;31m--------welcome--------\033[0m')
                print('\033[1;31m1.上传文件： geta.txt\033[0m')
                print('\033[1;31m2.下载文件： puta.txt\033[0m')
                print('\033[1;31m3.切换目录： cd photo\033[0m')
                print('\033[1;31m4.增加目录： add fang\033[0m')
                print('\033[1;31m5.查看所在目录下的所有文件: ls\033[0m')
                self.conroller()
            elif result == 'no':
                print('wrong username and password!')

    def close(self):
        self.socket.close()

    def file_md5(self, filepath):
        """读取文件变成bytes类型，进行md5处理"""
        with open(filepath, 'rb') as f:
            filedata = f.read()
            return hashlib.md5(filedata).hexdigest()

    def progress_bar(self,data):
        """接收上传文件大小，总文件大小，进行进度条处理"""
        a = int(data.split(',')[0]) #上传文件大小
        b = int(data.split(',')[1]) #总文件大小
        c = round(a/b *10,1) * 10
        if c == 0:
            pass
        else:
            sys.stdout.write('\r')
            sys.stdout.write("%s%% |%s" % (int(c), int(c) * '#'))
            sys.stdout.flush()
            time.sleep(0.01)

    def put(self,data):
        """上传文件
        1.判断文件是否存在，发送结果到服务端
        2.制作固定报头
        3.发送报头长度
        4.发送报头
          4.1接收服务端发来的磁盘结果
            4.1.1接收的信息为 0 用户磁盘空间不足
            4.1.2没有接收信息为 1 的话,将文件数据发送
            4.1.3接收的服务端发来的文件结果
                 4.2.1接收的信息为1,说明文件存在，让用户选择是否断点续传
                 4.2.2接收的信息为0,说明文件不存在，
                 4.2.3 发送文件数据
                 4.2.4 进度条处理
                 4.2.4 接受结果为1上传成功
        """
        cmd = data[0]
        filename = data[1]
        filepath = "%s\%s" %(self.upload_dir, filename) # 文件路径
        if os.path.exists(filepath):
            self.socket.send(struct.pack('i', 1))
            filesize = os.path.getsize(filepath)  # 文件大小
            file_data = {
                'cmd': cmd,
                'filename': filename,
                'filesize': filesize,
                'md5': self.file_md5(filepath)
            }
            file_json = json.dumps(file_data)
            file_bytes = file_json.encode('utf-8')
            file_struct = struct.pack('i', len(file_bytes))
            self.socket.send(file_struct)  # 发送报头长度
            self.socket.send(file_bytes)   # 发送报头

            disk_result = struct.unpack('i', self.socket.recv(4))[0]
            if disk_result:
                file_result = struct.unpack('i', self.socket.recv(4))[0]
                if file_result:
                    choise = input('是否进行断点续传(Y/N):')
                    if choise == 'Y' or 'y':
                        num = int(struct.unpack('i', self.socket.recv(4))[0])
                    elif choise == 'N' or 'n':
                        num = 0
                else:
                    num = 0
                with open(filepath,'rb') as f:
                    f.seek(num)
                    for line in f:
                        self.socket.send(line)
                        data = self.socket.recv(self.max_packet_size).decode('utf-8')
                        self.progress_bar(data) # 进度条处理

                md5_result = struct.unpack('i', self.socket.recv(4))[0]
                if md5_result:
                    print('上传成功')
                else:
                    print('上传失败')
            else:
                print('\033[1;31m您的磁盘空间不足\033[0m')
        else:
            print('\033[1;31m文件不存在\033[0m')
            self.socket.send(struct.pack('i', 0))

    def get(self, data):
        """
        1.接收判断文件信息的结果
          1.1 接收结果为 yes
          1.2 接收报头长度
          1.3 接收报头
          1.4 接收服务端发来文件数据
          1.5 用md5 判断服务端发来的文件信息是否完整
        """
        result = struct.unpack('i', self.socket.recv(4))[0]
        if result:
            try:
                header_size = struct.unpack('i', self.socket.recv(4))[0]  # 报头长度
                header_bytes = self.socket.recv(header_size)  # 接收报头
                header_json = json.loads(header_bytes)  # 文件信息
                recv_size = 0
                user_file_path = '%s\%s' % (self.download_dir, header_json['filename'])  # 用户客户端的文件目录

                if os.path.exists(user_file_path):
                    filesize = os.path.getsize(user_file_path)
                    total_size = header_json['filesize'] - filesize
                    self.socket.send(struct.pack('i', 1))
                    self.socket.send(str(filesize).encode('utf-8'))
                else:
                    self.socket.send(struct.pack('i', 0))
                    total_size = header_json['filesize']

                with open(user_file_path, 'ab') as f:
                    while recv_size < total_size:
                        res = self.socket.recv(self.max_packet_size)
                        f.write(res)
                        recv_size += len(res)
                        self.progress_bar('%s,%s' %(recv_size,total_size))
                if header_json['md5'] == self.file_md5(user_file_path):
                    print('下载成功')
                else:
                    print('下载失败')
            except:
                print('文件下载失败')
        else:
            print('\033[1;31m文件不存在\033[0m')

    def lis(self,data):
        catalog = data[0]
        file = data[1]
        if catalog or file:
            for i in catalog:
                if i:
                    print('目录',i)
                else:
                    pass
            for i in file:
                if i:
                    print('文件',i)
                else:
                    pass
        else:
            print('该目录下没有文件')

    def ls(self,data):
        """查看当前目录的所有文件"""
        catalog_name = self.socket.recv(self.max_packet_size).decode('utf-8')
        catalog_result = self.socket.recv(self.max_packet_size).decode('utf-8')
        print('\033[1;31m----目录%s的所有文件如下----\033[0m' %catalog_name)
        if catalog_result :
            catalog = self.socket.recv(self.max_packet_size)
            self.lis(json.loads(catalog))
        else:
            print('\033[1;31m当前目录没有文件\033[0m')

    def add(self,data):
        """增加目录"""
        self.socket.send(data[1].encode('utf-8'))

    def cd(self,data):
        """切换目录"""
        self.socket.send(data[1].encode('utf-8'))
        result = struct.unpack('i', self.socket.recv(4))[0]
        if result:
            print('成功切换到%s目录' %data[1])
        else:
            print('\033[1;31m没有%s目录\033[0m' %data[1])

    def q(self,data):
        exit()

    def conroller(self):
        """
        与服务端进行信息交互，
        将命令发送到服务端
        1.上传文件： get a.txt
        2.下载文件： put a.txt
        3.切换目录： cd photo
        4.增加目录： add fang
        3.查看所在目录下的所有文件: ls
        """
        while True:
            try:
                inp = input('>>(q退出):').strip() # 输入命令
                if not inp: continue
                if inp != 'q':
                    self.socket.send(inp.encode('utf-8'))
                    data = inp.split()  # ['put','a.txt']
                    cmd = data[0]
                    if hasattr(self, cmd):
                        func = getattr(self, cmd)
                        func(data)
                    else:
                        print('\033[1;31m输入的命令错误\033[0m')
                else:
                    exit()
            except Exception:
                self.socket.close()
                exit()


if __name__ == '__main__':
    obj = MYTCPClient(('127.0.0.1', 8060))
    obj.run()
    obj.close()