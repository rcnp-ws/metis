# @filename gto_scaler.py
# Create : 2020-10-07 16:03:39 JST (ota)
# Last Modified : 2020-10-08 01:57:48 JST (ota)

import socket
import time

class sock_com :
    def __init__(self) :
        self.__socket = None
        self.__port = 0
        self.__address = ""
        self.__bufsize = 16384
        self.__cache =  None

    @property
    def socket(self) :
        return self.__socket
    @socket.setter
    def socket(self, socket) :
        self.__socket = socket
    
    @property
    def address(self) :
        return self.__address
    @address.setter
    def address(self, address) :
        self.__address = address

    @property
    def port(self) :
        return self.__port
    @port.setter
    def port(self, port) :
        self.__port = port

    @property
    def bufsize(self) :
        return self.__bufsize

    @bufsize.setter
    def bufsize(self, bufsize) :
        self.__bufsize = bufsize
    
    @property
    def cache(self) :
        return self.__cache
    @cache.setter
    def cache(self, cache) :
        self.__cache = cache

    def open(self) :
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1);
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try :
            self.socket.connect((self.address,self.port))
        except:
            print("Cannot connect")
            self.socket = None
        time.sleep(0.001)

        
    def close(self) :
        if self.socket is None :
            return
        self.socket.close()
        time.sleep(0.001)
        
    def sendAndReceive(self,com) :
        self.open()
        if self.socket is None :
            return None
        self.socket.sendall(com)
        ret = self.socket.recv(self.bufsize)
        time.sleep(0.001)
        self.close()       
        return ret
    def send(self,com) :
        self.open()
        self.socket.sendall(com)
        self.close()       
        
