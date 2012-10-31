swift-stats
===========

Swift对象存储计费统计方案
 
  
 计费统计项：
 读、写请求次数
 读写带宽
 占用空间
 计费统计方法：
 读、写请求次数
 读写带宽
 占用空间
 计费统计实现方式：
 Plugin方式
 Filter方式
 计费统计API消息格式：
 获取tenant一段时间内读写请求次数总和
 获取tenant一段时间内带宽总和
 获取tenant占用的空间
 数据库表结构
 全局数据结构
 获取计费统计数据服务API接口：
 获取读、写请求次数接口
 获取读写带宽接口
 获取占用空间接口

  
  
  
  
 Swift对象存储计费统计
 计费统计项：
 
        读、写请求次数
 
        读写带宽
 
        占用空间
 
  
计费统计方法：
 
读、写请求次数
 
      一个全局数据结构，以account分组，每次读写请求都加一。每小时持久化一次到数据库中。

读写带宽
 
      一个全局数据结构，以account分组，每次读写请求都累加相应的带宽。每小时持久化一次到数据库中。

占用空间
 
      每小时遍历一遍每个account下container下文件占用空间大小并累加。持久化到数据库。
  
 计费统计实现方式：
 
 Plugin方式
 
      需要修改swift代码，插入对计费统计代码的调用。


 计费统计API消息格式：
 
 获取tenant一段时间内使用资源总和
 
      请求消息格式：
 {
     X-Query-Method: io_sum
     X-Account-Id: <Account ID>
     X-Begin-Time: <Begin time>
     X-End-Time: <End time>
     X-Format: [json|xml]
 }
  
      响应消息格式：
 
 {
     {"Account_ID": <Account ID>, "Begin Time": <Begin time>, "End Time":  <End time>}, 
     {
         "Bytes_In": <Bytes In>,
         "Bytes_Out": <Bytes out>,
         "DELETE": <Delete count>,
         "GET": <Get count>,
         "HEAD": <Head count>,
         "OTHER": <Other op count>,
         "POST": <Post count>,
         "PUT": <Put count>
     }
 }
 
 获取tenant一段时间内使用资源详细信息
 
      请求消息格式：
 {
     X-Query-Method: io_detail
     X-Account-Id: <Account ID>
     X-Begin-Time: <Begin time>
     X-End-Time: <End time>
     X-Format: [json|xml]
 }
 
   响应消息格式：
 {
     {"Account_ID": <Account ID>, "Begin Time": <Begin time>, "End Time":  <End time>}, 
     {
         <Time_1>: {"Bytes_In": <Bytes In>, "Bytes_Out": <Bytes out>, "DELETE": <Delete count>, "GET": <Get count>, "HEAD": <Head count>, "OTHER": <Other op count>, "POST": <Post count>, "PUT": <Put count>}, 
         ...
         <Time_n>: {"Bytes_In": <Bytes In>, "Bytes_Out": <Bytes out>, "DELETE": <Delete count>, "GET": <Get count>, "HEAD": <Head count>, "OTHER": <Other op count>, "POST": <Post count>, "PUT": <Put count>}
     }
 }
 获取占用空间消息格式
 
 
 请求消息格式：
 {
     X-Query-Method: space_detail
     X-Account-Id: <Account ID>
     X-Begin-Time: <Begin time>
     X-End-Time: <End time>
     X-Format: [json|xml]
 }
 
   响应消息格式：
 {
     {"Account_ID": <Account ID>, "Begin Time": <Begin time>, "End Time":  <End time>}, 
     {
         <Time_1>: {"Space": <Space>, "Container": <Container count>, "Object": <Object count>}, 
         ...
         <Time_n>: {"Space": <Space>, "Container": <Container count>, "Object": <Object count>}
     }
 }
 
 数据库表结构
 
 字段名称  字段类型	说明
 ServerID	Int unsigned	 
 AddTime	Datetime	 
 AccountID	Char(33) binary	 
 OperPUTCount	Int unsigned	 
 OperGETCount	Int unsigned	 
 OperHEADCount	Int unsigned	 
 OperPOSTCount	Int unsigned	 
 OperDELETECount	Int unsigned	 
 OperOTHERCount	Int unsigned	 
 BWIn	Int unsigned	 
 BWOut	 Int unsigned	
 
  注：加粗字段为联合主键项
 全局数据结构
 
 GET = 0
 PUT = 1
 HEAD = 2
 POST = 3
 DELETE = 4
 OTHER = 5                                                                                                                                                 
 BONDIN = 6
 BONDOUT = 7
 dict {AccountID: [0,0,0,0,0,0,0,0]}
 
 获取计费统计数据服务使用资源总和API接口
 	提供一个获取计费统计数据的服务，RESTFull接口。服务端解析相关请求，从数据库中获的相关数据，按要求的格式返回。
 查询参数列表：
 format
 可以指定返回的格式是XML或者JSON。
 其他参数待扩展
  
 获取读、写请求次数与流量统计接口
 
   方法一：
 GET  /[io_sum|io_detail]?account_id=<AccoutId>;begin_time=<BeginTime>;end_time=<EndTime>;format=[json|xml] HTTP/1.1
 Host: <storage URL>
 X-Auth-Token: <authentication-token-key>
 
  
 方法二：
 GET  /[io_sum|io_detail] HTTP/1.1
 Host: <storage URL>
 X-Auth-Token: <authentication-token-key>
 X-Account-Id: <AcountId>
 X-Begin-Time: <Begin Time>
 X-End-Time: <End Time>
 X-Format: [json|xml]
 
 
 
 示例：
 curl -X GET "http://10.12.28.101:8070/io_detail" -H "X-Account-Id: 7f6ae4f0f48c49bc8a1b4f8975d" -H "X-Begin-Time: 2012-10-22 08:00:00" -H "X-End-Time: 2012-10-22 10:00:00" -H "X-Format: json" -H “X-Auth-Token: 485f19b76eba47cb9d1cc6ceefc4ff99”
 
 curl -X GET "http://10.12.28.101:8070/io_sum" -H "X-Account-Id: 7f6ae4f0f48c49bc8a1b4f8975d" -H "X-Begin-Time: 2012-10-22 08:00:00" -H "X-End-Time: 2012-10-22 10:00:00" -H "X-Format: json" -H “X-Auth-Token: 485f19b76eba47cb9d1cc6ceefc4ff99”
 获取占用空间接口
 
  
 GET  /[space_detail] HTTP/1.1
 Host: <storage URL>
 X-Auth-Token: <authentication-token-key>
 X-Account-Id: <AcountId>
 X-Begin-Time: <Begin Time>
 X-End-Time: <End Time>
 X-Format: [json|xml]
 
 
  示例：
 
 curl -X GET "http://10.12.28.101:8070/space_detail" -H "X-Account-Id: 7f6ae4f0f48c49bc8a1b4f8975d" -H "X-Begin-Time: 2012-10-22 08:00:00" -H "X-End-Time: 2012-10-22 10:00:00" -H "X-Format: json" -H “X-Auth-Token: 485f19b76eba47cb9d1cc6ceefc4ff99”
 
 附件：
 WSGI（Python Web Server Gateway Interface，缩写为WSGI）也是为了解决Web应用程序和Web Server之间的交互而提出的一种规范，不过这种规范是以CGI为基础（因为CGI是底层通信协议），位于CGI的上一层更好地去解决应用程序和服务器之间的配合问题。
 http://angeloce.iteye.com/blog/519286
  
  