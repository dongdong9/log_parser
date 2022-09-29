import re, os
from src.tool.tool import get_project_dir_path

PROJECT_DIR_PATH = get_project_dir_path()
DATA_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "data")
CONFIG_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "config_ini")

STAR_CHAR = "*"

DEFAULT_STR_VALUE = "-"


USE_OLD_FUNCTION_EXTRACT_PARAMETER = False

CHINESE_SUBSTR_TYPE = "中"
SPACE_SUBSTR_TYPE = "空格"
ENGLISH_SUBSTR_TYPE = "英"
PUNCTUATION_MARK_TYPE = "标点"
CONNECTOR_CHAR = "^"

CHINESE_SPACE_CHINESE_PATTERN = CONNECTOR_CHAR.join([CHINESE_SUBSTR_TYPE, SPACE_SUBSTR_TYPE,CHINESE_SUBSTR_TYPE])


#CHINESE_REGEXP = re.compile(u"([\u4e00-\u9fff|\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b]+)")
CHINESE_REGEXP = re.compile(u"([\u4e00-\u9fff]+)")
PUNCTUATION_MARK_REGEXP = re.compile(u"(。|,|，|:|：|=)")

#NONE_CHINESE_REGEXP = re.compile(u"([^\u4e00-\u9fff|\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b]+)")
NONE_CHINESE_REGEXP = re.compile(u"([^\u4e00-\u9fff|。,，:：=]+)")

CLUSTER_ID_KEY = "cluster_id"
CLUSTER_SIZE_KEY = "cluster_size"
TEMPLATE_MINED_KEY = "template_mined"
LOG_TEMPLATE_TOKENS_KEY = "log_template_tokens"
CLUSTER_COUNT_KEY = "cluster_count" #用于统计当前已经有多少个cluster了，一个cluster就是一个log template

IS_CONTAIN_CHINESE_KEY = "is_contain_chinese"
SUBSTR_TYPE_PATTERN_KEY = "substr_type_pattern"
SUBSTR_DETAIL_LIST_KEY = "substr_detail_list"
TOKEN_LIST_KEY = "token_list"