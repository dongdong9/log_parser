# SPDX-License-Identifier: MIT

import base64
import logging
import re
import time
import zlib
from typing import Optional, List, NamedTuple

import jsonpickle
from cachetools import LRUCache, cachedmethod

from drain3.drain import Drain, LogCluster
from drain3.masking import LogMasker
from drain3.persistence_handler import PersistenceHandler
from drain3.simple_profiler import SimpleProfiler, NullProfiler, Profiler
from drain3.template_miner_config import TemplateMinerConfig

logger = logging.getLogger(__name__)

config_filename = 'drain3.ini'

ExtractedParameter = NamedTuple("ExtractedParameter", [("value", str), ("mask_name", str)])


class TemplateMiner:

    def __init__(self,
                 persistence_handler: PersistenceHandler = None,
                 config: TemplateMinerConfig = None):
        """
        Wrapper for Drain with persistence and masking support

        :param persistence_handler: The type of persistence to use. When None, no persistence is applied.
        :param config: Configuration object. When none, configuration is loaded from default .ini file (if exist)
        """
        logger.info("Starting Drain3 template miner")

        if config is None:
            logger.info(f"Loading configuration from {config_filename}")
            config = TemplateMinerConfig()
            config.load(config_filename)

        self.config = config

        self.profiler: Profiler = NullProfiler()
        if self.config.profiling_enabled:
            self.profiler = SimpleProfiler()

        self.persistence_handler = persistence_handler

        param_str = self.config.mask_prefix + "*" + self.config.mask_suffix #yd。将param_str的值设为<*>
        self.drain = Drain(
            sim_th=self.config.drain_sim_th,
            depth=self.config.drain_depth,
            max_children=self.config.drain_max_children,
            max_clusters=self.config.drain_max_clusters,
            extra_delimiters=self.config.drain_extra_delimiters,
            profiler=self.profiler,
            param_str=param_str,
            parametrize_numeric_tokens=self.config.parametrize_numeric_tokens
        )
        self.masker = LogMasker(self.config.masking_instructions, self.config.mask_prefix, self.config.mask_suffix)
        self.parameter_extraction_cache = LRUCache(self.config.parameter_extraction_cache_capacity)
        self.last_save_time = time.time() #yd。表示最近一次将self.drain对象进行序列化得到state，并保存state的时间
        if persistence_handler is not None: #yd。如果持久化handler不为None，则加载state
            self.load_state()

    def load_state(self):
        """
        yd。加载之前保存的state，然后将state反序列化，用反序列化的结果来更新self.drain对象，
        :return:
        """
        # yd。这里选择不许需要之前的状态
        return

        logger.info("Checking for saved state")

        state = self.persistence_handler.load_state()
        if state is None:
            logger.info("Saved state not found")
            return

        if self.config.snapshot_compress_state:
            state = zlib.decompress(base64.b64decode(state))

        loaded_drain: Drain = jsonpickle.loads(state, keys=True)

        # json-pickle encoded keys as string by default, so we have to convert those back to int
        # this is only relevant for backwards compatibility when loading a snapshot of drain <= v0.9.1
        # which did not use json-pickle's keys=true
        if len(loaded_drain.id_to_cluster) > 0 and isinstance(next(iter(loaded_drain.id_to_cluster.keys())), str):
            loaded_drain.id_to_cluster = {int(k): v for k, v in list(loaded_drain.id_to_cluster.items())}
            if self.config.drain_max_clusters:
                cache = LRUCache(maxsize=self.config.drain_max_clusters)
                cache.update(loaded_drain.id_to_cluster)
                loaded_drain.id_to_cluster = cache

        self.drain.id_to_cluster = loaded_drain.id_to_cluster
        self.drain.clusters_counter = loaded_drain.clusters_counter
        self.drain.root_node = loaded_drain.root_node

        logger.info("Restored {0} clusters built from {1} messages".format(
            len(loaded_drain.clusters), loaded_drain.get_total_cluster_size()))

    def save_state(self, snapshot_reason):
        """
        yd。功能：将self.drain对象序列化后得到state，将state保存到指定文件中
        :param snapshot_reason:
        :return:
        """
        state = jsonpickle.dumps(self.drain, keys=True).encode('utf-8') #yd。将self.drain这个对象序列化
        if self.config.snapshot_compress_state:#yd。如果需要压缩state snapshot，则进行压缩
            state = base64.b64encode(zlib.compress(state))

        logger.info(f"Saving state of {len(self.drain.clusters)} clusters "
                    f"with {self.drain.get_total_cluster_size()} messages, {len(state)} bytes, "
                    f"reason: {snapshot_reason}")

        self.persistence_handler.save_state(state) #yd。文件持久化，即将state保存到指定路径所在的文件中

    def get_snapshot_reason(self, change_type, cluster_id):
        """
        yd。功能：获取保存snapshot的原因，主要原因有两个：
            1、change_type不为none；
            2、距离上次保存snapshot的时间超过配置的间隔时间
        :param change_type:
        :param cluster_id:
        :return:
        """
        if change_type != "none":
            return "{} ({})".format(change_type, cluster_id)

        diff_time_sec = time.time() - self.last_save_time
        if diff_time_sec >= self.config.snapshot_interval_minutes * 60:
            return "periodic"

        return None

    def add_log_message(self, log_message: str) -> dict:
        """
        yd。功能：根据当前传入的日志内容，获取对应的日志模板的logCluster
        :param log_message: 一条日志的内容
        :return:
        """
        self.profiler.start_section("total")

        if 0:
            self.profiler.start_section("mask")
            # yd。将log_message字符串中正则匹配的子串，用特定符号替换。
            # 比如将"connected to 10.0.0.1"中的ip数字用"<:IP:>"替换，返回"connected to <:IP:>"
            masked_content = self.masker.mask(log_message)
            self.profiler.end_section()
        else:
            masked_content = log_message

        self.profiler.start_section("drain")
        # yd。根据传入的masked_content，获取匹配的logCluster
        cluster, change_type, content_tokens = self.drain.add_log_message(masked_content)
        self.profiler.end_section("drain")

        result = {
            "content_tokens":content_tokens,
            "change_type": change_type,
            "cluster_id": cluster.cluster_id,
            "cluster_size": cluster.size, #yd。用于统计当前cluster匹配的日志条数
            "log_template_tokens": cluster.log_template_tokens,
            "template_mined": cluster.get_template(), #yd。返回挖掘处理的日志模板

            "cluster_count": len(self.drain.clusters) #yd。统计当前已经挖掘的模板的 总数

        }

        #yd。这里是将当前的日志模板信息的快照保存下来
        if self.persistence_handler is not None:
            self.profiler.start_section("save_state")
            snapshot_reason = self.get_snapshot_reason(change_type, cluster.cluster_id)
            if snapshot_reason:
                self.save_state(snapshot_reason)
                self.last_save_time = time.time()
            self.profiler.end_section()

        self.profiler.end_section("total")
        self.profiler.report(self.config.profiling_report_sec) #yd。这个方法啥事都没有干，可以不管
        return result

    def match(self, log_message: str, full_search_strategy="never") -> LogCluster:
        """
        Mask log message and match against an already existing cluster.
        Match shall be perfect (sim_th=1.0).
        New cluster will not be created as a result of this call, nor any cluster modifications.

        :param log_message: log message to match
        :param full_search_strategy: when to perform full cluster search.
            (1) "never" is the fastest, will always perform a tree search [O(log(n)] but might produce
            false negatives (wrong mismatches) on some edge cases;
            (2) "fallback" will perform a linear search [O(n)] among all clusters with the same token count, but only in
            case tree search found no match.
            It should not have false negatives, however tree-search may find a non-optimal match with
            more wildcard parameters than necessary;
            (3) "always" is the slowest. It will select the best match among all known clusters, by always evaluating
            all clusters with the same token count, and selecting the cluster with perfect all token match and least
            count of wildcard matches.
        :return: Matched cluster or None if no match found.
        """

        masked_content = self.masker.mask(log_message)
        matched_cluster = self.drain.match(masked_content, full_search_strategy)
        return matched_cluster

    def get_parameter_list(self, log_template: str, log_message: str) -> List[str]:
        """
        Extract parameters from a log message according to a provided template that was generated
        by calling `add_log_message()`.

        This function is deprecated. Please use extract_parameters instead.

        :param log_template: log template corresponding to the log message
        :param log_message: log message to extract parameters from
        :return: An ordered list of parameter values present in the log message.
        """

        extracted_parameters = self.extract_parameters(log_template, log_message, exact_matching=False)
        if not extracted_parameters:
            return []
        return [parameter.value for parameter in extracted_parameters]

    def extract_parameters_by_compare(self, content_tokens, log_template_tokens):
        parameter_list = []
        for token1, token2 in zip(content_tokens, log_template_tokens):
            if token1 == token2:
                continue
            extracted_parameter = ExtractedParameter(token1, mask_name="-")
            parameter_list.append(extracted_parameter)
        return parameter_list


    def extract_parameters(self,
                           log_template: str,
                           log_message: str,
                           exact_matching: bool = True) -> Optional[List[ExtractedParameter]]:
        """
        Extract parameters from a log message according to a provided template that was generated
        by calling `add_log_message()`.

        For most accurate results, it is recommended that
        - Each `MaskingInstruction` has a unique `mask_with` value,
        - No `MaskingInstruction` has a `mask_with` value of `*`,
        - The regex-patterns of `MaskingInstruction` do not use unnamed back-references;
          instead use back-references to named groups e.g. `(?P=some-name)`.

        :param log_template: log template corresponding to the log message
        :param log_message: log message to extract parameters from
        :param exact_matching: whether to apply the correct masking-patterns to match parameters, or try to approximate;
            disabling exact_matching may be faster but may lead to situations in which parameters
            are wrongly identified.
        :return: A ordered list of ExtractedParameter for the log message
            or None if log_message does not correspond to log_template.
        """
        #yd。将delimiter用空格替换
        for delimiter in self.config.drain_extra_delimiters:
            log_message = re.sub(delimiter, " ", log_message)

        template_regex, param_group_name_to_mask_name = self._get_template_parameter_extraction_regex(
            log_template, exact_matching)

        # Parameters are represented by specific named groups inside template_regex.
        parameter_match = re.match(template_regex, log_message)

        # log template does not match template
        if not parameter_match:
            return None

        # create list of extracted parameters
        extracted_parameters = []
        for group_name, parameter in parameter_match.groupdict().items(): #yd。对正则匹配的结果进行遍历
            if group_name in param_group_name_to_mask_name:
                mask_name = param_group_name_to_mask_name[group_name]
                extracted_parameter = ExtractedParameter(parameter, mask_name)
                extracted_parameters.append(extracted_parameter)

        return extracted_parameters

    @cachedmethod(lambda self: self.parameter_extraction_cache)
    def _get_template_parameter_extraction_regex(self, log_template: str, exact_matching: bool):
        """
        yd。功能：构建模板参数抽取的正则表达式
        :param log_template:
        :param exact_matching:
        :return: template_regex:
                param_group_name_to_mask_name，以dict的形式保存着正则表达式的名称和mask_name，例如{'p_0': 'HEX', 'p_1': '*', 'p_2': 'CMD', 'p_3': 'SEQ', 'p_4': 'IP', 'p_5': 'NUM', 'p_6': 'ID'}
        """
        param_group_name_to_mask_name = dict()
        param_name_counter = [0]
        #print(f"  log_template传入的值 = {log_template}")
        def get_next_param_name():
            param_group_name = "p_" + str(param_name_counter[0])
            param_name_counter[0] += 1
            return param_group_name

        # Create a named group with the respective patterns for the given mask-name.
        def create_capture_regex(_mask_name):
            allowed_patterns = []
            if exact_matching:
                # get all possible regex patterns from masking instructions that match this mask name
                masking_instructions = self.masker.instructions_by_mask_name(_mask_name)
                for mi in masking_instructions:
                    # MaskingInstruction may already contain named groups.
                    # We replace group names in those named groups, to avoid conflicts due to duplicate names.
                    if hasattr(mi, 'regex'):
                        mi_groups = mi.regex.groupindex.keys()
                        pattern = mi.pattern #yd。取出构造正则表达式时的字符串
                    else:
                        # non regex masking instructions - support only non-exact matching
                        mi_groups = []
                        pattern = ".+?"

                    for group_name in mi_groups:
                        param_group_name = get_next_param_name()

                        def replace_captured_param_name(param_pattern):
                            _search_str = param_pattern.format(group_name)
                            _replace_str = param_pattern.format(param_group_name)
                            return pattern.replace(_search_str, _replace_str)

                        pattern = replace_captured_param_name("(?P={}")
                        pattern = replace_captured_param_name("(?P<{}>")

                    # support unnamed back-references in masks (simple cases only)
                    pattern = re.sub(r"\\(?!0)\d{1,2}", r"(?:.+?)", pattern)
                    allowed_patterns.append(pattern)

            if not exact_matching or _mask_name == "*":
                allowed_patterns.append(r".+?")

            # Give each capture group a unique name to avoid conflicts.
            param_group_name = get_next_param_name()
            param_group_name_to_mask_name[param_group_name] = _mask_name
            joined_patterns = "|".join(allowed_patterns) #yd。将正则表达式join起来
            capture_regex = "(?P<{}>{})".format(param_group_name, joined_patterns)
            return capture_regex

        # For every mask in the template, replace it with a named group of all
        # possible masking-patterns it could represent (in order).
        mask_names = set(self.masker.mask_names)

        # the Drain catch-all mask
        mask_names.add("*")

        escaped_prefix = re.escape(self.masker.mask_prefix) #yd。将字符串中所有可能被解释为正则运算符的字符进行转义
        escaped_suffix = re.escape(self.masker.mask_suffix)
        template_regex = re.escape(log_template)
        #print(f"template_regex最初的值 = {template_regex}")

        # replace each mask name with a proper regex that captures it
        for mask_name in mask_names:
            search_str = escaped_prefix + re.escape(mask_name) + escaped_suffix
            while True:
                rep_str = create_capture_regex(mask_name)
                # Replace one-by-one to get a new param group name for each replacement.
                template_regex_new = template_regex.replace(search_str, rep_str, 1)
                # Break when all replaces for this mask are done.
                if template_regex_new == template_regex:
                    break
                template_regex = template_regex_new

        #print(f"template_regex处理的值 = {template_regex}")
        #yd。将正则表达式template_regex进行改造，将其中的空格替换为"\\s+"，并且在template_regex前后分别加上起始符和结束符
        # match also messages with multiple spaces or other whitespace chars between tokens
        template_regex = re.sub(r"\\ ", r"\\s+", template_regex)
        template_regex = "^" + template_regex + "$"
        return template_regex, param_group_name_to_mask_name
