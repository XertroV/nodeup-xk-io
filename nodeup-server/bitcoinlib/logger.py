import sys
import pprint


class Log(object):

    def __init__(self, filename=None):
        if filename is not None:
            self.fh = open(filename, 'a+')
        else:
            self.fh = sys.stdout

    def write(self, msg):
        line = "%s\n" % msg
        self.fh.write(line)


class PrettyLog():

    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        return pprint.pformat(self.obj) 
