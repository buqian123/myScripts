# -*- coding: utf-8 -*-
# @Time    : 2021/2/15 06:00
# @Author  : srcrs
# @Email   : srcrs@foxmail.com
import os,sys
import base64,rsa,time,requests,logging,traceback,random,json,execjs
from utils.encryption import encryption

# 随机imei
def imei_random():
    value = '86' + ''.join(random.choices('0123456789', k=12))
    sum_ = 0
    parity = 1
    for i, digit in enumerate([int(x) for x in value]):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        sum_ += digit
    value += str((10 - sum_ % 10) % 10)
    return value


#进行登录
#手机号和密码加密代码，参考自这篇文章 http://www.bubuko.com/infodetail-2349299.html?&_=1524316738826
def login(username,password,appId,imei):
    global session
    session = requests.Session()
    flag = False

    session.cookies.update({'devicedId':imei})
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'content-length': '796',
        'accept-encoding': 'gzip',
        'user-agent': 'okhttp/4.4.0',
    }

    data={
        'simCount': '1',
        'yw_code': '',
        'deviceOS': 'android9',
        'mobile': encryption(username),
        'netWay': '4G',
        'deviceCode': imei,
        'isRemberPwd': 'true',
        'version': 'android@8.0805',
        'deviceId': imei,
        'password': encryption(password),
        'keyVersion': '1',
        'pip': '192.168.43.1',
        'provinceChanel': 'general',
        'appId': appId,
        'deviceModel': 'Redmi Note 7',
        'deviceBrand': 'Xiaomi',
        'timestamp': time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())),
    }
    
    response = session.post('https://m.client.10010.com/mobileService/login.htm', headers=headers, data=data)
    response.encoding='utf-8'
    try:
        result = response.json()
        if result['code'] == '0':
            logging.info('【账号密码登录】: ' + result['default'][:3]+'********')
            flag = True
        else:
            logging.info('【账号密码登录】: ' + result['dsc'])
    except Exception as e:
        print(traceback.format_exc())
        logging.info('【账号密码登录】: 发生错误，原因为: ' + str(e))

    if flag:
        saveCookie(username+'login', session.cookies.get_dict())   # 保存cookie
        return session
    else:
        return False


# 保存cookie
def saveCookie(key, cookies):
    if os.path.abspath('.')=='/var/user' and os.path.exists('/tmp'):
        logging.info('当前环境为云函数，无法保存cookie')
    if not isinstance(cookies, dict):
        cookies = requests.utils.dict_from_cookiejar(cookies)     # 把cookies转化成字典。
    with open(f"./utils/{key}.json",'w') as f:
        json.dump(cookies,f)
        logging.info('保存cookie成功')


# 读取cookie
def readCookie(key):
    if not os.path.exists(f"./utils/{key}.json"):
        logging.info('未找到cookie')
        return
    try:
        with open(f"./utils/{key}.json", 'r') as f:
            cookies_dict = json.loads(f.read()) 
        cookies = requests.utils.cookiejar_from_dict(cookies_dict)
        return cookies
    except:
        logging.error('读取cookie失败，请确保cookie为json格式')


# 获取login会话  
def get_loginSession(username,password,appId,imei):
    if not imei:    # 设备ID(通常是获取手机的imei) 联通判断是否登录多台设备 不能多台设备同时登录 填写常用的设备ID
        imei=imei_random()
    cookies=readCookie(username+'login')    # 读取已保存的cookie
    if cookies:
        logging.info(f'【cookie登录】 {username[:3]}******** ')
        session = requests.Session()
        session.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 9; RMX1901 Build/QKQ1.190918.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.186 Mobile Safari/537.36; unicom{version:android@8.0805,desmobile:' + str(username) + '};devicetype{deviceBrand:Realme,deviceModel:RMX1901};{yw_code:}',
        }
        session.cookies=cookies
        if checklogin(username,session):    # 验证cookie是否有效
            return session
    # 使用cookie登录失败，进行账号密码登录
    session=login(username,password,appId,imei)
    session.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; RMX1901 Build/QKQ1.190918.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.186 Mobile Safari/537.36; unicom{version:android@8.0805,desmobile:' + str(username) + '};devicetype{deviceBrand:Realme,deviceModel:RMX1901};{yw_code:}',
    }
    return session


# 验证cookie是否有效        
def checklogin(username,session):
    url='https://m.client.10010.com/mobileService/customer/query/getMyUnicomDateTotle.htm'
    headers={
    'content-type': 'application/x-www-form-urlencoded',
    'content-length': '52',
    'accept-encoding': 'gzip',
    'user-agent': 'okhttp/4.4.0',
    }
    data=f'yw_code=&mobile={username}&version=android%408.0805'
    res=session.post(url,headers=headers,data=data)
    try:
        resjson=res.json()
        if resjson.get('nickName',None) or resjson.get('top',None):
            logging.info(f'【cookie登录】 成功')
            saveCookie(username+'login', session.cookies.get_dict())   # 保存此次cookie
            return True
    except:
        logging.info('cookie已失效')
