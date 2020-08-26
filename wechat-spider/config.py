# -*- coding: utf-8 -*-
'''
Created on 2019/5/18 11:54 AM
---------
@summary:
---------
@author:
'''
import os
import socket
import sys
import shutil

import yaml  # pip3 install pyyaml

if 'python' in sys.executable:
    abs_path = lambda file: os.path.abspath(os.path.join(os.path.dirname(__file__), file))
else:
    abs_path = lambda file: os.path.abspath(os.path.join(os.path.dirname(sys.executable), file))  # mac 上打包后 __file__ 指定的是用户根路径，非当执行文件路径

if not os.path.exists('./config/config.yaml'):
    shutil.copyfile('./config.yaml', './config/config.yaml')

config = yaml.full_load(open(abs_path('./config/config.yaml'), encoding='utf8'))


def get_host_ip():
    """
    利用 UDP 协议来实现的，生成一个UDP包，把自己的 IP 放如到 UDP 协议头中，然后从UDP包中获取本机的IP。
    这个方法并不会真实的向外部发包，所以用抓包工具是看不到的
    :return:
    """
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        if s:
            s.close()

    return ip


IP = get_host_ip()
