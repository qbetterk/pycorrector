# -*- coding: utf-8 -*-
import os

# word dictionary file
word_dict_path = 'data/word_dict.txt'
# word_dict_path = 'data/360wan-utf8.dict'

# word dictionary model file path, file will be built from word_freq_path
word_dict_model_path = 'data/word_dict.pkl'
# char set file
char_dict_path = 'data/char_set.txt'
# same pinyin char file
same_pinyin_text_path = 'data/same_pinyin.txt'
# pinyin model file path, file will be built from same_pinyin_text_path
same_pinyin_model_path = 'data/same_pinyin.pkl'
# same stroke file
same_stroke_text_path = 'data/same_stroke.txt'
# stroke model file path, file will be built from same_stroke_text_path
same_stroke_model_path = 'data/same_stroke.pkl'

# language model path

# language_model_path = 'data/kenlm/nlpcc_char.klm'

language_model_path = 'data/kenlm/nlpcc_char_5gram.klm'
