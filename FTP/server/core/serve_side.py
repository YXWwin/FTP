#!/usr/bin/env python
# _*_ coding:utf-8 _*_
# Author:Mr.yang
from core.user_manage import user_process
from conf.settings import USERDATA
from threading import Thread
import queue
import hashlib
import socket
import struct
import json
import os


class MYTCPServer:
    server_address = ('127.0.0.1', 8060)

    socket_type = socket.SOCK_STREAM

    address_family = socket.AF_INET

    maximum_concurrent_number = 2

    request_queue_size = 5

    max_packet_size = 8096

    coding = 'utf-8'

    server_dir = {}

    def __init__(self):
        self.socket = socket.socket(self.address_family, self.socket_type)
        self.queue = queue.Queue(self.maximum_concurrent_number)
        self.bind()
        self.listen()

    def server_close(self):
        self.socket.close()

    def bind(self):
        """与客户端进行双管链接"""
        self.socket.bind(self.server_address)

    def listen(self):
        """设置最大链接数"""
        self.socket.listen(self.request_queue_size)

    def file_md5(self, file_path):
        """读取文件，变成bytes类型，之后进行md5"""
        with open(file_path, 'rb') as f:
            file_data = f.read()
            return hashlib.md5(file_data).hexdigest()

    def server_accept(self):
        """链接客户端"""
        while True:
            print('setting...')
            conn, client_addr = self.socket.accept()
            print('客户端地址:',client_addr)
            try:
                t = Thread(target=self.run, args=(conn,))
                self.queue.put(t)
                t.start()
            except Exception:
                conn.close()
                self.queue.get()

    def run(self, conn):
        """
        用户验证
        1.将接收的用户信息交给,user_manage中的user_judge进行处理
        2.用户登录成功，则运用concoller对客户端发来的命令进行处理
        """
        print('\033[1;31m--------welcome--------\033[0m')
        while True:
            try:
                user_json = conn.recv(self.max_packet_size)
                user_data = json.loads(user_json)
                username = user_data['username']
                password = user_data['password']

                user_obj = user_process()
                result = user_obj.user_judge(username, password) # 获取到用户验证的信息的结果
                conn.send(bytes(result, encoding='utf-8')) # 将结果发送给客户端
                if result == 'yes':
                    self.server_dir[username] = '%s\%s' %(USERDATA,username)
                    self.conroller(conn,username)
                else:
                    print('用户%s的密码或用户名错误' %(username))
            except Exception:
                conn.close()
                self.queue.get()
                break

    def disk(self, conn, header_json, username):
        """对用户的磁盘空间进行判断"""
        file_name = header_json['filename']
        file_size = header_json['filesize']
        user_obj = user_process()
        disk = user_obj.user_disk(username)  # 获取到用户的磁盘配额
        if file_size < disk:
            conn.send(struct.pack('i', 1))
            return 1
        else:
            conn.send(struct.pack('i', 0))
            return 0

    def file_md5(self, filepath):
        """读取文件变成bytes类型，进行md5处理"""

        with open(filepath, 'rb') as f:
            filedata = f.read()
            return hashlib.md5(filedata).hexdigest()


    def put(self, data, conn, username):
        """
        接收上传文件
        1.判断上传的文件是否存在
        2.接收报头长度
        3.接收报头
        4.loads出文件信息
        5.向客户端发送磁盘空间状况
        6.将总文件大小，接收文件大小发送到客户端
        7.用md5 判断客户端发来的文件信息是否完整
        """
        file_result = struct.unpack('i', conn.recv(4))[0]
        if file_result:
            header_size = struct.unpack('i', conn.recv(4))[0]  # 接收报头长度
            header_bytes = conn.recv(header_size)   # 接收报头
            header_json = json.loads(header_bytes)  # 文件信息

            user_file_path = '%s\%s' % (self.server_dir[username], header_json['filename'])  # 用户服务端的文件目录

            disk_result = self.disk(conn, header_json, username)
            if disk_result:
                if os.path.exists(user_file_path):
                    filesize = os.path.getsize(user_file_path)

                    total_size = header_json['filesize'] - filesize
                    conn.send(struct.pack('i', 1))
                    conn.send(struct.pack('i', filesize))
                else:
                    conn.send(struct.pack('i', 0))
                    total_size = header_json['filesize']
                recv_size = 0
                with open(user_file_path, 'ab') as f:
                    while recv_size < total_size:
                        # print(recv_size)
                        # print(total_size)
                        res = conn.recv(self.max_packet_size)
                        f.write(res)
                        recv_size += len(res)
                        conn.send(bytes('%s,%s' %(recv_size,total_size),encoding='utf-8')) #发送给客户端进行进度条操作
                if header_json['md5'] == self.file_md5(user_file_path):
                    conn.send(struct.pack('i', 1))
                else:
                    conn.send(struct.pack('i', 0))
            else:
                print('磁盘空间不足')
        else:
            print('\033[1;31m文件不存在\033[0m')

    def get(self, data, conn, username):
        """下载文件
        1.判断文件是否存在
        2.制作固定报头
        3.发送报头长度
        4.发送报头
        5.判断下载的文件是否存在
          5.1 存在的话，判断出已有文件的大小，这个大小用来文件写入的时候指定光标
        5.将文件数据发送到客户端
        """
        filename = data.split()[1]
        filepath = '%s\%s' % (self.server_dir[username],filename)  # 文件的绝对路径
        if os.path.exists(filepath):
            filesize = os.path.getsize(filepath)  # 文件大小
            conn.send(struct.pack('i', 1))
            file_data = {
                'filename': filename,
                'filesize': filesize,
                'md5': self.file_md5(filepath)
            }
            file_json = json.dumps(file_data)
            file_bytes = file_json.encode('utf-8')
            file_struct = struct.pack('i', len(file_bytes))
            conn.send(file_struct)  # 发送报头长度
            conn.send(file_bytes)  # 发送报头

            file_result = struct.unpack('i', conn.recv(4))[0]
            if file_result:
                num = int(struct.unpack('i', conn.recv(4))[0])
            else:
                num = 0
            with open(filepath, 'rb') as f:
                f.seek(num)
                for line in f:
                    conn.send(line)
        else:
            conn.send(struct.pack('i', 0))

    def ls(self, data, conn, username):
        """查看当前目录的所有文件"""
        catalog_name = self.server_dir[username].split('\\')[-1]
        conn.send(catalog_name.encode('utf-8'))
        file_data = None
        for files in os.walk(self.server_dir[username]):
            file_data = files[1:]
            break
        if file_data:
            conn.send(struct.pack('i', 1))
            file_bytes = json.dumps(file_data).encode('utf-8')
            conn.send(file_bytes)
        else:
            conn.send(struct.pack('i', 0))
            print('当前目录没有文件')

    def cd(self, data, conn, username):
        """切换目录"""
        catalog_name = conn.recv(self.max_packet_size).decode('utf-8')
        if os.path.exists('%s\%s'%(self.server_dir[username], catalog_name)):
            conn.send(struct.pack('i', 1))
            self.server_dir[username] = '%s\%s'%(self.server_dir[username], catalog_name)
        else:
            conn.send(struct.pack('i', 0))

    def add(self, data, conn, username):
        """创建目录"""
        catalog_name = conn.recv(self.max_packet_size).decode('utf-8')
        catalog_path = '%s/%s' %(self.server_dir[username], catalog_name)
        if os.path.exists(catalog_path):
            print('目录已存在')
        else:
            os.makedirs(catalog_path)

    def conroller(self, conn, username):
        """
        与客户端进行信息交互，
        接受服务端发来的命令
        1.上传文件： get a.txt
        2.下载文件： put a.txt
        3.切换目录： cd photo
        3.查看所在目录下文件: ls
        """
        while True:
            data = conn.recv(self.max_packet_size).decode('utf-8')
            if data:
                print('客户端的命令:', data)
                cmd = data.split()[0]
                if not cmd:
                    continue
                if hasattr(self, cmd):
                    func = getattr(self, cmd)
                    func(data, conn, username)
                else:
                    print('\033[1;31m输入的命令错误\033[0m')
            else:
                exit()

obj = MYTCPServer()












