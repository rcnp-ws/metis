# @filename multimeter.py
# Create : 
# Last Modified : 

import json
import signal
import time
import datetime
from sock_com import sock_com

class multimeter (sock_com) :
    def __init__(self) :
        super().__init__()
        self.port = 1394
        self.__com = {
            "reset"    : b"*RST\r\n",
            "abort"    : b"ABOR\r\n",
            "rcl"      : b"*RCL 0\r\n",
            "sys_preset"    : b"SYST:PRES\r\n",
            "read"          : b"READ?\r\n",
            "data"          : b"DATA?\r\n",
            "cont_off"      : b"INIT:CONT OFF\r\n",
            "buff_clear"     : b"TRAC:CLE\r\n",
            "buff_auto_off" : b"TRAC:CLE:AUTO OFF\r\n",
            "ini_trig"      : b"TRIG:COUN 1\r\n",
            "trig_imm"      : b"TRIG:SOUR IMM\r\n",
            "trig_standby"  : b"ROUT:SCAN:TSO IMM\r\n",
            "DC_vol"        : b"FUNC 'VOLT:DC'\r\n",
            "DC_vol_ch2"    : b"FUNC 'VOLT:DC',(@102) \r\n",
            "DC_vol_ch3"    : b"FUNC 'VOLT:DC',(@103) \r\n",
            "DC_vol_ch4"    : b"FUNC 'VOLT:DC',(@104) \r\n",
            "DCV_rauto_off" : b"SENS:VOLT:DC:RANG:AUTO OFF\r\n",
            "DCV_rauto_on"  : b"SENS:VOLT:DC:RANG:AUTO ON\r\n",
            "DC_curr"       : b"SENS:FUNC 'CURR:DC' \r\n",
            "DCC_rauto_off" : b"SENS:CURR:DC:RANG:AUTO OFF\r\n",
            "DCC_rauto_on"  : b"SENS:CURR:DC:RANG:AUTO ON\r\n",
            "RES"           : b"FUNC 'RES'\r\n",            
            "RES_rauto_off" : b"SENS:RES:RANG:AUTO OFF\r\n",
            "RES_rauto_on"  : b"SENS:RES:RANG:AUTO ON\r\n",
            "FRES"          : b"SENS:FUNC 'FRES'\r\n",            
            "FRES_ch1"      : b"SENS:FUNC 'FRES', (@101)\r\n",
            "FRES_rauto_off": b"SENS:FRES:RANG:AUTO OFF\r\n",
            "FRES_rauto_on" : b"SENS:FRES:RANG:AUTO ON\r\n",
            "FRES_ocom_off" : b"SENS:FRES:OCOM OFF\r\n",
            "FRES_ocom_on"  : b"SENS:FRES:OCOM ON\r\n",
            "chan_all_open" : b"ROUT:OPEN:ALL\r\n",
            "ask_close"     : b"ROUT:CLOS?\r\n",
            "scan_number"   : b"SAMP:COUN 3\r\n",
            "chan1_close"   : b"ROUT:CLOS (@101)\r\n",
            "chan2_close"   : b"ROUT:CLOS (@102)\r\n",
            "chan3_close"   : b"ROUT:CLOS (@103)\r\n",
            "chan4_close"   : b"ROUT:CLOS (@104)\r\n",
            "chan_all_close": b"ROUT:CLOS (@102:104)\r\n",            
            "scan_all"      : b"ROUT:SCAN (@101, 102, 103, 104)\r\n",
            "scan_start"    : b"ROUT:SCAN:LSEL INT\r\n",
            "scan_stop"     : b"ROUT:SCAN:LSEL NONE\r\n"            
        }

    def reset(self) :
        self.send(self.__com["reset"])

    def buff_clear(self) :
        self.send(self.__com["buff_clear"])
        
    def read_ch1(self) :
        self.send(self.__com["cont_off"])
        time.sleep(0.5)        
        self.send(self.__com["ini_trig"])
        time.sleep(0.5)
        self.send(self.__com["chan_all_open"])        
        time.sleep(0.5)        
        self.send(self.__com["FRES"])
        time.sleep(0.5)               
        self.send(self.__com["chan1_close"])        
        time.sleep(0.5)
        result = []
        result.append(datetime.datetime.now().timestamp())
        temp = self.sendAndReceive(self.__com["read"])
        if temp is None :
            return None
        result.append(float(temp.decode()[0:15]))
        time.sleep(0.5)                                                
        return result

        
    def read_ch2(self) :
        self.send(self.__com["cont_off"])
        time.sleep(0.5)        
        self.send(self.__com["ini_trig"])
        time.sleep(0.5)
        self.send(self.__com["chan_all_open"])        
        time.sleep(0.5)                
        self.send(self.__com["DC_vol"])
        time.sleep(0.5)                
        self.send(self.__com["chan2_close"])
        time.sleep(0.5)                        
        result = []
        result.append(datetime.datetime.now().timestamp())
        temp = self.sendAndReceive(self.__com["read"])
        if temp is None :
            return None
        result.append(float(temp.decode()[0:15]))
        time.sleep(0.5)                                                
        return result

    def read_ch3(self) :
        self.send(self.__com["cont_off"])
        time.sleep(0.5)        
        self.send(self.__com["ini_trig"])
        time.sleep(0.5)
        self.send(self.__com["chan_all_open"])        
        time.sleep(0.5)                
        self.send(self.__com["DC_vol"])
        time.sleep(0.5)                
        self.send(self.__com["chan3_close"])
        time.sleep(0.5)                        
        result = []
        result.append(datetime.datetime.now().timestamp())
        temp = self.sendAndReceive(self.__com["read"])
        if temp is None :
            return None
        result.append(float(temp.decode()[0:15]))
        time.sleep(0.5)                                                
        return result

    def read_ch4(self) :
        self.send(self.__com["cont_off"])
        time.sleep(0.5)        
        self.send(self.__com["ini_trig"])
        time.sleep(0.5)
        self.send(self.__com["chan_all_open"])        
        time.sleep(0.5)                
        self.send(self.__com["DC_vol"])
        time.sleep(0.5)                
        self.send(self.__com["chan4_close"])
        time.sleep(0.5)                        
        result = []
        result.append(datetime.datetime.now().timestamp())
        temp = self.sendAndReceive(self.__com["read"])
        if temp is None :
            return None
        result.append(float(temp.decode()[0:15]))
        time.sleep(0.5)                                                
        return result

    def data(self) :

        data_ch1 = self.read_ch1()
        data_ch2 = self.read_ch2()
        data_ch3 = self.read_ch3()
        data_ch4 = self.read_ch4()        

        datetimes = [data_ch1[0], data_ch2[0], data_ch3[0], data_ch4[0]]        
        values = []
        values.append(data_ch1[1])
        values.append(data_ch2[1])
        values.append(data_ch3[1])
        values.append(data_ch4[1])        

        calcs = []        
        calcs.append(-245.88 + 2.35979 * values[0] + 0.000990554 * values[0]*values[0])
        calcs.append(50.0 * (values[1]-3.0))
        calcs.append(50.0 * (values[2]-3.0))
        calcs.append(20.0 * values[3])

        types = ["pt100_cat", "gauge_catout", "gauge_catin", "gauge_srppac"]
        units = ["Ohm","V","V","V"]
        calcunits = ["C","kPa","kPa","torr"]
        
        retjson = {}
        retjson["log"] = []
        for i in range(4):
            retjson["log"].append({"datetime" : datetimes[i], "type" : types[i], "value" : values[i], "unit" : units[i], "calc" : calcs[i], "calcunit" : calcunits[i]})

        self.cache = retjson
        return retjson

        
if __name__ == "__main__":

    dev = multimeter()    
    dev.address = "10.32.8.152"    

    while True:
        print(dev.data())
        time.sleep(10)
        
