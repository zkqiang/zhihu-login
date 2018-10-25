#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'zkqiang'
__zhihu__ = 'https://www.zhihu.com/people/z-kqiang'
__github__ = 'https://github.com/zkqiang/Zhihu-Login'

import requests
import time
import re
import base64
import hmac
import hashlib
import json
import matplotlib.pyplot as plt
from http import cookiejar
from PIL import Image


class ZhihuAccount(object):

    def __init__(self):
        self.login_url = 'https://www.zhihu.com/signup'
        self.login_api = 'https://www.zhihu.com/api/v3/oauth/sign_in'
        self.login_data = {
            'client_id': 'c3cef7c66a1843f8b3a9e6a1e3160e20',
            'grant_type': 'password',
            'source': 'com.zhihu.web',
            'username': '',
            'password': '',
            # 传入'cn'是倒立汉字验证码
            'lang': 'en',
            'ref_source': 'homepage',
        }
        self.session = requests.session()
        self.session.headers = {
            'Host': 'www.zhihu.com',
            'Referer': 'https://www.zhihu.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
        }
        self.session.cookies = cookiejar.LWPCookieJar(filename='./cookies.txt')

    def login(self, username=None, password=None, captcha_lang='en', load_cookies=True):
        """
        模拟登录知乎
        :param username: 登录手机号
        :param password: 登录密码
        :param captcha_lang: 验证码类型 'en' or 'cn'
        :param load_cookies: 是否读取上次保存的 Cookies
        :return: bool
        """
        if load_cookies and self.load_cookies():
            if self.check_login():
                print('登录成功')
                return True

        headers = self.session.headers.copy()
        headers.update({
            'xsrftoken': self._get_xsrf(),
            'x-zse-83': '3_1.1'
        })
        self.session.headers = headers['x-udid'] = self._get_udid(headers)
        username, password = self._check_user_pass(username, password)
        self.login_data.update({
            'username': username,
            'password': password,
            'captcha_lang': captcha_lang
        })
        timestamp = str(int(time.time()*1000))
        self.login_data.update({
            'captcha': self._get_captcha(self.login_data['lang'], headers),
            'timestamp': timestamp,
            'signature': self._get_signature(timestamp)
        })

        resp = self.session.post(self.login_api, data=self.login_data, headers=headers)
        if 'error' in resp.text:
            print(json.loads(resp.text)['error']['message'])
        if self.check_login():
            print('登录成功')
            return True
        print('登录失败')
        return False

    def load_cookies(self):
        """
        读取 Cookies 文件加载到 Session
        :return: bool
        """
        try:
            self.session.cookies.load(ignore_discard=True)
            return True
        except FileNotFoundError:
            return False

    def check_login(self):
        """
        检查登录状态，访问登录页面出现跳转则是已登录，
        如登录成功保存当前 Cookies
        :return: bool
        """
        resp = self.session.get(self.login_url, allow_redirects=False)
        if resp.status_code == 302:
            self.session.cookies.save()
            return True
        return False

    def _get_xsrf(self):
        """
        从登录页面获取 xsrf
        :return: str
        """
        resp = self.session.get('https://www.zhihu.com/', allow_redirects=False)
        xsrf = resp.cookies['_xsrf']
        return xsrf

    def _get_udid(self, headers):
        """
        从uuid接口获得 uuid
        :param headers: 带授权信息的请求头部
        :return: str
        """
        resp = self.session.post('https://www.zhihu.com/udid', headers=headers)
        udid = re.search(r'[\w=\-]+', resp.cookies['d_c0'])[0]
        return udid

    def _get_captcha(self, lang, headers):
        """
        请求验证码的 API 接口，无论是否需要验证码都需要请求一次
        如果需要验证码会返回图片的 base64 编码
        根据 lang 参数匹配验证码，需要人工输入
        :param lang: 返回验证码的语言(en/cn)
        :param headers: 带授权信息的请求头部
        :return: 验证码的 POST 参数
        """
        if lang == 'cn':
            api = 'https://www.zhihu.com/api/v3/oauth/captcha?lang=cn'
        else:
            api = 'https://www.zhihu.com/api/v3/oauth/captcha?lang=en'
        resp = self.session.get(api, headers=headers)
        show_captcha = re.search(r'true', resp.text)

        if show_captcha:
            put_resp = self.session.put(api, headers=headers)
            json_data = json.loads(put_resp.text)
            img_base64 = json_data['img_base64'].replace(r'\n', '')
            with open('./captcha.jpg', 'wb') as f:
                f.write(base64.b64decode(img_base64))
            img = Image.open('./captcha.jpg')
            if lang == 'cn':
                plt.imshow(img)
                print('点击所有倒立的汉字，按回车提交')
                points = plt.ginput(7)
                capt = json.dumps({'img_size': [200, 44],
                                   'input_points': [[i[0]/2, i[1]/2] for i in points]})
            else:
                img.show()
                capt = input('请输入图片里的验证码：')
            # 这里必须先把参数 POST 验证码接口
            self.session.post(api, data={'input_text': capt}, headers=headers)
            return capt
        return ''

    def _get_signature(self, timestamp):
        """
        通过 Hmac 算法计算返回签名
        实际是几个固定字符串加时间戳
        :param timestamp: 时间戳
        :return: 签名
        """
        ha = hmac.new(b'd1b964811afb40118a12068ff74a12f4', digestmod=hashlib.sha1)
        grant_type = self.login_data['grant_type']
        client_id = self.login_data['client_id']
        source = self.login_data['source']
        ha.update(bytes((grant_type + client_id + source + timestamp), 'utf-8'))
        return ha.hexdigest()

    def _check_user_pass(self, username, password):
        """
        检查用户名和密码是否已输入，若无则手动输入
        """
        if username is None:
            username = self.login_data.get('username')
            if not username:
                username = input('请输入手机号：')
        if len(username) == 11 and username.isdigit() and '+86' not in username:
            username = '+86' + username

        if password is None:
            password = self.login_data.get('password')
            if not password:
                password = input('请输入密码：')
        return username, password


if __name__ == '__main__':
    account = ZhihuAccount()
    account.login(username=None, password=None, captcha_lang='en', load_cookies=True)
