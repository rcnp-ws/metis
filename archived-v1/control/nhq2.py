# @file nhq.py
# @brief data holder via usb connection
# Last Modified : 2020-11-22 00:23:49 JST (ota)
import time
import datetime
import os
import re
import serial
from typing import List, Dict
import os

cmdMonCh = (
   'D1', # read set voltage A
   'D2', # read set voltage B
   'U1', # read measured voltage A
   'U2', # read measured voltage B
   'I1', # read measured current A
   'I2', # read measured current B
   'S1', # read status word A
   'S2', # read status word B
   'T1', # read module status A
   'T2', # read module status B
   'V1', # read ramp spped A
   'V2', # read ramp spped B
)

statBit = (
   'ON', 'RUP', 'RDW', 'OVC', 'OVV', 'UNV', 'MAXV', 'TRIP',
   'OVP', 'OVT', 'DIS', 'KILL', 'ILK', 'NOCAL', 'N.C.', 'N.C.'
)


cmdSetCh = (
   'D1', # write set vltage A
   'D2', # write set vltage B
   'L1', # write current trip A
   'L2', # write current trip B
)

cmdSetMod = ('BDILKM', 'BDCLR')

class nhq:
   def __init__(self,dev):
      self.__delim = b'\r\n'
      self.__fd = os.open(dev,os.O_RDWR)
      self.__cache = {}

      self.__tty = serial.Serial(dev,9600,timeout=1)
#      print(self.exec('#'))
#      print(self.exec('V1'))
#      print(self.exec('V2'))
#      self.getModuleIdentifier()
#      self.getStatus()
#      print(self.getCache())

   def exec(self,cmd) :
      for c in list(cmd) :
         self.__tty.write(c.encode())
         time.sleep(0.003)
      self.__tty.write(self.__delim)
      self.__tty.readline()
      line = self.__tty.readline()
      return line.decode().lstrip().rstrip()
   def getModuleIdentifier(self) :
      ret = self.exec('#')
      vals = re.match('([^;]+);([^;]+);([^;]+);([^;]+)',ret);
      if vals :
         self.__cache['id'] = vals.group(1)
         self.__cache['fw'] = vals.group(2)
         self.__cache['vomax'] = vals.group(3)
         self.__cache['iomax'] = vals.group(4)

   def getStatus(self) :
      for com in cmdMonCh : 
         self.__cache[com] = self.exec(com);

   def getCache(self) :
      return self.__cache

#   def monch(self,par):
#      cmd = par + self.__delim
#      os.write(self.__fd,1024,cmd.encode())
#      ret = os.read(self.__fd, 1024).decode()
#      regexp = self.__regexpAllChOK.format(bd)
#      vals = re.match(regexp,ret)
#      if par not in self.__cache.keys():
#         self.__cache[par] = [0,0]
#      if vals :
#         for i in range(len(vals.groups())):
#            self.__cache[par][i] = vals.group(i+1)
#
#   def setch(self,bd,ch,par,val):
#      cmd = self.__fmtSetCh.format(bd,ch,par,val) + self.__delim
#      os.write(self.__fd, cmd.encode())
#      ret = os.read(self.__fd, 1024).decode()
#      print(ret)
#   def onch(self,bd,ch):
#      cmd = self.__fmtOnCh.format(bd,ch)+self.__delim
#      os.write(self.__fd, cmd.encode())
#      ret = os.read(self.__fd, 1024).decode()
#      print(cmd,ret)
#   def offch(self,bd,ch):
#      cmd = self.__fmtOffCh.format(bd,ch)+self.__delim
#      os.write(self.__fd, cmd.encode())
#      ret = os.read(self.__fd, 1024).decode()
#      print(cmd,ret)
#      
#
#   def get(self,par):
#      return self.__cache[par]
#            
#   def getChache(self):
#      return self.__cache
   
if __name__ == "__main__":
#   mod = [nhq("/dev/ttyUSB0"), nhq("/dev/ttyUSB1"), nhq("/dev/ttyUSB2"), nhq("/dev/ttyUSB3")]
   mod = [nhq("/dev/ttyUSB0"), nhq("/dev/ttyUSB1"), nhq("/dev/ttyUSB2")]
   for i in range(len(mod)):
      print(mod[i].exec("#"))
      mod[i].exec("V1=50")
      mod[i].exec("V2=50")
      print(str(i) + " : Vramp1 = " + mod[i].exec("V1") + ", Vramp2 = " + mod[i].exec("V2") )
      


#   mod[0].exec("D1=550")
#   mod[0].exec("D2=36")
#   mod[1].exec("D1=25")
#
#   mod[1].exec("D2=620")
#   mod[2].exec("D1=40")
#   mod[2].exec("D2=28")

   mod[0].exec("D1=0")
   mod[0].exec("D2=0")
   mod[1].exec("D1=0")

   mod[1].exec("D2=0")
   mod[2].exec("D1=0")
   mod[2].exec("D2=0")

   
   mod[0].exec("G1")
   mod[0].exec("G2")
   mod[1].exec("G1")
   mod[1].exec("G2")
   mod[2].exec("G1")
   mod[2].exec("G2")

   print("\n")

   while True:
      print(datetime.datetime.now())
      print("XeL")
      print("  Main   : Voltage=" + mod[0].exec("U1") + " Currnet =" + mod[0].exec("I1"))
      print("Dynode11 : Voltage=" + mod[0].exec("U2") + " Currnet =" + mod[0].exec("I2"))
      print("Dynode12 : Voltage=" + mod[1].exec("U1") + " Currnet =" + mod[1].exec("I1"))
      print("")
      print("XeR")
      print("  Main   : Voltage=" + mod[1].exec("U2") + " Currnet =" + mod[1].exec("I2"))
      print("Dynode11 : Voltage=" + mod[2].exec("U1") + " Currnet =" + mod[2].exec("I1"))
      print("Dynode12 : Voltage=" + mod[2].exec("U2") + " Currnet =" + mod[2].exec("I2"))
      print("")

      time.sleep(5)
