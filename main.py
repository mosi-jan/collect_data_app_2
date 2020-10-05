from client import Client
import app_setting



if __name__ == '__main__':

    cli = Client(client_id=app_setting.client_id, db_info=app_setting.db_info)

    res = cli.collect_all_shares_info()
    #res = cli.collect_all_index_daily_data()
    #res = cli.collect_all_share_data()

    print(res)
