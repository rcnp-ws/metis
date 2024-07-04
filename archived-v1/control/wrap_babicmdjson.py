# @filename wrap_babicmdjson.py
# Create : 2020-10-07 15:44:32 JST (ota)
# Last Modified : 2020-10-25 13:40:11 JST (ota)

import json
import signal
import time
import datetime
import subprocess

babicmdjson = "/usr/babirl/babicon/babicmdjson"

class runinfo :
    def __init__(self,host) :
        if not host :
            raise RuntimeError("Host is not provided")
        self.__cache = {}
        self.__host = host
        self.__nullret = "{}"

    @property
    def cache(self) : 
        return self.__cache

    @cache.setter
    def cache(self,cache) :
        self.__cache = cache

    @property
    def host(self) :
        return self.__host
    @host.setter
    def host(self,host) :
        self.__host = host

    @property
    def nullret (self) :
        return self.__nullret
    @nullret.setter
    def nullret (self,nullret) :
        pass


    def getconfig(self, doUpdate = False) :
        return self.getinfo("getconfig","",doUpdate)

    def getevtnumber(self, doUpdate = False) :
        return self.getinfo("getevtnumber","",doUpdate)

    def getinfo(self,cmd,arg="",doUpdate = False) :
        self.execute(cmd,arg) if doUpdate else None
        return self.getCache(cmd)

    def getCache(self,cmd) : 
        return self.cache[cmd] if cmd in self.cache else self.nullret    


    def execute(self,cmd,arg="") :
 #       print(babicmdjson,self.host,cmd,arg)
        try :
            ret = subprocess.run([babicmdjson, self.host, cmd, arg],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout;
#            print(ret)
            ret = ret.decode()
            ret = ret.replace('\n','')
            if ret != "" : 
                self.cache[cmd] = json.loads(ret)
            time.sleep(0.1)
        except:
            print("Cannot read but just ignore ..")

