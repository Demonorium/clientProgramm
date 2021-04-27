from threading import *
from Log import Log
import socket

import Protocol

class BasicNetworkThread(Thread):
    """Универсальный класс для работы с потоками."""

    def __init__(self, name: str, log: Log, timeout, request_send, force_send):
        Thread.__init__(self)
        self.name = name                    #Имя потока: отображается в логе при запуске
        self.log = log                      #Объект для вывода в лог
        self.timeout = timeout              #Таймаут для сокета: время, которое сокет ждёт следующего сообщения
        self.stoped = True                  #Остановлен ли сейчас поток
        self.request_send   = request_send  #Запрос к главному серверу: отправка пакета
        self.force_send     = force_send    #Принудительная асинхронная отправка пакета: может повлечь краш 

    def wlog(self, *args):
        '''Вывод в лог'''
        self.log.write(*args)

    def send_to_main_server(self, *args):
        '''Запросить отправку у главного потока'''
        self.request_send(*args)

    def init_socket(self):
        '''Создаёт TCP сокет и настраивает его таймаут на self.timeout'''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)

    def init_action(self):
        '''Действие при запуске потока'''
        self.wlog('Запуск потока:', self.name)
        self.init_socket()
        

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
        exit()

    def stop(self):
        '''Остановить поток'''
        self.stoped = True

    def finalize(self):
        '''Действие после остановки потока'''
        if self.socket != None:
            self.socket.close()
        
    def run(self):
        '''Данный метод не должен вызываться пользователем класса, он вызывается только при запуске потока.'''
        
        self.stoped = False #Поток запущен
        try:
            self.init_action() #Вызов дейтсвия запуска
        except Exception as ex:
            self.critical_error_action(ex) #Если в нём всё упало - говорим об этом

        while not self.stoped: #До тех пор, пока поток не остановлен
            try:
                self.loop_action() #Выполняем действие из loop_action
            except socket.timeout as ex: #Если сокет выкинул timeout
                self.timeout_action(ex) 
            except socket.error as ex:   #Если произошла ошибка в сокете, например разрыв соединения
                self.error_action(ex)
            except Exception as ex:      #Если упало всё
                self.critical_error_action(ex)

        self.finalize() #Действие при конце исполнения кода 