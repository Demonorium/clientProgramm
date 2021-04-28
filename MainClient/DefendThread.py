import socket
import random

import time
from BasicNetworkThread import BasicNetworkThread
import Protocol
import RawData




class DefendThread(BasicNetworkThread):
    '''Поток, который умеет загадывать число и убивает программу при получении числа'''
    def __init__(self, log, timeout, request_send, force_send, death_checker, kill_everything):
        BasicNetworkThread.__init__(self, 
                                    name = "Защитник",
                                    log = log,
                                    timeout = timeout,
                                    request_send = request_send,
                                    force_send   = force_send)
        self.death_checker = death_checker     #Метод, который должен проверить жив ли игрок
        self.kill_everything = kill_everything #Метод, который должен убить все потоки в случае смерти игрока

    def init_action(self):
        super().init_action()

        self.socket.bind(('', Protocol.INPUT_PORT)) #Наш сокет слушает входящие соединения с порта указнного в протоколе
        self.socket.listen(1)                       #Мы принимаем не более 1 соединения за раз
        #Работа в многопоточном режиме не даёт использовать math.random (риск ошибок)
        self.rnd = random.Random()
        self.rnd.seed(round(1000* time.time()))

        #Выбираем число при котором умираем
        self.death_number = self.rnd.randint(Protocol.MIN_NUMBER, Protocol.MAX_NUMBER)
        self.wlog('Загадано число:', self.death_number)

        self.connection = None

    def error_action(self, exception):
        super().error_action(exception)
        if self.connection != None:
            self.wlog('Разрыв соединения')
            try:
                self.connection.close() #Если разоварлось соединение убиваем соединение с игроком
            except socket.error as ex:
                self.wlog(ex)
    
    def timeout_action(self, exception):
        super().timeout_action(exception)
        if self.connection != None:
            self.wlog('Разрыв соединения: превышено время ожидания')
            try:
                self.connection.close()  #Если разоварлось соединение убиваем соединение с игроком
            except socket.error as ex:
                self.wlog(ex)

    def loop_action(self):
        self.connection, self.enemy_address = self.socket.accept() #Ждём подключения
        self.enemy_ip = self.enemy_address[0]                      #Если подключились, запоминаем ip
        
        self.wlog('Принято подключение:', self.enemy_address)
        while not self.stoped:
            #Слушаем данные от цели
            data = self.connection.recv(255) 
            if self.stoped:
                self.connection.close() #Если что-то убило нас - отключаемся
                break;


            if not data: #Если данные не получены
                #Проверяем не помер ли враг
                if self.death_checker(self.enemy_ip): 
                    self.wlog('Атакующий умер')
                    self.connection.close()
                    break;

            elif len(data) >= RawData.BYTE_RANGE_SIZE:  #Если пакет может содержать число
                self.wlog('Получены данные', data)
                number = RawData.read_number(data, RawData.BYTE_RANGE_SIZE)      #Читаем число
                self.wlog('Получено число:', number)
                if number == self.death_number:         #Если число равно загаданому  - умираем
                    self.wlog('Смерть')
                    self.kill_everything()              #Если мы умерли - убиваем все потоки
                    self.connection.send(RawData.DEATH_DATA)    #Говорим, что умерли
                    self.connection.close()                     #Разрываем соединение
                    exit()                                      #Прерываем исполнение
                else:
                    #Если число неверное, сообщаем с некоторым шансом направление поиска
                    if self.rnd.random() > Protocol.NO_CHANCE:
                        if number < self.death_number:  #Если меньше загаданного
                            self.connection.send(RawData.GREATER_DATA)
                        else: #Если больше
                            self.connection.send(RawData.LESS_DATA)
                    else:  #Если игроку не повезло
                        self.connection.send(RawData.NO_DATA)
            else:
                self.wlog('Некорректный пакет от:', self.enemy_ip)
                self.wlog(data)

        self.connection     = None
        self.enemy_address  = None
        self.enemy_ip       = None


