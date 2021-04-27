from datetime import datetime

class Log:
    '''Класс записывает в указанный при создании файл при вызове метода write.
    write ведёт себя точно также, как print, но имеет дополнительные опции'''
    def __init__(self, fname):
        self.fname = fname

    def write(self, *args, console = True, time = True, sep = ' ', end = '\n'):
        '''В целом поведение аналогично print, time определяет будет ли выведено время сообщения.
        console будет ли сообщение продублировано в консоль или отправленно только в файл.'''
        time_str = ''
        if time:
            time_str = '[' + str(datetime.now()) + ']\t'

        if console:
            print(time_str, *args, sep = sep, end = end)

        with open(self.fname, 'a', encoding="utf-8") as file:
            if time:
                file.write(time_str)

            for arg in args:
                file.write(str(arg))
                if (sep != None) and (sep != ''):
                    file.write(str(sep))
            if (end != None) and (end != ''):
                file.write(str(end))

