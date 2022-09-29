# log_parser
## 功能：
这是一个日志解析的项目，对中文、英文和中英文混杂三种类型的日志进行解析，得到每条日志的模板、参数和该模板出现的次数。

## 运行环境：
python3.7

## 运行方式：
对于中文、中英文混杂的日志，采用统计的方法进行解析，直接执行src/log_parser_by_statistic.py;

对于中文、英文和中英文混杂三种类型的日志，采用Drain3的方法进行解析，直接执行src/log_parser_by_drain3.py。

src/drain3_examples/drain_stdin_demo.py 可以从输入的日志中学习到日志模板，并且通过学习的模板对实时输入的日志进行解析，得到日志中的参数


