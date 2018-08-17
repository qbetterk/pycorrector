# -*- coding: utf-8 -*-
# Author: XuMing <xuming624@qq.com>
# Brief:
import sys
sys.path.append("../")
from pycorrector import corrector

error_sentences = [

    # # # test
    # '他等公车，看他的手标，觉得下次他应该早一点睡。'
    # '因为怕爸妈在看他，所以天天假装懂得样子，这样对学生哪有好处呢？',
    # '因为怕爸妈在看他，所以天天假装懂的样子，这样对学生哪有好处呢？',
    # '天华你还记得芳芳吗？你有他的点话吗？我也想请他一起吃。',
    # '您好！我是王天华，这里的里长。',
    # '我失王天华，一位住在您的工厂附近的邻居。',
    # '他看得出来明德真的很累，所以他情明德进车去要把明德送到火车站。',
    # '那个时间有一个人开车来，所以李明德叫住他问问火车站怎么去。',
    # '请你去五大唱片店帮我买，那点在中友百货附近。',
    # '我门看美国电影，我觉得很有意事。',
    # '我的好朋友，你好！习惯你的生活都很好。',
    # '我真的喜欢去你的会，可是那个时候我有一个重要的考试。',
    # '许多家长一昧地认为网络是传递和散播不良资讯的途径，但是他们这样的行为动作却无形中抹杀了接触新资讯的空间与时间。',
    # '他们最喜欢的地方是高雄的柴山，那里很漂亮友山友海。'
    # '噪音会影响睡眠平直，孩子无法在家里专心地写功课，更无法在家里休息。',
    # '在说，装摄影机也意味学校不相信老师。',
    # '如果您不接受这些要求，我拒绝将跟市长在说。',
    # '如果您不接受这些要求，我将拒绝在跟市长说。',
    # '过了一回儿，开始下大雨。',
    # '这是多么恐怖的事呢？这样教室跟监狱那有差别呢？',
    # '我希望你退休以后你就多多去吕行，检查健康，多多赔妈妈享收你的另以外的人生。'
    # '青少年的时候会很容易被游戏吸引，一但被游戏卓迷，就很难控制自己。'

    # '可是很多外国人很喜欢赛太杨在海边，在印尼有很多外国人来路性。',
    # '我看火车到的地图，可是我不董，因为我不懂中文。',
    # # '他们的吵翻很不错，再说他们做的咖哩鸡也好吃！',
    # '我姐姐下个月要回印尼了，可是她还没决定几号要丁飞机票。',

    # # cannot understand!!!!!
    # '因为她可以闻李大明的衣服很香抽烟的味道，所以老师就知道李大明试试骗她！'
    # '一是为了维护小孩们的睡觉、晚上或很早的时间麻烦您停您们工厂的稼？',
    # '说实话，我本来很羨慕你，你还年轻，可是已经成为一个厂长，前途一定非常辉煌。'
    # '如果教室装一个绿影机学生跟老师的关系会太假的，而老师们不愿意适应教式因为别的父母要全部是标准的方法。'
    # '小孩不过不知道那个好那个不好，也不知道那作法是适合，难怪常常看到他们用部是对的。'

    # # can understand but how to change???
    # '在家说，装摄影机也意义学校不相信老师。'

    # # no change but with error alarm
    # '我今天本来想去看你，可是明天要期末考，我需要复习。',
    # '他等公车，看他的手表，觉得下次他应该早一点睡。',
    # '现在我在台北西个半月了，周末的时候我跟同学练习中文还有一起去看电影。',
    # '如果打工的项目是刚好跟你或你有关自己的课系的相关的话当然非常不错。'

    # # '的地得'
    # '真麻烦你了。希望你们好好地跳无。',
    # '所以无论是上网打电动或者上网聊天，上网的时间一定会比念书来的更多。'
    # '为什么不先找钱包就已经指责是你拿的呢？他是不是之前也对你不太好啊？',
    # '但是我有电脑以后我才发现，我上网的时数比看书的时间长的多。',
    # '可是我想那个一天成你们的最幸福的一天。',
    '可能你的同学还不知道你是非常诚实的一个人。',
    # '他戴着眼镜跟袜子入睡了。', # *!!!!!!!!!!

    # # # value of threshold. 
    # '不过在许多传统文化的国家，女人向未得到平等。',     ## 28.71314 --> 24.86139
    # '公园的旁边有一家餐厅，我们一起去哪里吃饭。',        ## 9.0183108 --> 8.08504
    # '你们也可以走路也可以做公共汽车。',               ## 11.968 --> 8.4575
    # '看电影时候，我都觉得这个电影很有意思，可是现在我把什么事都不济的。',   ##16.095643 -> 12.051
    # '今天下了课，我打算跟我的奴朋友去看电影，所以我有一点儿领张，六点半我就起床了。',  ## 12.331646. -> 7.87076
    # '我要跟我的朋友一起去市大夜市吃晚饭。', # 12.463. ->. 16.21970
    # '小祥有女朋友。他的女朋友是同班同学，而且他们两个是邻住。' # 32.034513 --> 23.3937, 23.393771 --> 16.83796
    # '我今天二十三个小时的考试，热后我应该回家到下个星期，所以我觉得我们没有办法见面了。',
    # '我听说这个礼拜六你要开一个误会。可是那天我会很忙，因为我男朋友要回国来看我。',  #20.163218 -> 20.20958738

]
for line in error_sentences:
    print("starting correction...")
    correct_sent = corrector.correct(line)
    print("original sentence:{} => correct sentence:{}".format(line, correct_sent))




