
from database import Database
from collect_data_multiprocessing_subclass import collect_trade_data_multi_process

from termcolor import colored
from time import sleep

from my_time import get_now_time_second


class Client:
    def __init__(self, client_id, db_info):
        self.print_color = 'green'

        self.client_id = client_id
        self.db_info = db_info

        self.db_obj = Database(db_info=self.db_info)

        self.setting = self.get_setting(True)
        if self.setting is False:
            return

    # -------------------------
    def print_c(self, text, color=None):
        try:
            if color is None:
                print(colored(text, self.print_color))
            else:
                print(colored('| ', self.print_color) + colored(text, color))
        except Exception as e:
            # self.print_c(str(e), 'red')
            print(str(e))

    # -------------------------
    def get_setting(self, is_new_loop):

        runtime_setting = self.db_obj.get_client_runtime_settings(client_id=self.client_id)

        if runtime_setting is False:
            return False

        if is_new_loop is True:
            runtime_setting['last'] = runtime_setting['first']

        if runtime_setting['last'] >= runtime_setting['end']:
            print('client on finish loop : start new loop')
            runtime_setting['last'] = runtime_setting['first']

        self.db_obj.set_client_runtime_setting(self.client_id, runtime_setting)

        return runtime_setting

    def get_database_record_count(self):
        return self.db_obj.get_database_record()

    def collect_all_share_data(self):
        new_loop = True
        max_loop = 3
        loop_number = 1
        # sum_new_record = 0
        while True:
            #  check exit condition
            if loop_number > max_loop:
                self.print_c('exit client in max loop')
                break  # exit function

            # if self.setting['last']
            if new_loop is True:
                self.print_c('loop number ' + str(loop_number), color='blue')

            else:
                if self.setting['last'] >= self.setting['end']:
                    loop_number += 1
                    self.print_c('loop number ' + str(loop_number), color='blue')

            #  load setting
            self.print_c('get setting')
            self.setting = self.get_setting(is_new_loop=new_loop)
            if self.setting is False:
                self.print_c('cant get setting: loop_number += 1')
                loop_number += 1
                continue

            #  check exit condition
            self.print_c('check exit condition')
            if self.setting['execute_status'] > 0:
                self.print_c('exit client from user')
                break  # exit function

            if new_loop is True:
                new_loop = False

            #  load wait list from server
            self.print_c('load wait list')

            # print('self.setting[last]:{}'.format(self.setting['last']))
            # print('self.setting[offset]:{}'.format(self.setting['offset']))
            # print('self.setting[end]:{}'.format(self.setting['end']))

            # calc offset
            if self.setting['last'] + self.setting['offset'] > self.setting['end']:
                offset = self.setting['end'] - self.setting['first']
            else:
                offset = self.setting['last'] + self.setting['offset'] - self.setting['first']

            # print('offset:{}'.format(offset))

            # گرتن لیست روز نماد از سرور
            wait_list = self.db_obj.get_wait_list(start_index=self.setting['first'], offset=offset)

            # print(wait_list)
            # print(len(wait_list))
            # wait_list=()
            if wait_list is False:
                self.print_c('cant get wait list from server')
                continue

            # update setting
            self.setting['last'] = self.setting['first'] + offset
            self.print_c('save setting')
            self.db_obj.set_client_runtime_setting(client_id=self.client_id, data=self.setting)
            # sleep(7)

            if len(wait_list) > 0:
                self.print_c('collect data')
                # print(wait_list)
                # گرفتن تعداد رکوردهای دیتابیس
                # before_record_count, err = self.get_database_record_count()

                # جمع آوری اطلاعات
                # self.collect_data(wait_list)  # جمع آوری اطلاعات
                collect_data_obj = collect_trade_data_multi_process(database_info=self.db_info,
                                                                    max_process=self.setting['max_process'],
                                                                    wait_list=wait_list,
                                                                    client_id=self.client_id)

                collect_data_obj.run_collect_all_share_data()

                # گرفتن تعداد رکوردهای دیتابیس
                # after_record_count, err = self.get_database_record_count()

                # if before_record_count > after_record_count:
                #    sum_new_record += (before_record_count - after_record_count)
                # else:
                #    sum_new_record += (after_record_count - before_record_count)

                # print('before record count: {}'.format(before_record_count))
                # print('after record count: {}'.format(after_record_count))
                # print('sum new record: {}'.format(sum_new_record))
    # ---------------------------------------------------
            sleep(1)
            # print('end one loop')
            # sleep(10)

    def collect_all_shares_info(self):  # multi processing
        collect_data_obj = collect_trade_data_multi_process(database_info=self.db_info,
                                                            max_process=self.setting['max_process'],
                                                            wait_list=list(),
                                                            client_id=self.client_id)

        self.print_c(1)
        res = collect_data_obj.run_collect_all_shares_info()

        if res is False:
            collect_data_obj = None
            # sleep(20)
        return res

    def collect_all_shares_info_single_processing(self):  # single processing
        from tsetmc import Tsetmc

        obj = Tsetmc(id=self.client_id, db_info=self.db_info, lock=None, wait_list=None, complete_list=None,
                     running_list=None, fail_list=None, status={}, log_file_name=None, log_table_name=None,
                     logging_mod=None, log_obj=None, excel_files_path=None)

        res = obj.collect_all_shares_info()

        print(res)

    def collect_all_index_daily_data(self):
        from tsetmc import Tsetmc

        obj = Tsetmc(id=self.client_id, db_info=self.db_info, lock=None, wait_list=None, complete_list=None,
                     running_list=None, fail_list=None, status={}, log_file_name=None, log_table_name=None,
                     logging_mod=None, log_obj=None, excel_files_path=None)

        res = obj.collect_all_index_daily_data(excel_path='', mod=1)

        print(res)

    def find_shares_fail_source_data(self, latest_day=None):
        # get candidate list
        #  load setting
        self.print_c('get setting')
        self.setting = self.get_setting(is_new_loop=False)
        if self.setting is False:
            self.print_c('cant get setting')
            return False, 'cant get setting'

        #  check exit condition
        self.print_c('check exit condition')
        if self.setting['execute_status'] > 0:
            self.print_c('exit client from user')
            return True, 'exit client from user'

        #  load latest day from server
        if latest_day is None:
            latest_day = self.db_obj.get_latest_open_day()
            if latest_day is False:
                self.print_c('cant get latest_day')
                return False, 'cant get latest_day'

        #  load wait list from server
        self.print_c('load wait list')
        wait_list = self.db_obj.get_share_closed_list(end_date=latest_day)
        if wait_list is False:
            self.print_c('cant get wait list from server')
            return False, 'cant get wait list from server'

        # update setting
        self.db_obj.set_client_runtime_setting(client_id=self.client_id, data=self.setting)

        if len(wait_list) > 0:
            self.print_c('find shares fail source data')

            # run function to test list
            collect_data_obj = collect_trade_data_multi_process(database_info=self.db_info,
                                                                max_process=self.setting['max_process'],
                                                                wait_list=wait_list,
                                                                client_id=self.client_id)

            res = collect_data_obj.run_find_shares_fail_source_data(latest_day=latest_day)

            if res is False:
                return res, 'error on run_find_shares_fail_source_data() function'

            return res, None

        return True, 'empty candidate list'

    # ====================
    def test_db_function_negative_volumn(self):
        now_total = get_now_time_second()
        i = 0
        symbols = self.db_obj.get_all_share_info()
        print('total symbol: {}'.format(len(symbols)))
        for symbol in symbols:
            now = get_now_time_second()
            i = i + 1
            res = self.db_obj.get_all_fail_sub_trade(en_symbol_12_digit_code=symbol[0])

            if res is not False:
                for item in res:
                    self.db_obj.collect_all_share_data_rollback(en_symbol_12_digit_code=item[0], tsetmc_id=1, date_m=item[1], error_msg='for negative volume', error_code=9000)
                print('{}: en_symbol_12_digit_code: {}  day_count: {}  runtime: {}'.format(i, symbol[0], len(res), get_now_time_second() - now))
            else:
                print('{}: en_symbol_12_digit_code: {}  day_count: {}  runtime: {}'.format(i, symbol[0], 'fail', get_now_time_second()-now))

        print(get_now_time_second()-now_total)

    def test_db_function_transfer(self,source_table,destination_table):
        now_total = get_now_time_second()
        i = 0
        symbol = self.db_obj.get_all_share_info()
        #source_table='share_sub_trad_data'
        #destination_table='share_sub_trad_data_backup'
        print('total symbol: {}'.format(len(symbol)))
        for item in symbol:
            now = get_now_time_second()
            i= i+1
            self.db_obj.transfer_share_sub_trad_data(source_table=source_table, destination_table=destination_table, en_symbol_12_digit_code=item[0])
            print('{}: en_symbol_12_digit_code: {}  runtime: {}'.format(i, item[0], get_now_time_second()-now))
            #sleep(10)

        print(get_now_time_second()-now_total)


        # ----------------
        # res = self.db_obj.get_wait_list(start_index=0, offset=10)
        #res = self.db_obj.test()
        #print(res)
        #print(len(res))

    def get_table_records(self, table_name):
        print(self.db_obj.get_table_records_count(table_name))
    # ====================
    def collect_data(self, wait_list):
        collect_data_obj = collect_trade_data_multi_process(database_info=self.db_info,
                                                            max_process=self.setting['max_process'],
                                                            wait_list=wait_list,
                                                            client_id=self.client_id)

        self.print_c(1)
        res = collect_data_obj.run_collect_all_share_data()

        if res is False:
            collect_data_obj = None
            # sleep(20)
        return res
