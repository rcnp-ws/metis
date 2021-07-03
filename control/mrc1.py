# @file mrc1.py
# @brief module for mrc1
# Created       : 2021-01-19 16:22:21 JST (ota)
# Last Modified : 2021-01-20 00:27:44 JST (ota)


import serial
import time
import re
import threading
from collections import deque
from collections import defaultdict

execLock = threading.Lock()
lineLock = threading.Lock()

class MRC1 :
    def __init__ (self, ttydev) :
        self.__ttydev = ttydev
        self.__tty = serial.Serial(ttydev,9600,timeout=0.5)
        self.__modules = []
        self.__cache = defaultdict(lambda: defaultdict(lambda :defaultdict(dict)))
        self.__cmds = ""
        self.__lines = deque()
        self.__types = { 17 : mhv4, 27 : mhv4}
        self.__doPolling = True

        self.push("X0")
        self.push("P0")
        self.execute()
        self.resetLines()

        self.initModules(0)
        self.initModules(1)

        t = threading.Thread(target=self.pollingWorker)
        t.start()

    def __del__ (self) :
        self.__doPolling = False
        self.__tty.close()

    @property
    def lines (self) :
        return self.__lines

    @property
    def cache (self) :
        return self.__cache

    def resetLines(self) :
        self.__lines.clear()

    def resetCommads(self) :
        self.__cmds = ""

    def updateCache(self,bus,dev,addr,val) :
        self.__cache[bus][dev][addr] = val
        
    def push (self, cmds) :
        execLock.acquire()
        for cmd in cmds : 
            self.__cmds += cmd + "\r"
        execLock.release()

    def stopPolling() :
        self.__doPolling = False

    def execute (self) :
        execLock.acquire()
        self.__tty.write(self.__cmds.encode())
        self.__cmds = ""
        time.sleep(0.2)
        lines = self.__tty.readlines()
        for line in lines :
            line = line.decode().lstrip().rstrip()
            if line == "" :
                continue
            self.__lines.append(line)
        execLock.release()
        
    def initModules (self,bus) :
        self.push(["SC {}".format(bus)])
        self.execute()
        print(self.lines)
        while len(self.lines) != 0 :
            line = self.lines.popleft()
            result = re.match("(\d+): (\d+),.*",line)
            if (result and len(result.groups()) != 0):
                dev = int(result.group(1))
                idc = int(result.group(2))
                if idc in self.__types and callable(self.__types[idc]) :
                    self.__modules.append(self.__types[idc](bus,dev,idc,self))

    def ramp (self, configs) :
        for module in self.__modules :
            if hasattr(module,'ramp') and callable(getattr(module,'ramp')) :
                module.ramp(configs)
            
        
    def pollingWorker (self) :
        while self.__doPolling :
            print("monitoring and executing")
            for module in self.__modules :
                module.monitor()
            self.execute()
            for module in self.__modules :
                module.parse(self.lines,lineLock)
            

class mhv4 :
    def __init__ (self, bus, dev, idc, mrc1) :
        self.__bus = bus
        self.__dev = dev
        self.__idc = idc
        self.__mrc1 = mrc1
        self.__isRamping = [False] * 4
        self.__rampTarget = [0] *4
        self.__tstep = 1
        self.__vstep = 1

        self.monitor()
        mrc1.execute()
        self.parse(mrc1.lines,lineLock)


    def ramp (self, configs) :
        for config in configs.copy() :
            if config['bus'] == self.__bus and config['dev'] == self.__dev :
                if addr > 3 :
                    configs.remote(config)
                    continue
                if self.__isRamping[addr] :
                    self.__rampTarget[addr] = config['val']
                    configs.remote(config)
                    continue
                # start working and remove configuration
                t = threading.Thread(target=self.rampWorker, args=(config))
                t.start()
                configs.remove(config)
        
    def rampWorker (self, aConfig) :
        bus  = aConfig['bus']
        dev  = aConfig['dev']
        addr = aConfig['addr']
        self.__rampTarget[addr]  = aConfig['val']
        doneRamp = False
        next = time.perf_counter()
        self.__mrc1.updateCache(bus,dev,1000 + addr, True)
        while not doneRamp :
            while time.pref_counter() < next :
                time.sleep(self.__step * 0.1)
            next += self.__tstep
            volTgt = abs(self.__rampTarget[addr])
            volMon = abs(self.__mrc1.cache[bus][dev][addr+32])
            volSet = volMon
            diff = volTgt - volMon
            if abs(diff) < self.__vstep * 0.9 :
                volSet = volTgt
                doneRamp = True
            else : 
                volSet += diff / abs(diff) * self.__vstep
            self.__mrc1.push("SE {} {} {} {}".format(bus,dev,addr,volSet))
        self.__isRamping[addr] = False
        self.__mrc1.updateCache(bus,dev,1000+addr,False)
            

    def monitor (self) :
        addrs = [0, 1, 2, 3, 32, 33, 34, 35, 36, 37, 38, 39, 50, 51, 52, 53]
        cmds = []
        for addr in addrs :
            cmds.append("RE {} {} {}".format(self.__bus,self.__dev,addr))
        self.__mrc1.push(cmds)

    def parse (self, lines, lock) :
        lock.acquire()
        for line in lines.copy() :
            result = re.match("(\w+) (\d+) (\d+) (\d+) (\S+)",line)
            if not result or len(result.groups()) == 0:
                continue
            cmd = result.group(1)
            bus = int(result.group(2))
            dev = int(result.group(3))
            addr = int(result.group(4))
            val = int(result.group(5))
            if bus != self.__bus or dev != self.__dev :
                # doesn't care of different module
                continue
            self.__mrc1.updateCache(bus,dev,addr,val)
            lines.remove(line)
        lock.release()


import json        
if __name__ == '__main__' :
    mrc1 = MRC1("/dev/ttyUSB0")
    for i in range(5) :
        time.sleep(1)
        print(json.dumps(mrc1.cache))
    end = time.perf_counter()

