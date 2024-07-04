# @filename storeDAta.py
# Create : 2020-10-07 15:44:32 JST (ota)
# Last Modified : 2020-10-25 09:45:56 JST (ota)

import json
import signal
import time
import datetime
import subprocess

class runinfo :
    def __init__(self) :
        self.__cache = {}
        self.__host = ""

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

    def execute(self,cmd,arg="") :
        babicmdjson = "/usr/babirl/babicon/babicmdjson"
        host    = self.host
        if not host :
            return

        try: 
            ret = subprocess.run([babicmdjson, host, cmd, arg], stdout=subprocess.PIPE).stdout.decode();
            self.cache[cmd] = json.loads(ret)
            time.sleep(0.005)
        except:
            print("Cannot read but just ignore ..")
