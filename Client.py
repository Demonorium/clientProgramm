

from threading import *
import socket
import sys
import random

#Объявление соектов
udp_socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket_receive.bind(('', 4444)) # 0001 0001 0101 1100
udp_socket_receive.settimeout(0.25)

host = 'localhost'
port = 3333
send_addr = (host, port)

password = 'valid cd'
name = 'kruglov igor'

def insert(data, string):
    for i in string:
        data.append(ord(i))

def make_data(lst):
    data = bytearray()
    for v in lst:
        if type(v) == str:
            insert(data, v)
        else:
            data.append(v)
    return data

def send_data(data):
    global udp_socket_send
    print('Отправка:', send_addr)
    udp_socket_send.sendto(make_data(data), send_addr)
    
START_REQUEST = [0, password, 92, 17, name]


any_data_rec = False

player_list = []
player_list_lock = Lock()
self_ip = '127.0.0.1'

death_found = False
death_id = []

self_death = False

def make_ip(b1, b2, b3, b4):
    return f'{b1}.{b2}.{b3}.{b4}'

class Protocol:
    GREATER = make_data(['G'])
    LESS = make_data(['L'])
    DEATH = make_data(['D'])
    NO = make_data(['N'])

    def equals(data1, data2):
        if len(data1) != len(data2):
            return False

        for i in range(len(data1)):
            if data1[i] != data2[i]:
                return False
        return True

class Listener(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stoped = False
        self.timeout = 1.5
        self.back = None


    def run(self):
        global self_death, self_killer, self_ip, death_found
        input_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        input_socket.bind(('', 2222))
        input_socket.listen(1)
        input_socket.settimeout(self.timeout)
        #Выбираю число
        amount = random.randint(0, 127)
        print('Выбрано число:', amount)
        rnd = random.Random()
        
        self.stoped = False
        while not self.stoped:
            try:
                connection, address = input_socket.accept()
                enemy_ip = address[0]

                try:
                    while True:
                        data = connection.recv(255)
                        if not data:
                            if death_found:
                                player_list_lock.acquire()
                                if enemy_ip in death_id:
                                    connection.close()
                                    player_list_lock.release()
                                    death_found = False
                                    print('Пытавшийся убить умер')
                                    break
                                death_found = False
                                player_list_lock.release()
                        else:
                            if data[0] == amount:
                                connection.send(Protocol.DEATH)

                                print('Умираю')
                                data_array = [3]
                                for n in address[0].split('.'):
                                    data_array.append(int(n))

                                send_data(data_array)
                                self_killer = enemy_ip
                                self.stop()
                                break
                            if rnd.random() > 0.8:
                                if data[0] < amount:
                                    connection.send(Protocol.GREATER)
                                else:
                                    connection.send(Protocol.LESS)
                            else:
                                connection.send(Protocol.NO)

                except socket.timeout as ex:
                    connection.close()
                    continue;
                except socket.error as ex:
                    connection.close()
                    print('Произошла ошибка')
                    print(ex)
                    continue;
            except socket.timeout as ex:
                continue;
            except socket.error as ex:
                print('Произошла ошибка')
                print(ex)
                continue;
        input_socket.close()

        if self.back != None:
            self.back.stop()
        
    def stop(self):
        self.stoped = True


class NumberGenerator:
    def __init__(self):
        self.L = 0
        self.R = 128

        self.mark = {}
        self.current = (self.R + self.L) // 2
        self.step = False
        self.start_left = self.current
        self.start_right = self.current


    def get_number(self):
        self.step = not self.step
        if self.step and (self.start_right < self.R):
            temp = self.start_right
            self.start_right += 1
            return temp
        else:
            temp = self.start_left
            self.start_left -= 1
            return temp

    def tip(self, data):
        if Protocol.equals(data, Protocol.GREATER):
            self.L = self.start_right
            self.current = (self.R + self.L) // 2
            self.start_left = self.current
            self.start_right = self.current
        elif Protocol.equals(data, Protocol.LESS):
            self.R = self.start_left + 1
            self.current = (self.R + self.L) // 2
            self.start_left = self.current
            self.start_right = self.current
        else:
            if self.step and (self.start_right < self.R):
                self.start_right += 1
            else:
                self.start_left -= 1
      

class Attacker(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stoped = False
        self.timeout = 0.1
        self.generators = dict() 

    def run(self):
        global player_list
        
        try:
            self.stoped = False
            while not self.stoped:
                status = False
            
                #Выбор игрока
                player_list_lock.acquire()
                if len(player_list) > 1:
                    index = player_list.index(self_ip)
                    target_index = index
                    while target_index == index:
                        target_index = random.randint(0, len(player_list) - 1)

                    target_ip = player_list[target_index]
                else:
                    player_list_lock.release()
                    continue
                player_list_lock.release()

                try:
                    print('Пытаюсь подключиться к', target_ip)
                    output_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    output_socket.settimeout(self.timeout)
                    output_socket.connect((target_ip, 2222))
                    print('Атакую цель', target_ip)

                    generator = None
                    if target_ip in self.generators:
                        generator = self.generators[target_ip]

                    if generator == None:
                        generator = NumberGenerator()
                        self.generators[target_ip] = generator

                    while True:
                        num = generator.get_number()
                        print(num)
                        output_socket.send(make_data([num]))
                        data = output_socket.recv(255)
                        if Protocol.equals(data, Protocol.DEATH):
                            break;
                        else:
                            generator.tip(data)
                    output_socket.close()
                except socket.timeout as ex:
                    continue;
                except socket.error as ex:
                    print('Произошла ошибка')
                    print(ex)
                    continue;
        except ValueError as er:
            print(er)

    def stop(self):
        self.stoped = True

output_thread = Attacker()
input_thread = Listener()
input_thread.back = output_thread

send_data(START_REQUEST)
while True:
    try:
        content = udp_socket_receive.recv(255)
        if self_death:
            if content[0] == 3:
                ip = make_ip(content[1], content[2], content[3], content[4])
                print('Обнаружена смерть:', ip)
                if ip == self_ip:
                    udp_socket_receive.close()
                    exit(0)
                else:
                    data_array = [3]
                    for n in self_killer.split('.'):
                        data_array.append(int(n))

                    send_data(data_array)
            else:
                data_array = [3]
                for n in self_killer.split('.'):
                    data_array.append(int(n))

                send_data(data_array)
                continue

        if not any_data_rec:
            any_data_rec = 0 <= content[0] <= 4

        if content[0] == 0:
            send_data([2])

        if content[0] == 1:
            send_data([4])
            if not output_thread.stoped:
                output_thread.start()
                input_thread.start()

        if content[0] == 2:
            count = content[1]
            player_list_lock.acquire()
            player_list = []
            for i in range(count):
                player_list.append(make_ip(content[1 + i*4 + 1], content[1 + i*4 + 2], 
                                           content[1 + i*4 + 3], content[1 + i*4 + 4]))

            print('Таблица обновлена:', player_list)
            player_list_lock.release()

        if content[0] == 3:
            ip = make_ip(content[1], content[2], content[3], content[4])
            print('Обнаружена смерть:', ip)
            if ip == self_ip:
                exit(0)
            else:
                if ip in player_list:
                    death_id.append(ip)
                    death_found = True

                    player_list_lock.acquire()
                    player_list.remove(ip)
                    player_list_lock.release()

                send_data([4])
        if content[0] == 4:
            self_ip = make_ip(content[1], content[2], content[3], content[4])
            print('Регистрация как', self_ip)
    except socket.timeout as tm:
        if not any_data_rec:
            send_data(START_REQUEST)
    except OSError as ex:
        print(ex)
        if not any_data_rec:
            send_data(START_REQUEST)


