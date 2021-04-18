from threading import *
import socket
import sys


from Log import Log
import Protocol
from Protocol import ServerRequests
from Protocol import ServerResponse


#Объявление констант
SERVER_IP = '127.0.0.1'
SERVER_PORT = 3333
SERVER_ADDRESS = (SERVER_IP, SERVER_PORT)

SERVER_PASSWORD = 'valid cd'
USERNAME = 'Kruglov Igor'

INPUT_PORT = 4444
INPUT_BUFFER = 255 #Максимальный размер пакета, который может прилететь от сервера
INPUT_TIMEOUT = 0.25

MAIN_SERVER_LOG_FILE = "m-server.log"
INPUT_LOG            = "input.log"
OUTPUT_LOG           = "output.log"

ENEMY_INPUT_TIMEOUT  = Protocol.SEND_DELAY*2 + 0.25

TABLE_UPDATE_DELAY = 2.0


#Создание сокетов для работы с главным сервером
udp_socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket_receive.bind(('', INPUT_PORT)) 
udp_socket_receive.settimeout(INPUT_TIMEOUT)


#Формирование запроса о регистрации
from RawData import make_data
from RawData import Number

REGISTER_REQUEST = make_data(
    ServerRequests.REGISTER,    #Код запроса
    SERVER_PASSWORD,            #Пароль
    Number(INPUT_PORT, 2),      #Порт для приёма сообщений
    USERNAME                    #Имя
    )

#Объявление глобальных переменных
data_received = False       #Если был получен хоть один ответ от сервера - true
player_list = []            #Список игроков
player_list_lock = Lock()   #Мьютекс списка игроков

user_ip = None              #IP под которым главный сервер видит игрока

attacker = None             #Поток, атакующий игроков
defender = None             #Поток, принимающий подключения

death_found      = False    #Наличие смерти

table_request_time = 0      #Время с последнего запроса таблицы
last_time          = 0      #Время последней итерации

game_started = False        #Игра началась?

#Запрос на отправку на сервер
request_list = []
request_lock = Lock()


main_log    = Log(MAIN_SERVER_LOG_FILE)
output_log  = Log(OUTPUT_LOG)
input_log   = Log(INPUT_LOG)

#Главный цикл
main_loop = True;
#Вспомогательные процедуры
from DefendThread import DefendThread
from AttackThread import AttackThread

def check_request(data: bytearray, code: int):
    '''Проверяет, что прилетевшее сообщение содержит указанный код'''
    if len(data) < 1:
        return False
    else:
        return data[0] == code

def make_ip(b1, b2, b3, b4):
    '''Преобразует 4 числа в строку ip'''
    return f'{b1}.{b2}.{b3}.{b4}' 

def send_to_server_raw(bin_data: bytearray):
    '''Отправляет указанные данные серверу'''
    global main_log, udp_socket_send, SERVER_ADDRESS
    main_log.write('Отправка запроса к главному серверу:', bin_data)
    udp_socket_send.sendto(bin_data, SERVER_ADDRESS)

def send_to_server(*data):
    '''Переводит данные в двоичный вид и отправляет главному серверу'''
    send_to_server_raw(make_data(*data))


def request_send(*data):
    global request_list, request_lock

    request_lock.acquire()
    request_list.append(data)
    request_lock.release()

def is_ready():
    '''Проверка на готовность к игре, true, если клиент знает свой ip'''
    global self_ip
    return self_ip != None


def request_player_list_clone():
    '''Запрашивает копию списка игроков'''
    global player_list, player_list_lock
    player_list_lock.acquire()
    clone = player_list.copy()
    player_list_lock.release()
    return clone

def remove_player(ip):
    '''Удаляет игрока из списка'''
    global player_list, player_list_lock

    player_list_lock.acquire()
    if ip in player_list:
        player_list.remove(ip)
    player_list_lock.release()

def death_checker(ip):
    global death_found
    '''Проверяет не умер ли игрок'''
    if death_found:
        death_found = False
        player_list_lock.acquire()
        if not ip in player_list:
            return True
        player_list_lock.release()

    return False


def kill_everything():
    '''Убивает все потоки'''
    global attacker, defender, main_loop
    if (attacker != None) and not attacker.stoped:
        attacker.stop();
    if (defender != None) and not defender.stoped:
        defender.stop();
    main_loop = False

def thread_inited():
    global attacker, defender
    return ((attacker != None) and not attacker.stoped) and ((defender != None) and not defender.stoped)

def init_threads():
    '''Создаёт атакующий и защищающийся поток, как объекты'''
    global attacker, defender
    main_log.write('Инициализация объектов-потоков')
    no_def = True
    no_atk = True

    if attacker != None:
        if not attacker.stoped:
            attacker.stop();
            attacker.join();
        else:
            no_atk = False

    if no_atk:
        attacker = AttackThread(
            log = output_log,
            timeout = ENEMY_INPUT_TIMEOUT,
            request_send=request_send,
            force_send=send_to_server,
            request_table=request_player_list_clone, 
            remove_player=remove_player
            )

    if defender != None:
        if not defender.stoped:
            defender.stop();
            defender.join();
        else:
            no_def = False
    if no_def:
        defender = DefendThread(
            log = input_log,
            timeout = ENEMY_INPUT_TIMEOUT,
            request_send=request_send,
            force_send=send_to_server,
            death_checker=death_checker,
            kill_everything=kill_everything
            )
    



#Запуск игры
import time
main_log.write('Запуск основного потока')
main_log.write('Запрос регистрации')

send_to_server_raw(REGISTER_REQUEST)

while main_loop:
    try:
        if game_started:
            #Обновления меток времени
            current_time = time.time()
            table_request_time += current_time - last_time
            #Если таблица игроков давно не обновлялась - обновляем
            if table_request_time > TABLE_UPDATE_DELAY:
                main_log.write('Переодический запрос таблицы игроков')
                send_to_server(ServerRequests.REQ_TABLE)
                table_request_time = 0

            last_time = current_time
        request_lock.acquire()
        if len(request_list) > 0:
            send_to_server(request_list)
        request_lock.release()
        #Ждём сообщения от сервера
        server_input, sender = udp_socket_receive.recvfrom(INPUT_BUFFER)
        main_log.write('Получена датаграмма:', server_input)
        
        if not main_loop:
            exit(0)
        #Помечаем, что мы получили данные от сервера
        if not data_received:
            data_received = True

        if check_request(server_input, ServerResponse.GAME_START):
            if is_ready():
                main_log.write('Игра началась')

                if not thread_inited():
                    main_log.write('Ошибка: потоки не созданы, обнаружен форсированный запуск')
                    init_threads()

                main_log.write('Запуск атакующего')
                attacker.start()
                main_log.write('Запрос таблицы участников')
                send_to_server(ServerRequests.REQ_TABLE)
                main_log.write('Запуск защитника')
                defender.start()
                game_started = True
            else:
                main_log.write('Ошибка: сервер не готов, невозможно присоединится');
        elif check_request(server_input, ServerResponse.DEATH):
            death_found = True
            death_ip    = make_ip(server_input[1], server_input[2], server_input[3], server_input[4])
            if death_ip == self_ip:
                main_log.write('КРИТИЧЕСКАЯ ОШИБКА: получено сообщение о собственной смерти')
                exit(-1)
            
            main_log.write('Получено уведомление о смерти:', death_ip)
            remove_player(death_ip)
            main_log.write('Запрос таблицы игроков')
            send_to_server(ServerRequests.REQ_TABLE)
        elif check_request(server_input, ServerResponse.TABLE):
            table_request_time = 0
            table_size = server_input[1] 

            player_list_lock.acquire()
            player_list.clear()
            for i in range(table_size):
                ip = make_ip(server_input[1 + i*4 + 1], server_input[1 + i*4 + 2], 
                             server_input[1 + i*4 + 3], server_input[1 + i*4 + 4])
                if ip != self_ip:
                    player_list.append(ip)
            player_list_lock.release()
            main_log.write('Таблица обновлена')
        elif check_request(server_input, ServerResponse.REGISTER):
            self_ip = make_ip(server_input[1], server_input[2], server_input[3], server_input[4])
            main_log.write('Регистрация подтверждена:', self_ip)

        elif check_request(server_input, ServerResponse.START_REQUEST):
            if is_ready():
                if not thread_inited():
                    init_threads();
                main_log.write('Сервер готов к игре, отправка подтверждения')
                send_to_server(ServerRequests.ACCEPT)
            else:
                main_log.write('Сервер НЕ готов к игре, неизвестен внешний ip')
                main_log.write('Запрос регистрации')
                send_to_server_raw(REGISTER_REQUEST)
        elif check_request(server_input, ServerResponse.GAME_ENDED):
            game_started = False;
            if attacker != None:
                attacker.stop()
            if defender != None:
                defender.stop()
        elif check_request(server_input, ServerResponse.DEATH_REQUEST):
            main_log.write('Подтверждение активности')
            send_to_server(ServerRequests.CANCEL_DEATH)
        else:
            main_log.write('Ошибка: запрос не был распознан, неизвестный код')
    except socket.timeout as tm:
        pass
    except socket.error as ex:
        pass

    if not data_received:
        main_log.write('Запрос регистрации')
        send_to_server_raw(REGISTER_REQUEST)
        main_log.write('Запрос внешнего адреса')
        send_to_server(ServerRequests.GET_NAME)


