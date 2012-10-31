from webob import Request, Response
from swift.common.utils import get_logger 
from webob.exc import HTTPMethodNotAllowed, HTTPBadRequest, \
    HTTPInternalServerError
from datetime import datetime, timedelta
import MySQLdb

import pyfo
import json

class formater(object):
    def __init__(self):
        self.formaters = {}
        self.formaters["xml"] = xml_formater()
        self.formaters["json"] = json_formater()

    def __call__(self, d, format):
        try:
            formater = self.formaters[format]
        except KeyError:
            formater = self.formaters["json"]

        return formater(d)

class json_formater(object):
    def __call__(self, d):
        return "json", json.dumps(d, sort_keys = True)

class xml_formater(object):
    def __call__(self, d):

        #pyfo do not work properly.
        return "xml", pyfo.pyfo(d, pretty=True,
                                prolog=True, 
                                encoding='UTF-8'
                                ).encode('UTF-8', 'xmlcharrefreplace')

class query_parser(object):
    def __init__(self):
        self.parsers = []
        self.parsers.append(url_query_parser())
        self.parsers.append(header_query_parser())

    def __call__(self, req):
        query_info = None
        for parser in self.parsers:
            query_info = parser(req)
            if query_info != None:
                break
        return query_info

class header_query_parser(object):
    def __call__(self, req):
        query_method = req.path_info_peek()

        try:
            if query_method == "" :
                query_method = req.headers['X-Query-Method']
            account_id = req.headers["X-Account-Id"]
            begin_time = req.headers["X-Begin-Time"]
            end_time = req.headers["X-End-Time"]
        except KeyError, e:
            print e
            return None

        try:
            format = req.headers["X-Format"]
        except KeyError:
            format = "json"

        return {"query_method":query_method, 
                "account_id":account_id, 
                "begin_time": begin_time, 
                "end_time": end_time, 
                "format":format}

class url_query_parser(object):
    def __call__(self, req):
        query_method = req.path_info_peek()

        if query_method == None:
            return None

        try:
            account_id = req.GET["account_id"]
            begin_time = req.GET["begin_time"]
            end_time = req.GET["end_time"]
        except KeyError:
            return None

        try:
            format = req.GET["format"]
        except KeyError:
            format = "json"

        return {"query_method":query_method, 
                "account_id":account_id, 
                "begin_time": begin_time, 
                "end_time": end_time, 
                "format": format}

class swiftdb(object):
    def __init__(self, conf):
        self.__cursors__ = []
        self.conn = None
        self.host = conf.get("sql_host", "127.0.0.1")
        self.user = conf.get("sql_user", "root")
        self.passwd = conf.get("sql_passwd", "123456")
        self.db = conf.get("sql_db", "statistics")

    def __del__(self):
        self.close()
        
    def close(self):
        if self.conn != None:
            self.conn.close()
            self.conn = None

    def getConn(self):
        if self.conn == None:
            try:
                self.conn = MySQLdb.connect(host=self.host, 
                                            user=self.user, 
                                            passwd=self.passwd, 
                                            db=self.db)
            except MySQLdb.Error, e:
                print e.args[0], e.args[1]
                pass
        return self.conn

    def getCursor(self):
        conn = self.getConn()
        if conn == None:
            return None
        cursor = conn.cursor()
        return cursor

    def io_sum(self, account, begin_time, end_time):
        cursor = self.getCursor()
        ret = 0
        if cursor == None:
            ret = -1
            return ret, []

        try:
            cursor.execute("""
                   select IFNULL(sum(OperPUTCount),0) as OperPUTCount, 
                   IFNULL(sum(OperGETCount),0) as OperGETCount, 
                   IFNULL(sum(OperHEADCount),0) as OperHEADCount, 
                   IFNULL(sum(OperPOSTCount),0) as OperPOSTCount, 
                   IFNULL(sum(OperDELETECount),0) as OperDELETECount, 
                   IFNULL(sum(OperOTHERCount),0) as OperOTHERCount, 
                   IFNULL(sum(BWIn),0) as BWIn, IFNULL(sum(BWOut),0) as BWOut 
                   from swift_statistics where AccountID=%s and AddTime >= ""%s""
                    and Addtime < ""%s""
                   """, (account, begin_time, end_time))

        except MySQLdb.Error, e:
            ret = -1
            return ret, []

        cur = cursor.fetchone()
        cursor.close()

        if cur != None:
            msg = [{"Account_ID": account, "Begin Time": begin_time, "End Time": end_time},
                   {"PUT": int(cur[0]), "GET": int(cur[1]), "HEAD": int(cur[2]), 
                    "POST": int(cur[3]), "DELETE": int(cur[4]), "OTHER":int(cur[5]), 
                    "Bytes_In": int(cur[6]), "Bytes_Out": int( cur[7])}]

        else:
            msg = [{"Account_ID": account, "Begin Time": begin_time, 
                    "End Time": end_time}, {"PUT": 0, "GET": 0,"HEAD": 0, 
                                            "POST": 0, "DELETE": 0, "OTHER": 0, 
                                            "Bytes_In": 0, "Bytes_Out": 0}]

        ret = 0
        return ret, msg

    def io_detail(self, account, begin_time, end_time):
        cursor = self.getCursor()
        ret = -1

        if cursor == None:
            return ret, []

        try:
            cursor.execute("""
                  select AddTime, sum(OperPUTCount) as OperPUTCount,
                  sum(OperGETCount) as OperGETCount, 
                  sum(OperHEADCount) as OperHEADCount, 
                  sum(OperPOSTCount) as OperPOSTCount, 
                  sum(OperDELETECount) as OperDELETECount, 
                  sum(OperOTHERCount) as OperOTHERCount, 
                  sum(BWIn) as BWIn, sum(BWOut) as BWOut 
                  from swift_statistics where AccountID=%s 
                  and AddTime >= ""%s"" and AddTime < ""%s"" 
                  group by AddTime order by AddTime 
                  """, (account, begin_time, end_time))
        except MySQLdb.Error, e:
            return ret, []

        begin_tm = datetime.strptime(begin_time, "%Y-%m-%d %H:%M:%S")
        end_tm = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

        delta = end_tm - begin_tm
        cur = cursor.fetchone()
        itr_tm = begin_tm
        details={}

        for i in range(delta.days * 24 + (delta.seconds / 3600)):
            if cur != None and itr_tm == cur[0]:

                details[cur[0].strftime("%Y-%m-%d %H:00:00")] = {
                    "PUT": int(cur[1]), "GET": int(cur[2]), "HEAD": int(cur[3]), 
                    "POST": int(cur[4]), "DELETE": int(cur[5]), "OTHER":int(cur[6]), 
                    "Bytes_In": int(cur[7]), "Bytes_Out": int( cur[8])}
                    
                cur = cursor.fetchone()
            else:
                 details[itr_tm.strftime("%Y-%m-%d %H:00:00")] = {
                     "PUT": 0, "GET":0, "HEAD": 0, "POST":0, "DELETE":0, 
                     "OTHER":0, "Bytes_In":0, "Bytes_Out":0}

            itr_tm += timedelta(hours=1)

        msg = [{"Account_ID": account, "Begin Time": begin_time, 
                "End Time": end_time}, details]

        cursor.close()
        ret = 0

        return ret, msg

    def space_detail(self, account, begin_time, end_time):
        cursor = self.getCursor()
        ret = -1

        if cursor == None:
            return ret, []

        try:
            cursor.execute("""
                  select AddTime, sum(AccountContainerCount) as AccountContainerCount,
                  sum(AccountObjectCount) as AccountObjectCount, 
                  sum(AccountBytesUsed) as AccountBytesUsed
                  from swift_space_stats where AccountID=%s 
                  and AddTime >= ""%s"" and AddTime < ""%s"" 
                  group by AddTime order by AddTime 
                  """, (account, begin_time, end_time))
        except MySQLdb.Error, e:
            return ret, []

        begin_tm = datetime.strptime(begin_time, "%Y-%m-%d %H:%M:%S")
        end_tm = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

        delta = end_tm - begin_tm
        cur = cursor.fetchone()
        itr_tm = begin_tm
        details={}

        for i in range(delta.days * 24 + (delta.seconds / 3600)):
            if cur != None and itr_tm == cur[0]:

                details[cur[0].strftime("%Y-%m-%d %H:00:00")] = {
                    "Container": int(cur[1]),
                    "Object": int(cur[2]), 
                    "Space": int(cur[3])}

                cur = cursor.fetchone()
            else:
                 details[itr_tm.strftime("%Y-%m-%d %H:00:00")] = {
                    "Container": 0,
                    "Object": 0, 
                    "Space": 0}

            itr_tm += timedelta(hours=1)

        msg = [{"Account_ID": account, "Begin Time": begin_time, 
                "End Time": end_time}, details]

        cursor.close()
        ret = 0
        return ret, msg

class Application(object):
    """Statistics server"""
    def __init__(self, conf):
        self.logger = get_logger(conf, log_route='statistics-server')
        self.db = swiftdb(conf)
        self.query_parser = query_parser()
        self.formater = formater()

        return

    def __call__(self, env, start_response):
        #self.logger.info("%r" % env)
        req = Request(env)
        response = self.handle_request(req)(env, start_response)
        return response

    def handle_request(self, req):

        query_info = self.query_parser(req)
        if query_info == None:
            return HTTPMethodNotAllowed(request=req)
        req.environ['query_info'] = query_info

        try:
            datetime.strptime(query_info["begin_time"], "%Y-%m-%d %H:%M:%S")
            datetime.strptime(query_info["end_time"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return HTTPMethodNotAllowed(request=req)

        try:
            handler=getattr(self, req.method)
        except AttributeError:
            return HTTPMethodNotAllowed(request=req)

        if 'stats.authorize' in req.environ:
            resp = req.environ['stats.authorize'](req)
            if not resp:
                del req.environ['stats.authorize']
            else:
                return resp

        return handler(req)

    def GET(self, req):
        return self.GET_POST(req)

    def POST(self, req):
        return self.GET_POST(req)

    def GET_POST(self, req):

        env = req.environ
        query_info = env['query_info']

        try:
            queryer = getattr(self.db, query_info["query_method"].lower())
        except AttributeError:
            return HTTPBadRequest(request=req)
            #return HTTPMethodNotAllowed(request=req)

        resp = Response(request=req)
        ret, bodies = queryer(query_info["account_id"], 
                              query_info["begin_time"], 
                              query_info["end_time"])

        if ret == -1:
            return HTTPInternalServerError(request=req)

        resp.status='200 OK'
        format, resp.body = self.formater(bodies, query_info["format"])
        resp.content_type = 'text/%s' % format
        return resp

def app_factory(global_conf, **local_conf):
    """paste.deploy app factory for creating WSGI proxy apps."""
    conf = global_conf.copy()
    conf.update(local_conf)
    return Application(conf)
