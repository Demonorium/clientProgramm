import Protocol

class Number:
    '''Число и сколько байт оно занимает'''
    def __init__(self, data, size):
        self.data = data
        self.size = size;
    
  
def append_number(data, number, size):
    for i in range(size):
        data.append(number & 255)
        number = number >> 8

def append_string(data, string):
    for i in string:
        data.append(ord(i))

def append_data(data, *args):
    for arg in args:
        if type(arg) == str:
           append_string(data, arg)
        elif type(arg) == Number:
            append_number(data, arg.data, arg.size)
        elif type(arg) == list:
            append_data(data, *arg)
        elif type(arg) == tuple:
            append_data(data, *arg)
        else:
            data.append(arg)


def make_data(*args):
    '''Сформировать bytearray из данных'''
    data = bytearray()
    append_data(data, args)
    return data



def minimal_number_bytecount(number):
    '''Минимальное количество байт необходимое, чтобы записать число'''
    count = 0
    while number > 0:
        number = number >> 8
        count += 1
    return count
   
'''Минимальное количество байт необходимое, чтобы записать ответ'''
BYTE_RANGE_SIZE = max(minimal_number_bytecount(Protocol.MIN_NUMBER), minimal_number_bytecount(Protocol.MAX_NUMBER))

LESS_DATA       = make_data(Protocol.LESS)
GREATER_DATA    = make_data(Protocol.GREATER)
DEATH_DATA      = make_data(Protocol.DEATH)
NO_DATA         = make_data(Protocol.NO)


def check(input, check_data):
    '''Проверить что check_data содержится в начале input'''
    if len(input) < len(check_data):
        return False
    for i in range(len(check_data)):
        if input[i] != check_data[i]:
            return False
    return True

def read_number(data, size):
    '''Прочитать число из двоичных данных'''
    number = 0;
    for i in range(size):
        number += data[i] << (8*i)
    return number;