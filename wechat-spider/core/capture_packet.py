# -*- coding: utf-8 -*-
'''
Created on 2019/5/8 10:59 PM
---------
@summary:
---------
@author:
'''
import re

import mitmproxy
from mitmproxy import ctx

from core.deal_data import deal_data


class WechatCapture():

    def response(self, flow: mitmproxy.http.HTTPFlow):
        url = flow.request.url

        next_page = None
        try:
            if 'mp/profile_ext?action=home' in url or 'mp/profile_ext?action=getmsg' in url:  # 文章列表 包括html格式和json格式

                ctx.log.info('抽取文章列表数据')
                next_page = deal_data.deal_article_list(url, flow.response.text)

                flow.response.text = re.sub('<img.*?>', '', flow.response.text)

            elif '/s?__biz=' in url or '/mp/appmsg/show?__biz=' in url or '/mp/rumor' in url:  # 文章内容；mp/appmsg/show?_biz 为2014年老版链接;  mp/rumor 是不详实的文章

                ctx.log.info('抽取文章内容')
                next_page = deal_data.deal_article(url, flow.response.text)

                # 修改文章内容的响应头，去掉安全协议，否则注入的 < script > setTimeout(function() {window.location.href = 'url';}, sleep_time); < / script > js脚本不执行
                flow.response.headers.pop('Content-Security-Policy', None)
                flow.response.headers.pop('content-security-policy-report-only', None)
                flow.response.headers.pop('Strict-Transport-Security', None)

                #  不缓存
                flow.response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

                # 去掉图片
                flow.response.text = re.sub('<img.*?>', '', flow.response.text)

            elif 'mp/getappmsgext' in url:  # 阅读量 观看量

                ctx.log.info('抽取阅读量 观看量')
                deal_data.deal_article_dynamic_info(flow.request.data.content.decode('utf-8'), flow.response.text)

            elif '/mp/appmsg_comment' in url:  # 评论列表

                ctx.log.info('抽取评论列表')
                deal_data.deal_comment(url, flow.response.text)

        except Exception as e:
            # log.exception(e)
            next_page = "Exception: {}".format(e)

        if next_page:
            # 修改请求头 json 为text
            flow.response.headers['content-type'] = 'text/html; charset=UTF-8'
            if 'window.location.reload()' in next_page:
                flow.response.set_text(next_page)
            else:
                flow.response.set_text(next_page + flow.response.text)


addons = [
    WechatCapture(),
]

# 运行  mitmdump -s capture_packet.py -p 8080
