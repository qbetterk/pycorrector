#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# Author: XuMing <xuming624@qq.com>
# Brief: 
import sys
sys.path.append("../")
from pycorrector.corrector import *
from pycorrector.utils.text_utils import *

c = get_same_pinyin('儿')
print('get_same_pinyin:', c)

c = get_same_stroke('儿')
print('get_same_stroke:', c)

# freq = get_frequency('龟龙麟凤')
# print('freq:', freq)

# sent = '少先队员应该为老人让座'
# sent_seg = segment(sent)
# ppl = get_ppl_score(sent_seg)
# print('get_ppl_score:', ppl)

# sent = '少先队员因该为老人让坐'
# sent_seg = segment(sent)
# ppl = get_ppl_score(sent_seg)
# print('get_ppl_score:', ppl)

# print(detect(sent))

# corrected_sent, detail = correct('少先队员因该为老人让坐')
# print(corrected_sent, detail)
