import os
import pandas as pd
from collections import defaultdict
from tqdm import tqdm  # 进度条
from src.tool.read_save_file import open_excel, save_dataframe

from src.common_config import DATA_DIR_PATH, CONNECTOR_CHAR, \
    STAR_CHAR
from src.tool.str_related import get_tow_set_diff
from src.tool.tool import calculate_normalize_ratio
from src.tool.tokenizer import get_token_list


class LogParserByStatistics:

    def get_event_template_and_parameter(self, is_contain_chinese, token_list, token_2_frequency, event_occurrences):
        """
        功能：判断event中每个token出现的频次与event_occurrences是否相对，
             如果相等，则该token就是模板中的词；
             如果不相等，则该token就是parameter。
        :param is_contain_chinese:
        :param token_list:
        :param token_2_frequency: 记录当前event_id对应的所有token出现的频次
        :param event_occurrences:当前event出现的次数
        :return:
        """
        template_token_list = []
        parameter_set = set([])
        parameter_list = []
        star_count = 0
        for token in token_list:
            frequency = token_2_frequency[token]
            if frequency == event_occurrences: #如果该词在当前event中出现的频次等于该event出现的频次，则该词就是模板词
                template_token_list.append(token)
                continue

            template_token_list.append(STAR_CHAR) #该词是参数，用星号表示
            star_count += 1
            if token not in parameter_set: #将参数分别保存在list和set中
                parameter_set.add(token)
                parameter_list.append(token)

        connector_char = " "
        if is_contain_chinese == True:
            connector_char = ""
        event_template = connector_char.join(template_token_list)
        star_ratio = calculate_normalize_ratio(star_count, len(token_list))
        return event_template, parameter_list, star_ratio

    def update_token_2_frequency(self, token_2_frequency, token_list):
        token_set = set(token_list)
        for token in token_set:
            if token in token_2_frequency:
                token_2_frequency[token] += 1
            else:
                token_2_frequency[token] = 1
        return token_2_frequency

    def update_event_key_2_id(self, event_key, event_key_2_id):
        if event_key not in event_key_2_id:
            event_id = len(event_key_2_id)
            event_key_2_id[event_key] = event_id
        return event_key_2_id

    def update_event_id_2_occurrences(self, event_id, event_id_2_occurrences):
        if event_id not in event_id_2_occurrences:
            event_id_2_occurrences[event_id] = 1
        else:
            event_id_2_occurrences[event_id] += 1
        return event_id_2_occurrences

    def parse_log_content(self, content, event_key_2_id, event_id_2_occurrences, event_id_2_token_2_frequency):

        is_contain_chinese, substr_type_pattern, substr_detail_list, token_list = get_token_list(content)
        pattern_length = len(substr_detail_list)
        token_count = len(token_list)

        event_key = substr_type_pattern + CONNECTOR_CHAR + str(token_count)
        self.update_event_key_2_id(event_key, event_key_2_id)
        event_id = event_key_2_id[event_key]

        self.update_event_id_2_occurrences(event_id, event_id_2_occurrences)
        Occurrences = event_id_2_occurrences[event_id]

        token_2_frequency = event_id_2_token_2_frequency[event_id]
        token_2_frequency_new = self.update_token_2_frequency(token_2_frequency, token_list)
        event_id_2_token_2_frequency[event_id] = token_2_frequency_new

        event_template, parameter_list, star_ratio = self.get_event_template_and_parameter(is_contain_chinese, token_list,
                                                                               token_2_frequency, Occurrences)
        analysis_result_detail = [
                                  substr_detail_list, substr_type_pattern, pattern_length,
                                  is_contain_chinese,
                                  token_list, token_count, event_key,
                                  event_id, event_template,star_ratio, Occurrences, parameter_list]
        return analysis_result_detail


    def parse_log_file(self, raw_log_csv_path, result_file_path):
        log_item_df = open_excel(raw_log_csv_path)
        log_csv_header = ["_time", "content"]
        log_item_df = log_item_df[log_csv_header]
        analysis_result_list = []
        event_key_2_id = {}
        event_id_2_occurrences = {}
        event_id_2_token_2_frequency = defaultdict(dict)
        log_item_count = len(log_item_df)
        progress_bar = tqdm(total=log_item_count)
        for line_index, line_detail in enumerate(log_item_df.values.tolist()):
            [time_str, content] = line_detail
            progress_bar.update(1)
            if content != content:
                content = ""
            if isinstance(content,str)==False:
                content = str(content)
            #content = "终端服务器安全层在协议流中检测到错误，并已取消客户端连接。 客户端 IP: 192.168.100.132。"
            #content = "DSN3201I -PB4A ABNORMAL EOT IN PROGRESS FOR 825 825 USER=NVTWS CONNECTION-ID=UTILITY CORRELATION-ID=PIMGEKD2 825 JOBNAME=PIMGEKD2 ASID=0102 TCB=0088C840"
            analysis_result_detail = self.parse_log_content(content, event_key_2_id, event_id_2_occurrences, event_id_2_token_2_frequency)

            analysis_result_list.append(line_detail + analysis_result_detail)
        progress_bar.close()
        analysis_result_df = pd.DataFrame(analysis_result_list,
                                          columns=["_time", "content",
                                                   "子串类型明细", "子串类型模式","模式长度",
                                                   "是否包含中文",
                                                   "切分的结果", "切分后的长度","event_key",
                                                   "EventId", "EventTemplate","star_ratio", "Occurrences", "ParameterList"])
        save_dataframe(analysis_result_df, result_file_path)

    def compare_predict_with_gold(self, predict_file_path, gold_file_path, compare_result_file_path):
        predict_item_df = open_excel(predict_file_path)
        result_table_header = ["_time", "content","EventId", "EventTemplate", "Occurrences", "ParameterList"]
        predict_item_df = predict_item_df[result_table_header]
        predict_item_count = len(predict_item_df)
        print(predict_item_count)

        gold_item_df = open_excel(gold_file_path)
        gold_item_df = gold_item_df[result_table_header]
        gold_item_count = len(gold_item_df)
        print(gold_item_count)
        if predict_item_count != gold_item_count:
            print(f"---error: predict_item_count != gold_item_count, predict_item_count = {predict_item_count}, gold_item_count = {gold_item_count}")
            return None
        progress_bar = tqdm(total=gold_item_count)
        compare_result_list = []
        for row_index in range(predict_item_count):
            predict_line_detail = predict_item_df.loc[row_index].tolist()
            gold_line_detail = gold_item_df.loc[row_index].tolist()
            progress_bar.update(1)

            [time_predict, content_predict, EventId_predict, EventTemplate_predict, Occurrences_predict, ParameterList_predict] = predict_line_detail
            [time_gold, content_gold, EventId_gold, EventTemplate_gold, Occurrences_gold, ParameterList_gold] = gold_line_detail
            if time_predict != time_gold:
                print(
                    f"---error: time_predict != time_gold, time_predict = {time_predict}, time_gold = {time_gold}")
                return None
            if content_predict != content_gold:
                print(
                    f"---error: content_predict != content_gold, content_predict = {content_predict}, content_gold = {content_gold}")
                return None

            is_template_same = False
            if EventTemplate_predict == EventTemplate_gold:
                is_template_same = True

            ParameterList_predict = eval(ParameterList_predict)
            ParameterList_gold = eval(ParameterList_gold)
            is_parameter_same, intersection_set, only_in_predict_set, only_in_gold_set = get_tow_set_diff(set(ParameterList_predict), set(ParameterList_gold))
            compare_result_detail = [time_gold, content_gold, EventId_gold,
                                     EventTemplate_predict, EventTemplate_gold, is_template_same,
                                     Occurrences_gold,
                                     ParameterList_predict, ParameterList_gold, is_parameter_same, intersection_set, only_in_predict_set, only_in_gold_set]
            compare_result_list.append(compare_result_detail)
        progress_bar.close()
        compare_result_df = pd.DataFrame(compare_result_list, columns=["_time", "content","EventId",
                                                   "EventTemplate_predict", "EventTemplate_gold", "is_template_same",
                                                    "Occurrences_gold",
                                                   "ParameterList_predict", "ParameterList_gold", "is_parameter_same", "intersection_set", "only_in_predict_set", "only_in_gold_set"])
        save_dataframe(compare_result_df, compare_result_file_path)


if __name__ == '__main__':
    is_get_parse_result = True
    is_get_indicator = True
    log_parser = LogParserByStatistics()

    if is_get_parse_result:
        raw_log_csv_path = os.path.join(DATA_DIR_PATH, "english_logs.csv")
        result_file_path = os.path.join(DATA_DIR_PATH, "english_logs_parse_by_statistic.csv")
        log_parser.parse_log_file(raw_log_csv_path, result_file_path)

        raw_log_csv_path = os.path.join(DATA_DIR_PATH, "chinese_english_logs.csv")
        result_file_path = os.path.join(DATA_DIR_PATH, "chinese_english_logs_parse_by_statistic.csv")
        log_parser.parse_log_file(raw_log_csv_path, result_file_path)

    if is_get_indicator:
        raw_log_csv_path = os.path.join(DATA_DIR_PATH, "english_logs.csv")
        result_file_path = os.path.join(DATA_DIR_PATH, "english_logs_parse_by_statistic.csv")
        gold_file_path = raw_log_csv_path
        compare_result_file_path = os.path.join(DATA_DIR_PATH, "解析结果与金标准对比的结果_by_statistic.xlsx")
        log_parser.compare_predict_with_gold(result_file_path, gold_file_path,compare_result_file_path)