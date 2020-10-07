# @filename gto_scaler.py
# Create : 2020-10-07 16:03:39 JST (ota)
# Last Modified : 2020-10-07 21:02:13 JST (ota)

import json
import signal
import time
import datetime
import socket

class gto_scaler :
    def __init__(self) :
        self.__port = 10001
        self.__address = ""
        self.__s = None
        self.__GTO_SCR_SIZE = 24
        self.__cache = {}
        self.__com = {
            "version": b"!!@@",
            "data"   : b"!!R0",
            "init"   : b"!!0I",
            "clear"  : b"!!0C"
        }

    @property
    def address(self) :
        return self.__address
    @address.setter
    def address(self, address) :
        self.__address = address

    @property
    def cache(self) :
        return self.__cache
    @cache.setter
    def cache(self, cache) :
        self.__cache = cache

    def open(self) :
        self.__s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__s.connect((self.__address,self.__port))

        
    def close(self) :
        self.__s.close()
        time.sleep(0.001)
        
    def sendAndReceive(self,com) :
        self.open()
        self.__s.sendall(com)
        ret = self.__s.recv(16384)
        self.close()       
        return ret
    def send(self,com) :
        self.open()
        self.__s.sendall(com)
        self.close()       

    def init(self) :
        self.send(self.__com["init"])

    def clear(self) :
        self.send(self.__com["clear"])
        
    def version(self) :
        return self.sendAndReceive(self.__com["version"])
    def data(self) :
        result = self.sendAndReceive(self.__com["data"])
        values = []
        retjson = {}
        for i in range(self.__GTO_SCR_SIZE) :
            values.append(int.from_bytes(
                [result[4*i],
                 result[4*i+1],
                 result[4*i+2],
                 result[4*i+3]],
                byteorder='little',
                signed = False))
            
        retjson["gateena"] = 1 if (values[0] & 0x10000000) else 0
        retjson["softveto"] = 1 if (values[0] & 0x20000000) else 0
        retjson["gatenum"] = (values[0] & 0xfffffff)
        retjson["veto"] = 1 if (values[22] & 0x40000000) else 0
        retjson["level"] = 1 if (values[22] & 0x80000000) else 0
        retjson["gnt1k"] = (values[22] & 0x3fffffff)
        retjson["cnt1k"] = (values[23] & 0x3fffffff)
        retjson["scr"] = []
        for i in range(20) :
            retjson["scr"].append(values[i+1])
        self.__cache = retjson
        return retjson
            

if __name__ == "__main__":
    scr = gto_scaler()
    scr.address = "192.168.253.151"
    scr.clear()
    print(scr.data())


