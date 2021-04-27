'''Данный файл используется, чтобы преобразовать любые данные в их двоичное представление.
Указанные здесь функции способны преобразовывать списки, числа, строки в единую последовательность, которую
можно отправить серверу.'''

import Protocol

class Number:
    '''Хранит число и сколько байт оно занимает.'''
    def __init__(self, data, size):
        self.data = data
        self.size = size;
    
  
def append_number(data: bytearray, number: int, size: int):
    '''Первым аргументом идёт bytearray. Вторым идёт число, которое должно быть добавлено, третьим
    размер добавляемого число. Процедура добавит это число в последовательность data'''
    for i in range(size):
        data.append(number & 255)
        number = number >> 8

def append_string(data, string):
    '''Первым аргументом идёт bytearray. Вторым идёт строка, добавляемая в последовательность. 
    Процедура добавит эту строку в последовательность data в стандартной кодировке'''
    for i in string:
        data.append(ord(i))

def append_data(data, *args):
    '''Первым аргументом идёт bytearray. Далее идёт произвольная последовательность аргументов, которая будет распознана и добавлена'''
    for arg in args: #Перебираем аргументы
        if type(arg) == str: #Если встретилась строка, добавляем соотвествующей процедурой
           append_string(data, arg)
        elif type(arg) == Number: #Специальный объект для чисел произвольного размера
            append_number(data, arg.data, arg.size)
        elif type(arg) == list: #Если встречается список используем оператор распаковки, т.е. append_data(data, [100, 20]) тоже самое, что append_data(data, 100, 20)
            append_data(data, *arg)
        elif type(arg) == tuple: #Если встречается кортеж используем оператор распаковки, т.е. append_data(data, [100, 20]) тоже самое, что append_data(data, 10
            append_data(data, *arg)
        else:   #Если не встретился указанный тип, считаем, что arg - число от 0 до 255 и записываем
            data.append(arg)

def make_data(*args):
    '''Сформировать bytearray из данных.
    Преобразует любую последовательность аргументов в bytearray'''
    data = bytearray()
    append_data(data, args)
    return data

def minimal_number_bytecount(number):
    '''Минимальное количество байт необходимое, чтобы записать число(минимальная степень двойки, большая чем число)'''
    count = 0
    while number > 0:
        number = number >> 8
        count += 1
    return count
   
'''Минимальное количество байт необходимое, чтобы записать ответ'''
BYTE_RANGE_SIZE = max(minimal_number_bytecount(Protocol.MIN_NUMBER), minimal_number_bytecount(Protocol.MAX_NUMBER))

#Для каждой команды, которая может прилететь от другого игрока находим то,
#как эта команда будет выглядеть в доичной виде

LESS_DATA       = make_data(Protocol.LESS)
GREATER_DATA    = make_data(Protocol.GREATER)
DEATH_DATA      = make_data(Protocol.DEATH)
NO_DATA         = make_data(Protocol.NO)


def check(input, check_data):
    '''Проверить что check_data содержится в начале input, т.е. check(make_data(10, 20), make_data(10)) = True'''
    if len(input) < len(check_data):
        return False
    for i in range(len(check_data)):
        if input[i] != check_data[i]:
            return False
    return True

def read_number(data, size):
    '''Прочитать число из двоичных данных. Операция обратная append_number'''
    number = 0;
    for i in range(size):
        number += data[i] << (8*i)
    return number;