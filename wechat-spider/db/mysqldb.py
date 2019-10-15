# -*- coding: utf-8 -*-
'''
Created on 2016-11-16 16:25
---------
@summary: 操作mysql数据库
---------
@author: Boris
'''
import datetime
import json

import pymysql
from DBUtils.PooledDB import PooledDB
from pymysql import cursors
from pymysql import err

from utils.log import log


def auto_retry(func):
    def wapper(*args, **kwargs):
        for i in range(3):
            try:
                return func(*args, **kwargs)
            except (err.InterfaceError, err.OperationalError, err.ProgrammingError) as e:
                log.error('''
                    error:%s
                    sql:  %s
                    ''' % (e, kwargs.get('sql') or args[1]))

    return wapper


class MysqlDB():

    def __init__(self, ip=None, port=None, db=None, user=None, passwd=None, **kwargs):
        # 可能会改setting中的值，所以此处不能直接赋值为默认值，需要后加载赋值
        try:
            self.connect_pool = PooledDB(creator=pymysql, mincached=1, maxcached=100, maxconnections=100, blocking=True, ping=7,
                                         host=ip, port=port, user=user, passwd=passwd, db=db, charset='utf8mb4', cursorclass=cursors.SSCursor)  # cursorclass 使用服务的游标，默认的在多线程下大批量插入数据会使内存递增
        except Exception as e:
            input('''
            ******************************************
                未链接到mysql数据库，
                您当前的链接信息为：
                    ip = {}
                    port = {}
                    db = {}
                    user = {}
                    passwd = {}
                请参考教程正确安装配置mysql，然后重启本程序 
                Exception: {}'''.format(ip, port, db, user, passwd, str(e))
                  )
            import sys
            sys.exit()

    def get_connection(self):
        conn = self.connect_pool.connection(shareable=False)
        # cursor = conn.cursor(cursors.SSCursor)
        cursor = conn.cursor()

        return conn, cursor

    def close_connection(self, conn, cursor):
        cursor.close()
        conn.close()

    def size_of_connections(self):
        '''
        当前活跃的连接数
        @return:
        '''
        return self.connect_pool._connections

    def size_of_connect_pool(self):
        '''
        池子里一共有多少连接
        @return:
        '''
        return len(self.connect_pool._idle_cache)

    @auto_retry
    def find(self, sql, limit=0, to_json=False, cursor=None):
        '''
        @summary:
        无数据： 返回()
        有数据： 若limit == 1 则返回 (data1, data2)
                否则返回 ((data1, data2),)
        ---------
        @param sql:
        @param limit:
        ---------
        @result:
        '''
        conn, cursor = self.get_connection()

        cursor.execute(sql)

        if limit == 1:
            result = cursor.fetchone()  # 全部查出来，截取 不推荐使用
        elif limit > 1:
            result = cursor.fetchmany(limit)  # 全部查出来，截取 不推荐使用
        else:
            result = cursor.fetchall()

        if to_json:
            columns = [i[0] for i in cursor.description]

            # 处理时间类型
            def fix_lob(row):
                def convert(col):
                    if isinstance(col, (datetime.date, datetime.time)):
                        return str(col)
                    elif isinstance(col, str) and (col.startswith('{') or col.startswith('[')):
                        try:
                            return json.loads(col)
                        except:
                            return col
                    else:
                        return col

                return [convert(c) for c in row]

            result = [fix_lob(row) for row in result]
            result = [dict(zip(columns, r)) for r in result]

        self.close_connection(conn, cursor)

        return result

    def add(self, sql, exception_callfunc=''):
        affect_count = None

        try:
            conn, cursor = self.get_connection()
            affect_count = cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error('''
                error:%s
                sql:  %s
                ''' % (e, sql))
            if exception_callfunc:
                exception_callfunc(e)
        finally:
            self.close_connection(conn, cursor)

        return affect_count

    def add_batch(self, sql, datas):
        '''
        @summary:
        ---------
        @ param sql: insert ignore into (xxx,xxx) values (%s, %s, %s)
        # param datas:[[..], [...]]
        ---------
        @result:
        '''
        affect_count = None

        try:
            conn, cursor = self.get_connection()
            affect_count = cursor.executemany(sql, datas)
            conn.commit()

        except Exception as e:
            log.error('''
                error:%s
                sql:  %s
                ''' % (e, sql))
        finally:
            self.close_connection(conn, cursor)

        return affect_count

    def update(self, sql):
        try:
            conn, cursor = self.get_connection()
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error('''
                error:%s
                sql:  %s
                ''' % (e, sql))
            return False
        else:
            return True
        finally:
            self.close_connection(conn, cursor)

    def delete(self, sql):
        try:
            conn, cursor = self.get_connection()
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error('''
                error:%s
                sql:  %s
                ''' % (e, sql))
            return False
        else:
            return True
        finally:
            self.close_connection(conn, cursor)

    def execute(self, sql):
        try:
            conn, cursor = self.get_connection()
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error('''
                error:%s
                sql:  %s
                ''' % (e, sql))
            return False
        else:
            return True
        finally:
            self.close_connection(conn, cursor)

    def set_unique_key(self, table, key):
        try:
            sql = 'alter table %s add unique (%s)' % (table, key)

            conn, cursor = self.get_connection()
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error(table + ' ' + str(e) + ' key = ' + key)
            return False
        else:
            log.debug('%s表创建唯一索引成功 索引为 %s' % (table, key))
            return True
        finally:
            self.close_connection(conn, cursor)


if __name__ == '__main__':
    db = MysqlDB()
    sql = "select is_done from qiancheng_job_list_batch_record where id = 3"

    data = db.find(sql)
    print(data)
