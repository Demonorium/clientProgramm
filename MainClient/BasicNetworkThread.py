from threading import *
from Log import Log
import socket

import Protocol

class BasicNetworkThread(Thread):
    """Универсальный класс для работы с потоками"""

    def __init__(self, name: str, log: Log, timeout, request_send, force_send):
        Thread.__init__(self)
        self.name = name
        self.log = log
        self.timeout = timeout
        self.stoped = True
        self.request_send   = request_send
        self.force_send     = force_send

    def wlog(self, *args):
        '''Вывод в лог'''
        self.log.write(*args)

    def send_to_main_server(self, *args):
        '''Запросить отправку у главного потока'''
        self.request_send(*args)

    def init_action(self):
        '''Действие при запуске потока'''
        self.wlog('Запуск потока:', self.name)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        

    def loop_action(self):
        '''Действие выполняющиеся в цикле, пока поток активен'''
        pass
    
    def timeout_action(self, exception):
         '''Действие при прерывании по причине превышения времени ожидания'''
         pass
   
    def error_action(self, exception):
        '''Действие при прерывании по причине ошибки (разрыв связи или что-то ещё)'''
        self.wlog(exception)

    def critical_error_action(self, exception):
        '''Действие при неизвестной ошибке (стандарт: вывод в лог)'''
        self.wlog('КРИТИЧЕСКАЯ ОШИБКА В ПОТОКЕ:', self.name)
        self.wlog(exception)

        try:
            self.wlog('Закрытие сокета в потоке:', self.name)
            self.socket.close()
        except Exception as ex:
            print(ex)

        self.force_send(Protocol.DEATH, 0, 0, 0, 0)
        exit(0)

    def stop(self):
        self.stoped = True

    def finalize(self):
        self.socket.close()
        
    def run(self):
        self.stoped = False
        try:
            self.init_action()
        except Exception as ex:
            self.critical_error(ex)

        while not self.stoped:
            try:
                self.loop_action()
            except socket.timeout as ex:
                self.timeout_action(ex)
            except socket.error as ex:
                self.error_action(ex)
            except Exception as ex:
                self.critical_error_action(ex)

        self.finalize()