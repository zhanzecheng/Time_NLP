#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/11/20 16:39
# @Author  : zhm
# @File    : TimeNormalizer.py
# @Software: PyCharm
import pickle
import regex as re
import arrow
import json
import os

from StringPreHandler import StringPreHandler
from TimePoint import TimePoint
from TimeUnit import TimeUnit

import sys
#reload(sys)
#sys.setdefaultencoding('utf8')


# 时间表达式识别的主要工作类
class TimeNormalizer:
    def __init__(self, isPreferFuture=True):
        self.isPreferFuture = isPreferFuture
        self.pattern, self.holi_solar, self.holi_lunar = self.init()

    def init(self):
        fpath = os.path.dirname(__file__) + '/resource/reg.pkl'
        try:
            with open(fpath, 'rb') as f:
                pattern = pickle.load(f)
        except:
            with open(os.path.dirname(__file__) + '/resource/regex.txt', 'r') as f:
                content = f.read()
            p = re.compile(content)
            with open(fpath, 'wb') as f:
                pickle.dump(p, f)
            with open(fpath, 'rb') as f:
                pattern = pickle.load(f)
        with open(os.path.dirname(__file__) + '/resource/holi_solar.json', 'r', encoding='utf-8') as f:
            holi_solar = json.load(f)
        with open(os.path.dirname(__file__) + '/resource/holi_lunar.json', 'r', encoding='utf-8') as f:
            holi_lunar = json.load(f)
        return pattern, holi_solar, holi_lunar

    def parse(self, target, timeBase=arrow.now()):
        """
        TimeNormalizer的构造方法，timeBase取默认的系统当前时间
        :param timeBase: 基准时间点
        :param target: 待分析字符串
        :return: 时间单元数组
        """
        self.isTimeSpan = False
        self.invalidSpan = False
        self.timeSpan = ''
        self.target = target
        self.timeBase = arrow.get(timeBase).format('YYYY-M-D-H-m-s')
        self.oldTimeBase = self.timeBase
        self.__preHandling()
        self.timeToken = self.__timeEx()
        dic = {}
        res = self.timeToken
        if self.isTimeSpan:
            if self.invalidSpan:
                dic['error'] = 'no time pattern could be extracted.'
            else:
                dic['type'] = 'timedelta'
                dic['timedelta'] = self.timeSpan
        else:
            if len(res) == 0:
                dic['error'] = 'no time pattern could be extracted.'
            elif len(res) == 1:
                dic['type'] = 'timestamp'
                dic['timestamp'] = res[0].time.format("YYYY-MM-DD HH:mm:ss")
            else:
                dic['type'] = 'timespan'
                dic['timespan'] = [res[0].time.format("YYYY-MM-DD HH:mm:ss"), res[1].time.format("YYYY-MM-DD HH:mm:ss")]
        return json.dumps(dic)

    def __preHandling(self):
        """
        待匹配字符串的清理空白符和语气助词以及大写数字转化的预处理
        :return:
        """
        self.target = StringPreHandler.delKeyword(self.target, u"\\s+")  # 清理空白符
        self.target = StringPreHandler.delKeyword(self.target, u"[的]+")  # 清理语气助词
        self.target = StringPreHandler.numberTranslator(self.target)  # 大写数字转化

    def __timeEx(self):
        """

        :param target: 输入文本字符串
        :param timeBase: 输入基准时间
        :return: TimeUnit[]时间表达式类型数组
        """
        startline = -1
        endline = -1
        rpointer = 0
        temp = []

        match = self.pattern.finditer(self.target)
        for m in match:
            startline = m.start()
            if startline == endline:
                rpointer -= 1
                temp[rpointer] = temp[rpointer] + m.group()
            else:
                temp.append(m.group())
            endline = m.end()
            rpointer += 1
        res = []
        # 时间上下文： 前一个识别出来的时间会是下一个时间的上下文，用于处理：周六3点到5点这样的多个时间的识别，第二个5点应识别到是周六的。
        contextTp = TimePoint()

        for i in range(0, rpointer):
            # 这里是一个类嵌套了一个类
            res.append(TimeUnit(temp[i], self, contextTp))
            contextTp = res[i].tp
        res = self.__filterTimeUnit(res)

        return res

    def __filterTimeUnit(self, tu_arr):
        """
        过滤timeUnit中无用的识别词。无用识别词识别出的时间是1970.01.01 00:00:00(fastTime=0)
        :param tu_arr:
        :return:
        """
        if (tu_arr is None) or (len(tu_arr) < 1):
            return tu_arr
        res = []
        for tu in tu_arr:
            if tu.time.timestamp != 0:
                res.append(tu)
        return res
