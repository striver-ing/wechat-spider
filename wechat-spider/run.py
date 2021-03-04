# -*- coding: utf-8 -*-
'''
Created on 2019/5/18 9:52 PM
---------
@summary:
---------
@author:
'''

from core.capture_packet import WechatCapture
from create_tables import create_table
from mitmproxy import options
from mitmproxy import proxy
from mitmproxy.tools.dump import DumpMaster
from config import config, IP


def start():
    ip = IP
    port = config.get('spider').get('service_port')

    print("温馨提示：服务IP {} 端口 {} 请确保代理已配置".format(ip, port))

    myaddon = WechatCapture()
    opts = options.Options(listen_port=port)
    pconf = proxy.config.ProxyConfig(opts)
    m = DumpMaster(opts)
    m.options.set('flow_detail={mitm_log_level}'.format(mitm_log_level=config.get('mitm').get('log_level')))
    m.server = proxy.server.ProxyServer(pconf)
    m.addons.add(myaddon)

    try:
        m.run()
    except KeyboardInterrupt:
        m.shutdown()


create_table()
start()
