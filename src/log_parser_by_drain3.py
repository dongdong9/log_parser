import os
import pandas as pd
from collections import defaultdict
from tqdm import tqdm  # 进度条
from src.tool.read_save_file import open_excel, save_dataframe

from src.common_config import DATA_DIR_PATH, DEFAULT_STR_VALUE, USE_OLD_FUNCTION_EXTRACT_PARAMETER,\
    CLUSTER_ID_KEY,CLUSTER_SIZE_KEY,TEMPLATE_MINED_KEY, IS_CONTAIN_CHINESE_KEY, SUBSTR_TYPE_PATTERN_KEY, \
    SUBSTR_DETAIL_LIST_KEY, TOKEN_LIST_KEY, LOG_TEMPLATE_TOKENS_KEY

from src.tool.str_related import get_tow_set_diff
import json
import sys,os

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistence

from src.common_config import CONFIG_DIR_PATH

class LogParserByDrain3:
    def __init__(self):
        persistence_type = "FILE"
        drain3_state_bin_file_path = os.path.join(CONFIG_DIR_PATH, "drain3_state.bin")
        persistence = FilePersistence(drain3_state_bin_file_path)


        config = TemplateMinerConfig()
        drain3_ini_file_path = os.path.join(CONFIG_DIR_PATH, "drain3.ini")
        config.load(drain3_ini_file_path)
        config.profiling_enabled = False

        self.template_miner = TemplateMiner(persistence, config)
        print(f"Drain3 started with '{persistence_type}' persistence")
        print(f"{len(config.masking_instructions)} masking instructions are in use")
        print(f"Starting training mode. Reading from std-in ('q' to finish)") #yd。利用输入的一条条日志，训练得到模板

    def parse_log_content(self, log_line):
        result = self.template_miner.add_log_message(log_line)
        result_json = json.dumps(result,ensure_ascii=False)
        #print(result_json)
        # if USE_OLD_FUNCTION_EXTRACT_PARAMETER:
        #     template = result["template_mined"]
        #     params = self.template_miner.extract_parameters(template, log_line)
        # else:
        #     content_tokens = result.get(TOKEN_LIST_KEY,[])
        #     log_template_tokens = result["log_template_tokens"]
        #     params = self.template_miner.extract_parameters_by_compare(content_tokens, log_template_tokens)
        if USE_OLD_FUNCTION_EXTRACT_PARAMETER:
            # template = result["template_mined"]
            template = result.get(TEMPLATE_MINED_KEY, DEFAULT_STR_VALUE)
            params = self.template_miner.extract_parameters(template, log_line)
        else:
            content_tokens = result.get(TOKEN_LIST_KEY, [])
            # log_template_tokens = result["log_template_tokens"]
            log_template_tokens = result.get(LOG_TEMPLATE_TOKENS_KEY, [])
            params = self.template_miner.extract_parameters_by_compare(content_tokens, log_template_tokens)
        #print("Parameters: " + str(params))
        return result, params

    def parse_log_file(self, raw_log_csv_path, result_file_path):
        log_item_df = open_excel(raw_log_csv_path)
        log_csv_header = ["_time", "content"]
        log_item_df = log_item_df[log_csv_header]
        analysis_result_list = []
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
            result_dict, extract_parameter_list = self.parse_log_content(content)


            parameter_list = []
            if extract_parameter_list is not None:
                for parameter in extract_parameter_list:
                    parameter_list.append(parameter.value)

            event_id = result_dict.get(CLUSTER_ID_KEY, 1) -1
            event_template = result_dict.get(TEMPLATE_MINED_KEY, 0)
            Occurrences = result_dict.get(CLUSTER_SIZE_KEY, DEFAULT_STR_VALUE)
            substr_detail_list = result_dict.get(SUBSTR_DETAIL_LIST_KEY, DEFAULT_STR_VALUE)
            substr_type_pattern = result_dict.get(SUBSTR_TYPE_PATTERN_KEY, DEFAULT_STR_VALUE)
            pattern_length = len(substr_detail_list)
            is_contain_chinese = result_dict.get(IS_CONTAIN_CHINESE_KEY, DEFAULT_STR_VALUE)
            token_list = result_dict.get(TOKEN_LIST_KEY, DEFAULT_STR_VALUE)
            token_count = len(token_list)
            event_key = "-"
            star_ratio = "-"
            analysis_result_detail = [
                substr_detail_list, substr_type_pattern, pattern_length,
                is_contain_chinese,
                token_list, token_count, event_key,
                event_id, event_template, star_ratio, Occurrences, parameter_list]


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
    log_parser = LogParserByDrain3()

    if is_get_parse_result:
        raw_log_csv_path = os.path.join(DATA_DIR_PATH, "english_logs.csv")
        result_file_path = os.path.join(DATA_DIR_PATH, "english_logs_parse_by_drain3.csv")
        log_parser.parse_log_file(raw_log_csv_path, result_file_path)

        raw_log_csv_path = os.path.join(DATA_DIR_PATH, "chinese_english_logs.csv")
        result_file_path = os.path.join(DATA_DIR_PATH, "chinese_english_logs_parse_by_drain3.csv")
        log_parser.parse_log_file(raw_log_csv_path, result_file_path)

    if is_get_indicator:
        raw_log_csv_path = os.path.join(DATA_DIR_PATH, "english_logs.csv")
        result_file_path = os.path.join(DATA_DIR_PATH, "english_logs_parse_by_drain3.csv")
        gold_file_path = raw_log_csv_path
        compare_result_file_path = os.path.join(DATA_DIR_PATH, "解析结果与金标准对比的结果_by_drain3.xlsx")
        log_parser.compare_predict_with_gold(result_file_path, gold_file_path,compare_result_file_path)