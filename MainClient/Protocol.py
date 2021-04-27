'''
Описание констант.
Описывает все константы связанные с игрой.
'''

LESS    = 'L' #Отправляется, когда число меньше присланого
GREATER = 'R' #Когда число больше присланого
DEATH   = 'D' #Я умер!
NO = 'N'      #Отправляется, если сервер не хочет отвечать на число L или R

NO_CHANCE = 0.8 #Шанс отправить NO

'''Задержка перед отправкой'''
SEND_DELAY = 0.2

MIN_NUMBER = 0          #Минимальное число
MAX_NUMBER = 2147483648 #Максимальное число
INCLUDE_LIMIT = True    #Включая максимальное число

INPUT_PORT = 2222


class ServerRequests:
    REGISTER     = 0
    REMOVE       = 1
    ACCEPT       = 2
    DEATH        = 3
    REQ_TABLE    = 4
    CANCEL_DEATH = 5
    GET_NAME     = 6
    KILL         = 7

class ServerResponse:
    START_REQUEST   = 0
    GAME_START      = 1
    TABLE           = 2
    DEATH           = 3
    REGISTER        = 4
    DEATH_REQUEST   = 5
    GAME_ENDED      = 6


def GET_NUMBER_COUNT():
    if INCLUDE_LIMIT:
        return MAX_NUMBER + 1
    else:
        return MAX_NUMBER