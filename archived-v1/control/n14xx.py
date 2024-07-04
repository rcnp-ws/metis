# @file n14xx.py
# @brief data holder via usb connection
# Last Modified : 2020-11-22 00:23:49 JST (ota)
import time
import os
import re
from ttyusb import ttyusb
from typing import List, Dict
import os

cmdMonCh = (
   'VSET', 'VMIN', 'VMAX', 'VDEC', 'VMON', 'ISET', 'IMIN', 'IMAX', 'ISDEC', 'IMON',
   'IRANGE', 'MAXV', 'MVMIN', 'MVMAX', 'MVDEC',
   'RUP', 'RUPMIN', 'RUPMAX', 'RUPDEC', 'RDW', 'RDWMIN', 'RDWMAX', 'RDWDEC',
   'TRIP', 'TRIPMIN', 'TRIPMAX', 'TRIPDEC', 'PDWN', 'POL', 'STAT'
)

statBit = (
   'ON', 'RUP', 'RDW', 'OVC', 'OVV', 'UNV', 'MAXV', 'TRIP',
   'OVP', 'OVT', 'DIS', 'KILL', 'ILK', 'NOCAL', 'N.C.', 'N.C.'
)

cmdMonMod = (
   'BDNAME', 'BDNCH', 'NDFREL', 'BDSNUM', 'BDILK', 'BDILKM', 'BDCTR', 'BDTERM', 'BDALARM'
)

alrmBit = ('CH0', 'CH1', 'CH2', 'CH3', 'PWFAIL', 'OVP', 'HVCKFAIL')

cmdSetCh = (
   'VSET', 'ISET', 'MAXV', 'RUP', 'RDW', 'TRIP', 'PDWN', 'IMRANGE', 'ON', 'OFF'
)

cmdSetMod = ('BDILKM', 'BDCLR')

class n14xx:
   def __init__(self,dev):
      self.__delim = "\r\n"
      self.__fmtMonCh = "$BD:{},CMD:MON,CH:{},PAR:{}"
      self.__fmtSetCh = "$BD:{},CMD:SET,CH:{},PAR:{},VAL:{}"
      self.__fmtOnCh = "$BD:{},CMD:SET,CH:{},PAR:ON"
      self.__fmtOffCh = "$BD:{},CMD:SET,CH:{},PAR:OFF"
      self.__regexpAllChOK = "#BD:{:02d},CMD:OK,VAL:([^;]+);([^;]+);([^;]+);([^;]+)"+self.__delim
      self.__fd = os.open(dev,os.O_RDWR)
      self.__cache = {}

   def __del__(self):
      os.close(self.__fd)
      
   def monch(self,bd,par):
      ch = 4 # always read all the channels
      cmd = self.__fmtMonCh.format(bd,ch,par) + self.__delim
      os.write(self.__fd, cmd.encode())
      ret = os.read(self.__fd, 1024).decode()
      regexp = self.__regexpAllChOK.format(bd)
      vals = re.match(regexp,ret)
      if par not in self.__cache.keys():
         self.__cache[par] = [0,0,0,0]
      if vals :
         for i in range(len(vals.groups())):
            self.__cache[par][i] = vals.group(i+1)

   def setch(self,bd,ch,par,val):
      cmd = self.__fmtSetCh.format(bd,ch,par,val) + self.__delim
      os.write(self.__fd, cmd.encode())
      ret = os.read(self.__fd, 1024).decode()
      print(ret)
   def onch(self,bd,ch):
      cmd = self.__fmtOnCh.format(bd,ch)+self.__delim
      os.write(self.__fd, cmd.encode())
      ret = os.read(self.__fd, 1024).decode()
      print(cmd,ret)
   def offch(self,bd,ch):
      cmd = self.__fmtOffCh.format(bd,ch)+self.__delim
      os.write(self.__fd, cmd.encode())
      ret = os.read(self.__fd, 1024).decode()
      print(cmd,ret)
      

   def get(self,par):
      return self.__cache[par]
            
   def getChache(self):
      return self.__cache
   
if __name__ == "__main__":
   mod = n14xx("/dev/ttyUSB0")
   mod.setch(0,0,"VSET",10)
   mod.monch(0,"VSET")
   print(mod.get("VSET"))
   mod.monch(0,"VMON")
   print(mod.get("VMON"))

