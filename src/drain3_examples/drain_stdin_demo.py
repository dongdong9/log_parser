# SPDX-License-Identifier: MIT

import json
import logging
import sys, os
from os.path import dirname

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from src.common_config import CONFIG_DIR_PATH,USE_OLD_FUNCTION_EXTRACT_PARAMETER
from src.tool.tokenizer import get_token_list

# persistence_type = "NONE"
# persistence_type = "REDIS"
# persistence_type = "KAFKA"
persistence_type = "FILE"

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

if persistence_type == "KAFKA":
    from drain3.kafka_persistence import KafkaPersistence

    persistence = KafkaPersistence("drain3_state", bootstrap_servers="localhost:9092")

elif persistence_type == "FILE":
    from drain3.file_persistence import FilePersistence
    #persistence = FilePersistence("drain3_state.bin")
    drain3_state_bin_file_path = os.path.join(CONFIG_DIR_PATH, "drain3_state.bin")
    persistence = FilePersistence(drain3_state_bin_file_path)

elif persistence_type == "REDIS":
    from drain3.redis_persistence import RedisPersistence

    persistence = RedisPersistence(redis_host='',
                                   redis_port=25061,
                                   redis_db=0,
                                   redis_pass='',
                                   is_ssl=True,
                                   redis_key="drain3_state_key")
else:
    persistence = None

config = TemplateMinerConfig()
# config.load(dirname(__file__) + "/drain3.ini")
drain3_ini_file_path = os.path.join(CONFIG_DIR_PATH, "drain3.ini")
config.load(drain3_ini_file_path)
config.profiling_enabled = False

template_miner = TemplateMiner(persistence, config)
print(f"Drain3 started with '{persistence_type}' persistence")
print(f"{len(config.masking_instructions)} masking instructions are in use")
print(f"Starting training mode. Reading from std-in ('q' to finish)") #yd。利用输入的一条条日志，训练得到模板
while True:
    log_line = input("> ")
    if log_line == 'q':
        break
    # is_contain_chinese, substr_type_pattern, substr_detail_list, token_list, token_join_str = get_token_list(log_line)
    # log_line = token_join_str
    result = template_miner.add_log_message(log_line)
    result_json = json.dumps(result,ensure_ascii=False)
    print(result_json)
    if USE_OLD_FUNCTION_EXTRACT_PARAMETER:
        template = result["template_mined"]
        params = template_miner.extract_parameters(template, log_line)
    else:
        content_tokens = result["content_tokens"]
        log_template_tokens = result["log_template_tokens"]
        params = template_miner.extract_parameters_by_compare(content_tokens, log_template_tokens)
    print("Parameters: " + str(params))
#yd。训练完毕，打印挖掘的每个cluster
print("Training done. Mined clusters:")
for cluster in template_miner.drain.clusters:
    print(cluster)

print(f"Starting inference mode, matching to pre-trained clusters. Input log lines or 'q' to finish")
while True:
    log_line = input("> ")
    if log_line == 'q':
        break
    cluster = template_miner.match(log_line)
    if cluster is None:
        print(f"No match found")
    else:
        template = cluster.get_template()
        print(f"Matched template #{cluster.cluster_id}: {template}")
        print(f"Parameters: {template_miner.get_parameter_list(template, log_line)}")
