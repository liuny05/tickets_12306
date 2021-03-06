# -*- coding:utf-8 -*-

"""命令行火车票查看器

Usage:
    tickets [-gdtkz] <from> <to> <date>

Options:
    -h,--help   显示帮助菜单
    -g          高铁
    -d          动车
    -t          特快
    -k          快速
    -z          直达

Example:
    tickets 北京 上海 2016-10-10
    tickets -dg 成都 南京 2016-10-10
"""
from stations import stations

from docopt import docopt
# 因为requests速度很慢，使用urllib3获取
import urllib3
import json
from prettytable import PrettyTable
from colorama import init, Fore, Style

init()

class TrainsCollection(object):
    """解析火车数据"""

    # 诚然可以直接把header写成一个list，但这样写更方便！
    header = '车次 车站 时间 历时 一等 二等 软卧 硬卧 硬座 无座 备注'.split()

    def __init__(self, available_trains, options):
        """查询到的火车班次集合

        :param available_trains: 一个列表, 包含可获得的火车班次, 每个
                                 火车班次是一个字典
        :param options: 查询的选项, 如高铁, 动车, etc...
        """
        self.available_trains = available_trains
        self.options = options

    # 因为raw_train只有类内部的方法才能得到，因此将方法访问设为protected
    def _get_duration(self, raw_train):
        if raw_train.get('controlled_train_flag') == '0':
            duration = raw_train.get('lishi').replace(':', u'小时') + u'分'
            if duration.startswith('00'):
                return duration[4:]
            if duration.startswith('0'):
                return duration[1:]
            return duration
        else:
            return '------'

    def _get_message(self, raw_train):
        if raw_train.get('controlled_train_flag') == '0':
            return raw_train.get('note').replace('<br/>', '')
        else:
            return raw_train.get('controlled_train_message')

    # win10 cmd 中进行中文着色时，结束符Fore.RESET会使命令行显示时“吃掉”末尾的中文字符
    # 被“吃掉”的字符数为字符串长度的一半，因此补上相同长度的空字符即可
    # 当然不一定要空字符，直接输出两份原字符也是可以的~
    def _get_none(self, text):
        ascii_none = ''
        for x in xrange(len(text)):
            ascii_none = ascii_none + '\x00'
        return ascii_none

    def _get_time(self, raw_train):
        if raw_train.get('controlled_train_flag') == '0':
            return [Fore.GREEN + raw_train['start_time'] + Fore.RESET, Fore.RED + raw_train['arrive_time'] + Fore.RESET]
        else:
            return ['-----', '-----']

    @property
    def trains(self):
        for raw_train in self.available_trains:
            train_no = raw_train['station_train_code']
            initial = train_no[0].lower()
            if not self.options or initial in self.options:
                # 貌似在括号内的内容换行是不会有影响的，可以换行以使代码更美观
                train = [
                    train_no,
                    # win10的cmd命令行，或者是python的print函数本身？会将中文字符串的第一个字符替换成3个标识字符编码为utf-8格式的BOM'\xef\xbf\xbd'
                    # 但是命令行却不知道这是一个BOM...因此会显示为乱码���
                    # 鉴于这是比较底层的东西不好修改，被迫在字符串开头加上两个ascii码'\x00\x08'，意思为'空字符''退格'
                    # 这样从显示效果来看就跟乱码前没有区别了~
                    # 另外进行中文着色时一半字符会被“吃掉”，见_get_none()函数注释
                    '\n'.join(
                        [Fore.GREEN + '\x00\x08' + raw_train['from_station_name'] + self._get_none(raw_train['from_station_name']) + Fore.RESET,
                         Fore.RED + '\x00\x08' + raw_train['to_station_name'] + self._get_none(raw_train['to_station_name']) + Fore.RESET]),
                    '\n'.join(self._get_time(raw_train)),
                    self._get_duration(raw_train),
                    raw_train['zy_num'],
                    raw_train['ze_num'],
                    raw_train['rw_num'],
                    raw_train['yw_num'],
                    raw_train['yz_num'],
                    raw_train['wz_num'],
                    self._get_message(raw_train)
                ]
                yield train # 此关键字用于返回生成器

    def pretty_print(self):
        pt = PrettyTable()
        pt._set_field_names(self.header)
        for train in self.trains:
            pt.add_row(train)
        print pt

def cli():
    """command-line interface"""
    arguments = docopt(__doc__)
    # 从命令行获得的数据为gbk编码，因此要进行转码
    from_station = stations.get(arguments['<from>'].decode('gbk'))
    to_station = stations.get(arguments['<to>'].decode('gbk'))
    date = arguments['<date>']
    # 输入城市判断
    if not from_station:
        print "Can't find city: " + arguments['<from>'].decode('gbk').encode('utf-8') + "!"
        return
    if not to_station:
        print "Can't find city: " + arguments['<to>'].decode('gbk').encode('utf-8') + "!"
        return

    # 从12306获取数据
    url = 'https://kyfw.12306.cn/otn/lcxxcx/query?purpose_codes=ADULT&queryDate={}&from_station={}&to_station={}'.format(date, from_station, to_station)
    http = urllib3.PoolManager()
    urllib3.disable_warnings() # 尝试去掉没有https证书的warning失败，只好去掉了所有warning
    response = http.request('GET', url)
    if response.status != 200 or response.data == '-1':
        print 'Download data false!'
        return
    data = json.loads(response.data)
    # 返回结果判断
    if not data['data']['flag']:
        print data['data']['message'].encode('utf-8')
        return
    available_trains = data['data']['datas']

    # 获取参数
    options = ''.join([
        key for key, value in arguments.items() if value is True
    ])

    # 调用解析类输出
    TrainsCollection(available_trains, options).pretty_print()


if __name__ == '__main__':
    cli()
