
# main linux : 1
# laptop : 2
# ----------------
client_id = 1


# local main linux : 1
# local laptop : 2
# remote main linux : 3
# remote main linux temp : 4
# ----------------
db_server_id = 1

# ===============================
def get_db_info(db_server_id):
    db_info = {
        'db_name': 'cd2',
        'db_username': 'CD2',
        'db_user_password': 'Asdf@13579.',
        'db_host_name': 'localhost',
        'db_port': 3306
    }

    if db_server_id == 1:  # local main linux
        db_info = {
            'db_name': 'cd2',
            'db_username': 'CD2',
            'db_user_password': 'Asdf@13579.',
            'db_host_name': 'localhost',
            'db_port': 3306
        }

    elif db_server_id == 2:  # local laptop
        db_info = {
            'db_name': 'cd2',
            'db_username': 'CD2',
            'db_user_password': 'Asdf@13579.',
            'db_host_name': 'localhost',
            'db_port': 3306
        }

    elif db_server_id == 3:  # remote main linux
        db_info = {
            'db_name': 'cd2',
            'db_username': 'CD2_R',
            'db_user_password': 'Asdf@13579.',
            'db_host_name': '192.168.1.35',
            'db_port': 3306
        }

    elif db_server_id == 4:  # remote main linux temp
        db_info = {
            'db_name': 'cd2',
            'db_username': 'CD2_R',
            'db_user_password': 'Asdf@13579.',
            'db_host_name': '192.168.43.164',
            'db_port': 3306
        }

    return db_info