import pymysql
from Log import *


class Database:

    def __init__(self, db_info, log_obj=None):
        try:
            if log_obj is None:
                self.log = Logging()
                self.log.logConfig(account_id=db_info['db_username'])
            else:
                self.log = log_obj

            self.log.trace()

            self.db_host_name = db_info['db_host_name']
            self.db_username = db_info['db_username']
            self.db_user_password = db_info['db_user_password']
            self.db_name = db_info['db_name']
            self.db_port = db_info['db_port']
        except Exception as e:
            self.log.error('cant create database object: ', str(e))
            return

    def get_connection(self, ):
        try:
            if self.db_port is None:
                con = pymysql.connect(host=self.db_host_name, user=self.db_username,
                                      password=self.db_user_password, db=self.db_name)
            else:
                con = pymysql.connect(host=self.db_host_name, user=self.db_username, password=self.db_user_password,
                                      db=self.db_name, port=self.db_port)
            return con, None
        except Exception as e:
            self.log.error('cant create connection: ', str(e))
            return False, str(e)

    def select_query(self, query, args, mod=0):
        # mod=0 => return cursor
        # mod=1 => retyrn cursor.fetchall()
        self.log.trace()
        if query == '':
            self.log.error('query in empty')
            return False
        con = None
        try:
            con, err = self.get_connection()
            if err is not None:
                raise Exception(err)
            db = con.cursor()
            db.execute(query, args)
            con.close()
        except Exception as e:
            self.log.error('except select_query', str(e))
            try:
                if con.open is True:
                    con.close()
            finally:
                return False

        if mod == 0:
            return db
        else:
            return db.fetchall()

    def select_query_dictionary(self, query, args, mod=0):
        # mod=0 => return cursor
        # mod=1 => retyrn cursor.fetchall()
        self.log.trace()
        if query == '':
            self.log.error('query in empty')
            return False
        con = None
        try:
            con, err = self.get_connection()
            if err is not None:
                raise Exception(err)
            db = con.cursor(pymysql.cursors.DictCursor)
            db.execute(query, args)
            con.close()
        except Exception as e:
            self.log.error('except select_query_dictionary', str(e))
            try:
                if con.open is True:
                    con.close()
            finally:
                return False

        if mod == 0:
            return db
        else:
            return db.fetchall()

    def command_query(self, query, args, write_log=True):
        self.log.trace()
        if query == '':
            self.log.error('query in empty')
            return 'query in empty'
        con = None
        try:
            con, err = self.get_connection()
            if err is not None:
                raise Exception(err)

            db = con.cursor()
            db._defer_warnings = True
            db.autocommit = False
            db.execute(query, args)
            # db.executemany(query, args)
            con.commit()
            con.close()
            return True
        except Exception as e:
            if write_log is True:
                print('command_query. error:{0} query:{1}, args:{2}'.format(e, query, args))

                t = 'cant execute command_query_many and rollback. query:{0}'.format(query)
                if query.find('share_status') > 0:
                    t = 'cant execute command_query_many and rollback. query:{0}, args:{1}'.format(query, args)

                self.log.error(t, str(e))
                #self.log.error('cant execute command_query and rollback. query:{0}'.format(query), str(e))
            try:
                if con.open is True:
                    con.rollback()
                    con.close()
            finally:
                return 'cant execute command_query: {}'.format(str(e))

    def command_query_many(self, query, args, write_log=True):
        self.log.trace()
        if query == '':
            self.log.error('query in empty')
            return 'query in empty'
        con = None
        try:
            con, err = self.get_connection()
            if err is not None:
                raise Exception(err)

            db = con.cursor()
            db._defer_warnings = True
            db.autocommit = False
            # db.execute(query, args)
            db.executemany(query, args)
            con.commit()
            con.close()
            return True
        except Exception as e:
            if write_log is True:
                print('command_query_many. error:{0} query:{1}, args:{2}').format(e, query, args)

                t = 'cant execute command_query_many and rollback. query:{0}'.format(query)
                if query.find('share_status') > 0:
                    t = 'cant execute command_query_many and rollback. query:{0}, args:{1}'.format(query, args)

                self.log.error(t, str(e))
            try:
                if con.open is True:
                    con.rollback()
                    con.close()
            finally:
                return 'cant execute command_query_many: {}'.format(str(e))

    # -------------
    def get_client_runtime_settings(self, client_id):
        query = 'select * from runtime_setting where client_id = %s'
        args = (client_id,)
        ret = False
        try:
            res = self.select_query_dictionary(query, args, 1)
            if len(res) > 0:
                ret = res[0]

        finally:
            return ret

    def set_client_runtime_setting(self, client_id, data):
        query = 'update runtime_setting set first=%s, end=%s, offset=%s, last=%s, max_thread=%s, max_process=%s ' \
                'where client_id = %s'

        args = (data['first'], data['end'], data['offset'], data['last'], data['max_thread'], data['max_process'], client_id)

        return self.command_query(query, args, True)

    def get_main_stop_flag(self, client_id):
        res = self.get_client_runtime_settings(client_id)
        if res is not False:
            return res['execute_status']
        return False

    def get_max_process_from_db(self, client_id):
        res = self.get_client_runtime_settings(client_id)
        if res is not False:
            return res['max_process']
        return False

    # -------------
    def get_wait_list(self, start_index, offset):
        max_integrity_count = 2
        max_hang_count = 2
        max_other_count = 3

        query = 'SELECT date_m FROM open_days ORDER BY date_m DESC LIMIT {0}, {1}'.format(start_index, offset)
        args = ()

        days = self.select_query(query, args, 1)
        if days is False:
            return False

        d = list()
        for day in days:
            d.append(int(day[0]))
        d = tuple(d)
        d = '{0}'.format(d)
        d = d.replace(',)', ')')

        #d='((1,),)'

        query = 'SELECT en_symbol_12_digit_code, tsetmc_id, date_m FROM (SELECT * from share_info JOIN open_days WHERE share_info.is_active = 1 AND  open_days.date_m IN ' + d + ' ) as a WHERE a.min_date <= a.date_m And '\
                ' ((a.en_symbol_12_digit_code, a.date_m) not in (SELECT share_daily_data.en_symbol_12_digit_code, share_daily_data.date_m FROM share_daily_data)) AND' \
                ' ((a.en_symbol_12_digit_code, a.date_m) not in (SELECT fail_integrity_share.en_symbol_12_digit_code, fail_integrity_share.date_m FROM fail_integrity_share WHERE fail_integrity_share.fail_count >= {0})) AND' \
                ' ((a.en_symbol_12_digit_code, a.date_m) not in (SELECT fail_hang_share.en_symbol_12_digit_code, fail_hang_share.date_m FROM fail_hang_share WHERE fail_hang_share.fail_count >= {1})) AND' \
                ' ((a.en_symbol_12_digit_code, a.date_m) not in (SELECT fail_other_share.en_symbol_12_digit_code, fail_other_share.date_m FROM fail_other_share WHERE fail_other_share.fail_count >= {2}))' \
                .format(max_integrity_count, max_hang_count, max_other_count)

        args = ()
        return self.select_query(query, args, 1)

    # -------------
    def collect_all_share_data_rollback(self, en_symbol_12_digit_code, tsetmc_id, date_m):
        query = 'delete from shareholders_data where en_symbol_12_digit_code = %s and date_m = %s'
        args = (en_symbol_12_digit_code, date_m)
        self.command_query(query, args)

        query = 'delete from share_sub_trad_data where en_symbol_12_digit_code = %s and date_m = %s'
        args = (en_symbol_12_digit_code, date_m)
        self.command_query(query, args)

        query = 'delete from share_daily_data where en_symbol_12_digit_code = %s and date_m = %s'
        args = (en_symbol_12_digit_code, date_m)
        self.command_query(query, args)

        query = 'delete from share_second_data where en_symbol_12_digit_code = %s and date_time >= %s and date_time < %s'
        args = (en_symbol_12_digit_code, date_m * 1000000, (date_m + 1) * 1000000)
        self.command_query(query, args)

        query = 'delete from share_status where en_symbol_12_digit_code = %s and date_m = %s'
        args = (en_symbol_12_digit_code, date_m)
        self.command_query(query, args)

        return self.add_share_to_fail_other_share(en_symbol_12_digit_code, tsetmc_id, date_m)

    # -------------
    def add_share_to_fail_other_share(self, en_symbol_12_digit_code, tsetmc_id, date_m):
        query = 'insert into fail_other_share (en_symbol_12_digit_code, tsetmc_id, date_m) VALUES (%s, %s, %s) ' \
                'ON DUPLICATE KEY UPDATE fail_count = fail_count + 1'
        args = (en_symbol_12_digit_code, tsetmc_id, date_m)
        return self.command_query(query, args)

    def add_share_to_fail_hang_share(self, en_symbol_12_digit_code, date_m):
        # 'insert into hang_acdc_data values ' + values + ' ON DUPLICATE KEY UPDATE fail_count = fail_count + 1'
        query = 'insert into fail_hang_share (en_symbol_12_digit_code, date_m) ' \
                'VALUES (%s, %s) ON DUPLICATE KEY UPDATE fail_count = fail_count + 1'
        args = (en_symbol_12_digit_code, str(date_m))
        return self.command_query(query, args)

    # -------------
    def get_database_record(self):
        sum_record = 0

        query = 'select count(*) from index_data'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from index_info'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from open_days'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from share_daily_data'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from share_adjusted_data'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from share_info'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from share_second_data'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from share_status'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from share_sub_trad_data'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        query = 'select count(*) from shareholders_data'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            sum_record += int(res[0][0])

        return sum_record, None


    # ==========================================

    # -------------
    def add_share_daily_data(self, data):
        # if self.exist_share_daily_data(data['en_symbol_12_digit_code'], data['date_m']) is True:
        #   return True
        query = 'INSERT IGNORE INTO share_daily_data (en_symbol_12_digit_code, date_m, ' \
                'first_price, last_price, min_price, max_price, end_price, ' \
                'trade_count, trade_volume, trade_value, last_trade_time, yesterday_price, ' \
                'Legal_buy_count, Legal_buy_volume, Legal_buy_value, Legal_buy_avg_price, person_buy_count, ' \
                'person_buy_volume, person_buy_value, person_buy_avg_price, Legal_sell_count, Legal_sell_volume, ' \
                'Legal_sell_value, Legal_sell_avg_price, person_sell_count, person_sell_volume, person_sell_value, ' \
                'person_sell_avg_price, status, share_count, base_volume) ' \
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ' \
                '%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

        args = (data['en_symbol_12_digit_code'], data['date_m'], data['first_price'], data['last_price'],
                data['min_price'], data['max_price'], data['end_price'], data['trade_count'], data['trade_volume'],
                data['trade_value'], data['last_trade_time'], data['yesterday_price'], data['legal_buy_count'],
                data['legal_buy_volume'], data['legal_buy_value'], data['legal_buy_avg_price'],
                data['person_buy_count'], data['person_buy_volume'], data['person_buy_value'],
                data['person_buy_avg_price'], data['legal_sell_count'], data['legal_sell_volume'],
                data['legal_sell_value'], data['legal_sell_avg_price'], data['person_sell_count'],
                data['person_sell_volume'], data['person_sell_value'], data['person_sell_avg_price'], data['status'],
                data['share_count'], data['base_volume'])

        return self.command_query(query, args)
    def add_shareholder_data(self, args_list):

        query = 'INSERT IGNORE INTO shareholders_data ' \
                '(en_symbol_12_digit_code, date_m, sh_id, sh_name, volume, percent) VALUES (%s, %s, %s, %s, %s, %s)'
        args = args_list
        return self.command_query_many(query, args)
    def add_share_sub_trad_data(self, args_list, en_symbol_12_digit_code, date_m):
        arg = list()
        for row in args_list:
            arg.append(tuple([en_symbol_12_digit_code, date_m] + row))

        query = 'INSERT IGNORE INTO share_sub_trad_data ' \
                '(en_symbol_12_digit_code, date_m, trad_time, trad_number, volume, price, false_trade) ' \
                'VALUES (%s, %s, %s, %s, %s, %s, %s)'
        args = arg
        return self.command_query_many(query, args)
    def add_status(self, status_list):
        # status_list[en_symbol, date_m, change_time, status, change_number]
        query = 'INSERT IGNORE INTO share_status ' \
                '(en_symbol_12_digit_code, date_m, change_time, share_status, change_number) ' \
                'VALUES (%s, %s, %s, %s, %s)'
        args = status_list
        if len(status_list) > 1:
            return self.command_query_many(query, args)
        else:
            return self.command_query(query, args[0])


    # ----------------------------------
    def get_start_accept_date(self, en_symbol_12_digit_code):
        query = 'select * from share_info where en_symbol_12_digit_code = %s'
        args = (en_symbol_12_digit_code,)

        res = self.select_query_dictionary(query, args, 1)
        if res is not False:
            return res[0]['min_date']
        return False

    def set_start_accept_date(self, en_symbol_12_digit_code, start_accept_date):
        query = 'update share_info set min_date = %s where en_symbol_12_digit_code = %s'
        args = (start_accept_date, en_symbol_12_digit_code)

        return self.command_query(query, args, True)

    def get_end_accept_date(self, en_symbol_12_digit_code):
        query = 'select * from share_info where en_symbol_12_digit_code = %s'
        args = (en_symbol_12_digit_code,)

        res = self.select_query_dictionary(query, args, 1)
        if res is not False:
            return res[0]['max_date']
        return False

    def set_end_accept_date(self, en_symbol_12_digit_code, end_accept_date):
        if end_accept_date > 0:
            query = 'update share_info set max_date = %s, is_active = %s where en_symbol_12_digit_code = %s'
            args = (end_accept_date, 0, en_symbol_12_digit_code)
        else:
            query = 'update share_info set max_date = %s where en_symbol_12_digit_code = %s'
            args = (end_accept_date, en_symbol_12_digit_code)

        return self.command_query(query, args, True)

    # ----------------------------------
    def add_share_second_data(self, en_symbol_12_digit_code, args_list):
        query = 'INSERT IGNORE INTO share_second_data (en_symbol_12_digit_code, date_time, ' \
                'open_price, close_price, high_price, low_price, ' \
                'trade_volume, trade_value, trade_count) ' \
                'VALUES (\'{0}\', %s, %s, %s, %s, %s, %s, %s, %s)'.format(en_symbol_12_digit_code)

        args = args_list

        if len(args) == 1:
            return self.command_query(query, args[0])

        elif len(args) > 1:
            return self.command_query_many(query, args)

        return True  # 'empty arg list'

    # ----------------------------------
    def is_open_day(self, date_m):
        query = 'select count(*) from open_days where date_m = %s'
        args = date_m
        res = self.select_query(query, args, 1)
        if res is not False:
            if res[0][0] > 0:
                return True
        return False




    # ----------------------------------
    def add_share_info(self, info):
        if self.exist_share(info['en_symbol_12_digit_code']) is True:
            query = 'update share_info set fa_symbol_30_digit_code=%s, fa_symbol_name=%s, ' \
                    'company_fa_name=%s, company_en_name=%s, company_4_digit_code=%s, company_12_digit_code=%s, ' \
                    'bord_code=%s, industry_code=%s, sub_industry_code=%s, tsetmc_id=%s, market_flow=%s '\
                    'where en_symbol_12_digit_code = %s'

            args = (info['fa_symbol_30_digit_code'], info['fa_symbol_name'],
                    info['company_fa_name'], info['company_en_name'], info['company_4_digit_code'],
                    info['company_12_digit_code'], info['bord_code'], info['industry_code'],
                    info['sub_industry_code'], info['tsetmc_id'], info['market_flow'],
                    info['en_symbol_12_digit_code'])
        else:
            query = 'INSERT INTO share_info (en_symbol_12_digit_code, en_symbol_5_digit_code, ' \
                    'fa_symbol_30_digit_code, fa_symbol_name, company_fa_name, company_en_name, ' \
                    'company_4_digit_code, company_12_digit_code, ' \
                    'bord_code, industry_code, sub_industry_code, tsetmc_id, is_active, market_flow) ' \
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

            args = (info['en_symbol_12_digit_code'], info['en_symbol_5_digit_code'], info['fa_symbol_30_digit_code'],
                    info['fa_symbol_name'], info['company_fa_name'], info['company_en_name'],
                    info['company_4_digit_code'], info['company_12_digit_code'], info['bord_code'],
                    info['industry_code'], info['sub_industry_code'], info['tsetmc_id'],
                    info['is_active'], info['market_flow'])

        return self.command_query(query, args, True)
    def exist_share(self, share_en_symbol_12_digit_code):
        query = 'select count(*) from share_info where en_symbol_12_digit_code = %s'
        args = share_en_symbol_12_digit_code

        res = self.select_query(query, args, 1)
        if res is not False:
            if res[0][0] > 0:
                return True
        return False
    def add_share_adjusted_coefficient(self, data):
        query = 'INSERT IGNORE INTO share_adjusted_data ' \
                '(en_symbol_12_digit_code, date_m, adjusted_type, old_data, new_data, coefficient, do_data) ' \
                'VALUES (%s, %s, %s, %s, %s, %s, %s)'
        args = data
        return self.command_query_many(query, args)
    def deleted_share_info(self, current_running_share_id):
        query = 'delete from share_info where tsetmc_id = %s'
        args = (current_running_share_id,)
        return self.command_query(query, args)

    # ----------------------------------
    def get_all_index_id(self):
        query = 'select en_index_12_digit_code, index_id from index_info'
        args = ()
        return self.select_query(query, args, 1)
    def add_index_data(self, data):

        query = 'INSERT IGNORE INTO index_data ' \
                '(en_index_12_digit_code, date_m, date_sh, high_index, low_index, ' \
                'open_index, close_index, volume_index) ' \
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
        args = data
        return self.command_query_many(query, args)
    def auto_update_open_days_table(self):
        query = 'INSERT IGNORE INTO open_days SELECT date_m, date_sh FROM index_data ' \
                'GROUP BY date_m ORDER BY date_m DESC'
        args = ()
        return self.command_query(query, args, True)




# ==========================================
class Database_old:

    def __init__(self, db_info, log_obj=None):
        try:
            if log_obj is None:
                self.log = Logging()
                self.log.logConfig(account_id=db_info['db_username'])
            else:
                self.log = log_obj

            self.log.trace()

            self.db_host_name = db_info['db_host_name']
            self.db_username = db_info['db_username']
            self.db_user_password = db_info['db_user_password']
            self.db_name = db_info['db_name']
            self.db_port = db_info['db_port']
        except Exception as e:
            self.log.error('cant create database object: ', str(e))
            return

    # -------------

    # -------------

    # -------------
    def is_empty_db(self):
        query = 'select count(*) from share_daily_data'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            if res[0][0] > 0:
                return False

        query = 'select count(*) from fail_hang_share'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            if res[0][0] > 0:
                return False

        query = 'select count(*) from fail_other_share'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            if res[0][0] > 0:
                return False

        query = 'select count(*) from fail_integrity_share'
        args = ()
        res = self.select_query(query, args, 1)
        if res is not False:
            if res[0][0] > 0:
                return False

        return True



    # ----------------------------------


    def get_active_share_info(self):
        query = 'select en_symbol_12_digit_code, tsetmc_id from share_info where is_active = 1'
        args = ()
        return self.select_query(query, args, 1)

    def get_share_adjusted_data(self, en_symbol_12_digit_code, date_m):
        query = 'select * from share_adjusted_daily_data where en_symbol_12_digit_code = %s and date_m = %s'
        args = (en_symbol_12_digit_code, date_m)
        return self.select_query(query, args, 1)

    def add_share_adjusted_data(self, data):
        query = 'INSERT IGNORE INTO share_adjusted_daily_data ' \
                '(en_symbol_12_digit_code, date_m, high_price, low_price, ' \
                'open_price, close_price, trade_volume, end_price) ' \
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
        args = data
        return self.command_query_many(query, args)

    def clear_share_adjusted_data(self, en_symbol_12_digit_code):
        query = 'delete from share_adjusted_daily_data where en_symbol_12_digit_code = %s'
        args = (en_symbol_12_digit_code)
        return self.command_query(query, args)

    # ----------------------------------
    def add_share_adjusted_coefficient0(self, data):
        query = 'INSERT IGNORE INTO adjusted_coefficient ' \
                '(en_symbol_12_digit_code, date_m, coefficient) ' \
                'VALUES (%s, %s, %s)'
        args = data
        return self.command_query_many(query, args)

    def clear_adjusted_coefficient(self, en_symbol_12_digit_code):
        query = 'delete from adjusted_coefficient where en_symbol_12_digit_code = %s'
        args = (en_symbol_12_digit_code)
        return self.command_query(query, args)


    def add_index_info(self, info):
        query = 'INSERT IGNORE INTO index_info (en_index_12_digit_code, index_id, fa_index_name, fa_index_code, ' \
                'company_4_digit_code, company_en_name) ' \
                'VALUES (%s, %s, %s, %s, %s, %s)'

        args = (info['en_index_12_digit_code'], info['index_id'], info['fa_index_name'], info['fa_index_code'],
                info['company_4_digit_code'], info['company_en_name'])

        return self.command_query(query, args, True)

    def clean_table(self, source_table_name):
        query = 'delete from {0} where 1'.format(source_table_name)
        args = ()
        res = self.command_query(query, args, True)
        if res is False:
            return False
        return True


    # ----------------------------------
    def set_database_update_time(self, update_time):
        query = 'update db_setting set update_time=%s'
        args = (update_time)

        return self.command_query(query, args)



    def get_open_day_count(self):
        query = 'select count(*) from open_days'
        args = ()

        res = self.select_query(query, args, 1)
        if res is not False:
            return int(res[0][0])
        return False




    def update_share_daily_data(self, data):
        query = 'update share_daily_data set end_price=%s, trade_count=%s, trade_volume=%s, trade_value=%s, ' \
                'Legal_buy_count=%s, Legal_buy_volume=%s, Legal_buy_value=%s, Legal_buy_avg_price=%s, ' \
                'person_buy_count=%s, person_buy_volume=%s, person_buy_value=%s, person_buy_avg_price=%s, ' \
                'Legal_sell_count=%s, Legal_sell_volume=%s, Legal_sell_value=%s, Legal_sell_avg_price=%s, ' \
                'person_sell_count=%s, person_sell_volume=%s, person_sell_value=%s, person_sell_avg_price=%s ' \
                'where en_symbol_12_digit_code=%s and date_m=%s'

        args = (data['end_price'], data['trade_count'], data['trade_volume'], data['trade_value'],
                data['legal_buy_count'], data['legal_buy_volume'], data['legal_buy_value'], data['legal_buy_avg_price'],
                data['person_buy_count'], data['person_buy_volume'], data['person_buy_value'], data['person_buy_avg_price'],
                data['legal_sell_count'], data['legal_sell_volume'], data['legal_sell_value'], data['legal_sell_avg_price'],
                data['person_sell_count'], data['person_sell_volume'], data['person_sell_value'], data['person_sell_avg_price'],
                data['en_symbol_12_digit_code'], data['date_m'])

        return self.command_query(query, args)
