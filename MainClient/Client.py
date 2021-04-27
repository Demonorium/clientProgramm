from threading import *
import socket
import sys


from Log import Log
import Protocol
from Protocol import ServerRequests
from Protocol import ServerResponse


#Объявление констант
SERVER_IP = '127.0.0.1'  #IP сервера
SERVER_PORT = 3333       #Порт сервера
SERVER_ADDRESS = (SERVER_IP, SERVER_PORT)

SERVER_PASSWORD = 'valid cd'    #Пароль от сервера. Не менять!
USERNAME = 'Kruglov Igor'       #Имя пользователя

INPUT_PORT = 4444       #Порт для приёма сообщений от сервера
INPUT_BUFFER = 255      #Максимальный размер пакета, который может прилететь от сервера
INPUT_TIMEOUT = 0.25    #Таймаут для сообщений от сервера

#Название файлов для лога
MAIN_SERVER_LOG_FILE = "m-server.log"   
INPUT_LOG            = "input.log"
OUTPUT_LOG           = "output.log"

#Таймаут для сокетов приёма и отправки игроку
PLAYER_INPUT_TIMEOUT  = Protocol.SEND_DELAY*2 + 1.25

TABLE_UPDATE_DELAY = 8.0


#Создание сокетов для работы с главным сервером
udp_socket_send     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Сокет для отрпавки серверу
udp_socket_receive  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Сокет для приёма сообщений от сервера
udp_socket_receive.bind(('', INPUT_PORT))   #Указываем, что слушаем порт INPUT_PORT
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
request_list = []       #Список запросов
request_lock = Lock()   #Мьютек запросов


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
    '''Запрашиваем отправку на главный сервер'''
    global request_list, request_lock

    request_lock.acquire()      #Говорим, что мы редактируем список
    request_list.append(data)   #Добавляем наш запрос в список
    request_lock.release()      #Заканчиваем редактирование

def is_ready():
    '''Проверка на готовность к игре, true, если клиент знает свой ip'''
    global self_ip
    return self_ip != None


def request_player_list_clone():
    '''Запрашивает копию списка игроков'''
    global player_list, player_list_lock
    player_list_lock.acquire() #Говорим, что работать со списком можно только нам
    clone = player_list.copy() #Копируем список
    player_list_lock.release() #Возвращаем список всем
    return clone   #Возвращаем клон

def remove_player(ip):
    '''Удаляет игрока из списка'''
    global player_list, player_list_lock

    player_list_lock.acquire() #Говорим, что работать со списком можно только нам
    if ip in player_list:
        player_list.remove(ip) #Если игрок всё ещё в списке - удаляем
    player_list_lock.release() #Возвращаем список всем

def death_checker(ip):
    '''Проверяет не умер ли игрок'''
    global death_found
    
    if death_found: #Если была смерть
        death_found = False #Говорим, что мы уже посмотрели
        #Проверяем, что указанного ip нет в списке (значит умер плак-плак)
        player_list_lock.acquire()
        result = not ip in player_list
        player_list_lock.release()
        #Возвращаем результат проверки
        return result

    return False


def kill_everything():
    '''Убивает все потоки'''
    global attacker, defender, main_loop, main_log, request_lock
    #Останавливаем главный цикл
    main_loop = False

    #Если поток attacker сейчас работает - останавливем
    if (attacker != None) and not attacker.stoped:
        attacker.stop();
    #Если поток defender сейчас работает - останавливем
    if (defender != None) and not defender.stoped:
        defender.stop();

def thread_inited():
    '''Проверяем, что у нас есть полностью работающие потоки.'''
    global attacker, defender
    return ((attacker != None) and attacker.stoped) and ((defender != None) and defender.stoped)

def init_threads():
    '''Создаёт атакующий и защищающийся поток, как объекты'''
    global attacker, defender
    main_log.write('Инициализация объектов-потоков')


    #Если поток attacker сейчас работает - останавливем
    if ((attacker != None) and not attacker.stoped):
            attacker.stop();
            attacker.join();

    #Создаём новый поток, но не запускаем
    attacker = AttackThread(
        log = output_log,
        timeout = PLAYER_INPUT_TIMEOUT,
        request_send=request_send,
        force_send=send_to_server,
        request_table=request_player_list_clone, 
        remove_player=remove_player
        )

    #Если поток defender сейчас работает - останавливем
    if ((defender != None) and not defender.stoped):
        defender.stop();
        defender.join();

    #Создаём новый поток, но не запускаем
    defender = DefendThread(
        log = input_log,
        timeout = PLAYER_INPUT_TIMEOUT,
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


while main_loop: #Бесконечный цикл
    try:
        if game_started:
            #Обновления меток времени
            current_time = time.time()
            table_request_time += current_time - last_time
            #Если таблица игроков давно не обновлялась - обновляем
            if table_request_time > TABLE_UPDATE_DELAY:
                main_log.write('Периодический запрос таблицы игроков')
                send_to_server(ServerRequests.REQ_TABLE)
                table_request_time = 0  

            last_time = current_time

        #Если какой-то поток просил нас сообщить что-то серверу - сообщаем
        request_lock.acquire() #Говорим, что мы сейчас работаем с request_list
        if len(request_list) > 0:
            for request in request_list:
                send_to_server(request)
            request_list.clear()
        request_lock.release() #Возвращаем request_list людям
        #Ждём сообщения от сервера
        server_input, sender = udp_socket_receive.recvfrom(INPUT_BUFFER)
        main_log.write('Получена датаграмма:', server_input)
        
        if not main_loop: #Если цикл пора заканчивать
            break

        #Помечаем, что мы получили какие-то данные от сервера
        if not data_received:
            data_received = True

        if check_request(server_input, ServerResponse.GAME_START): #Сервер сказал, что игра началась
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
            else: #Сервер не готов к игре
                main_log.write('Ошибка: сервер не готов, невозможно присоединится');

        elif check_request(server_input, ServerResponse.DEATH): #Получено сообщение о смерти
            death_found = True #Говорим, что чел реально умер
            death_ip    = make_ip(server_input[1], server_input[2], server_input[3], server_input[4])
            if death_ip == self_ip:
                main_log.write('КРИТИЧЕСКАЯ ОШИБКА: получено сообщение о собственной смерти')
                exit(-1)
            
            main_log.write('Получено уведомление о смерти:', death_ip)
            remove_player(death_ip)
            main_log.write('Запрос таблицы игроков')
            send_to_server(ServerRequests.REQ_TABLE)

        elif check_request(server_input, ServerResponse.TABLE): #Если пришла таблица
            table_request_time = 0      #Говорим, что таблица пришла, не надо запрашивать больше пока
            table_size = server_input[1] #Размер таблицы

            player_list_lock.acquire()  #Забираем себе список игроков
            player_list.clear()         #Очищаем
            for i in range(table_size): #Заполняем его с помощью ip из таблицы
                ip = make_ip(server_input[1 + i*4 + 1], server_input[1 + i*4 + 2], 
                             server_input[1 + i*4 + 3], server_input[1 + i*4 + 4])
                if ip != self_ip: #Не включаем себя в таблицу
                    player_list.append(ip)
            player_list_lock.release()
            main_log.write('Таблица обновлена')

        elif check_request(server_input, ServerResponse.REGISTER): #Подтверждение регистрации
            self_ip = make_ip(server_input[1], server_input[2], server_input[3], server_input[4])
            main_log.write('Регистрация подтверждена:', self_ip) 

        elif check_request(server_input, ServerResponse.START_REQUEST): #Запрос начала игры
            if is_ready():
                if not thread_inited(): #Если нет потоков, готовых к игре, создаём их
                    init_threads();
                main_log.write('Сервер готов к игре, отправка подтверждения')
                send_to_server(ServerRequests.ACCEPT)
            else:
                main_log.write('Сервер НЕ готов к игре, неизвестен внешний ip')
                main_log.write('Запрос внешнего адреса')
                send_to_server(ServerRequests.GET_NAME)

        elif check_request(server_input, ServerResponse.GAME_ENDED): #Игра закончена
            game_started = False;
            init_threads(); #Останавливаем и пересоздаём все потоки

        elif check_request(server_input, ServerResponse.DEATH_REQUEST):  #Сервер хочет узнать живы ли мы
            main_log.write('Подтверждение активности')
            send_to_server(ServerRequests.CANCEL_DEATH) #Говорим, что живы

        else:
            main_log.write('Ошибка: запрос не был распознан, неизвестный код')
    except socket.timeout as tm: #Игоририруем ошибки сокета
        pass
    except socket.error as ex:
        pass
    except BaseException as ex: #Выводим в лог сообщения об остальном
        main_log.write(ex)

    if not data_received: #Если ни разу не прилетел ответ от сервера
        main_log.write('Запрос регистрации')
        send_to_server_raw(REGISTER_REQUEST)
        main_log.write('Запрос внешнего адреса')
        send_to_server(ServerRequests.GET_NAME)


main_log.write('Остановка игры')