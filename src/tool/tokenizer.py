from src.common_config import DATA_DIR_PATH,CHINESE_REGEXP,CONNECTOR_CHAR,\
    PUNCTUATION_MARK_REGEXP,NONE_CHINESE_REGEXP, CHINESE_SUBSTR_TYPE,SPACE_SUBSTR_TYPE, ENGLISH_SUBSTR_TYPE,\
    CHINESE_SPACE_CHINESE_PATTERN,PUNCTUATION_MARK_TYPE
from src.tool.str_related import str_normalize, get_tow_set_diff
import jieba

def get_substr_pattern(content):
    substr_detail_list = []
    reg_match_list = CHINESE_REGEXP.finditer(content)

    for match_item in reg_match_list:
        match_str = match_item.group()
        (start_index, end_index) = match_item.span()
        substr_detail_list.append([start_index, end_index, match_str, CHINESE_SUBSTR_TYPE])  # 不包括end_index

    reg_match_list = PUNCTUATION_MARK_REGEXP.finditer(content)
    for match_item in reg_match_list:
        match_str = match_item.group()
        (start_index, end_index) = match_item.span()
        substr_detail_list.append([start_index, end_index, match_str, PUNCTUATION_MARK_TYPE])  # 不包括end_index

    reg_match_list = NONE_CHINESE_REGEXP.finditer(content) #提取非中文的结果
    for match_item in reg_match_list:
        match_str = match_item.group()
        (start_index, end_index) = match_item.span()
        match_str_strip = match_str.strip()

        #获取前缀空格
        match_index = match_str.find(match_str_strip)
        prefix_space_start_index = start_index
        prefix_space_end_index = prefix_space_start_index + match_index
        if prefix_space_start_index != prefix_space_end_index:
            prefix_space_str = content[prefix_space_start_index:prefix_space_end_index]
            substr_detail_list.append([prefix_space_start_index, prefix_space_end_index, prefix_space_str,
                                         SPACE_SUBSTR_TYPE])  # 不包括end_index

        #获取中间的英文字符串
        mid_substr_start_index = prefix_space_end_index
        mid_str_end_index = mid_substr_start_index + len(match_str_strip)
        if mid_substr_start_index != mid_str_end_index:
            mid_substr = content[mid_substr_start_index:mid_str_end_index]
            substr_detail_list.append( [mid_substr_start_index, mid_str_end_index, mid_substr,ENGLISH_SUBSTR_TYPE])  # 不包括end_index

        #获取结尾的空格
        suffix_space_start_index = mid_str_end_index
        suffix_space_end_index = end_index
        if suffix_space_start_index != suffix_space_end_index:
            suffix_space_str = content[suffix_space_start_index:suffix_space_end_index]
            substr_detail_list.append(
                [suffix_space_start_index, suffix_space_end_index, suffix_space_str,
                 SPACE_SUBSTR_TYPE])  # 不包括end_index

    substr_detail_list.sort(key=lambda x: x[0], reverse=False)

    substr_type_pattern = CONNECTOR_CHAR.join([item[3] for item in substr_detail_list])
    # print(substr_detail_list)
    # print(substr_type_pattern)
    return substr_detail_list, substr_type_pattern

def split_substr(substr_detail_list, need_split_substr_type, is_split_by_space):
    """

    :param substr_detail_list:
    :param need_split_substr_type: 表示哪些类型的子串需要被切分
    :param is_split_by_space: 表示是否以空格的方式来切，如果该值为False，则表示用结巴来切分
    :return:
    """
    split_list = []
    #split_substr_count = 0
    for substr_item_detail in substr_detail_list:
        [start_index, end_index, match_str, substr_type] = substr_item_detail
        if substr_type == need_split_substr_type:
            if is_split_by_space:
                temp_token_list = match_str.split()
            else:
                temp_token_list = list(jieba.cut(match_str))

            split_list.extend(temp_token_list)
        else:
            split_list.append(match_str)
    return split_list

def get_token_list(content):
    content = content.strip()
    # content = str_normalize(content)
    substr_detail_list, substr_type_pattern = get_substr_pattern(content)
    is_contain_chinese = False
    if substr_type_pattern.find(CHINESE_SUBSTR_TYPE) != -1:  # 如果模式中包含中文
        is_contain_chinese = True
    if is_contain_chinese:  # 如果模式中包含中文
        if substr_type_pattern.find(CHINESE_SPACE_CHINESE_PATTERN) != -1:  # 如果模式中包含中文空格中文，则将中文按空格切分
            token_list = split_substr(substr_detail_list, CHINESE_SUBSTR_TYPE, is_split_by_space=True)
        else:  # 情况2，中文与中文之间，没有空格隔开，则针对中文用jieba分词，英文的保持不变
            token_list = split_substr(substr_detail_list, CHINESE_SUBSTR_TYPE, is_split_by_space=False)
    else:  # 即模式中不包含中文，则对英文按空格进行切分
        token_list = split_substr(substr_detail_list, ENGLISH_SUBSTR_TYPE, is_split_by_space=True)
    return is_contain_chinese, substr_type_pattern, substr_detail_list, token_list


if __name__ == '__main__':
    content = "今天  456  名。明天"
    get_substr_pattern(content)
    content = "今天  4 56  名"
    get_substr_pattern(content)
    content = "终端服务器安全层在协议流中检测到错误，并已取消客户端连接。 客户端 IP: 192.168.100.132。"
    get_substr_pattern(content)