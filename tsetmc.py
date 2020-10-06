# import database
import database
from Log import *
from date_converter import jalali_to_gregorian_int, gregorian_to_jalali_int
from my_time import get_now_time_second
import xlrd
from glob import glob
import requests
from multiprocessing import current_process

import threading
import ast


class My_Response:
    status_code = 0
    error = ''

    def Status_code(self, code):
        self.status_code = code

    def Error(self, error):
        self.error = error


class Tsetmc:

    def __init__(self, id, db_info, lock, wait_list, complete_list, running_list, fail_list, status,
                 log_file_name=None, log_table_name=None, logging_mod=None, log_obj=None, excel_files_path=None):
        self.tsetmc_base_url = 'http://www.tsetmc.com/Loader.aspx'
        self.id = id
        self.obj_status = dict()

        self.wait_list = wait_list
        self.complete_list = complete_list
        self.running_list = running_list
        self.fail_list = fail_list
        self.lock = lock
        self.status = status
        self.status[self.id] = self.obj_status
        self.set_status('stop_flag', False)
        self.set_status('last_run_time', get_now_time_second())

        # database param
        self.db = None
        # ------------------------------
        # log param
        self.log_file_name = 'Logging.log'
        self.log_table_name = 'bot_log'
        self.logging_mod = Log_Mod.console
        self.log = None
        # ----- create log object -------------------------
        if log_file_name is not None:
            self.log_file_name = log_file_name
        if log_table_name is not None:
            self.log_table_name = log_table_name
        if logging_mod is not None:
            self.logging_mod = logging_mod
        if log_obj is None:
            self.log = Logging()
            self.log.logConfig(log_file_name=self.log_file_name, log_table_name=self.log_table_name,
                               logging_mod=self.logging_mod, db_obj=self.db)
        else:
            self.log = log_obj

        # ----- create database object -------------------------
        self.db = database.Database(db_info=db_info, log_obj=self.log)
        if self.db is None:
            return
        # ------------------------------
        if excel_files_path is not None:
            self.excel_files_path = excel_files_path

        self.print_color = 'green'
        self.request_obj = requests
        self.request_obj_timeout = (100, 180)
        # self.request_obj_header = {'User-Agent': 'Mozilla/5.0 (X11; CentOS; Linux x86_64) AppleWebKit/537.36 '
         #                                        '(KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36'}

    # -------------------------------
    def print_c(self, text, color=None):
        try:
            if color is None:
                print(colored(text, self.print_color))
            else:
                print(colored('| ', self.print_color) + colored(text, color))
        except Exception as e:
            self.print_c(str(e), 'red')

    def set_status(self, item, value):
        self.obj_status = self.status[self.id]
        self.obj_status[item] = value
        self.status[self.id] = self.obj_status

    def get_status(self, item):
        self.obj_status = self.status[self.id]
        return self.obj_status[item]

    def get_var_list(self, response, var_name):
        # fins start position
        start_pos = response.text.find(var_name)
        if start_pos < 0:
            result = False
            error = 'cant find start position'
            return result, error

        start_pos += len(var_name)

        # fins end position
        end_pos = response.text.find(';', start_pos)
        if end_pos < 0:
            result = False
            error = 'cant find end position'
            return result, error

        #if result is True:
        var_str = str( response.text[start_pos:end_pos])
        if len(var_str) > 15000000:
            result = False
            error = 'cant get list: much long list'
            return result, error

        try:
            # self.print_c('{3}  start_pos:{0}  end_pos:{1}  var_str_len:{2}'.format(start_pos, end_pos, len(var_str), var_name))
            var_list = ast.literal_eval(var_str)
            result = var_list
            error = None
        except Exception as e:
            result = False
            error = 'get_var_list error: {0}'.format(str(e))

        return result, error

    # -------------------
    def get_web_data(self, url, timeout=None):
        try:
            if timeout is None:
                return self.request_obj.get(url, timeout=self.request_obj_timeout)
                # return self.request_obj.get(url, headers=self.request_obj_header, timeout=self.request_obj_timeout)
            else:
                return self.request_obj.get(url, timeout=timeout)
                # return self.request_obj.get(url, headers=self.request_obj_header, timeout=timeout)
        except Exception as e:
            a = My_Response()
            a.Status_code(100)
            a.Error(e)
            return a

        # return response
        # if response.status_code == 200:
        #    return True, response
        # else:
        #    return False, response

    # -------------------
    def collect_all_share_data(self):
        lock_status = False
        self.print_c('worker: {0} :{1}'.format(current_process().name, 'start run_collect_all_share_data function'))

        start_time = get_now_time_second()

        while self.get_status('stop_flag') is False:
            self.set_status('last_run_time', get_now_time_second())

            self.lock.acquire()
            lock_status = True

            # check exit condition
            if len(self.wait_list) <= 0:
                self.lock.release()
                lock_status = False
                self.print_c('worker: {0} :{1}'.format(current_process().name, 'wait list empty'))
                break

            #  گرفتن یک آیتم
            # get new item
            try:
                self.current_running_share = None
                self.current_running_share = self.wait_list.pop()
                self.running_list.append(self.current_running_share)
                self.lock.release()
                lock_status = False

            except Exception as e:
                if self.current_running_share is not None: # error in running_list append item
                    if self.current_running_share not in self.wait_list:
                        self.wait_list.append(self.current_running_share)

                self.current_running_share = None
                self.lock.release()
                lock_status = False
                self.print_c('worker: {0} :{1} ;{2}'.format(current_process().name, 'get new share : fail', str(e)))
                continue

            self.set_status('current_running_share', self.current_running_share)

            en_symbol_12_digit_code = self.current_running_share[0]
            tsetmc_id = self.current_running_share[1]
            date_m = self.current_running_share[2]

            self.set_status('tsetmc_id_date_m', str(tsetmc_id) + ':' + str(date_m))
            self.set_status('en_symbol_12_digit_code', str(en_symbol_12_digit_code))
            self.set_status('tsetmc_id', str(tsetmc_id))
            self.set_status('date_m', str(date_m))

            try:
                self.print_c('worker: {0} :{1}'.format(current_process().name, 'start collect data'))
                self.set_status('state', 'running')
                result, error = self.get_share_data(self.current_running_share)

                if result is False:
                    self.print_c('--- result: {0}, error: {1}'.format(result, error))
                    raise Exception(error)

                self.lock.acquire()
                lock_status = True
                self.running_list.remove(self.current_running_share)
                self.complete_list.append(self.current_running_share)
                self.lock.release()
                lock_status = False

                self.print_c('worker: {0} :{1}'.format(current_process().name, 'end collect data'))

            except Exception  as e:
                # sleep(5)
                if lock_status is True:
                    self.print_c('worker {0} except: lock status: {1} : {2} :{3}'.format(str(self.id), True, 13, str(e)))
                    self.set_status('state', 'failing')
                    self.lock.release()
                else:
                    self.print_c('worker {0} except: lock status: {1} : {2} :{3}'.format(str(self.id), False, 14, e))
                    self.set_status('state', 'failing')

                try:
                    self.print_c('worker: {0} : except: {1}'.format(current_process().name, 'rollback data'))
                    self.db.collect_all_share_data_rollback(en_symbol_12_digit_code, tsetmc_id, date_m)
                finally:
                    self.lock.acquire()
                    self.running_list.remove(self.current_running_share)
                    self.fail_list.append(self.current_running_share)
                    self.lock.release()
                    self.print_c('worker: {0} :{1}'.format(current_process().name, 'fail'))

        self.print_c('worker: {0} :{1}'.format(current_process().name, 'quit'))

        end_time = get_now_time_second()

        self.print_c('runtime:{0}'.format(end_time - start_time), color='red')

        return True

    def get_share_data(self, share_info):
        result = None
        error = None

        en_symbol_12_digit_code = share_info[0]
        tsetmc_id = share_info[1]
        date_m = share_info[2]

        url = 'http://cdn.tsetmc.com/Loader.aspx?ParTree=15131P&i={0}&d={1}'.format(tsetmc_id, date_m)
        response = self.get_web_data(url)

        # check response code
        if response.status_code != 200:
            error = 'html error code:{0}'.format(response.status_code)
            result = False
            return result, error

        # ------------------------------------
        # get all data list
        # var_name = 'var IntraDayPriceData='  # ---- کندل های نمودار -----
        # var_name = 'var ShareHolderData='  # --- سهامداران ابتدای روز -----
        var_name = 'var InstSimpleData='  # ---- اطلاعات نمودار ----
        share_info_data, share_info_data_error = self.get_var_list(response, var_name)
        if share_info_data_error is not None:
            error = share_info_data_error
            result = False
            return result, error

        var_name = 'var IntraTradeData='  # ---- ریز معاملات ------
        sub_trade_data, sub_trade_data_error = self.get_var_list(response, var_name)
        if sub_trade_data_error is not None:
            error = sub_trade_data_error
            result = False
            return result, error

        var_name = 'var ShareHolderDataYesterday='  # --- سهامداران انتهای روز ---
        share_holder_data, share_holder_data_error = self.get_var_list(response, var_name)
        if share_holder_data_error is not None:
            error = share_holder_data_error
            result = False
            return result, error
        # add date_m to list
        for i in share_holder_data:
            i[4] = date_m

        var_name = 'var ClientTypeData='  # --- حقیقی حقوقی -----
        person_legal_data, person_legal_data_error = self.get_var_list(response, var_name)
        if person_legal_data_error is not None:
            error = person_legal_data_error
            result = False
            return result, error

        var_name = 'var BestLimitData='  # --- پیشنهاد های خرید و فروش -----
        buy_sell_order_data, buy_sell_order_data_error = self.get_var_list(response, var_name)
        if buy_sell_order_data_error is not None:
            error = buy_sell_order_data_error
            result = False
            return result, error

        var_name = 'var ClosingPriceData='  # ---- اطلاعات ثانیه ای----
        closing_price_data, closing_price_data_error = self.get_var_list(response, var_name)
        if closing_price_data_error is not None:
            error = closing_price_data_error
            result = False
            return result, error

        var_name = 'var InstrumentStateData='  # ---- اطلاعات تغییر وضعیت نماد -----
        instrument_state_data, instrument_state_data_error = self.get_var_list(response, var_name)
        if instrument_state_data_error is not None:
            error = instrument_state_data_error
            result = False
            return result, error

        # ------------------------------------
        # check exit status
        if len(instrument_state_data) == 0:  # پذیرش نشده
            lower_than_start_accept_date = date_m
            self.set_start_accept_date(en_symbol_12_digit_code, lower_than_start_accept_date)
            error = None
            result = True
            return result, error

        if len(closing_price_data) == 0:  # روز غیر معاملاتی
            candidate_end_accept_date = date_m  # کاندید روز حذف نماد
            self.set_end_accept_date(en_symbol_12_digit_code, candidate_end_accept_date)
            error = None
            result = True
            return result, error

        # ------------------------------------
        # calculate daily data from sub trade date
        first_price = 0
        last_price = 0
        min_price = 0
        max_price = 0
        end_price = 0
        trade_count = 0
        trade_volume = 0
        trade_value = 0
        last_trade_time = 0
        yesterday_price = int(closing_price_data[0][5])

        legal_buy_count = 0
        legal_buy_volume = 0
        legal_buy_value = 0
        legal_buy_avg_price = 0
        person_buy_count = 0
        person_buy_volume = 0
        person_buy_value = 0
        person_buy_avg_price = 0
        legal_sell_count = 0
        legal_sell_volume = 0
        legal_sell_value = 0
        legal_sell_avg_price = 0
        person_sell_count = 0
        person_sell_volume = 0
        person_sell_value = 0
        person_sell_avg_price = 0

        status = ''
        share_count = int(share_info_data[8])
        base_volume = int(share_info_data[9])

        # ----------------
        sub_trade_data_list = list()

        min_num = len(sub_trade_data)
        max_num = 0

        for item in sub_trade_data:
            # ---------
            num = int(item[0])
            time = int(item[1].replace(':', ''))
            volume = int(item[2])
            price = int(item[3])
            flag = int(item[4])

            # existing data
            if sub_trade_data_list.count([time, num, volume, price, flag]) > 0:
                continue

            sub_trade_data_list.append([time, num, volume, price, flag])

            if len(sub_trade_data_list) == 1:
                min_price = price
                max_price = price

            # ---------------
            if flag == 0:

                if num <= min_num:
                    min_num = num
                    first_price = price

                if num >= max_num:
                    max_num = num
                    last_price = price
                    last_trade_time = time

                if min_price > price:
                    min_price = price

                if max_price < price:
                    max_price = price

                trade_volume += volume
                trade_value += volume * price

                trade_count += 1

            if trade_count % 100 == 0:
                self.set_status('last_run_time', get_now_time_second())
                #   self.print_c('sub_trade_data loop count: {0}'.format(trade_count / 100))

        if trade_volume > 0:
            if trade_volume < base_volume:
                end_price = round(((trade_value / trade_volume) - yesterday_price) * (trade_volume / base_volume) +
                                  yesterday_price)
            else:
                end_price = round(trade_value / trade_volume)
        else:
            # ممکن است ریز معاملات خالی باشد
            if len(closing_price_data) > 1:
                #print(1)
                # fail in sub trade date
                #for item in closing_price_data:
                for i in range(len(closing_price_data)):
                    if i == 0:
                        #print(2)
                        continue
                    # dt = str(closing_price_data[i][0]).split(' ')
                    # time = int(dt[1].replace(':', ''))
                    time = int(closing_price_data[i][12])
                    num = int(closing_price_data[i][8])
                    volume = int(closing_price_data[i][9]) - int(closing_price_data[i - 1][9])
                    # price = (int(closing_price_data[i][10]) - int(closing_price_data[i - 1][10])) / volume
                    price = int(closing_price_data[i][2])
                    flag = 0

                    if sub_trade_data_list.count([time, num, volume, price, flag]) > 0:
                        #print(3)
                        continue

                    sub_trade_data_list.append([time, num, volume, price, flag])
                    # ----------

                min_price = int(closing_price_data[-1][7])
                max_price = int(closing_price_data[-1][6])
                last_price = int(closing_price_data[-1][2])
                last_trade_time = int(closing_price_data[-1][12])
                trade_volume = int(closing_price_data[-1][9])
                trade_value = int(closing_price_data[-1][10])
                trade_count = int(closing_price_data[-1][8])
                end_price = int(closing_price_data[-1][3])
                #print(4)

            else:
                end_price = yesterday_price
                last_price = yesterday_price
                # dt = str(closing_price_data[-1][0]).split(' ')
                # dt = str(closing_price_data[len(closing_price_data) - 1][0]).split(' ')
                # last_trade_time = int(dt[1].replace(':', ''))
                last_trade_time = int(closing_price_data[-1][12])
                #print(5)

        # ---------------
        # extract state change
        status_list = list()
        row = 0
        last_status = None
        is_start_accept_date = True
        for item in instrument_state_data:
            last_status = item[2]
            if item[1] != 1:
                item.insert(0, en_symbol_12_digit_code)
                item.append(row)
                status_list.append(item)
                row += 1
            else:
                is_start_accept_date = False

        status = last_status
        if is_start_accept_date is True:
            start_accept_date = instrument_state_data[0][1]
        else:
            start_accept_date = 0

        # ---------------
        if len(person_legal_data) != 0:
            legal_buy_count = person_legal_data[1]
            legal_buy_volume = person_legal_data[5]
            legal_buy_value = person_legal_data[13]
            legal_buy_avg_price = person_legal_data[17]
            person_buy_count = person_legal_data[0]
            person_buy_volume = person_legal_data[4]
            person_buy_value = person_legal_data[12]
            person_buy_avg_price = person_legal_data[16]
            legal_sell_count = person_legal_data[3]
            legal_sell_volume = person_legal_data[7]
            legal_sell_value = person_legal_data[15]
            legal_sell_avg_price = person_legal_data[19]
            person_sell_count = person_legal_data[2]
            person_sell_volume = person_legal_data[6]
            person_sell_value = person_legal_data[14]
            person_sell_avg_price = person_legal_data[18]
            # ---------------
            # تصحیح خطا حقیقی حقوقی
            if legal_buy_volume + person_buy_volume != trade_volume:
                beta = trade_volume / (legal_buy_volume + person_buy_volume)
                legal_buy_volume *= beta
                person_buy_volume *= beta
                legal_sell_volume *= beta
                person_sell_volume *= beta

            if legal_buy_value + person_buy_value != trade_value:
                beta = trade_value / (legal_buy_value + person_buy_value)
                legal_buy_value *= beta
                person_buy_value *= beta
                legal_sell_value *= beta
                person_sell_value *= beta

            if legal_buy_volume != 0:
                legal_buy_avg_price = legal_buy_value / legal_buy_volume
            else:
                legal_buy_avg_price = 0

            if person_buy_volume != 0:
                person_buy_avg_price = person_buy_value / person_buy_volume
            else:
                person_buy_avg_price = 0

            if legal_sell_volume != 0:
                legal_sell_avg_price = legal_sell_value / legal_sell_volume
            else:
                legal_sell_avg_price = 0

            if person_sell_volume != 0:
                person_sell_avg_price = person_sell_value / person_sell_volume
            else:
                person_sell_avg_price = 0

        # ---------------
        # get shareholder list
        share_holder_list = list()
        for item in share_holder_data:
            share_holder_list.append([en_symbol_12_digit_code, date_m, item[0], item[5], item[2], item[3]])

        # ---------------
        # create second data
        second_time_series = list()
        if len(sub_trade_data_list) > 0:
            open = 0
            close = 0
            high = 0
            low = 0
            count = 0
            volume = 0
            value = 0
            start_p1 = 0
            start_p2 = 0
            start_time_date = 0
            start = True

            for item in sub_trade_data_list:
                # canceled trade
                if item[4] == 1:
                    continue

                p1 = date_m * 1000000 + item[0]
                p2 = item[1]

                if start is True:
                    start = False
                    open = item[3]
                    close = item[3]
                    high = item[3]
                    low = item[3]
                    volume = 0
                    value = 0
                    count = 0
                    start_p1 = p1
                    start_p2 = p2
                    start_time_date = start_p1

                if p1 == start_p1:
                    if p2 < start_p2:
                        open = item[3]

                    if p2 > start_p2:
                        close = item[3]

                    if item[4] < low:
                        low = item[3]

                    if item[4] > high:
                        high = item[3]

                    volume += item[2]
                    value += item[2] * item[3]
                    count += 1

                else:
                    # end = round(float(value) / volume)
                    second_time_series.append([start_time_date, int(open), int(close),
                                               int(high), int(low), volume, value, count])
                    open = item[3]
                    close = item[3]
                    high = item[3]
                    low = item[3]
                    count = 1
                    volume = item[2]
                    value = item[2] * item[3]
                    start_p1 = p1
                    start_p2 = p2
                    start_time_date = start_p1

            if volume != 0:
                # end = round(float(value) / volume)
                second_time_series.append([start_time_date, int(open), int(close),
                                           int(high), int(low), volume, value, count])

        # ---------------
        # save data to database
        data = dict()
        data['en_symbol_12_digit_code'] = en_symbol_12_digit_code
        data['date_m'] = date_m
        data['first_price'] = first_price
        data['last_price'] = last_price
        data['min_price'] = min_price
        data['max_price'] = max_price
        data['end_price'] = end_price
        data['trade_count'] = trade_count
        data['trade_volume'] = trade_volume
        data['trade_value'] = trade_value
        data['last_trade_time'] = last_trade_time
        data['yesterday_price'] = yesterday_price
        data['legal_buy_count'] = legal_buy_count
        data['legal_buy_volume'] = legal_buy_volume
        data['legal_buy_value'] = legal_buy_value
        data['legal_buy_avg_price'] = legal_buy_avg_price
        data['person_buy_count'] = person_buy_count
        data['person_buy_volume'] = person_buy_volume
        data['person_buy_value'] = person_buy_value
        data['person_buy_avg_price'] = person_buy_avg_price
        data['legal_sell_count'] = legal_sell_count
        data['legal_sell_volume'] = legal_sell_volume
        data['legal_sell_value'] = legal_sell_value
        data['legal_sell_avg_price'] = legal_sell_avg_price
        data['person_sell_count'] = person_sell_count
        data['person_sell_volume'] = person_sell_volume
        data['person_sell_value'] = person_sell_value
        data['person_sell_avg_price'] = person_sell_avg_price
        data['status'] = status
        data['share_count'] = share_count
        data['base_volume'] = base_volume

        res = self.db.add_share_daily_data(data)
        if res is not True:
            result = False
            error = res
            return result, error

        # res = self.db.update_share_daily_data(data)
        # if res is not True:
        #    result = False
        #    error = res
        #    return result, error

        # -------------
        res = self.db.add_shareholder_data(share_holder_list)
        if res is not True:
            result = False
            error = res
            return result, error

        # -------------
        res = self.db.add_share_sub_trad_data(sub_trade_data_list, en_symbol_12_digit_code, date_m)
        if res is not True:
            result = False
            error = res
            return result, error

        # -------------
        res = self.db.add_share_second_data(en_symbol_12_digit_code, second_time_series)
        if res is not True:
            result = False
            error = res
            return result, error

        # -------------
        if len(status_list) > 0:
            self.db.add_status(status_list)

        # -------------
        if is_start_accept_date is True:
            self.set_start_accept_date(en_symbol_12_digit_code, start_accept_date)

        result = True
        error = None

        return result, error

    def set_start_accept_date(self, en_symbol_12_digit_code, start_accept_date):
        db_start_accept_date = self.db.get_start_accept_date(en_symbol_12_digit_code)
        if db_start_accept_date is False:
            return False
        if start_accept_date > db_start_accept_date:
            return self.db.set_start_accept_date(en_symbol_12_digit_code, start_accept_date)
        return True

    def set_end_accept_date(self, en_symbol_12_digit_code, end_accept_date):
        if self.db.is_open_day(end_accept_date) is False:
            return True

        db_end_accept_date = self.db.get_end_accept_date(en_symbol_12_digit_code)

        if db_end_accept_date is False:
            return False

        if end_accept_date < db_end_accept_date or (db_end_accept_date == 0 and end_accept_date > 0):
            return self.db.set_end_accept_date(en_symbol_12_digit_code, end_accept_date)

        return True

    # -------------------
    # گرفتن اطلاعات تمام سهامهای موجود
    def collect_all_shares_info_multiprocess(self):
        lock_status = False
        self.print_c('worker: {0} :{1}'.format(current_process().name, 'start collect_all_shares_info function'))

        start_time = get_now_time_second()

        bourse_index = 32097828799138957
        farabourse_index = 43685683301327984

        bourse, bourse_error = self.get_shares_in_index(bourse_index)
        farabourse, farabourse_error = self.get_shares_in_index(farabourse_index)

        if bourse_error is None:
            self.add_share_id_to_unread_page_list(bourse)

        if farabourse_error is None:
            self.add_share_id_to_unread_page_list(farabourse)

        while self.get_status('stop_flag') is False:
            self.set_status('last_run_time', get_now_time_second())

            self.lock.acquire()
            lock_status = True

            # check exit condition
            if len(self.wait_list) <= 0:
                self.lock.release()
                lock_status = False
                self.print_c('worker: {0} :{1}'.format(current_process().name, 'wait list empty'))
                break

            #  گرفتن یک آیتم
            # get new item
            current_running_share_id = None
            try:
                current_running_share_id = self.wait_list.pop()
                self.running_list.append(current_running_share_id)
                self.lock.release()
                lock_status = False

            except Exception as e:
                if current_running_share_id is not None: # error in running_list append item
                    if current_running_share_id not in self.wait_list:
                        self.wait_list.append(current_running_share_id)

                current_running_share_id = None
                self.lock.release()
                lock_status = False
                self.print_c('worker: {0} :{1} ;{2}'.format(current_process().name, 'get new share : fail', str(e)))
                continue

            self.set_status('current_running_share_id', current_running_share_id)

            try:
                self.print_c('worker: {0} :{1}'.format(current_process().name, 'start collect share info'))
                self.set_status('state', 'running')

                # get all related companies id
                all_related_companies_id, all_related_companies_id_error = self.get_all_related_companies_id(current_running_share_id)
                if all_related_companies_id_error is None:
                    self.add_share_id_to_unread_page_list(all_related_companies_id)

                # get share info
                share_info, error = self.get_share_info(current_running_share_id)
                if error is not None:
                    self.lock.acquire()
                    lock_status = True
                    self.fail_list.append(current_running_share_id)
                    self.running_list.remove(current_running_share_id)
                    self.lock.release()
                    lock_status = False
                    self.print_c('worker: {0} fail collect_shares_info: info: {1} remind: {2} complete: {3}'.
                                 format(current_process().name, current_running_share_id, len(self.wait_list), len(self.complete_list)))
                    continue

                adjust_info_1, error = self.get_share_adjust_info_1(current_running_share_id)
                if error is not None:
                    self.lock.acquire()
                    lock_status = True
                    self.fail_list.append(current_running_share_id)
                    self.running_list.remove(current_running_share_id)
                    self.lock.release()
                    lock_status = False
                    self.print_c('worker: {0} fail collect_shares_info: adjust_info_1: {1} remind: {2} complete: {3}'.
                                 format(current_process().name, current_running_share_id, len(self.wait_list), len(self.complete_list)))
                    continue

                adjust_info_2, error = self.get_share_adjust_info_2(current_running_share_id)
                if error is not None:
                    self.lock.acquire()
                    lock_status = True
                    self.fail_list.append(current_running_share_id)
                    self.running_list.remove(current_running_share_id)
                    self.lock.release()
                    lock_status = False
                    self.print_c('worker: {0} fail collect_shares_info:adjust_info_2: {1} remind: {2} complete: {3}'.
                                 format(current_process().name, current_running_share_id, len(self.wait_list), len(self.complete_list)))
                    continue

                share_info['tsetmc_id'] = current_running_share_id
                self.db.add_share_info(share_info)

                # ---
                adjust_data = list()
                en_symbol_12_digit_code = share_info['en_symbol_12_digit_code']

                # سود
                if len(adjust_info_1) > 0:
                    adjust_type = 1
                    for item in adjust_info_1:
                        date_m = jalali_to_gregorian_int(item[0])
                        old = item[2]
                        new = item[1]
                        coefficient = float(new / old)
                        do_date = date_m
                        adjust_data.append([en_symbol_12_digit_code, date_m, adjust_type,
                                            old, new, coefficient, do_date])
                # افزایش سرمایه
                if len(adjust_info_2) > 0:
                    adjust_type = 2
                    for item in adjust_info_2:
                        date_m = jalali_to_gregorian_int(item[0])
                        old = item[2]
                        new = item[1]
                        coefficient = float(old / new)
                        do_date = date_m
                        adjust_data.append([en_symbol_12_digit_code, date_m, adjust_type,
                                            old, new, coefficient, do_date])

                if len(adjust_data) > 0:
                    self.db.add_share_adjusted_coefficient(adjust_data)
                # ---
                self.lock.acquire()
                lock_status = True
                self.complete_list.append(current_running_share_id)
                self.running_list.remove(current_running_share_id)
                self.lock.release()
                lock_status = False
                self.print_c('worker: {0} True collect_shares_info: {1} remind: {2} complete: {3}'.
                             format(current_process().name, current_running_share_id, len(self.wait_list), len(self.complete_list)))

                # self.print_c('worker: {0} :{1}'.format(current_process().name, 'end collect data'))

            except Exception  as e:
                # sleep(5)
                if lock_status is True:
                    self.print_c('worker {0} except: lock status: {1} : {2} :{3}'.format(str(self.id), True, 13, str(e)))
                    self.set_status('state', 'failing')
                    self.lock.release()
                else:
                    self.print_c('worker {0} except: lock status: {1} : {2} :{3}'.format(str(self.id), False, 14, e))
                    self.set_status('state', 'failing')

                try:
                    self.print_c('worker: {0} : except: {1}'.format(current_process().name, 'rollback data'))
                    self.db.deleted_share_info(current_running_share_id)
                finally:
                    self.lock.acquire()
                    self.running_list.remove(self.current_running_share)
                    self.fail_list.append(self.current_running_share)
                    self.lock.release()
                    self.print_c('worker: {0} :{1}'.format(current_process().name, 'fail'))

        self.print_c('worker: {0} :{1}'.format(current_process().name, 'quit'))

        end_time = get_now_time_second()

        self.print_c('runtime:{0}'.format(end_time - start_time), color='red')

        return True

    def collect_all_shares_info(self):
        self.unreade_page = list()
        self.running_page = list()
        self.readed_page = list()
        self.fail_readed_page = list()

        bourse_index = 32097828799138957
        farabourse_index = 43685683301327984

        bourse, bourse_error = self.get_shares_in_index(bourse_index)
        farabourse, farabourse_error = self.get_shares_in_index(farabourse_index)

        if bourse_error is None:
            for share_id in bourse:
                self.unreade_page.append(int(share_id))

        if farabourse_error is None:
            for share_id in farabourse:
                self.unreade_page.append(int(share_id))

        i = 0
        while len(self.unreade_page) != 0:
            i += 1
            share_id = self.unreade_page.pop()
            self.running_page.append(share_id)

            all_related_companies_id, all_related_companies_id_error = self.get_all_related_companies_id(share_id)
            if all_related_companies_id_error is None:
                self.add_share_id_to_unread_page_list(all_related_companies_id)
                # کارهایی که در صفحه هر سهام باید انجام داد
                # info, error = self.get_share_info(share_id)
                # if error is None:
                #    info['tsetmc_id'] = share_id
                #    self.db.add_share_info(info)
                # ---
                share_info, error = self.get_share_info(share_id)
                if error is not None:
                    self.fail_readed_page.append(share_id)
                    self.running_page.remove(share_id)
                    continue

                adjust_info_1, error = self.get_share_adjust_info_1(share_id)
                if error is not None:
                    self.fail_readed_page.append(share_id)
                    self.running_page.remove(share_id)
                    continue

                adjust_info_2, error = self.get_share_adjust_info_2(share_id)
                if error is not None:
                    self.fail_readed_page.append(share_id)
                    self.running_page.remove(share_id)
                    continue


                share_info['tsetmc_id'] = share_id
                self.db.add_share_info(share_info)
                # ---
                adjust_data = list()
                en_symbol_12_digit_code = share_info['en_symbol_12_digit_code']

                # سود
                if len(adjust_info_1) > 0:
                    adjust_type = 1
                    for item in adjust_info_1:
                        date_m = jalali_to_gregorian_int(item[0])
                        old = item[2]
                        new = item[1]
                        coefficient = float(new / old)
                        do_date = date_m
                        adjust_data.append([en_symbol_12_digit_code, date_m, adjust_type,
                                            old, new, coefficient, do_date])
                # افزایش سرمایه
                if len(adjust_info_2) > 0:
                    adjust_type = 2
                    for item in adjust_info_2:
                        date_m = jalali_to_gregorian_int(item[0])
                        old = item[2]
                        new = item[1]
                        coefficient = float(old / new)
                        do_date = date_m
                        adjust_data.append([en_symbol_12_digit_code, date_m, adjust_type,
                                            old, new, coefficient, do_date])

                if len(adjust_data) > 0:
                    self.db.add_share_adjusted_coefficient(adjust_data)
                # ---

                self.readed_page.append(share_id)
                self.running_page.remove(share_id)
                self.print_c('True collect_shares_info: {0} remind: {1} complete: {2}'.
                             format(share_id, len(self.unreade_page), i))
            else:
                self.print_c('fail collect_shares_info: {0} remind: {1} complete: {2}'.
                             format(share_id, len(self.unreade_page), i))
                self.fail_readed_page.append(share_id)
                self.running_page.remove(share_id)

        # self.browser.close()
        return (self.fail_readed_page, self.running_page, self.unreade_page, self.readed_page)

    def get_all_related_companies_id(self, share_id):  # کرفتن لیست سهام های هم گروه
        error = None
        url = '{0}?ParTree=151311&i={1}'.format(self.tsetmc_base_url, share_id)
        response = self.get_web_data(url)

        # check response code
        if response.status_code != 200:
            error = 'html error code:{0}'.format(response.status_code)
            result = False
            return result, error

        # -------------------
        var_name = 'var RelatedCompanies='  # ---- شرکتهای هم گروه ----
        related_companies, related_companies_error = self.get_var_list(response, var_name)
        if related_companies_error is not None:
            error = related_companies_error
            result = False
            return result, error
        share_id_list = list()
        for item in related_companies:
            try:
                share_id_list.append(int(item[0]))
            except Exception as e:
                error= str(e)
                break

        return share_id_list, error

    def get_share_info(self, share_id):  # کرفتن اطلاعات سهام
        error = None
        url = '{0}?Partree=15131M&i={1}'.format(self.tsetmc_base_url, share_id)
        response = self.get_web_data(url)

        # check response code
        if response.status_code != 200:
            error = 'html error code:{0}'.format(response.status_code)
            result = False
            return result, error

        # -------------------
        result = dict()
        start_pos = 0
        end_pos = 0
        offset = 0
        td_list = list()
        while start_pos >= 0 and end_pos >= 0:
            start_pos = response.text.find('<td>', offset)
            if start_pos < 0:
                continue
            start_pos += 4  # len(var_name)

            # fins end position
            end_pos = response.text.find('</td>', start_pos)
            if end_pos < 0:
                continue

            try:
                var_str = str(response.text[start_pos:end_pos])
                td_list.append(var_str)
            except Exception as e:
                error = str(e)
                result = False
                return result, error
            offset = end_pos

        try:
            result['en_symbol_12_digit_code'] = str(td_list[1])  # 'کد 12 رقمی نماد'
            result['en_symbol_5_digit_code'] = str(td_list[3])  # 'کد 5 رقمی نماد'
            result['company_en_name'] = str(td_list[5])  # 'نام لاتین شرکت'
            result['company_4_digit_code'] = str(td_list[7])  # 'کد 4 رقمی شرکت'
            result['company_fa_name'] = str(td_list[9])  # 'نام شرکت'
            result['fa_symbol_name'] = str(td_list[11])  # 'نماد فارسی'
            result['fa_symbol_30_digit_code'] = str(td_list[13])  # 'نماد 30 رقمی فارسی'
            result['company_12_digit_code'] = str(td_list[15])  # 'کد 12 رقمی شرکت'
            result['market_flow'] = str(td_list[17])  # 'بازار'
            result['bord_code'] = int(td_list[19])  # 'کد تابلو'
            result['industry_code'] = int(td_list[21])  # 'کد گروه صنعت'
            result['sub_industry_code'] = int(td_list[25])  # 'کد زیر گروه صنعت'

            result['is_active'] = 1

        except Exception as e:
            error = str(e)
            result = False
            return result, error

        return result, error

    def get_share_adjust_info_1(self, share_id):
        # سود
        error = None
        result = list()
        url = '{0}?Partree=15131G&i={1}'.format(self.tsetmc_base_url, share_id)
        response = self.get_web_data(url)

        # check response code
        if response.status_code != 200:
            error = 'html error code:{0}'.format(response.status_code)
            result = False
            return result, error

        # -------------------
        start_pos = 0
        end_pos = 0
        offset = 0
        tr_list = list()
        td_list = list()
        while start_pos >= 0 and end_pos >= 0:
            start_pos = response.text.find('<tr>', offset)
            if start_pos < 0:
                continue
            start_pos += 4  # len(var_name)

            # fins end position
            end_pos = response.text.find('</tr>', start_pos)
            if end_pos < 0:
                continue

            try:
                row_str = str(response.text[start_pos:end_pos])
                tr_list.append(row_str)
            except Exception as e:
                error = str(e)
                result = False
                return result, error
            offset = end_pos

        if len(tr_list) < 1:
            error = 'error to get adjusted data'
            result = False
            return result, error

        elif len(tr_list) == 1:
            # error = None
            # result = True
            return result, error

        else:
            for row in tr_list:
                start_pos = 0
                end_pos = 0
                offset = 0
                td_list.clear()

                while start_pos >= 0 and end_pos >= 0:
                    start_pos = row.find('<td>', offset)
                    if start_pos < 0:
                        continue
                    start_pos += 4  # len(var_name)

                    # fins end position
                    end_pos = row.find('</td>', start_pos)
                    if end_pos < 0:
                        continue

                    try:
                        row_str = str(row[start_pos:end_pos])
                        td_list.append(row_str)
                    except Exception as e:
                        error = str(e)
                        result = False
                        return result, error
                    offset = end_pos

                if len(td_list) > 0:
                    try:
                        dt_list = td_list[0].split('/')
                        dt = int(dt_list[0]) * 10000 + int(dt_list[1]) * 100 + int(dt_list[2])
                        result.append([dt,
                                       int(td_list[1].replace(',', '')),
                                       int(td_list[2].replace(',', ''))])

                    except Exception as e:
                        error = str(e)
                        result = False
                        return result, error

            return result, error

    def get_share_adjust_info_2(self, share_id):
        # افزایش سرمایه
        error = None
        result = list()
        url = '{0}?Partree=15131H&i={1}'.format(self.tsetmc_base_url, share_id)
        response = self.get_web_data(url)

        # check response code
        if response.status_code != 200:
            error = 'html error code:{0}'.format(response.status_code)
            result = False
            return result, error

        # -------------------
        start_pos = 0
        end_pos = 0
        offset = 0
        tr_list = list()
        td_list = list()
        while start_pos >= 0 and end_pos >= 0:
            start_pos = response.text.find('<tr>', offset)
            if start_pos < 0:
                continue
            start_pos += 4  # len(var_name)

            # fins end position
            end_pos = response.text.find('</tr>', start_pos)
            if end_pos < 0:
                continue

            try:
                row_str = str(response.text[start_pos:end_pos])
                tr_list.append(row_str)
            except Exception as e:
                error = str(e)
                result = False
                return result, error
            offset = end_pos

        if len(tr_list) < 1:
            error = 'error to get adjusted data'
            result = False
            return result, error

        elif len(tr_list) == 1:
            # error = None
            # result = True
            return result, error

        else:
            for row in tr_list:
                start_pos = 0
                end_pos = 0
                offset = 0
                td_list.clear()

                while start_pos >= 0 and end_pos >= 0:
                    start_pos = row.find('<td>', offset)
                    if start_pos < 0:
                        continue
                    start_pos += 4  # len(var_name)

                    # fins end position
                    end_pos = row.find('</td>', start_pos)
                    if end_pos < 0:
                        continue

                    try:
                        row_str = str(row[start_pos:end_pos])
                        td_list.append(row_str)
                    except Exception as e:
                        error = str(e)
                        result = False
                        return result, error
                    offset = end_pos

                if len(td_list) > 0:
                    try:
                        dt_list = td_list[0].split('/')
                        dt = int(dt_list[0]) * 10000 + int(dt_list[1]) * 100 + int(dt_list[2])
                        # --
                        start = td_list[1].find('<div class=\'ltr\' title="') + 24
                        end = td_list[1].find('">')
                        if start < 0 or end < 0:
                            new = int(td_list[1].replace(',', ''))
                        else:
                            new = int(td_list[1][start:end].replace(',', ''))
                        # --
                        start = td_list[2].find('<div class=\'ltr\' title="') + 24
                        end = td_list[2].find('">')

                        if start < 0 or end < 0:
                            old = int(td_list[2].replace(',', ''))
                        else:
                            old = int(td_list[2][start:end].replace(',', ''))

                        result.append([dt, new, old])

                    except Exception as e:
                        error = str(e)
                        result = False
                        return result, error

            return result, error

    def add_share_id_to_unread_page_list(self, id_list):
        try:
            self.lock.acquire()

            for id in id_list:
                if id in self.wait_list:
                    continue
                if id in self.complete_list:
                    continue
                if id in self.running_list:
                    continue
                if id in self.fail_list:
                    continue
                self.wait_list.append(id)
        except:
            self.lock.release()
            return True

        self.lock.release()
        return True

    def get_shares_in_index(self, index_id):
        error = None
        url = '{0}?ParTree=15131J&i={1}'.format(self.tsetmc_base_url, index_id)
        response = self.get_web_data(url)

        # check response code
        if response.status_code != 200:
            error = 'html error code:{0}'.format(response.status_code)
            result = False
            return result, error

        # -------------------
        start_pos = 0
        end_pos = 0
        offset = 0
        id_list = list()
        while start_pos >= 0 and end_pos >= 0:

            start_pos = response.text.find('<tr id=\'', offset)
            if start_pos < 0:
                continue
            start_pos += 8  # len(var_name)

            # fins end position
            end_pos = response.text.find('\'>', start_pos)
            if end_pos < 0:
                continue

            try:
                var_str = str(response.text[start_pos:end_pos])
                var_id = int(var_str)
                id_list.append(var_id)
            finally:
                offset = end_pos

        return id_list, error

    # -------------------
    def collect_all_index_daily_data(self, excel_path, mod=2):
        # بروز رسانی دادههای شاخصهای موجود در دیتابیس از طریق فایلهای اکسل و وب
        error = None
        all_db_index = self.db.get_all_index_id()
        i =0
        for index in all_db_index:
            i += 1
            res, err = self.get_index_daily_data(index[0], int(index[1]), excel_path, mod=mod)
            print('res:{0}  error:{1}'.format(res, err))
            print('remind: {0} complete: {1}'.format(len(all_db_index) - i, i))
            if err is not None:
                error = err
            #sleep(1)

        self.db.auto_update_open_days_table()

        return error

    def get_index_daily_data(self, en_index_12_digit_code, index_id, excel_path, mod=2):
        # mod = 0 --> only excel
        # mod = 1 --> only web
        # mod = 2 --> excel & web
        if mod == 0 or mod == 2:
            # from excel
            item = list()
            all_data = list()
            print('excel: ' + en_index_12_digit_code)
            try:
                wb = xlrd.open_workbook(excel_path + en_index_12_digit_code + '.xls')
                sheet = wb.sheet_by_index(0)
                for i in range(sheet.nrows - 1):
                    item.clear()

                    item.append(en_index_12_digit_code)  # en_index_12_digit_code
                    item.append(int(sheet.cell_value(i + 1, 1)))  # date_m
                    item.append(int(sheet.cell_value(i + 1, 13)))  # date_sh
                    item.append(float(sheet.cell_value(i + 1, 3)))  # high
                    item.append(float(sheet.cell_value(i + 1, 4)))  # low
                    item.append(float(sheet.cell_value(i + 1, 2)))  # open
                    item.append(float(sheet.cell_value(i + 1, 5)))  # close
                    item.append(float(sheet.cell_value(i + 1, 6)))  # volume

                    #all_data.append(item)
                    all_data.append([item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7]])

                self.db.add_index_data(all_data)
            except Exception as e:
                self.print_c('cant open excel file: {0}'.format(str(e)))
                #self.log.error('cant open excel file', str(e))

        if mod == 1 or mod == 2:
            # from web page
            error = None
            url = 'http://www.tsetmc.com/tsev2/chart/data/IndexFinancial.aspx?i={0}&t=ph'.format(index_id)
            response = self.get_web_data(url)
            print('web: ' + en_index_12_digit_code)

            # check response code
            if response.status_code != 200:
                error = 'html error code:{0}'.format(response.status_code)
                result = False
                return result, error

            # -------------------
            try:
                data_list = list()
                days_data = str(response.text).split(';')
                for day in days_data:
                    data_list.append(day.split(',')[0:6])  # date_m, high, low, open, close, value

                for day in data_list:
                    for item in day:
                        item = int(item)
                    day.insert(0, en_index_12_digit_code)
                    day.insert(2, gregorian_to_jalali_int(int(day[1])))

            except Exception as e:
                self.print_c('cant open web: {0}'.format(str(e)))
                error = '{0}'.format(str(e))
                result = False
                return result, error

            self.db.add_index_data(data_list)

        return True, None

    # -------------------------------
    # گرفتن لیست شاخصهای موجود از مجموعه فایلهای اکسل -- نیاز به کامل کردن اطلاعات در دیتابیس میباشد
    def get_index_info(self, excel_path):  # گرفتن لیست شاخصهای موجود از مجموعه فایلهای اکسل -- نیاز به کامل کردن اطلاعات در دیتابیس میباشد
        files = self.get_index_excel_file_name(excel_path, True)
        info = dict()
        for file in files:
            info.clear()
            try:
                wb = xlrd.open_workbook(excel_path + file)
                sheet = wb.sheet_by_index(0)
                info['en_index_12_digit_code'] = file[:-4]
                info['index_id'] = 0
                info['fa_index_name'] = sheet.cell_value(1, 12)
                info['fa_index_code'] = sheet.cell_value(1, 0)
                info['company_4_digit_code'] =sheet.cell_value(1, 10)
                info['company_en_name'] =sheet.cell_value(1, 11)

                self.db.add_index_info(info)
            except Exception as e:
                self.log.error('cant open excel sheet:' + file[:-4], str(e))

    def get_index_excel_file_name(self, folder_path, prefix=False):
        a = glob(folder_path + 'IRX*.xls')

        res = []
        for item in a:
            b = item.rfind('\\')
            if prefix is False:
                res.append(item[b + 1:-4])
            else:
                res.append(item[b + 1:])

        return res

    # -------------------------------
    def get_all_share_adjusted_data(self):
        all_share_info = self.db.get_active_share_info()
        i = 0
        for index in all_share_info:
            i += 1
            # get adjusted data from web
            result, error =self.get_share_adjusted_history_data(index[0], index[1])
            if error is not None:
                self.print_c('error to get share adjusted data: '
                             'en_symbol_12_digit_code:{0} tsetmc_id:{1} error:{2}'.format(index[0], index[1], error))
                continue

            if len(result) <= 0:
                continue

            # get first date web data from database
            first_result_adjusted_date = result[-1]
            first_db_adjusted_data = self.db.get_share_adjusted_data(index[0], first_result_adjusted_date[1])

            if first_db_adjusted_data is False:
                self.print_c('error to get share adjusted data: '
                             'en_symbol_12_digit_code:{0} date:{1}'.format(index[0], first_result_adjusted_date[1]))
                continue

            # if changed adjusted data deleted data from database
            if len(first_db_adjusted_data) > 0:
                if first_db_adjusted_data[0][3] != first_result_adjusted_date[3]:
                    if self.db.clear_share_adjusted_data(index[0]) is False:
                        continue

            self.db.add_share_adjusted_data(result)
            print('remind: {0} complete: {1}'.format(len(all_share_info) - i, i))

    def get_share_adjusted_history_data(self, en_symbol_12_digit_code, tsetmc_id):

        error = None
        url = 'http://members.tsetmc.com/tsev2/chart/data/Financial.aspx?i={0}&t=ph&a=1'.format(tsetmc_id)
        response = self.get_web_data(url)

        # check response code
        if response.status_code != 200:
            error = 'html error code:{0}'.format(response.status_code)
            result = False
            return result, error

        # -------------------
        try:
            data_list = list()
            days_data = str(response.text).split(';')
            for day in days_data:
                data_list.append(day.split(','))  # date_m, high, low, open, close, value, end

            for day in data_list:
                for item in day:
                    item = int(item)
                day.insert(0, en_symbol_12_digit_code)

        except Exception as e:
            self.print_c('cant open web: {0}'.format(str(e)))
            error = '{0}'.format(str(e))
            result = False
            return result, error

        # self.db.add_share_adjusted_data(data_list)
        result = data_list
        return result, error

    def get_share_daily_history_data(self, en_symbol_12_digit_code, tsetmc_id):

        error = None
        url = 'http://members.tsetmc.com/tsev2/chart/data/Financial.aspx?i={0}&t=ph&a=0'.format(tsetmc_id)
        response = self.get_web_data(url)

        # check response code
        if response.status_code != 200:
            error = 'html error code:{0}'.format(response.status_code)
            result = False
            return result, error

        # -------------------
        try:
            data_list = list()
            days_data = str(response.text).split(';')
            for day in days_data:
                data_list.append(day.split(','))  # date_m, high, low, open, close, value, end

            for day in data_list:
                for item in day:
                    item = int(item)
                day.insert(0, en_symbol_12_digit_code)

        except Exception as e:
            self.print_c('cant open web: {0}'.format(str(e)))
            error = '{0}'.format(str(e))
            result = False
            return result, error

        # self.db.add_share_adjusted_data(data_list)
        result = data_list
        return result, error

    def update_adjusted_coefficient(self, en_symbol_12_digit_code, tsetmc_id):
        error = None
        result = None

        daily_data, daily_data_error = self.get_share_daily_history_data(en_symbol_12_digit_code, tsetmc_id)
        adjusted_data, adjusted_data_error = self.get_share_adjusted_history_data(en_symbol_12_digit_code, tsetmc_id)

        if daily_data_error is not None:
            self.print_c('error to get share_daily_history_data en_symbol_12_digit_code:{0} tsetmc_id:{1}  error:{2}'
                         .format(en_symbol_12_digit_code, tsetmc_id, daily_data_error))
            error = daily_data_error
            result = False
            return result, error

        if adjusted_data_error is not None:
            self.print_c('error to get share_daily_history_data en_symbol_12_digit_code:{0} tsetmc_id:{1}  error:{2}'
                         .format(en_symbol_12_digit_code, tsetmc_id, adjusted_data_error))
            error = adjusted_data_error
            result = False
            return result, error

        if len(daily_data) != len(adjusted_data):
            self.print_c('error to get share_daily_history_data en_symbol_12_digit_code:{0} tsetmc_id:{1}  error:{2}'
                         .format(en_symbol_12_digit_code, tsetmc_id, 'data not equal'))
            error = 'data not equal'
            result = False
            return result, error

        a=len(daily_data)
        b=len(adjusted_data)

        coefficient_list = list()
        coefficient = round(float(adjusted_data[0][4]) / float(daily_data[0][4]), 2)

        for i in range(len(daily_data)):
            now_coefficient = round(float(adjusted_data[i][4]) /float( daily_data[i][4]), 2)
            if coefficient != now_coefficient:
                coefficient_list.append([daily_data[i - 1][1], coefficient])
                coefficient = now_coefficient
        coefficient_list.append([daily_data[len(daily_data) - 1][1], coefficient])

        return result, error

    # -------------------


tsetmc_excel_path = 'C:\\Users\\Mostafa_Laptop\\Documents\\TseClient 2.00\\'

def update_share_info(tsetmc_obj):
    tsetmc_obj.collect_all_shares_info()

def get_all_index_daily_data(tsetmc_obj, excel_path=tsetmc_excel_path, mod=2):
    tsetmc_obj.collect_all_index_daily_data(excel_path, mod)

if __name__ == '__main__':
    from constant_database_data import *

    log_file_name = 'log.txt'
    log_table_name = 'bot_log'
    logging_mod = Log_Mod.console_file

    status = dict()
    lock = threading.Lock()
    wait_list = list()
    complete_list = list()
    running_list = list()
    fail_list = list()

    #excel_path = 'C:\\Users\\Mostafa_Laptop\\Documents\\TseClient 2.0\\'
    excel_path = tsetmc_excel_path
    id = 1

    a = Tsetmc(id=id, db_info=laptop_client_role_db_info, log_file_name=log_file_name, log_table_name=log_table_name, logging_mod=logging_mod,
               lock=lock, wait_list=wait_list, complete_list=complete_list, running_list=running_list,
               fail_list=fail_list, status=status)

    get_all_index_daily_data(a, mod=1)


    share_info = list([0,0,0])

    #url = 'http://tsetmc.com/Loader.aspx?Partree=15131M&i={0}'.format(41309167317349268)
    ##response = a.get_web_data(url, (10, '20k'))
    #if response.status_code != 200:
    #    error = 'html error code:{0}'.format(response.status_code)

    #a.get_all_share_adjusted_data()


    # صكوك اجاره خليج فارس- 3ماهه16% (صفارس412)

    # پتروشيمي مارون

    # پتروشيمي مارون
    en_symbol_12_digit_code = 'IRO3PMRZ0001'
    tsetmc_id = '53449700212786324'
    date_m = 20150408



    share_info[0] = en_symbol_12_digit_code
    share_info[1] = tsetmc_id
    share_info[2] = date_m


    s = a.collect_all_shares_info()
    r, e = a.get_share_adjust_info_1(share_info[1])
    r1, e1 = a.get_share_adjust_info_2(share_info[1])




    a.get_share_data(share_info)



    en_symbol_12_digit_code = 'IRB6SEKF00C1'
    tsetmc_id = 41309167317349268
    date_m = 20190101

    # گز سكه (غگز) [ 97/2/11 ]
    en_symbol_12_digit_code = 'IRO3ZOBZ0001'
    tsetmc_id = 9211775239375291
    date_m = 20180501

    share_info[0] = en_symbol_12_digit_code
    share_info[1] = tsetmc_id
    share_info[2] = date_m

    a.update_adjusted_coefficient(en_symbol_12_digit_code, tsetmc_id)

    a.get_share_adjusted_history_data(share_info)
    result, error = a.get_share_adjusted_history_data(share_info)

    a.collect_all_index_daily_data(excel_path, mod=2)


    fail_readed_page, running_page, unreade_page, readed_pag = a.collect_all_shares_info()
    a.print_c('fail_readed_page:{0}, running_page:{1}, unreade_page:{2}, readed_pag:{3}'.format(len(fail_readed_page), len(running_page), len(unreade_page), len(readed_pag)))


    #bourse_id_list = a.collect_shares_id_on_bourse()
    #a.print_c(bourse_id_list)

    #farabourse_id_list = a.collect_shares_id_on_farabourse()
    #a.print_c(farabourse_id_list)

    res = a.get_all_related_companies_id(57551382352708199)
    a.print_c(res)




    # گز سكه (غگز) [ 97/2/11 ]
    en_symbol_12_digit_code = 'IRO5GSKS0001'
    tsetmc_id = 57551382352708199
    date_m = 20180501

    share_info[0] = en_symbol_12_digit_code
    share_info[1] = tsetmc_id
    share_info[2] = date_m

    #a.print_all_data(tsetmc_id, date_m)
    a.print_c('**********', 'blue')
    #a.get_share_data(share_info)


    # سهامي ذوب آهن اصفهان (ذوب) [ 98/3/12 ]
    en_symbol_12_digit_code = 'IRO3ZOBZ0001'
    tsetmc_id = 9211775239375291
    date_m = 20190602
    share_info[0] = en_symbol_12_digit_code
    share_info[1] = tsetmc_id
    share_info[2] = date_m

    #a.print_all_data(tsetmc_id, date_m, 1)
    a.print_c('**********', 'blue')
    #a.get_share_data(share_info)


    # گروه سرمايه گذاري ميراث فرهنگي (سمگا) [ 98/3/13 ] - بازار عادي فرابورس
    en_symbol_12_digit_code = 'IRO3IMFZ0001'
    tsetmc_id = 46741025610365786
    date_m = 20190603
    share_info[0] = en_symbol_12_digit_code
    share_info[1] = tsetmc_id
    share_info[2] = date_m

    a.print_c('**********', 'blue')
    a.get_share_data(share_info)


    # نوردوقطعات‌ فولادي‌ (فنورد) [ 98/3/13 ] - بازار دوم بورس
    en_symbol_12_digit_code = 'IRO1NGFO0001'
    tsetmc_id = 56324206651661881
    date_m = 20190603
    share_info[0] = en_symbol_12_digit_code
    share_info[1] = tsetmc_id
    share_info[2] = date_m

    #a.print_all_data(tsetmc_id, date_m, 0)
    a.print_c('**********', 'blue')
    #a.get_share_data(share_info)

    # نوردوقطعات‌ فولادي‌ (فنورد) [ 98/3/13 ] - بازار دوم بورس
    en_symbol_12_digit_code = 'IRO1LTOS0001'
    tsetmc_id = 59142194115401696
    date_m = 20190123
    share_info[0] = en_symbol_12_digit_code
    share_info[1] = tsetmc_id
    share_info[2] = date_m

    #a.print_all_data(tsetmc_id, date_m, 1)
    a.print_c('**********', 'blue')
    a.get_share_data(share_info)

    # بانك تجارت (وتجارت) [ 98/1/27 ] - بازار اول (تابلوي اصلي) بورس
    en_symbol_12_digit_code = 'IRO1BTEJ0001'
    tsetmc_id = 63917421733088077
    date_m = 20190416
    share_info[0] = en_symbol_12_digit_code
    share_info[1] = tsetmc_id
    share_info[2] = date_m

    a.print_c('**********', 'blue')
    a.get_share_data(share_info)

    a.print_c('end **********', 'blue')


    # a.run_collect_all_share_data()

    a.collect_all_shares_info()
    a.get_all_excel_share_daily_data(excel_path)
    a.collect_all_index_daily_data(excel_path, 0)
    a.db.auto_update_open_days_table()
    a.set_all_start_end_share_date()
