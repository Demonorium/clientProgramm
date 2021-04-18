import RawData
import Protocol


class NumberGenerator:
    GREATER = 0
    LESS = 1
    NO = 3

    def __init__(self):
        self.L = Protocol.MIN_NUMBER
        self.R = Protocol.GET_NUMBER_COUNT()

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
        if data == NumberGenerator.GREATER:
            self.L = self.start_right
            self.current = (self.R + self.L) // 2
            self.start_left = self.current
            self.start_right = self.current
        elif data == NumberGenerator.LESS:
            self.R = self.start_left + 1
            self.current = (self.R + self.L) // 2
            self.start_left = self.current
            self.start_right = self.current
        else:
            if self.step and (self.start_right < self.R):
                self.start_right += 1
            else:
                self.start_left -= 1


