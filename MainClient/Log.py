from datetime import datetime

class Log:
    def __init__(self, fname):
        self.fname = fname

    def write(self, *args, console = True, time = True, sep = ' ', end = '\n'):
        if console:
            print(*args)

        with open(self.fname, 'a') as file:
            if time:
                file.write('[')
                file.write(str(datetime.now()))
                file.write(']\t')

            for arg in args:
                file.write(str(arg))
                if (sep != None) and (sep != ''):
                    file.write(str(sep))
            if (end != None) and (end != ''):
                file.write(str(end))

