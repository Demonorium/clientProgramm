import RawData
import Protocol


class NumberGenerator:
    '''Генератор чисел, этот класс используется, чтобы подбирать число, которое будет
    отправлено другому игроку.'''

    GREATER = 0 #Настоящее число было больше, чем отправленное
    LESS    = 1 #Настоящее число было меньше, чем отправленное
    NO      = 3 #Сервер игрока послал нас

    def __init__(self):
        self.L = Protocol.MIN_NUMBER            #Левая граница двоичного поиска
        self.R = Protocol.GET_NUMBER_COUNT()    #Правая граница двоичного поиска

        self.current = (self.R + self.L) // 2   #Центр для двоичного поиска
        self.step = True                        #Направление движения поиска
        
        self.start_right = self.current         #Левая граница расмотренного промежутка
        self.start_left = self.current          #Правая граница расмотренного промежутка

    def get_number(self):
        '''Выбрать следующее число для проверки.'''
        self.step = not self.step
        if self.step and (self.start_right < self.R):
            temp = self.start_right
            self.start_right += 1
            return temp
        else:
            self.start_left -= 1
            return self.start_left

    def tip(self, data):
        '''Выбрать следующее число с учётом ответа от сервера.'''
        if data == NumberGenerator.GREATER:
            self.L = self.start_right
            self.current = (self.R + self.L) // 2
            self.start_right = self.current
            self.start_left = self.current
            self.step = True
        elif data == NumberGenerator.LESS:
            self.R = self.start_left + 1
            self.current = (self.R + self.L) // 2
            self.start_right = self.current
            self.start_left = self.current
            self.step = True


