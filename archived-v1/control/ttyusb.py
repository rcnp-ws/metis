import time
import os
import re

class ttyusb(object):
    def __init__(self,dev,delim):
        self._dev = dev
        self._fd = os.open(dev,os.O_RDWR)
        self._delim = delim

    def __del__(self):
        os.close(self._fd)
        
    def write(self, com):
        os.write(self._fd, com + delim)
    def read(self,len=1024):
        return os.read(self._fd,len)
