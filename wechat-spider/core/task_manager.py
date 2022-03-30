# -*- coding: utf-8 -*-
"""
Created on 2019/5/15 11:14 PM
---------
@summary:
---------
@author:
"""

import random

import utils.tools as tools
from config import config
from db.mysqldb import MysqlDB
from db.redisdb import RedisDB
from utils.log import log


class TaskManager:
    IS_IN_TIME_RANGE = 1  # 在时间范围
    NOT_REACH_TIME_RANGE = 2  # 没到达时间范围
    OVER_MIN_TIME_RANGE = 3  # 超过时间范围

    def __init__(self):

        self._mysqldb = MysqlDB(**config.get("mysqldb"))
        self._redis = RedisDB(**config.get("redisdb"))

        self._task_root_key = config.get("spider").get("redis_task_cache_root_key")

        self._account_task_key = self._task_root_key + ":z_account_task"
        self._article_task_key = self._task_root_key + ":z_article_task"
        self._last_article_publish_time = (
            self._task_root_key + ":h_last_article_publish_time"
        )
        self._new_last_article_publish_time = (
            self._task_root_key + ":h_new_last_article_publish_time"
        )

        self._ignore_haved_crawl_today_article_account = config.get("spider").get(
            "ignore_haved_crawl_today_article_account"
        )
        self._monitor_interval = config.get("spider").get("monitor_interval")
        self._zombie_account_not_publish_article_days = config.get("spider").get(
            "zombie_account_not_publish_article_days"
        )
        self._spider_interval_min = (
            config.get("spider").get("spider_interval").get("min_sleep_time")
        )
        self._spider_interval_max = (
            config.get("spider").get("spider_interval").get("max_sleep_time")
        )
        self._spider_interval_max = (
            config.get("spider").get("spider_interval").get("max_sleep_time")
        )
        self._crawl_time_range = (
            config.get("spider").get("crawl_time_range") or "~"
        ).split("~")
        self._crawl_article = config.get("spider").get("crawl_article")

    def __get_task_from_redis(self, key):
        task = self._redis.zget(key, is_pop=True)
        if task:
            task = eval(task[0])
            return task

    def __random_int(self, min, max):
        pass

    def get_account_task(self):
        """
        获取公众号任务
        :return:
            {'__biz': 'Mjc1NjM3MjY2MA==', 'last_publish_time': None}
            或
            None
        """
        task = self.__get_task_from_redis(self._account_task_key)
        if not task:
            publish_time_condition = (
                "AND last_publish_time < '{today}'".format(
                    today=tools.get_current_date(date_format="%Y-%m-%d" + " 00:00:00")
                )
                if self._ignore_haved_crawl_today_article_account
                else ""
            )
            sql = """
                SELECT
                    __biz,
                    last_publish_time
                FROM
                    wechat_account_task
                WHERE
                    `is_zombie` != 1
                AND (
                    (
                        (
                            UNIX_TIMESTAMP(CURRENT_TIMESTAMP) - UNIX_TIMESTAMP(last_spider_time)
                        ) > {monitor_interval}
                        {publish_time_condition}
                    )
                    OR (last_publish_time IS NULL)
                )
                """.format(
                monitor_interval=self._monitor_interval,
                publish_time_condition=publish_time_condition,
            )

            tasks = self._mysqldb.find(sql, to_json=True)
            if tasks:
                self._redis.zadd(self._account_task_key, tasks)
                task = self.__get_task_from_redis(self._account_task_key)

        return task

    def get_article_task(self):
        """
        获取文章任务
        :return:
            {'article_url': 'http://mp.weixin.qq.com/s?__biz=MzIxNzg1ODQ0MQ==&mid=2247485501&idx=1&sn=92721338ddbf7d907eaf03a70a0715bd&chksm=97f220dba085a9cd2b9a922fb174c767603203d6dbd2a7d3a6dc41b3400a0c477a8d62b96396&scene=27#wechat_redirect'}
            或
            None
        """
        task = self.__get_task_from_redis(self._article_task_key)
        if not task:
            sql = "select id, article_url from wechat_article_task where state = 0 limit 5000"
            tasks = self._mysqldb.find(sql)
            if tasks:
                # 更新任务状态
                task_ids = str(tuple([task[0] for task in tasks])).replace(",)", ")")
                sql = "update wechat_article_task set state = 2 where id in %s" % (
                    task_ids
                )
                self._mysqldb.update(sql)

            else:
                sql = "select id, article_url from wechat_article_task where state = 2 limit 5000"
                tasks = self._mysqldb.find(sql)

            if tasks:
                task_json = [{"article_url": article_url} for id, article_url in tasks]
                self._redis.zadd(self._article_task_key, task_json)
                task = self.__get_task_from_redis(self._article_task_key)

        return task

    def update_article_task_state(self, sn, state=1):
        sql = 'update wechat_article_task set state = %s where sn = "%s"' % (state, sn)
        self._mysqldb.update(sql)

    def record_last_article_publish_time(self, __biz, last_publish_time):
        self._redis.hset(
            self._last_article_publish_time, __biz, last_publish_time or ""
        )

    def is_reach_last_article_publish_time(self, __biz, publish_time):
        last_publish_time = self._redis.hget(self._last_article_publish_time, __biz)
        if not last_publish_time:
            # 查询mysql里是否有该任务
            sql = (
                "select last_publish_time from wechat_account_task where __biz = '%s'"
                % __biz
            )
            data = self._mysqldb.find(sql)
            if data:  # [(None,)] / []
                last_publish_time = str(data[0][0] or "")
                self.record_last_article_publish_time(__biz, last_publish_time)

        if last_publish_time is None:
            return

        if publish_time < last_publish_time:
            return True

        return False

    def is_in_crawl_time_range(self, publish_time):
        """
        是否在时间范围
        :param publish_time:
        :return: 是否达时间范围
        """
        if not publish_time or (
            not self._crawl_time_range[0] and not self._crawl_time_range[1]
        ):
            return TaskManager.IS_IN_TIME_RANGE

        if self._crawl_time_range[0]:  # 时间范围 上限
            if publish_time > self._crawl_time_range[0]:
                return TaskManager.NOT_REACH_TIME_RANGE

            if (
                publish_time <= self._crawl_time_range[0]
                and publish_time >= self._crawl_time_range[1]
            ):
                return TaskManager.IS_IN_TIME_RANGE

        if publish_time < self._crawl_time_range[1]:  # 下限
            return TaskManager.OVER_MIN_TIME_RANGE

        return TaskManager.IS_IN_TIME_RANGE

    def record_new_last_article_publish_time(self, __biz, new_last_publish_time):
        self._redis.hset(
            self._new_last_article_publish_time, __biz, new_last_publish_time
        )

    def get_new_last_article_publish_time(self, __biz):
        return self._redis.hget(self._new_last_article_publish_time, __biz)

    def update_account_last_publish_time(self, __biz, last_publish_time):
        sql = 'update wechat_account_task set last_publish_time = "{}", last_spider_time="{}" where __biz="{}"'.format(
            last_publish_time, tools.get_current_date(), __biz
        )
        self._mysqldb.update(sql)

    def is_zombie_account(self, last_publish_timestamp):
        if (
            tools.get_current_timestamp() - last_publish_timestamp
            > self._zombie_account_not_publish_article_days * 86400
        ):
            return True
        return False

    def sign_account_is_zombie(self, __biz, last_publish_time=None):
        if last_publish_time:
            sql = 'update wechat_account_task set last_publish_time = "{}", last_spider_time="{}", is_zombie=1 where __biz="{}"'.format(
                last_publish_time, tools.get_current_date(), __biz
            )
        else:
            sql = 'update wechat_account_task set last_spider_time="{}", is_zombie=1 where __biz="{}"'.format(
                tools.get_current_date(), __biz
            )

        self._mysqldb.update(sql)

    def get_task(self, url=None, tip="", sleep_time=None):
        """
        获取任务
        :param url: 指定url时，返回该url包装后的任务。否则先取公众号任务，无则取文章任务。若均无任务，则休眠一段时间之后再取
        :return:
        """

        sleep_time = sleep_time or random.randint(
            self._spider_interval_min, self._spider_interval_max
        )

        if not url:
            account_task = self.get_account_task()
            if account_task:
                __biz = account_task.get("__biz")
                last_publish_time = account_task.get("last_publish_time")
                self.record_last_article_publish_time(__biz, last_publish_time)
                tip = "正在抓取列表"
                url = "https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={}&scene=124#wechat_redirect".format(
                    __biz
                )
            elif self._crawl_article:
                article_task = self.get_article_task()
                if article_task:
                    tip = "正在抓取详情"
                    url = article_task.get("article_url")
                else:
                    sleep_time = config.get("spider").get("no_task_sleep_time")
                    log.info("暂无任务 休眠 {}s".format(sleep_time))
                    tip = "暂无任务 "
            else:
                sleep_time = config.get("spider").get("no_task_sleep_time")
                log.info("暂无任务 休眠 {}s".format(sleep_time))
                tip = "暂无任务 "

        if url:
            next_page = "{tip} 休眠 {sleep_time}s 下次刷新时间 {begin_spider_time} <script>setTimeout(function(){{window.location.href='{url}';}},{sleep_time_msec});</script>".format(
                tip=tip and tip + " ",
                sleep_time=sleep_time,
                begin_spider_time=tools.timestamp_to_date(
                    tools.get_current_timestamp() + sleep_time
                ),
                url=url,
                sleep_time_msec=sleep_time * 1000,
            )
        else:
            next_page = "{tip} 休眠 {sleep_time}s 下次刷新时间 {begin_spider_time} <script>setTimeout(function(){{window.location.reload();}},{sleep_time_msec});</script>".format(
                tip=tip and tip + " ",
                sleep_time=sleep_time,
                begin_spider_time=tools.timestamp_to_date(
                    tools.get_current_timestamp() + sleep_time
                ),
                sleep_time_msec=sleep_time * 1000,
            )

        return next_page

    def reset_task(self):
        # 清除redis缓存
        keys = self._task_root_key + "*"
        keys = self._redis.getkeys(keys)
        if keys:
            for key in keys:
                self._redis.clear(key)

            # 重设任务
            sql = "update wechat_article_task set state = 0 where state = 2"
            self._mysqldb.update(sql)


if __name__ == "__main__":
    task_manager = TaskManager()

    result = task_manager.get_task()
    print(result)
