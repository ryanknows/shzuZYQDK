# python3.9
# -*- coding: utf-8 -*-

# @Time    : 2022/10/19 15:52
# @Author  : Ryan Yang
# @Email   : ryanyang@vip.qq.com
# @File    : shzu战疫情打卡.py
# @Software: PyCharm
"""
石河子大学战疫情每日健康打卡爬虫V1.1

骂街：
我始终搞不懂这个傻逼的战疫情打卡有个jb用，稍微睡会儿懒觉就qq轰炸企业微信轰炸短信轰炸电话轰炸告诉你快打卡
我他妈现在在离新疆三千多公里之外的地方还天天监视定位？？？
就因为这个月打卡晚了几次直接被通报批评？？？
老子又不是没打卡这帮臭傻逼们我操你妈听到没有我操你妈！！！我！操！你！妈！
于是一气之下这个爬虫脚本被我个菜逼写出来了，很多地方都是现学现用所以是个屎堆代码，但凑合着用吧

简介：
因为这个傻逼打卡页面只让从企业微信进入，在模拟登录时候意识到自己是菜逼搞不定微信的身份验证后，采用定时发送请求保持连接，绕过重新登录的方法。
原理：抓包获取header和cookie和data，定时访问保证连接不断开，每天发送打卡数据。over，就这么简单。

使用方法：
-使用fiddler抓包，可以右键save，selectd sessions，as text ，再使用"抓包数据转成请求.py"很方便的转换成request请求
-配置自己信息
-你都会自己配置了还不会使用？
-嘤嘤嘤人家只是不想被通报批评
"""
import datetime
import json
import logging

import threading
import time

import requests
import smtplib
from email.mime.text import MIMEText

# 日志配置，log输出在autoSend.log
logging.basicConfig(
    level=logging.DEBUG,
    filename='autoSend.log',
    filemode='a',
    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s'
)
# 存放用户的列表
userList = ["name"]
# 存放用户简写为key，用户邮箱为value的字典
mail = {
    "name": "xxxxxxxxx@qq.com"
}
# 存放用户打卡数据的字典
msgData = \
    {
        "name":
            {
                'dwaddress': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                'jkzk': '1',
                'bszz': '',
                'tiwen': '36.5',
                'tiwen2': '',
                'tiwen3': '',
                'bz': '',
                "wxprovince": "xxxxxxxxxxxxx",
                "wxcity": "xxxxxxxxxxx",
                "longitude": "xxxxxxxxxxxxxxxx",
                "latitude": "xxxxxxxxxxxxxx",
                "dwtime": "2022-10-20 16:11:55",
                'deviceid': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            }

    }
# 存放用户打卡时的Header
msgHeadersData = \
    {
        "name":
            {'Host': 'xxxxxxxxxxx.edu.cn',
             'Connection': 'keep-alive',
             'Content-Length': 'xxxxxxxxxx',
             'Accept': 'application/json, text/plain, */*',
             'User-Agent': 'Mxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
             'Content-Type': 'xxxxxxxxxxxxxxxxxxxxx'
             }

    }
# 存放用户保持连接的Header
aliveHeadersData = \
    {
        "name":
            {'Host': 'xxxxxxxxxxxxxxxxxxxxxxxxxxx.edu.cn',
             'Connection': 'keep-alive',
             'Content-Length': '0',
             'Accept': 'application/json, text/plain, */*',
             'User-Agent': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
             'Content-Type': 'application/x-www-form-urlencoded'
             }

    }
# 存放用户的cookie
cookiesData = \
    {
        "name": {'JSESSIONID': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                 'gautappin': 'xxxxxxxxxxxxxxxxxxxxxxx',
                 'gautappid': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                 'gautuserbindid': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                 'gxqt_sso_sessionid': "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                 }

    }


class AliveTimer:
    """
    保持连接的定时封装，取用多线程定时，looptime 2700s = 45min，抓包得到连接寿命为2h，可自己修改但不建议太频繁
    类内进行循环调用，实例化一次即可自动循环定时
    若连接丢失会向该用户发送邮件并结束循环定时
    :param input：用户名
    """

    def __init__(self, usrname):

        self.usrname = usrname
        self.looptime = 2700  # 循环定时（单位秒）
        self.createTimer()  # 构建定时器的方法

    def createTimer(self):

        t = threading.Timer(self.looptime, self.repeat)
        t.start()  # 开始该定时线程

    def repeat(self):

        self.keepAlive()  # 执行访问请求保证连接不会丢失，把再次构建定时器加在该函数内是因为需要判断保持连接再调用，否则结束
        time.sleep(1)

    def keepAlive(self):

        url = 'http://xxxxxxxxxxxxxxxxxxxxxxxxxn/gaut/loginappsso'
        headers = aliveHeadersData[self.usrname]
        cookies = cookiesData[self.usrname]
        html = requests.post(url, headers=headers, verify=False, cookies=cookies)

        if json.loads(html.text).get("msg") == "登录成功！":

            logging.info(f"{self.usrname} 保持连接 {json.loads(html.text)}")

            self.createTimer()  # 再次构建定时器
        else:

            a = SendMail(mail[self.usrname])

            logging.info(f"{self.usrname} 连接丢失 {json.loads(html.text)}")

            a.txtmessage(f"{self.usrname} 连接丢失 " + str(wozhenniubi))
            a.send()


class SendTimer:
    """
    定时发送打卡数据的封装
    每天在指定时间段内发送一次打卡数据，looptime设置为一个小时至少一次至多两次被定时到即可，循环逻辑同上
    （其实可以把保持连接和发送数据作为定时的子类去写，但一开始这两个功能是在两个脚本内实现的，后面懒得改了）
    :param input：用户名
    """

    def __init__(self, usrname):

        self.usrname = usrname
        self.looptime = 3451
        self.createTimer()

    def createTimer(self):

        t = threading.Timer(self.looptime, self.repeat)
        t.start()

    def repeat(self):

        ctime = datetime.datetime.now().strftime('%H')
        if ctime == "06":  # 通过判断当前时间的小时是否是指定时间来决定是否发送打卡数据
            self.sendMsg()
        time.sleep(1)
        self.createTimer()

    def sendMsg(self):
        """
        发送打卡数据，前提是建立在连接不丢失的情况下，
        :return:
        """
        dwtime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        url = 'http:/xxxxxxxxxxxxxxxxxxxedu.cn/gxxxxxxxxxxxxxxxxxg/zyq/saveaddZyqJianKangDaKaForApp.do?client=gxqtapp'
        headers = msgHeadersData[self.usrname]
        cookies = cookiesData[self.usrname]
        data = msgData[self.usrname]
        data.update({"dwtime": dwtime})  # 更新当日打卡时间

        html = requests.post(url, headers=headers, verify=False, cookies=cookies, data=data)
        if json.loads(html.text).get("msg") == "操作成功":
            """
            在调试邮件发送模块的时候遇到了奇怪的问题，
            下面两行供调试使用
            """
            # msg = 1
            # if msg == 1:

            logging.info(f"{self.usrname} {dwtime} 打卡成功")

            a = SendMail(mail[self.usrname])
            a.txtmessage(self.usrname + " " + dwtime + " 打卡成功")

            logging.info(f"{self.usrname} {dwtime} 尝试发送邮件")

            a.send()

        else:
            logging.info(f"{self.usrname} {dwtime} 打卡失败")
            logging.info(f"{self.usrname} {dwtime} {html.text}")

            a = SendMail(mail[self.usrname])
            a.txtmessage(f"{self.usrname} + ' ' + {dwtime} + ' 打卡失败 ' + {html.text}")

            logging.info(f"{self.usrname} {dwtime} 尝试发送邮件")

            a.send()


class SendMail:
    """
    借鉴来的代码，改成自己需要的样子罢了
    mail_pwd不是邮箱密码，是开启SMTP时候的授权码
    """
    host = "smtp.qq.com"
    mail_user = "xxxxxxxxxxxxxxxx@vip.qq.com"
    mail_pwd = "xxxxxxxxxxxxxxxxxxx"
    sender = 'xxxxxxxxxxxxxxx@vip.qq.com'

    def __init__(self, receiver):

        self.message = None
        self.receiver = receiver

    def txtmessage(self, str):
        """
        获取自定义邮件内容
        :param str: 邮件内容，注意是str
        """
        # 三个参数：第一个为文本内容，第二个 plain 设置文本格式，第三个 utf-8 设置编码
        message = MIMEText(str, 'plain', 'utf-8')
        message['From'] = self.sender  # 发送者
        message['To'] = self.receiver  # 接收者
        message['Subject'] = "自动打卡小天使提示"
        self.message = message

    def send(self):

        try:
            smtpObj = smtplib.SMTP()  # 建立和SMTP邮件服务器的连接
            smtpObj.connect(self.host, 25)  # 25 为 SMTP 端口号
            # smtpObj.set_debuglevel(1)
            smtpObj.login(self.mail_user, self.mail_pwd)  # 完成身份认证
            smtpObj.sendmail(self.sender, self.receiver, self.message.as_string())  # 发送邮件

            logging.info(f"向{self.receiver}成功发送邮件")

            smtpObj.quit()  # 结束会话

        except smtplib.SMTPException as e:
            logging.error(e)


if __name__ == '__main__':

    wozhenniubi = {}  # 借鉴来的存储对象小tips
    for usr in userList:
        time.sleep(2)
        wozhenniubi['alive' + usr] = AliveTimer(usr)

    for usr in userList:
        time.sleep(2)
        wozhenniubi['msg' + usr] = SendTimer(usr)

    logging.info(f"{wozhenniubi}")
