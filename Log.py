
import os
import inspect
from termcolor import colored
from my_time import get_now_time_string  # str_to_time, time_to_str, get_now_time_datetime,


class Log_Level:
    error = 'error'
    warning = 'warning'
    info = 'info'
    debug = 'debug'
    trace = 'trace'
    f_name = 'f_name'
    def_start = 'def_start'
    data = 'data'


class Log_Mod:
    console = 0
    database = 1
    file = 2
    console_database = 3
    console_file = 4
    console_database_file = 5


class Logging:
    account_id = 'defult'
    log_file_name = 'Logging.log'
    log_table_name = 'bot_logs'
    logging_mod = Log_Mod.console
    group_id = 0
    db_obj = None

    log_string_template = '%s\t:=> %s\t:=> %s\t:=> %s\t:=> %s\t:=> %s'
    log_level = {'error', 'warning', 'info', 'debug', 'trace', 'f_name', 'data', 'def_start'}

    log_error_active = True
    log_warning_active = True
    log_info_active = True
    log_debug_active = True
    log_trace_active = False
    log_f_name_active = True
    log_data_active = True

    # check log file if not exist creat it
    def logConfig(self, group_id=None, account_id=None, log_file_name=None, log_table_name=None, logging_mod=None, db_obj=None):
        if account_id is not None:
            self.account_id = account_id
        if log_file_name is not None:
            self.log_file_name = log_file_name
        if log_table_name is not None:
            self.log_table_name = log_table_name
        if logging_mod is not None:
            self.logging_mod = logging_mod
        if db_obj is not None:
            self.db_obj = db_obj
        if group_id is not None:
            self.group_id = group_id

    def file_preparing(self):
        if self.log_file_name != '':
            if not os.path.exists(self.log_file_name):
                if os.path.dirname(self.log_file_name) != '':
                    if not os.path.exists(os.path.dirname(self.log_file_name)):
                        os.makedirs(os.path.dirname(self.log_file_name))
                f = open(self.log_file_name, 'w+', encoding='utf_8')
                f.write('this log file create at (%s) by %s\n' % (get_now_time_string(), self.account_id))
                f.write(self.log_string_template %
                        ('timestamp'.ljust(30), 'group_id'.ljust(5), 'account_id'.ljust(20),
                         'log_level'.ljust(20), 'log_text', 'log_discription'))
                f.write('\n' + ('-' * 175))
                f.close()
                self.write('log file not exist', Log_Level.error, self.log_file_name)
                self.write('log file created', Log_Level.info, self.log_file_name)

    def database_preparing(self):
        if self.db_obj is None:
            print('data base object is invalid!')
            return False

    def write(self, message, level, description='', color='grey'):

        if level not in self.log_level:
            self.write('level in function log.logging.write is invalid', Log_Level.error, level)
            return False
        log_time = get_now_time_string()
        log_string = self.log_string_template % (log_time, self.group_id, str(self.account_id).ljust(12), level.ljust(10), message, description)

        if self.logging_mod == Log_Mod.console:
            print(colored(log_string, color))

        elif self.logging_mod == Log_Mod.file:
            self.file_preparing()
            f = open(self.log_file_name, 'a+', encoding='utf_8')
            f.write('\n' + log_string)
            f.close()

        elif self.logging_mod == Log_Mod.console_file:
            print(colored(log_string, color))

            self.file_preparing()
            f = open(self.log_file_name, 'a+', encoding='utf_8')
            f.write('\n' + log_string)
            f.close()

        elif self.logging_mod == Log_Mod.database:
            if self.database_preparing() is True:
                self.db_obj.insert_log(self.account_id, log_time, level, message, description, self.log_table_name)

        elif self.logging_mod == Log_Mod.console_database:
            print(colored(log_string, color))
            if self.database_preparing() is True:
                self.db_obj.insert_log(self.account_id, log_time, level, message, description, self.log_table_name)

        elif self.logging_mod == Log_Mod.console_database_file:
            print(colored(log_string, color))
            self.file_preparing()
            f = open(self.log_file_name, 'a+', encoding='utf_8')
            f.write('\n' + log_string)
            f.close()
            if self.database_preparing() is True:
                self.db_obj.insert_log(self.account_id, log_time, level, message, description, self.log_table_name)

        return True

    def trace(self):
        if self.log_trace_active:
            stack_trace = ''
            for row in inspect.stack()[1:]:
                stack_trace = '{ ' + os.path.basename(str(row[1])) + ' , ' + str(row[2]) + ' , ' + str(row[3]) + ' } --> '+stack_trace
            stack_trace = stack_trace.rstrip(" --> ")
            log_text = '{ ' + os.path.basename(str(inspect.stack()[1][1])) + ' , ' + str(inspect.stack()[1][2]) + ' , ' + str(inspect.stack()[1][3]) + ' }'
            self.write(log_text, Log_Level.trace, stack_trace, 'blue')

    def f_name(self):
        if self.log_f_name_active:
            f_name = str(inspect.stack()[1][3])
            self.write(f_name, Log_Level.f_name, '', 'cyan')

    def error(self, message, description='', color='red'):
        if self.log_error_active:
            self.write(message, Log_Level.error, description, color)

    def warning(self, message, description='', color='magenta'):
        if self.log_warning_active:
            self.write(message, Log_Level.warning, description, color)

    def info(self, message, description='', color='green'):
        if self.log_info_active:
            self.write(message, Log_Level.info, description, color)

    def debug(self, message, description='', color='yellow'):
        if self.log_debug_active:
            self.write(message, Log_Level.debug, description, color)

    def data(self, data_name, data_value, color='green'):
        if self.log_debug_active:
            self.write(data_name, Log_Level.data, data_value, color)
