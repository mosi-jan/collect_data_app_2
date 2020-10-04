
import time
import tsetmc
from Log import Log_Mod
from my_time import get_now_time_second
import database
from termcolor import colored

from multiprocessing import Process, Lock, Manager  # , active_children, current_process
import psutil


class collect_process_obj(Process):

    def __init__(self, data):
        self.database_info = data['database_info']
        self.client_id = data['client_id']
        self.status = data['status']
        self.lock = data['lock']
        self.wait_list = data['wait_list']
        self.complete_list = data['complete_list']
        self.running_list = data['running_list']
        self.fail_list = data['fail_list']
        self.max_thread = data['max_thread']
        self.last_thread_id = data['last_thread_id']
        self.max_run_time = data['max_run_time']
        self.lock_acquire_wait = data['lock_acquire_wait']

        self.db = database.Database(db_info=self.database_info)

        Process.__init__(self, name=str(self.last_thread_id))
        self.is_hang = False
        # self.obj = None

        # log_file_name = 'log.txt'
        # log_table_name = 'bot_log'
        # logging_mod = Log_Mod.console_file

        # self.obj = tsetmc_2.Tsetmc(id=str(self.last_thread_id), db_info=self.database_info,
        #                           log_file_name=log_file_name, log_table_name=log_table_name, logging_mod=logging_mod,
        #                           lock=self.lock, wait_list=self.wait_list, complete_list=self.complete_list,
        #                           running_list=self.running_list, fail_list=self.fail_list, status=self.status)

    def process(self):
        log_file_name = 'log.txt'
        log_table_name = 'bot_log'
        logging_mod = Log_Mod.console_file

        obj = tsetmc.Tsetmc(id=str(self.last_thread_id), db_info=self.database_info,
                            log_file_name=log_file_name, log_table_name=log_table_name, logging_mod=logging_mod,
                            lock=self.lock, wait_list=self.wait_list, complete_list=self.complete_list,
                            running_list=self.running_list, fail_list=self.fail_list, status=self.status)

        return obj.collect_all_share_data()

    def run(self):
        self.process()

        return




class collect_trade_data_multi_process:

    def __init__(self, database_info, max_process, wait_list, client_id):
        self.print_color = 'cyan'

        self.database_info = database_info
        self.db = database.Database(db_info=self.database_info)
        self.client_id = client_id
        self.lock = Lock()
        self.manager = Manager()
        self.status = self.manager.dict()
        self.wait_list = self.manager.list()
        self.complete_list = self.manager.list()
        self.running_list =self.manager.list()
        self.fail_list = self.manager.list()

        self.max_process = max_process
        self.last_process_id = -1
        self.max_run_time = 200
        self.lock_acquire_wait = 15

        self.hang_list = list()

        for item in wait_list:
            self.wait_list.append(item)

        self.data = dict()  # common data from process
        self.set_data()

        self.process_list = list()

        self.lock_status = False


    def set_data(self):
        self.data['database_info'] = self.database_info
        self.data['client_id'] = self.client_id
        self.data['status'] = self.status

        self.data['lock'] = self.lock
        self.data['wait_list'] = self.wait_list
        self.data['complete_list'] = self.complete_list
        self.data['running_list'] = self.running_list
        self.data['fail_list'] = self.fail_list

        self.data['max_thread'] = self.max_process
        self.data['last_thread_id'] = self.last_process_id
        self.data['max_run_time'] = self.max_run_time
        self.data['lock_acquire_wait'] = self.lock_acquire_wait

    def set_status(self, obj_name, item, value):
        s = self.status[obj_name]
        s[item] = value
        self.status[obj_name] = s

    def terminate_process_tree(self, process, include_parent=True, timeout=None):
        print(colored('process id: {}'.format(process.pid), 'blue'))

        procs = psutil.Process(process.pid).children(recursive=True)

        print(colored(procs, 'red'))

        # send SIGTERM
        for ch_p in procs:
            try:
                print(colored(ch_p, 'red'))
                ch_p.terminate()
            except psutil.NoSuchProcess:
                pass
        gone, alive = psutil.wait_procs(procs, timeout=timeout)
        if alive:
            # send SIGKILL
            for ch_p in alive:
                print("process {} survived SIGTERM; trying SIGKILL" % process)
                try:
                    ch_p.kill()
                except psutil.NoSuchProcess:
                    pass
            gone, alive = psutil.wait_procs(alive, timeout=timeout)
            if alive:
                # give up
                for ch_p in alive:
                    print("process {} survived SIGKILL; giving up" % process)
                    return False

        if include_parent is True:
            process.terminate()
            process.join()
        # self.hang_process_list.remove(process)

        return True

    def print_c(self, text, color=None):
        try:
            if color is None:
                print(colored(text, self.print_color))
            else:
                print(colored('| ', self.print_color) + colored(text, color))
                # print(colored(text, color))
        except Exception as e:
            self.print_c(str(e), 'red')

    def stop_all_process(self):
        if self.lock.acquire(timeout=self.lock_acquire_wait) is True:
            self.lock_status = True
            for p in self.process_list:
                try:
                    self.set_status(p.name, 'stop_flag', True)

                except Exception as e:
                    print('cant stop process: {0} ; error: {1}'.format(p.name, str(e)))
            self.lock.release()
            self.lock_status = False

    def run(self):
        self.first_start_flag = True
        self.lock_status = False
        self.hang_time = self.max_run_time * 3 * self.max_process
        while True:
            try:
                self.print_c('get setting')

                main_stop_flag = self.db.get_main_stop_flag(self.client_id)
                if main_stop_flag is False:
                    raise Exception('fail to get main_stop_flag')

                self.max_process = self.db.get_max_thread_from_db(self.client_id)
                if self.max_process is False:
                    raise Exception('fail to get max_thread')

                # check exit condition
                self.print_c('check exit condition')
                if self.first_start_flag is True:
                    self.first_start_flag = False
                else:
                    if len(self.process_list) == 0 and (main_stop_flag > 0 or len(self.wait_list) == 0):
                        self.print_c('exit function from condition: 1')
                        result = True
                        break

                self.print_c('check stop flag')
                if main_stop_flag > 0:
                    self.print_c('stop all process from user')
                    self.stop_all_process()

                else:
                    if len(self.process_list) < self.max_process and (len(self.wait_list) > 0 or (len(self.complete_list) + len(self.running_list) + len(self.fail_list)) == 0):# ???
                        need_process = self.max_process - len(self.process_list) - 2
                        if need_process > 0:
                            for i in range(need_process):
                                if len(self.wait_list) <= 1:
                                    print('empty wait list')
                                    break
                                # ایجاد پروسس جدید
                                self.last_process_id += 1
                                self.print_c('create new process id:{0}'.format(self.last_process_id))
                                self.set_data()
                                p = collect_process_obj(self.data)
                                time.sleep(0.5)
                                p.start()
                                self.process_list.append(p)

                        # ایجاد پروسس جدید
                        self.last_process_id += 1
                        self.print_c('create new process id:{0}'.format(self.last_process_id))
                        self.set_data()
                        p = collect_process_obj(self.data)
                        time.sleep(0.5)
                        p.start()
                        self.process_list.append(p)

                    elif len(self.process_list) > self.max_process:
                        self.print_c('stop all process because upper than max process')
                        self.stop_all_process()

                # -------------
                if self.lock.acquire(timeout=self.lock_acquire_wait) is True:
                    self.lock_status = True
                    self.print_c('check process runtime')
                    for p in self.process_list:
                        # check started process
                        if p.name in self.status:
                            if 'last_run_time' in self.status[p.name]:
                                # check process runtime
                                try:
                                    if  (get_now_time_second() - self.status[p.name]['last_run_time']) > self.max_run_time:
                                        self.print_c('stop process {0} because max runtime'.format(p.name))
                                        self.set_status(p.name, 'stop_flag', True)

                                    if  (get_now_time_second() - self.status[p.name]['last_run_time']) > self.hang_time:
                                        self.print_c('terminate process {0} because hanged')

                                        hang_item = self.status[p.name]['current_running_share']
                                        if hang_item not in self.hang_list:
                                            self.hang_list.append(hang_item)
                                            self.print_c('terminate process: {0} ; en_symbol_12_digit_code: {1} ; tsetmc_id: {2} ; date_m: {3} ; process: {4}'.format(p.name, hang_item[0], hang_item[1],hang_item[2], p))
                                            # time.sleep(15)
                                            if self.terminate_process_tree(process=p, include_parent=True, timeout=10) is True:

                                                self.db.add_share_to_fail_hang_share(en_symbol_12_digit_code=hang_item[0], date_m=hang_item[1])
                                                self.running_list.remove(hang_item)
                                                # self.hang_list.remove(hang_item)

                                            else:
                                                self.db.add_share_to_fail_hang_share(en_symbol_12_digit_code=hang_item[0], date_m=hang_item[1])

                                except Exception as e:
                                    self.print_c('except: {0} ; error: {1} ; process: {2}'.format('cant chack process runtime', str(e), p))

                    self.lock.release()
                    self.lock_status = False
                self.print_c('check not alive process')
                for p in self.process_list:
                    if p.is_alive() is False:
                        self.print_c('terminate process: {}'.format(p.name))
                        p.terminate()
                        p.join()
                        self.process_list.remove(p)

                # print status
                self.lock.acquire(timeout=self.lock_acquire_wait)
                self.lock_status = True
                process_symbols = list()
                for p in self.process_list:
                    try:
                        a = self.status[p.name]['current_running_share']
                        process_symbols.append('{0}:{1}:{2}'.format(a[0], a[1], a[2]))
                    except:
                        pass

                running_list_symbol = list()
                for p in self.running_list:
                    running_list_symbol.append('{0}:{1}:{2}'.format(p[0], p[1], p[2]))

                hang_symbol = list()
                for p in self.hang_list:
                    hang_symbol.append('{0}:{1}:{2}'.format(p[0], p[1], p[2]))

                color = 'magenta'
                self.print_c('wait_list:{0}  complete_list:{1}  running_list:{2}  fail_list:{3}  '
                             'alive_process:{4}  hang_symbol:{5}  symbols:{6}, hang_symbol:{7}'
                             .format(len(self.wait_list), len(self.complete_list), len(self.running_list),
                                     len(self.fail_list), (len(self.process_list) - len(self.hang_list)),
                                     len(hang_symbol), process_symbols, hang_symbol), color)
                #self.print_c(
                #    'wait_list:{0}  complete:{1}  running:{2}  fail:{3}  hang:{4}  alive_process:{5}  process_symbols:{6}  running_symbols:{7}  hang_symbol:{8}'
                #    .format(len(self.wait_list), len(self.complete_list), len(self.running_list), len(self.fail_list), len(self.hang_list),
                #            (len(self.process_list) - len(self.hang_list)), process_symbols, running_list_symbol, hang_symbol), color)

                #self.print_c(
                #    'wait_list:{0}  complete:{1}  running:{2}  fail:{3}  hang:{4}  alive_process:{5}  process_symbols:{6}  running_symbols:{7}  hang_symbol:{8}'
                #        .format(len(self.wait_list), len(self.complete_list), len(self.running_list),
                #                len(self.fail_list), len(self.hang_list), len(self.process_list),
                #                process_symbols, running_list_symbol, hang_symbol), color)

                self.lock.release()
                self.lock_status = False

                time.sleep(5)

                # ----------------------
                # i += 1
                # if i > 5:
                #    print('start hang i:{0}'.format(i))
                #    for p in self.process_list:
                #        try:
                 #           name = p.name
                 #           print(colored('--- user terminate start:{0}'.format(name), 'green'))
                 #           print('--- user terminate start: ' + name)
                 #           if p not in self.hang_process_list:
                 #               if self.terminate_process_tree(process=p, include_parent=True, timeout=10) is False:
                 #                   print('terminate fail')
                 #               else:
                 #                   print('terminate ok')

                 #               print('--- user terminate end: ' + name)
                 #               print(colored('--- user terminate end:{0}'.format(name), 'green'))

                 #               break
                 #       except:
                 #           pass
                 #   i = 0



                # ----------------------

            except Exception as e:
                if self.lock_status is True:
                    self.print_c('main except: lock status: True :' + str(3) + ' : ' + str(e))
                    for p in self.process_list:
                        try:
                            self.print_c('terminate thread: ' + p.name)
                            # self.status[p.name]['stop_flag'] = True
                            self.set_status(p.name, 'stop_flag', True)
                        except Exception as e:
                            self.print_c('main except: ' + str(4) + ' : ' + str(e))
                    self.lock.release()
                else:
                    self.print_c('main except: lock status: False :' + str(5) + ' : ' + str(e))
                    self.lock.acquire()
                    for p in self.process_list:
                        try:
                            self.print_c('terminate thread: ' + p.name)
                            # self.status[p.name]['stop_flag'] = True
                            self.set_status(p.name, 'stop_flag', True)
                        except Exception as e:
                            self.print_c('main except: ' + str(6) + ' : ' + str(e))
                    self.lock.release()

                self.print_c('wait to exit all thread')
                while len(self.process_list) > 0:
                    try:
                        for p in self.process_list:
                            self.print_c('terminate process: {}'.format(p.name))
                            p.terminate()

                        for p in self.process_list:
                            self.print_c('wait to exit thread: {}'.format(p.name))
                            p.join()
                    except:
                        pass

                self.print_c('exit main: 2')
                result = False
                break
        return result
