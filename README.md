![pic](https://github.com/zkqiang/Zhihu-Login/blob/master/docs/0.jpg)
# Python 最新模拟登录知乎  支持验证码和保存 Cookies
> 知乎的登录页面已经改版多次，加强了身份验证，网络上大部分模拟登录均已失效，所以我重写了一份完整的，并实现了提交验证码 (包括中文验证码)，本文我对分析过程和代码进行步骤分解，完整的代码请见末尾 Github 仓库，不过还是建议看一遍正文，因为代码早晚会失效，解析思路才是永恒。

## 分析 POST 请求
首先打开控制台正常登录一次，可以很快找到登录的 API 接口，这个就是模拟登录 POST 的链接。

![pic](https://github.com/zkqiang/Zhihu-Login/blob/master/docs/1.jpg '操作前不要忘记勾选上面的 Preserve log')

我们的最终目标是构建 POST 请求所需的 Headers 和 Form-Data 这两个对象即可。

## 构建 Headers
继续看`Requests Headers`信息，和登录页面的 GET 请求对比发现，这个 POST 的头部多了三个身份验证字段，经测试`authorization`和`X-Xsrftoken`这两个是必需的。
`authorization`实际是一个固定值，直接复制过来即可；`X-Xsrftoken`则是防 Xsrf 跨站的 Token 认证，在`Response Headers`的`Set-Cookie`字段中可以找到。

![pic](https://github.com/zkqiang/Zhihu-Login/blob/master/docs/2.jpg '注意只有无Cookies请求才能找到')

所以我们需要先请求一次登录页面，然后用正则把这一段匹配出来。

## 构建 Form-Data
从控制台里可以看到提交了很多信息，中间的 -----WebKit 起到分隔的作用，经测试不需要添加也可以。
![pic](https://github.com/zkqiang/Zhihu-Login/blob/master/docs/6.jpg 'Request Payload 信息')

`timestamp` 时间戳，这个很好解决，区别是这里是13位整数，Python 生成的整数部分只有10位，需要额外乘以1000
timestamp = str(int(time.time()*1000))

`signature` 通过 Crtl+Shift+F 搜索找到是在一个 JS 里生成的，是通过 Hmac 算法对几个固定值和时间戳进行加密，那么只需要在 Python 里也模拟一次这个加密即可。

![pic](https://github.com/zkqiang/Zhihu-Login/blob/master/docs/3.jpg 'Python 内置 Hmac 函数，非常方便')
```
def _get_signature(self, timestamp):
    ha = hmac.new(b'd1b964811afb40118a12068ff74a12f4', digestmod=hashlib.sha1)
    grant_type = self.login_data['grant_type']
    client_id = self.login_data['client_id']
    source = self.login_data['source']
    ha.update(bytes((grant_type + client_id + source + timestamp), 'utf-8'))
    return ha.hexdigest()
```

`captcha`验证码，是通过 GET 请求单独的 API 接口返回是否需要验证码（无论是否需要，都要请求一次），如果是 True 则需要再次 PUT 请求获取图片的 base64 编码。

![pic](https://github.com/zkqiang/Zhihu-Login/blob/master/docs/4.jpg '将 base64 解码并写成图片文件即可')

```
resp = self.session.get(api, headers=headers)
show_captcha = re.search(r'true', resp.text)
if show_captcha:
    put_resp = self.session.put(api, headers=headers)
    img_base64 = re.findall(
        r'"img_base64":"(.+)"', put_resp.text, re.S)[0].replace(r'\n', '')
    with open('./captcha.jpg', 'wb') as f:
        f.write(base64.b64decode(img_base64))
        img = Image.open('./captcha.jpg')
```
实际上有两个 API，一个是识别倒立汉字，一个是常见的英文验证码，任选其一即可，代码中我将两个都实现了，汉字是通过 plt 点击坐标，然后转为 JSON 格式。（另外，这里其实可以通过重新请求登录页面避开验证码，如果你需要自动登录的话可以改造试试）
最后还有一点要注意，如果有验证码，需要将验证码的参数先 POST 到验证码 API，再随其他参数一起 POST 到登录 API。
```
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
```
![pic](https://github.com/zkqiang/Zhihu-Login/blob/master/docs/5.jpg '和正常登录传递的参数一模一样')

## 保存 Cookies
最后实现一个检查登录状态的方法，如果访问登录页面出现跳转，说明已经登录成功，这时将 Cookies 保存起来（这里 session.cookies 初始化为 LWPCookieJar 对象，所以有 save 方法），这样下次登录可以直接读取 Cookies 文件。
```
def check_login(self):
    resp = self.session.get(self.login_url, allow_redirects=False)
    if resp.status_code == 302:
        self.session.cookies.save()
        return True
    return False
```

## 完整代码
https://github.com/zkqiang/Zhihu-Login/blob/master/zhihu_login.py

## 运行环境
* Python 3
* requests
* matplotlib
* Pillow
