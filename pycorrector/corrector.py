# -*- coding: utf-8 -*-
# Author: XuMing <xuming624@qq.com>
# Brief: corrector with spell and stroke
import codecs
import os
import pdb
import time
from collections import defaultdict

from pypinyin import lazy_pinyin

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

pwd_path = os.path.abspath(os.path.dirname(__file__))
char_dict_path = os.path.join(pwd_path, config.char_dict_path)
word_dict_path = os.path.join(pwd_path, config.word_dict_path)

default_logger = get_logger(__file__)


def load_char_dict(path):
    char_dict = ''
    with codecs.open(path, 'r', encoding='utf-8') as f:
        for w in f:
            char_dict += w.strip()
    return char_dict

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

cn_char_set = load_char_dict(char_dict_path)

# # word dictionary
cn_word_set = load_word_dict(word_dict_path)
# word_dict_model_path = os.path.join(pwd_path, config.word_dict_model_path)
# if os.path.exists(word_dict_model_path):
#     cn_word_set = load_pkl(word_dict_model_path)
# else:
#     default_logger.debug('load word dict from text file:', word_dict_model_path)
#     cn_word_set = load_word_dict(word_dict_path)
#     dump_pkl(cn_word_set, word_dict_model_path)


# similar pronuciation
same_pinyin_text_path = os.path.join(pwd_path, config.same_pinyin_text_path)
same_pinyin_model_path = os.path.join(pwd_path, config.same_pinyin_model_path)
if os.path.exists(same_pinyin_model_path):
    same_pinyin = load_pkl(same_pinyin_model_path)
else:
    default_logger.debug('load same pinyin from text file:', same_pinyin_text_path)
    same_pinyin = load_same_pinyin(same_pinyin_text_path)
    # pdb.set_trace()
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


def get_same_pinyin(char):
    """
    取同音字
    :param char:
    :return:
    """
    return same_pinyin.get(char, set())


def get_same_stroke(char):
    """
    取形似字
    :param char:
    :return:
    """
    return same_stroke.get(char, set())


def edit_distance_word(word, char_set):
    """
    all edits that are one edit away from 'word'
    :param word:
    :param char_set:
    :return:
    """
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in char_set]
    return set(transposes + replaces)


def known(words):
    return set(word for word in words if word in word_freq)


def get_confusion_char_set(c):
    confusion_char_set = get_same_pinyin(c).union(get_same_stroke(c))
    if not confusion_char_set:
        confusion_char_set = set()
    return confusion_char_set

def get_confusion_two_char_set(word):
    return set([char_1 + char_2 for char_1 in get_confusion_char_set(word[0]) \
                                for char_2 in get_confusion_char_set(word[1]) \
                                if char_1 + char_2 in cn_word_set])



def get_confusion_word_set(word):
    confusion_word_set = set()
    candidate_words = list(known(edit_distance_word(word, cn_char_set)))
    for candidate_word in candidate_words:
        if lazy_pinyin(candidate_word) == lazy_pinyin(word):
            # same pinyin
            confusion_word_set.add(candidate_word)
    # #####################
    # print(word)
    # print(confusion_word_set)
    # pdb.set_trace()
    # #####################
    return confusion_word_set


def _generate_items(sentence, idx, word, fraction=1):
    candidates_1_order = []
    candidates_2_order = []
    candidates_3_order = []


    candidates_1_order.extend(get_confusion_word_set(word))

    # #####################
    # if candidates_1_order:
    #     print(candidates_1_order)
    #     pdb.set_trace()
    # #####################

    if len(word) == 1:
        confusion = [i for i in get_confusion_char_set(word[0]) if i]
        candidates_2_order.extend(confusion)

    if len(word) > 1:

        def combine_confusion_char(word, input_str, result, depth):
            # # go over all cases (quite slow when len(word) >=3!!!!)
            if depth != len(word):
                for char in get_confusion_char_set(word[depth]):
                    result = combine_confusion_char(word, input_str + char, result, depth + 1)
            elif len(word) == 2:
                if input_str in cn_word_set:
                    result.append(input_str)
            elif len(word) > 2:
                flag = True
                tokens = tokenize(input_str)

                if len(tokens) == len(word):
                    flag = False
                else:
                    for token, b_idx, e_idx in tokens:
                        if len(token) > 1 and token not in cn_word_set:
                            flag = False
                if flag:
                    result.append(input_str)
            return result

        def combine_two_confusion_char(word):
            # # assuming there is only two char to change
            # # definitely not the final version, need to be fixed!!!!
            result = []
            for i in range(len(word) - 1):
                for j in range(i + 1,len(word)):
                    result.extend([word[: i] + i_word + word[i + 1: j] + j_word + word[j + 1:] \
                                   for i_word in get_confusion_char_set(word[i]) if i_word \
                                   for j_word in get_confusion_char_set(word[j]) if j_word])
            return result

        def confusion_set(sentence, idx, word):
            # based on token and bigram model
            ##!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!@######
            # # TO DO ##
            ##!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!@######
            result = []
            tokens = tokenize(sentence)

            def get_token(i, tokens):
                for token, b_idx, e_idx in tokens:
                    if b_idx <= i < e_idx:
                        return (token, b_idx, e_idx)

            idx = list(range(int(idx.split(',')[0]), int(idx.split(',')[1])))

            conf_tokens = sorted(set([get_token(i, tokens) for i in idx]), \
                                                    key = lambda x: x[1])


            print(conf_tokens)
            # print(tokens)
            print(idx, word)
            pdb.set_trace()





            return result


        # confusion = confusion_set(sentence, idx, word)
        confusion  = combine_two_confusion_char(word)
        # confusion = combine_confusion_char(word, '', [], 0)
        candidates_2_order.extend(confusion)


        # # same first pinyin
        # confusion = [i + word[1:] for i in get_confusion_char_set(word[0]) if i]
        # candidates_2_order.extend(confusion)

        # # same last pinyin
        # confusion = [word[:-1] + i for i in get_confusion_char_set(word[-1]) if i]
        # candidates_2_order.extend(confusion)


        # if len(word) > 2:
        #     # same mid char pinyin
        #     # for idx in range(1,len(word) - 1):
        #     #     confusion = [word[:idx] + i + word[idx + 1:] for i in get_confusion_char_set(word[idx])]
        #     confusion = [word[0] + i + word[2:] for i in get_confusion_char_set(word[1])]
        #     candidates_3_order.extend(confusion)

        #     # same first word pinyin
        #     confusion_word = [i + word[-1] for i in get_confusion_word_set(word[:-1])]
        #     candidates_1_order.extend(confusion_word)

        #     # same last word pinyin
        #     confusion_word = [word[0] + i for i in get_confusion_word_set(word[1:])]
        #     candidates_1_order.extend(confusion_word)


        # #####################
        # print(candidates_2_order)
        # print(word, len(candidates_2_order))
        # pdb.set_trace()
        # ####################



    # add all confusion word list
    confusion_word_set = set(candidates_1_order + candidates_2_order + candidates_3_order)
    confusion_word_list = [item for item in confusion_word_set if is_chinese_string(item)]
    confusion_sorted = sorted(confusion_word_list, key=lambda k: \
        get_frequency(k), reverse=True)

    # #####################
    # print(confusion_word_set)
    # # print(confusion_sorted)
    # pdb.set_trace()
    # #####################

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



def _correct_item(sentence, idx, item):
    """
    纠正错误，逐词处理
    :param sentence:
    :param idx:
    :param item:
    :return: corrected word 修正的词语
    """

    #################################################################
    cor_start_time = time.time()
    #################################################################

    corrected_sent = sentence
    if not is_chinese_string(item):
        # print(item)
        return corrected_sent, []
    # 取得所有可能正确的词
    maybe_error_items = _generate_items(sentence, idx, item)

    ##################################################################
    get_cand_time = time.time()
    # print("getting candidate time : --- %s seconds ---" % (get_cand_time - cor_start_time))
    # ##################################################################

    # #####################
    # print(maybe_error_items)
    # pdb.set_trace()
    # #####################

    if not maybe_error_items:
        return corrected_sent, []
    ids = idx.split(',')
    begin_id = int(ids[0])
    end_id = int(ids[-1]) if len(ids) > 1 else int(ids[0]) + 1
    before = sentence[:begin_id]
    after = sentence[end_id:]

    def count_diff(str1, str2):
        # # assuming len(str1) == len(str2)
        count = 0
        if len(str1) != len(str2):
            print(str1)
            print(str2)
            pdb.set_trace()
        for i in range(len(str1)):
            if str1[i] != str2[i]:
                count += 1
        return count

    ######### !!!!!!!!!!!!! ###############
    factor = 5
    # ####################
    # # print(maybe_error_items)
    # print(item)
    # pdb.set_trace()
    # ####################

    #########################################
    # # edit cost
    #########################################
    min_score = get_ppl_score(list(before + item + after), mode=trigram_char) \
                            + factor * count_diff(item, item)
    corrected_item = item
    for k in maybe_error_items:
        score = get_ppl_score(list(before + k + after), mode=trigram_char) \
                            + factor * count_diff(item, k)
        if score < min_score:
            corrected_item = k
            min_score = score

    # corrected_item = min(maybe_error_items,
    #                      key=lambda \
    #                      k: get_ppl_score(list(before + k + after), mode=trigram_char) \
    #                         + factor * count_diff(item, k))


    # #####################
    # print(maybe_error_items)
    # print(corrected_item)
    # pdb.set_trace()
    # #####################
    wrongs, rights, begin_idx, end_idx = [], [], [], []
    if corrected_item != item:
        corrected_sent = before + corrected_item + after
        # default_logger.debug('pred:', item, '=>', corrected_item)
        wrongs.append(item)
        rights.append(corrected_item)
        begin_idx.append(begin_id)
        end_idx.append(end_id)
    detail = list(zip(wrongs, rights, begin_idx, end_idx))

    ##################################################################
    # eval_cand_time = time.time()
    # print("evaluating candidate time : --- %s seconds ---" % (eval_cand_time - get_cand_time))
    ##################################################################

    return corrected_sent, detail



def correct(sentence):
    """

    """
    ##################################################################
    # start_time = time.time()
    # print("--- %s seconds ---" % start_time)
    ##################################################################

    detail = []
    # pdb.set_trace()
    maybe_error_ids = get_valid_sub_array(sentence, 
                                          get_sub_array(detect(sentence)))
    # maybe_error_ids = get_valid_sub_array(sentence, detect(sentence))

    # ###################
    # print('maybe_error_ids : ', maybe_error_ids)
    # print([sentence[i[0]:i[1]] for i in maybe_error_ids])
    # pdb.set_trace()
    # ###################
    # ##################################################################
    # detect_time = time.time()
    # print("detect time: --- %s seconds ---" % (detect_time - start_time))
    # ##################################################################


    index_char_dict = dict()
    for index in maybe_error_ids:
        if len(index) == 1:

            index_char_dict[','.join(map(str, index))] = sentence[index[0]]
        else:

            index_char_dict[','.join(map(str, index))] = sentence[index[0]:index[-1]]

    for index, item in index_char_dict.items():


        # #####################
        # print(index_char_dict)
        # pdb.set_trace()
        # #####################

        sentence, detail_word = _correct_item(sentence, index, item)
        # print(detail_word)
        if detail_word:
            detail.append(detail_word)

    # ##################################################################
    # predict_time = time.time()
    # # print("correct time : --- %s seconds ---" % (predict_time - detect_time))
    # ##################################################################

    # #####################
    # print(index_char_dict)
    # pdb.set_trace()
    # #####################

    return sentence, detail
