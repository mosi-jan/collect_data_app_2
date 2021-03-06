from client import Client
import app_setting
from my_time import get_now_time_datetime
from my_time import get_now_time_second
import datetime
from time import sleep


if __name__ == '__main__':
    first_run = True

    cli = Client(client_id=app_setting.client_id,
                 db_info=app_setting.get_db_info(db_server_id=app_setting.db_server_id))
    # cli.test_db_function_transfer()

    # print('transfer share_second_data_part : start')
    # source_table = 'share_second_data'
    # destination_table = 'share_second_data_part'
    # cli.test_db_function_transfer(source_table=source_table, destination_table=destination_table)
    # print('transfer share_second_data_part : end')
    # exit(0)

    # start = get_now_time_second()
    # cli.get_table_records('share_second_data_part')
    # print('share_second_data_part runtime: {}'.format(get_now_time_second() - start))
    # exit(0)

    # print('*********************')
    # sleep(100)
    # exit(0)

    while True:
        now_time = get_now_time_datetime()
        now_timedelta = datetime.timedelta(hours=now_time.hour, minutes=now_time.minute, seconds=now_time.second)

        if first_run is True:
            first_run = False
        else:
            if (now_timedelta > datetime.timedelta(hours=9)) and (now_timedelta < datetime.timedelta(hours=18)):
                # ساعات معاملات
                offset = datetime.timedelta(hours=18, minutes=0, seconds=0) - now_timedelta
                print('sleep time {} second'.format(offset.seconds))
                sleep(offset.seconds)
                continue

        # update share info
        if now_time.day in (1, 15):
            print('collect_all_shares_info: {}'.format(cli.collect_all_shares_info()))

        # update index data
        print('collect_all_index_daily_data error: {}'.format(cli.collect_all_index_daily_data()))

        # find source fail data
        print('find_shares_fail_source_data error: {}'.format(cli.find_shares_fail_source_data()))

        # update trade data
        print('collect_all_share_data: {}'.format(cli.collect_all_share_data()))

        offset = datetime.timedelta(hours=18, minutes=0, seconds=0) - now_timedelta
        print('now time: {} ,sleep time {} second'.format(get_now_time_datetime().time(), offset.seconds))
        sleep(offset.seconds)
