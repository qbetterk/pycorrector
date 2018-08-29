# -*- coding: utf-8 -*-
#!/usr/bin/env bash
#
# Author: XuMing <xuming624@qq.com>
# Brief: corrector with spell and stroke
import codecs
import os
import pdb
import time
import math
import sys
import argparse
import jieba.posseg as pseg
from collections import defaultdict
from pypinyin import lazy_pinyin

pwd_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(pwd_path + '/../')

import pycorrector.config as config
from pycorrector.detector import detect
from pycorrector.detector import get_frequency
from pycorrector.detector import get_ppl_score
from pycorrector.detector import trigram_char
from pycorrector.detector import word_freq
from pycorrector.utils.io_utils import dump_pkl
from pycorrector.utils.io_utils import get_logger
from pycorrector.utils.io_utils import load_pkl
from pycorrector.utils.text_utils import is_chinese_string
from pycorrector.utils.text_utils import is_chinese
from pycorrector.utils.text_utils import traditional2simplified
from pycorrector.utils.text_utils import tokenize


default_logger = get_logger(__file__)


def load_char_dict(path):
    char_dict = ''
    with codecs.open(path, 'r', encoding='utf-8') as f:
        for w in f:
            char_dict += w.strip()
    return char_dict

def load_2char_dict(path):
    text = codecs.open(path, 'rb', encoding = 'utf-8').read()
    return set(text.split('\n'))

def load_word_dict(path):
    word_dict = set()
    word_dict_file = codecs.open(path, 'rb', encoding = 'utf-8').readlines()
    for line in word_dict_file:
        word_dict.add(line.split()[0])
    return word_dict

def load_same_pinyin(path, sep='\t'):
    """
    加载同音字
    :param path:
    :return:
    """
    result = dict()
    if not os.path.exists(path):
        default_logger.debug("file not exists:", path)
        return result
    with codecs.open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = traditional2simplified(line.strip())
            parts = line.split(sep)
            if parts and len(parts) > 2:
                key_char = parts[0]
                # same_pron_same_tone = set(list(parts[1]))
                # same_pron_diff_tone = set(list(parts[2]))
                # value = same_pron_same_tone.union(same_pron_diff_tone)
                value = set(list("".join(parts)))
                if len(key_char) > 1 or not value:
                    continue
                result[key_char] = value

    # these pairs would be dealed with rule
    result['他'] -= {'她', '它'}
    result['她'] -= {'他', '它'}
    result['它'] -= {'她', '他'}
    result['影'] -= {'音'}
    result['车'] = result['扯']

    return result

def load_same_stroke(path, sep=','):
    """
    加载形似字
    :param path:
    :param sep:
    :return:
    """
    result = defaultdict(set)
    if not os.path.exists(path):
        default_logger.debug("file not exists:", path)
        return result
    with codecs.open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = traditional2simplified(line.strip())
            parts = line.strip().split(sep)
            if parts and len(parts) > 1:
                for i, c in enumerate(parts):
                    # result[c].add(c)
                    # result[c] |= set(list(parts[:i] + parts[i + 1:]))
                    result[c] |= set(parts)
    return result

char_dict_path = os.path.join(pwd_path, config.char_dict_path)
cn_char_set = load_char_dict(char_dict_path)
two_char_dict = load_2char_dict(pwd_path + '/data/char_two_set.txt')

# # word dictionary
word_dict_text_path = os.path.join(pwd_path, config.word_dict_path)
word_dict_model_path = os.path.join(pwd_path, config.word_dict_model_path)
if os.path.exists(word_dict_model_path):
    cn_word_set = load_pkl(word_dict_model_path)
else:
    default_logger.debug('load word dict from text file:', word_dict_model_path)
    cn_word_set = load_word_dict(word_dict_text_path)
    dump_pkl(cn_word_set, word_dict_model_path)

# similar pronuciation
same_pinyin_text_path = os.path.join(pwd_path, config.same_pinyin_text_path)
same_pinyin_model_path = os.path.join(pwd_path, config.same_pinyin_model_path)
# same_pinyin = load_same_pinyin(same_pinyin_text_path)
if os.path.exists(same_pinyin_model_path):
    same_pinyin = load_pkl(same_pinyin_model_path)
else:
    default_logger.debug('load same pinyin from text file:', same_pinyin_text_path)
    same_pinyin = load_same_pinyin(same_pinyin_text_path)
    dump_pkl(same_pinyin, same_pinyin_model_path)

# similar shape
same_stroke_text_path = os.path.join(pwd_path, config.same_stroke_text_path)
same_stroke_model_path = os.path.join(pwd_path, config.same_stroke_model_path)
if os.path.exists(same_stroke_model_path):
    same_stroke = load_pkl(same_stroke_model_path)
else:
    default_logger.debug('load same stroke from text file:', same_stroke_text_path)
    same_stroke = load_same_stroke(same_stroke_text_path)
    dump_pkl(same_stroke, same_stroke_model_path)


def get_confusion_char_set(char):
    # confusion_char_set = get_same_pinyin(char).union(get_same_stroke(char))
    confusion_char_set = same_pinyin.get(char, set())
    confusion_char_set |= same_stroke.get(char, set())
    if not confusion_char_set:
        confusion_char_set = {char}
    return confusion_char_set


def get_confusion_two_char_set(word):
    return set([char_1 + char_2 for char_1 in get_confusion_char_set(word[0]) \
                                for char_2 in get_confusion_char_set(word[1]) \
                                if char_1 + char_2 in cn_word_set])


def _generate_items(sentence, idx, word, fraction=1):

    if len(word) == 1:
        confusion_word_set = set([i for i in get_confusion_char_set(word[0]) if i])

    if len(word) > 1:

        def combine_two_confusion_char(sentence, idx, word):
            # # assuming there is only two char to change
            # # definitely not the final version, need to be fixed!!!!
            result = set()
            for i in range(len(word) - 1):
                for j in range(i + 1,len(word)):
                    result |= set([word[: i] + i_word + word[i + 1: j] + j_word + word[j + 1:] \
                                   for i_word in get_confusion_char_set(word[i]) if i_word \
                                   for j_word in get_confusion_char_set(word[j]) if j_word])
            return result

        def confusion_set(sentence, idx, word):
            # maximum number of change char is set up by 'edit_distance'

            # the maximum edit-distance
            edit_distance = 2

            cands_tmp = [['',0]]
            result = set()
            ids = list(range(int(idx.split(',')[0]), int(idx.split(',')[1])))

            # # change individual char
            while cands_tmp:

                if len(cands_tmp[0][0]) == len(word):
                    result.add(cands_tmp[0][0])

                elif cands_tmp[0][1] == edit_distance:
                    result.add(cands_tmp[0][0] + word[len(cands_tmp[0][0]):])

                else:
                    target_idx = ids[len(cands_tmp[0][0])]
                    for char_cand in get_confusion_char_set(sentence[target_idx]):

                        if target_idx == 0:
                            if char_cand + sentence[target_idx + 1] not in two_char_dict:
                                continue

                        elif target_idx == len(sentence) - 1:
                            if sentence[target_idx - 1] + char_cand not in two_char_dict:
                                continue

                        elif char_cand + sentence[target_idx + 1] not in two_char_dict and \
                             sentence[target_idx - 1] + char_cand not in two_char_dict:
                            continue
                        
                        if char_cand == sentence[target_idx]:
                            cands_tmp.append([cands_tmp[0][0] + char_cand, cands_tmp[0][1]])
                        else:
                            cands_tmp.append([cands_tmp[0][0] + char_cand, cands_tmp[0][1] + 1])

                cands_tmp.pop(0)

            # # change connected two chars
            for i in range(len(word) - 1):
                for char_i in get_confusion_char_set(word[i]):
                    for char_j in get_confusion_char_set(word[i + 1]):
                        if char_i + char_j in two_char_dict:
                            result.add(word[:i] + char_i + char_j + word[i + 2:])



            return result

        confusion_word_set = confusion_set(sentence, idx, word)

    confusion_word_list = [item for item in confusion_word_set if is_chinese_string(item)]
    confusion_sorted = sorted(confusion_word_list, key=lambda k: get_frequency(k), reverse=True)

    return confusion_sorted[:len(confusion_word_list) // fraction + 1]


def get_sub_array(nums):
    """
    取所有连续子串，
    [0, 1, 2, 5, 7, 8]
    => [[0, 3], 5, [7, 9]]
    :param nums: sorted(list)
    :return:
    """
    ret = []
    for i, c in enumerate(nums):
        if i == 0:
            pass
        elif i <= ii:
            continue
        elif i == len(nums) - 1:
            ret.append([c])
            break
        ii = i
        cc = c
        # get continuity Substring
        while ii < len(nums) - 1 and nums[ii + 1] == cc + 1:
            ii = ii + 1
            cc = cc + 1
        if ii > i:
            ret.append([c, nums[ii] + 1])
        else:
            ret.append([c])
    return ret


def get_valid_sub_array(sentence, sub_array_list):
    """
    this function is to get rid of puctuation in detected string

    :param  sentence:    target sentence
            subarray:    index of suspected string
    :return valid_array: index of valid suspected string without punctuation
    """

    # print(sub_array_list)

    valid_array_detail = []

    for sub_array in sub_array_list:
        valid_sub_array_detail = []
        if len(sub_array) == 1:
            if is_chinese(sentence[sub_array[0]]):
                valid_array_detail.append([sub_array[0], sub_array[0]])
        else:
            for i in range(sub_array[0], sub_array[1]):
                if is_chinese(sentence[i]):
                    valid_sub_array_detail.append(i)
                elif valid_sub_array_detail:
                    valid_array_detail.append(valid_sub_array_detail)
                    valid_sub_array_detail = []
            if valid_sub_array_detail:
                valid_array_detail.append(valid_sub_array_detail)

    # print(valid_array_detail)
    return [[sub[0], sub[-1] + 1] for sub in valid_array_detail]


def count_diff(str1, str2):
    """
    Counting the number of different chars between two string.
    Assuming len(str1) == len(str2)
    """
    count = 0
    for i in range(len(str1)):
        if str1[i] != str2[i]:
            count += 1

    return count


def correct_stat(sentence, sub_sents, param_ec, param_gd):
    """
    statistical correction

    input
        sentence : error sentence in form of string
        sub_sents: pair of index range of suspect chars and corresponding suspect chars
                   in the form like: [['str(b_idx),str(e_idx)',str(suspect_chars)], ...]\
        param_ec : paramter for edition cost, might change for matching your own language model
        param_gd : paramter for global decision, might change for different lm
    output
        sentence : corrected sentence in form of string
        detail   : correction detail in form like [[err_chars, cor_chars, b_idx, e_idx + 1]]
    """

    detail = []
    cands   = []

    for idx, item in sub_sents:

        maybe_error_items = _generate_items(sentence, idx, item)

        if not maybe_error_items:
            continue
        ids = idx.split(',')
        begin_id = int(ids[0])
        end_id = int(ids[-1]) if len(ids) > 1 else int(ids[0]) + 1
        before = sentence[:begin_id]
        after = sentence[end_id:]

        base_score = get_ppl_score(list(before + item + after), mode=trigram_char)

        min_score  = base_score

        corrected_item = item
        for candidate in maybe_error_items:
            score = get_ppl_score(list(before + candidate + after), mode=trigram_char) \
                                + param_ec * count_diff(item, candidate) * math.log(base_score)
            if score < min_score:
                corrected_item = candidate
                min_score = score

        delta_score = base_score - min_score
 
        cands.append([idx, corrected_item, delta_score])

    cands.sort(key = lambda x: x[2], reverse = True)

    for i, [idx, corrected_item, delta_score] in enumerate(cands):
        if delta_score > i * param_gd * math.log(base_score):
            idx = [int(idx.split(",")[0]), int(idx.split(",")[1])]
            detail.append(list(zip([sentence[idx[0]:idx[1]]], \
                                   [corrected_item],          \
                                   [idx[0]],                  \
                                   [idx[1]])))  
            
            sentence = sentence[: idx[0]] + \
                       corrected_item +     \
                       sentence[idx[1]:]
        else:
            break

    return sentence, detail


def get_sub_sent(idx, sentence):
    """
    To get the longest sub_sentence which the target char(sentence[idx]) belong to 
    and does not contain any non-charactor symbol(punctuation)
    """
    begin_id = 0
    end_id = 0
    for i in range(idx,-1,-1):
        if not is_chinese(sentence[i]):
            begin_id = i
            break
    for i in range(idx, len(sentence)):
        if not is_chinese(sentence[i]):
            end_id = i
            break
    return [begin_id, end_id]


def correct_rule(sentence):
    """
    rule-based correction(strongly depending on POS tagging)

    input
        sentence : error sentence
    output
        sentence : corrected sentence
        detail   : correction detail(exactly same form as that of correct_stat())
    """
    detail = []

    old_sentence = sentence

    # # rule for '他她它' here is too simple to apply for present, improvement needed!
    # # rule for '他她它'('he, she, it')
    # dict_hsi  = {
    #             '他' : {'爸','父','爷','哥','弟','兄','子','叔','伯','他','爹','先生'},
    #             '她' : {'妈','母','奶','姐','妹','姑姑','婶','姊','妯','娌','她','婆','姨','太太','夫人','娘'},
    #             '它' : {'它'}
    #             }
    # for i in range(len(sentence)):
    #     if sentence[i] in dict_hsi.keys():
    #         for key in dict_hsi.keys():
    #             if set(list(sentence[:i])) & dict_hsi[key]:
    #                 sentence = sentence[:i] + key + sentence[i + 1:]
    #                 detail.append([(sentence[i], key, i, i + 1)])
    #                 continue

    # # rule for '的地得'
    if set(sentence) & {'的', '地', '得'}:

        seg = pseg.lcut(sentence)
        # # in the form of list of pair(w.word, w.flag)
        word = [w.word for w in seg]
        tag  = [w.flag for w in seg]

        for i in range(len(word)):
            if word[i] in {'的', '地', '得'} and 1 < i < len(word) - 1:
                # '地'
                if (tag[i + 1] == 'v' or \
                    word[i + 1] == '被' or \
                    tag[i + 1: i + 4] == ['p','n','v'] or \
                    tag[i + 1: i + 5] == ['p','n','f','v']) \
                    and \
                    (tag[i - 1] in {'i','d','ad','l'} or \
                    word[i-1] in {'一样','那么'}) \
                    and \
                    len(word[i - 1]) > 1 :
                    if i > 2 and tag[i - 2] in {'n','r','vn','an','d','x'}:
                        if word[i + 1] not in {'做法','看法','想法','行为','存在'}:
                            sentence = sentence[:len(''.join(word[:i]))] + \
                                       '地' +                              \
                                       sentence[len(''.join(word[:i])) + 1:]

                if tag[i + 1] == 'a' and \
                   (tag[i - 1] in {'d'} or word[i-1] in {'一样','那么'}) and \
                   (tag[i + 2] == 'x' or tuple(tag[i+2:i+4]) in {('y','x'),('ul','x')}):
                    sentence = sentence[:len(''.join(word[:i]))] + \
                               '地' +                              \
                               sentence[len(''.join(word[:i])) + 1:]

                if tag[i - 1] == 'd' and       \
                   tag[i + 1] in {'r','a'} and \
                   i < len(word) - 2 and       \
                   tag[i + 2] == 'v':
                    sentence = sentence[:len(''.join(word[:i]))] + \
                               '地' +                              \
                               sentence[len(''.join(word[:i])) + 1:]                    

                # '得'
                if tag[i - 1] == 'v' and tag[i + 1] in {'a','d'}:
                    if tag[i + 1] == 'a':
                        if i > len(word) - 5:
                            sentence = sentence[:len(''.join(word[:i]))] +   \
                                       '得' +                                \
                                       sentence[len(''.join(word[:i])) + 1:]
                        elif word[i + 2] not in {'的', '地', '得'} or         \
                             tag[i + 3] not in {'n','vn','r'}:
                            sentence = sentence[:len(''.join(word[:i]))] +   \
                                       '得' +                                \
                                       sentence[len(''.join(word[:i])) + 1:]
                    if tag[i + 1] == 'd':
                        sentence = sentence[:len(''.join(word[:i]))] +       \
                                   '得' +                                    \
                                   sentence[len(''.join(word[:i])) + 1:]
                if tag[i - 1] == 'a' and word[i + 1] == '多' and not is_chinese(word[i + 2]):
                    sentence = sentence[:len(''.join(word[:i]))] +       \
                               '得' +                                    \
                               sentence[len(''.join(word[:i])) + 1:]

                # for word '得到'
                if tag[i - 1] in {'n','r','vn'} and word[i + 1] == '到':
                    sentence = sentence[:len(''.join(word[:i]))] +       \
                               '得' +                                    \
                               sentence[len(''.join(word[:i])) + 1:]                                                            


                # '的'
                if tag[i - 1] == 'v' and (not is_chinese(word[i + 1]) or \
                                  (i < len(word) - 2 and not is_chinese(word[i + 2]) and tag[i + 1] == 'y')):
                    sentence = sentence[:len(''.join(word[:i]))] +       \
                               '的' +                                    \
                               sentence[len(''.join(word[:i])) + 1:] 

                if tag[i - 1] == 'n' and tag[i + 1] == 'n':
                    sentence = sentence[:len(''.join(word[:i]))] +       \
                               '的' +                                    \
                               sentence[len(''.join(word[:i])) + 1:]                    

            if word[i] in {'真得','真地'}:
                sentence = sentence[:len(''.join(word[:i]))] +        \
                           '真的' +                                    \
                           sentence[len(''.join(word[:i + 1])):]   

    # # rule for '啊阿'
    if set(sentence) & {'阿'}:
        for i in range(len(sentence)):
            if sentence[i] == '阿' and not is_chinese(sentence[i + 1]):
                sentence = sentence[:i] + '啊' + sentence[i + 1:]

    # # 疑问代词：to suggest question
    ques_word = {'怎','什么','多少','谁', \
                 '可不可','是不是', '能不能','会不会'} # to be added
    # # 引导疑问句的词: to introduce a question
    intr_word = {'知道','想一想','无论','不管'} # to be added

    # # rule for '那哪'    
    if set(sentence) & {'那', '哪'}:
        # for idx in detect(sentence):
        for idx in range(len(sentence)):
            if sentence[idx] in {'那', '哪'}:
                if idx < len(sentence) - 1 and sentence[idx + 1] == '么':
                    sentence = sentence[:idx] + '那' + sentence[idx + 1:]
                    continue
                [sub_sent_b, sub_sent_e] = get_sub_sent(idx, sentence)
                sub_sent = sentence[sub_sent_b: sub_sent_e + 1]

                # question sentence
                if sub_sent[-1] == '？':
                    if True in [i in sub_sent for i in ques_word] or \
                        ((idx == 0 or \
                          not is_chinese(sentence[idx - 1])) and \
                         (sentence[idx + 1: idx + 2]=='不' or \
                          sentence[idx + 1: idx + 3]=='岂不')):
                        sentence = sentence[:idx] + '那' + sentence[idx + 1:]
                    else:
                        sentence = sentence[:idx] + '哪' + sentence[idx + 1:]

                # # state sentence
                else:
                    if True in [i in sub_sent[:idx - sub_sent_b] for i in intr_word]:
                        if True not in [i in sub_sent for i in ques_word]:
                            sentence = sentence[:idx] + '哪' + sentence[idx + 1:]
                    else:
                        sentence = sentence[:idx] + '那' + sentence[idx + 1:]

    # # rule for '门们'
    if set(sentence) & {'门', '们'}:
        for idx in [i for i in range(len(sentence)) if sentence[i] in {'门', '们'}]:
            if idx == 0:
                sentence = '门' + sentence[1:]
            elif sentence[idx - 1] in {'你','我','他','她','它','哥'}:
                sentence = sentence[:idx] + '们' + sentence[idx + 1:]

    for idx in range(len(sentence)):
        if sentence[idx] != old_sentence[idx]:
            detail.append([old_sentence[idx], sentence[idx], idx, idx + 1])


    return sentence, detail


def correct(sentence, param_ec = 1.5, param_gd = 2.5):

    detail = []

    # # detecting for errors
    maybe_error_ids = get_valid_sub_array(sentence, get_sub_array(detect(sentence)))

    # # transfer index of error chars into pairs of (idx, error_chars)
    suspect_chars = [[','.join([str(i[0]), str(i[-1])]), sentence[i[0]: i[-1]]] for i in maybe_error_ids]

    # # statistical correction
    sentence, detail_stat = correct_stat(sentence, suspect_chars, param_ec, param_gd)
    detail += detail_stat

    # # rule-based correction
    sentence, detail_rule = correct_rule(sentence)
    detail += detail_rule

    return sentence, detail


def parse():
    parser = argparse.ArgumentParser(
             description = 'this file is to use pycorrector to test '
                           'sighan15 test file, and transfer the result'
                           'to the format that sighan15 eval tool required')
    parser.add_argument('-i', '--error_sentence', #required = True, 
                        help = 'input: error sentenced to be corrected'
                               '(format should be only one sentence per line)')
    parser.add_argument('-o', '--corrected_sentence', #required = True,
                        help = 'output: file to store corrected sentence(not required)')
    parser.add_argument('-v', '--correct_verbose',
                        default = False,
                        help = 'show the detail of correction or not')
    parser.add_argument('--param_ec', type = float,
                        default = 1.5,
                        help = 'parameter for adjust the weight of edition cost')
    parser.add_argument('--param_gd', type = float,
                        default = 2.5,
                        help = 'parameter for adjust the weight of global decision')
    return parser.parse_args()


def main():

    args = parse()

    if args.error_sentence == None:
        if args.corrected_sentence == None:
            sentence = input('input a sentence to correct errors: ')
            while sentence not in {'','q'}:
                pred_sent, pred_detail = correct(sentence.strip(), args.param_ec, args.param_gd)
                sys.stderr.write('input sentence : ' + sentence + '\n')
                sys.stderr.write('pred sentence  : ' + pred_sent + '\n')
                sys.stderr.write('predict change : ' + ', '.join([i[0][0] + '-->' + i[0][1] \
                                               for i in pred_detail if i]) + '\n')  
                sentence = input('input a sentence to continue correcting errors or input q to quit: ')          
        else:
            sys.stderr.write('Error: no path to error sentences.')

    elif args.corrected_sentence == None:
        sys.stderr.write('Error: no path to store corrected sentences.')

    else:
        sys.stderr.write('Starting correcting sentences......\n')
        sys.stderr.write('Please make sure the input file has only one sentence per line(no index!).')
        sys.stderr.write('error_sentences_path     : ' + args.error_sentence     + '\n')
        sys.stderr.write('corrected_sentences_path : ' + args.corrected_sentence + '\n')
        err_file = open(args.error_sentence,     'rb', encoding = 'utf-8')
        cor_file = open(args.corrected_sentence, 'w+', encoding = 'utf-8')

        if args.correct_verbose:
            for sentence in err_file.readlines():
                pred_sent, pred_detail = correct(sentence.strip(), args.param_ec, args.param_gd)

                sys.stderr.write('input sentence : ' + sentence + '\n')
                sys.stderr.write('pred sentence  : ' + pred_sent + '\n')
                sys.stderr.write('predict change : ' + ', '.join([i[0][0] + '-->' + i[0][1] \
                                           for i in pred_detail if i]) + '\n')

                cor_file.write(pred_sent + '\n')
        else:
            for sentence in tqdm(err_file.readlines()):
                pred_sent, pred_detail = correct(sentence.strip(), args.param_ec, args.param_gd)

                cor_file.write(pred_sent + '\n')

        cor_file.close()
        err_file.close()

        sys.stderr.write('Finishing correcting sentences.\n')


if __name__ == '__main__':
    main()







