import requests
import ImgMain
import re


# 获取cookie
def get_cookie(username, password):
    # 初次发送GET请求
    first_request = requests.get("http://202.119.81.113:8080/")

    # 获取访问的cookie
    login_cookie = first_request.headers.get('Set-Cookie')[11:43]
    login_cookie = {'JSESSIONID': login_cookie}

    # 以获取的cookie获取新的验证码
    get_verify_code = requests.get("http://202.119.81.113:8080/verifycode.servlet", cookies=login_cookie)
    verify_code = ImgMain.get_code(get_verify_code)

    # 合成登录表单
    useDogeCode = ""
    login_form = {'USERNAME': username, 'PASSWORD': password, 'useDogeCode': useDogeCode, 'RANDOMCODE': verify_code}

    # 发送POST请求
    login = requests.post("http://202.119.81.113:8080/Logon.do?method=logon", data=login_form, cookies=login_cookie)

    # 获取新的cookie
    cookie_pair = login.history[1].headers.get('Set-Cookie')[11:43]
    cookie = {'JSESSIONID': cookie_pair}

    return cookie


# 成绩查询
def get_rank(cookie, kksj='', kcxz='', kcmc='', xsfs='all'):
    # 根据页面的元素发送post请求
    # kksj：开课时间，kcxz：课程性质，kcmc：课程名称，xsfs：显示方式
    # 具体参数类型参照教务处html元素
    rank_data = {'kksj': kksj, 'kcxz': kcxz, 'kcmc': kcmc, 'xsfs': xsfs}
    # 发送post请求
    get_rank = requests.get('http://202.119.81.112:9080/njlgdx/kscj/cjcx_list', data=rank_data, cookies=cookie)
    get_rank.encoding = 'utf-8'
    html = get_rank.text

    # 获取表格内容
    table = re.findall(r'<table(.*?)</table>', html, re.S)
    rank_list = re.findall(r'<tr>(.*?)</tr>', table[1], re.S)
    # 移除表头内容
    rank_list.pop(0)
    # 返回的数据集
    data = []
    # 截取每行内容
    for i in range(len(rank_list)):
        data.append(re.findall(r'<td(.*?)</td>', rank_list[i], re.S))
    # 删除内容的css样式残余
    for i in range(len(data)):
        for j in range(len(data[i])):
            str_list = data[i][j].split('>')
            data[i][j] = str_list[1]
    return data


# 课表查询
def get_schedule(cookie):
    # 发送http请求
    get_schedule = requests.get('http://202.119.81.112:9080/njlgdx/xskb/xskb_list.do', cookies=cookie)
    get_schedule.encoding = 'utf-8'
    html = get_schedule.text

    # 获取表格中内容1表示日程表，2表示课程列表，两者内容需要结合
    table = re.findall(r'<table(.*?)</table>', html, re.S)
    location = table[1]
    data_list = re.findall(r'<tr>(.*?)</tr>', table[2], re.S)
    # 去除表头
    data_list.pop(0)

    # 获取每行内容
    for i in range(len(data_list)):
        data_list[i] = re.findall(r'<td(.*?)</td>', data_list[i], re.S)
    # 去除内容中的css样式残余
    for i in range(len(data_list)):
        for j in range(len(data_list[i])):
            # 由于一周多课的存在，开课时间另作处理
            if j == 5:
                continue
            str_list = data_list[i][j].split('>')
            data_list[i][j] = str_list[1]
    # 处理开课时间内容
    for i in range(len(data_list)):
        # 去除css样式残余
        data_list[i][5] = data_list[i][5].split('>')
        data_list[i][5].pop(0)
        # 对一周多课程内容进行分隔
        for j in range(len(data_list[i][5])):
            data_list[i][5][j] = data_list[i][5][j].split('<')[0]

    # 处理日程表内容
    # 将默认显示的内容kbcontent1删除
    location = re.sub('<div(.*)class="kbcontent1(.*)</div>', '', location)

    # 去除多余的id元素便于进一步截取
    location = re.sub('id="(.*)" class', 'class', location)
    # 截取展开的内容（即勾选放大选项后显示内容）
    location = re.findall(r'<div class="kbcontent">(.*?)</div>', location, re.S)
    # 删除空格元素
    while '&nbsp;' in location:
        location.remove('&nbsp;')
    # 构建课程教室与日期列表
    location_list = []
    # 同一时间多项课程的处理
    for i in range(len(location)):
        temp_list = location[i].split('---------------------')
        for j in range(len(temp_list)):
            location_list.append(temp_list[j])
    # 内容格式处理
    for i in range(len(location_list)):
        location_list[i] = location_list[i].split('<br/>')
        for j in range(len(location_list[i])):
            location_list[i][j] = location_list[i][j].split('</font>')[0]
        for j in range(len(location_list[i])):
            temp_list = location_list[i][j].split('>')
            if len(temp_list) > 1:
                location_list[i][j] = temp_list[1]
            else:
                location_list[i][j] = temp_list[0]

    # 列表内容去重
    # 结束指示符
    de_duplication = True
    i = 0
    while de_duplication:
        # 获取当前位置的比较对象
        compare = location_list[i]
        # 操作指示符
        operated = False
        # 当前比较对象在表中个数大于1时进行去重操作
        while location_list.count(compare) > 1:
            location_list.remove(compare)
            operated = True
        # 由于remove操作会删除第一次出现的比较对象，故该位置在操作后的比较对象改变，需要对是否操作进行判断
        # 当没有进行去重操作时，表示该位置课程记录唯一，进行下一项课程的判断
        if not operated:
            i += 1
        # 当全部遍历都不再进行去重操作后，即操作完成
        if i == len(location_list):
            de_duplication = False

    # 构建返回的数据集
    data = data_list
    for i in range(len(data)):
        # 操作判断符
        operated = False
        for j in range(len(location_list)):
            if location_list[j][0] == data[i][3]:
                data[i].append(location_list[j][2])
                data[i].append(location_list[j][3])
                operated = True
        # 日程表中无记录时，可能为网课或其他特殊课程，对其时间与地点另作说明
        if not operated:
            data[i].append('网课或无数据')
            data[i].append('网课或无数据')

    # 返回数据集
    return data


if __name__ == '__main__':
    username = input("键入教务系统的用户名：")
    password = input("键入教务系统的密码：")
    cookie = get_cookie(username, password)
    out = get_rank(cookie)
    print(out)
