# @filename gto_scaler.py
# Create : 2020-10-07 16:03:39 JST (ota)
# Last Modified : 2020-10-09 01:53:32 JST (ota)

import json
import signal
import time
import datetime
from sock_com import sock_com

class gto_scaler (sock_com) :
    def __init__(self) :
        super().__init__()
        self.port = 10001
        self.__GTO_SCR_SIZE = 24
        self.__com = {
            "version": b"!!@@",
            "data"   : b"!!R0",
            "init"   : b"!!0I",
            "clear"  : b"!!0C"
        }

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
        self.cache = retjson
        return retjson
            

if __name__ == "__main__":
    scr = gto_scaler()
    scr.address = "192.168.253.151"
#    scr.clear()
    print(scr.data())


