import os, json, random, sys
import requests

from collections import Counter


# 日志耗时装饰器
import time, datetime
import functools

def get_project_dir_path():

    # cur_path = os.getcwd()
    # print("get_project_dir_path, cur_path = {}".format(cur_path))
    # project_dir_path = os.path.abspath(os.path.join(os.getcwd(), "../.."))
    cur_file_path = os.path.abspath(__file__)
    #print("cur_file_path = {}".format(cur_file_path))
    # cur_dir_path = os.path.dirname(cur_file_path)
    # print("get_project_dir_path, cur_dir_path = {}".format(cur_dir_path))

    project_dir_path = os.path.abspath(os.path.join(cur_file_path, "../../.."))
    print("get_project_dir_path, project_dir_path = {}".format(project_dir_path))
    return project_dir_path

def merge_interval(interval_list):
    """
    区间合并，参考https://leetcode-cn.com/problems/merge-intervals/
    """
    interval_count = len(interval_list)
    if interval_count <= 1:
        return interval_list

    merge_interval_list = []
    start_acsend_intervals = sorted(interval_list, key=lambda x: x[0], reverse=False)
    [prev_interval_start, prev_interval_end] = start_acsend_intervals[0]
    for i in range(1, interval_count):
        [cur_start, cur_end] = start_acsend_intervals[i]

        if prev_interval_end < cur_start:  # [[,4],[8,]]
            merge_interval_list.append([prev_interval_start, prev_interval_end])
            prev_interval_start = cur_start
            prev_interval_end = cur_end
        else:  # prev_internal_end >= cur_start #[[1,4],[3,4]]
            prev_interval_end = max(prev_interval_end, cur_end)
    merge_interval_list.append([prev_interval_start, prev_interval_end])
    return merge_interval_list

def calculate_normalize_ratio(frequency, frequency_sum):
    """
    计算归一化的比值
    """
    if frequency_sum > 0:
        ratio = (frequency / frequency_sum)
        ratio = format(ratio, '.2f')   # 保留2位小数
    else:
        ratio = "-"
    return ratio