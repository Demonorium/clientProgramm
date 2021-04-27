import socket
import random
import time

from NumberGenerator import NumberGenerator
from BasicNetworkThread import BasicNetworkThread
import Protocol
import RawData

class AttackThread(BasicNetworkThread):
    '''Поток, который пытается положить врагов'''
    def __init__(self, log, timeout, request_send, force_send,  request_table, remove_player):
        BasicNetworkThread.__init__(self, 
                                    name = "Атакующий",
                                    log = log,
                                    timeout = timeout,
                                    request_send = request_send,
                                    force_send   = force_send)
        self.generators = dict() 
        self.request_table = request_table
        self.remove_player = remove_player
        self.link = False


    def error_action(self, exception):
        super().error_action(exception)
        if self.socket != None:
            self.wlog('Разрыв соединения')
            try:
                self.socket.close()
            except socket.error as ex:
                self.wlog(ex)
            self.socket = None
    
    def timeout_action(self, exception):
        super().timeout_action(exception)
        if self.socket != None:
            self.wlog('Разрыв соединения: превышено время ожидания')
            try:
                self.socket.close()
            except socket.error as ex:
                self.wlog(x)
            self.socket = None
                
    def init_action(self):
        super().init_action()
        
        #Работа в многопоточном режиме не даёт использовать math.random (риск ошибок)
        self.rnd = random.Random()
        self.rnd.seed(round(1000* time.time()))

    def loop_action(self):
        if self.socket == None:
            self.socket = socket.socket()
            self.socket.settimeout(self.timeout)

        players = self.request_table()
        target_index = 0
        target_ip = ''
        if len(players) > 0:
            target_index = self.rnd.randrange(0, len(players))
            target_ip = players[target_index]
        else:
            return;
        
        #Пытаемся подключиться к выбранному игроку
        self.wlog('Попытка атаковать:', target_ip)
        self.socket.connect((target_ip, Protocol.INPUT_PORT))
        self.wlog('Начало атаки:', target_ip)
        #Если подключение прошло
        
        #Проверяем, не подключались ли мы к нему раньше
        #Если подключались - у нас есть ПОПЫТКА ЕГО УБИЙСТВА в словаре ip-generator
        generator = None
        if target_ip in self.generators:
            #Если генератор найден
            generator = self.generators[target_ip]

        if generator == None:
            #Если игрока видим впервые, создаём пустой генератор
            generator = NumberGenerator()
            self.generators[target_ip] = generator #И говорим, что мы пытались убить игрока

        while not self.stoped: #Цикл продолжается до первой ошибки или остановки потока (смерти) или смерти оппонента 
            num = generator.get_number()        #Запрашиваем новое число у генератора
            self.wlog('Отправка числа:', num)   
            
            time.sleep(Protocol.SEND_DELAY) #Ждём указанную в протоколе задержку
            self.socket.send(RawData.make_data(RawData.Number(num, RawData.BYTE_RANGE_SIZE)))   #Отправляем игроку число
            
            data = self.socket.recv(255)        #Ждём ответ от игрока
            self.wlog('Получен ответ:', data)
            
            if RawData.check(data, RawData.DEATH_DATA): #Если игрок умер
                self.socket.close() #Отключаемся
                self.init_socket()  #Пересоздаём сокет
                
                ip = target_ip.split('.') #Преобразуем ip игрока в последовательность чисел
                
                for i in range(2):
                    #Дважды просим главный сервер убить его
                    self.request_send(Protocol.ServerRequests.KILL, 
                                 int(ip[0]), int(ip[1]), int(ip[2]), int(ip[3]))
                self.remove_player(target_ip) #Удаляем из НАШЕЙ таблицы
                break; #Выходим из цикла

            #Если игрок нам ответил, отправляем соотвествующую подсказку нашему гененатору
            elif RawData.check(data, RawData.GREATER_DATA): 
                generator.tip(NumberGenerator.GREATER)
            elif RawData.check(data, RawData.LESS_DATA):
                generator.tip(NumberGenerator.LESS)
            elif RawData.check(data, RawData.NO_DATA):
                generator.tip(NumberGenerator.NO)
            else:
                #Игрок отправил дичь...
                self.wlog('Неизвестный код ответа')





