# @file n14xx.py
# @brief data holder via usb connection
# Last Modified : 2020-11-20 06:52:21 JST (ota)
import time
import os
import re
from ttyusb import ttyusb
from typing import List, Dict
import numpy as np

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

class n14xx(ttyusb):
   def __init__(self,dev):
      self.__delim = "\r\n"
      super().__init__(dev,self.__delim)

      # read all the status
      for cmd in cmdMonCh:

      time.sleep(0.1)

   def monitorChannel(self,cmd,ch,cmd) : 
      
      
   def stopRamping (self) :
      self._stopRamping = True
      self._cache["isRamping"] = [False] * 4

   def isRamping (self) :
      return self._isRamping

   def write(self,com):
      os.write(self._fd,com)

   def read(self):
      return os.read(self._fd,1024)

   def setF(self,com,ch,val):
      self.write(b"%s %d %f\r" % (com, ch, val))

   def get(self,com,ch):
      self.write(b"%s %d\r" % (com, ch))
      return self.decode(self.read())

   def getChache(self):
      return self._cache;

   def RAMP(self, targets: Dict[int,float]):
      if self._isRamping == True :
         return 
      self._isRamping = True
      num = len(targets)
      if num == 0 :
         return
      doneRamp = [0] * num
      initVol = self.RU(4)
      for key in initVol:
         initVol[key] = abs(initVol[key])
         chs = list(targets.keys())
         vals = list(targets.values())
         # calculate ramp step
      next = time.perf_counter() + self._tstep
      while (0 in doneRamp) :
         if self._stopRamping :
            self._stopRamping = False
            break
         self.RU(4)
         self.RI(4)
         self.RUP(4)
         while time.perf_counter() < next :
            time.sleep(self._tstep * 0.1)
            next += self._tstep
         for i in range(num) :
            if doneRamp[i] == 1 :
               self._cache["isRamping"][i] = False
               continue
            ch = chs[i]
            target = vals[i]
            setval = initVol[ch] + np.sign(target-initVol[ch]) * self._vstep
            if abs(target - setval) < self._vstep * 0.9 :
               self.SU(ch,target)
               self.read();
               doneRamp[i] = 1
               continue
            self._cache["isRamping"][i] = True
            self.SU(ch,setval)
            self.read();
            initVol[ch] = setval
      self._isRamping = False
      self._cache["isRamping"] = [False] * 4


   def SU(self,ch,val):
      # values should be unit of 0.1 when set to MHV
      self.setF(b"SU",ch,val * 10)

   def SUL(self,ch,val):
      # values should be unit of 0.1 when set to MHV
      self.setF(b"SUL",ch,val * 10)

   def SIL(self,ch,val):
      # values should be unit of 0.1 when set to MHV
      self.setF(b"SIL",ch,val * 10)
        

    
   def RU(self,ch):
      self._cache['RU'] = self.get(b"RU",ch)
      return self._cache['RU']
   def RUP(self,ch):
      self._cache['RUP'] = self.get(b"RUP",ch)       
      return self._cache['RUP']
   def RUL(self,ch):
      return self.get(b"RUL",ch)
   def RI(self,ch):
      self._cache['RI'] = self.get(b"RI",ch)
      return self._cache['RI']
   def RIL(self,ch):
      return self.get(b"RIL",ch)


   def decode(self,lines):
      ret = {}
      for line in lines.splitlines():
         result = re.match(b".*?(\d): (\S+)",line)
         if result and len(result.groups()) != 0 :
            ret[int(result.group(1))] = float(result.group(2))
      return ret    
     
        
#    def setV(v):
        
