import copy, re
from collections import defaultdict

from src.common_config import DEFAULT_STR_VALUE


def process_none_str(input_str):
    if input_str != input_str:
        return DEFAULT_STR_VALUE
    if input_str is None:
        return DEFAULT_STR_VALUE
    if input_str == "":
        return DEFAULT_STR_VALUE
    return input_str

def str_normalize(input_str):
    input_str = process_none_str(input_str)
    if isinstance(input_str, str):
        normalize_str = input_str.strip()
        normalize_str = normalize_str.replace("（", "(").replace("）",")")
    else:
        normalize_str = str(input_str)
    normalize_str = normalize_str.replace("\r", "").replace("\n", "")
    normalize_str = string_full_to_half(normalize_str)
    return normalize_str


def get_tow_set_diff(set_a, set_b):
    intersection_set = set_a & set_b
    only_in_a_set = set_a - intersection_set
    only_in_b_set = set_b - intersection_set
    is_tow_set_same = False
    if len(intersection_set) == len(set_a) and len(intersection_set) == len(set_b):
        is_tow_set_same = True
    return is_tow_set_same, intersection_set, only_in_a_set, only_in_b_set

def get_bracket_index(input_str, is_debug = False):
    """
    功能：获取括号的索引，按从左到右的顺序
    @param input_str 输入的字符串，例如"()))","(()", ")()())", "", "(())", "((()())"
    @return bracket_index_list，以list的形式，范围最长有效括号组合的索引，格式为[(left_bracket_index, right_bracket_index), (left_bracket_index, right_bracket_index),]
    """
    if is_debug == True:
        print("--------input_str = {}".format(input_str))
    raw_bracket_list = []
    bracket_index_list = []
    for bracket_index, temp_char in enumerate(input_str):
        if temp_char != "(" and temp_char != ")":
            continue
        raw_bracket_list.append((temp_char, bracket_index))

    left_bracket_index_stack = []
    bracket_count = len(raw_bracket_list)
    for i in range(bracket_count):
        (bracket_symbol, bracket_index) = raw_bracket_list[i]
        if bracket_symbol == "(":
            left_bracket_index_stack.append(bracket_index)
        elif bracket_symbol == ")":
            if len(left_bracket_index_stack) == 0:#如果没有左括号，则当前的有右括号是无效的
                continue
            left_bracket_index = left_bracket_index_stack.pop(-1)
            bracket_index_list.append((left_bracket_index, bracket_index))
    bracket_index_list = merge_interval(bracket_index_list)

    for target_index_pair in bracket_index_list:
        (left_bracket_index, right_bracket_index) = target_index_pair
        target_str = input_str[left_bracket_index: right_bracket_index+1]
        if is_debug == True:
            print("input_str = {0}, left_bracket_index = {1}, right_bracket_index = {2}, target_str = {3}".format(input_str, left_bracket_index, right_bracket_index, target_str))
    return bracket_index_list

def drop_bracket_content(mj_name):
    bracket_index_list = get_bracket_index(mj_name)
    right_index = len(mj_name)
    new_name = mj_name
    prefix_end_index = -1
    for temp in bracket_index_list[::-1]:

        [start_index, end_index] = temp
        new_name = new_name[:start_index] + " " + new_name[end_index+1:]
        # end_right_index = end_index + 1
        # if end_right_index == right_index:
        #     right_index = start_index
        #     suffix_bracket_content = mj_name[start_index: end_right_index]
        #     suffix_bracket_content_list.insert(0, suffix_bracket_content)
        #     prefix_end_index = start_index
        # else:
        #     break
    return new_name

def get_bracket_content_prefix(mj_name):
    """
    获取括号内容的前缀，括号内容
    """
    bracket_content_list = []
    bracket_index_list = get_bracket_index(mj_name)
    right_index = len(mj_name)
    prefix_end_index = -1
    for temp in bracket_index_list[::-1]:
        [start_index, end_index] = temp
        end_right_index = end_index + 1
        if end_right_index == right_index:
            right_index = start_index
            bracket_content = mj_name[start_index: end_right_index]
            bracket_content_list.insert(0, bracket_content)
            prefix_end_index = start_index
        else:
            break
    if prefix_end_index != -1:
        prefix_content = mj_name[:prefix_end_index]
    else:
        prefix_content = ""
    suffix_bracket_content_join = "".join(bracket_content_list)
    all_bracket_content = suffix_bracket_content_join.replace("(", "").replace(")", "").strip()
    return prefix_content, bracket_content_list, all_bracket_content

def get_regexp_match_results(input_name, to_match_regexps ):
    """
    抽取正则匹配的结果
    """
    result_list = to_match_regexps.finditer(input_name)
    match_detail_list = []
    for result_detail in result_list:
        (left_index, right_index) = result_detail.span()
        match_str = result_detail.group()
        match_detail_list.insert(0, [left_index, right_index, match_str])
    return match_detail_list

def char_full_2_half(uchar):
    """单个字符 全角转半角"""
    inside_code = ord(uchar)
    if inside_code == 0x3000:
        inside_code = 0x0020
    else:
        inside_code -= 0xfee0
    if inside_code < 0x0020 or inside_code > 0x7e: #转完之后不是半角字符返回原来的字符
        return uchar
    return chr(inside_code)

def string_full_to_half(ustring):
    """把字符串全角转半角"""
    return "".join([char_full_2_half(uchar) for uchar in ustring])

def get_regexp_match_result(to_match_regexp, temp_str):
    target_list = []
    result_list = to_match_regexp.finditer(temp_str)
    for result_detail in result_list:
        (left_index, right_index) = result_detail.span()
        match_str = result_detail.group()
        target_list.insert(0, [left_index, right_index, match_str])
    return target_list





if __name__ == "__main__":
    if 0:
        input_name = "★(甲)速效救心丸(50粒*3瓶)"
        drop_bracket_content(input_name)
    if 0:
        ustring = "维生素ｂ１２注射液"
        new_str = string_full_to_half(ustring)
        print(ustring, new_str)
