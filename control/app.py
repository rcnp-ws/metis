import json
import responder
import mhv4
import threading
import signal
import time
from multiprocessing import Value
from json_dbstore import json_dbstore
import datetime

mod = mhv4.MHV4("/dev/ttyUSB0",0.5,0.5)
doMonitor = Value('i',1)
lock = threading.Lock()
lock_sql = threading.Lock()

def sigintHandler ():
   doMonitor.value = 0
   time.sleep(1)

def monitorWorker(mod,lock):
   while doMonitor.value == 1:
      lock.acquire()
      mod.RU(4)
      mod.RI(4)
      mod.RUP(4)
      lock.release()
      time.sleep(1.)

def insertWorker(mod) :
   db = json_dbstore()
   db.dbpath = "/home/daq/cyric2020a/%s_mhv4.db" % datetime.datetime.now().strftime('%Y%m%d%H%M%S')
   db.createTableIfNot()
   db.commit()
   while doMonitor.value == 1 :
      data = json.dumps(mod.getChache())
      type = "mhv4"
      lock_sql.acquire()
      db.insert(type,data)
      lock_sql.release()
      time.sleep(1)
   db.close()
      
api = responder.API()

@api.background.task
def rampWorker(mod,lock,ch0,ch1,ch2,ch3):
   lock.acquire();
   mod.RAMP({0: float(ch0), 1: float(ch1), 2: float(ch2), 3: float(ch3)});
   lock.release()
   

@api.route("/monitor/json")
def monitor (req, resp):
   resp.text = json.dumps(mod.getChache())
   resp.headers["Access-Control-Allow-Origin"] = "*"


@api.route("/setv/{ch0}:{ch1}:{ch2}:{ch3}")
def setv (req, resp, ch0, ch1, ch2, ch3):
   if mod.isRamping() :
      mod.stopRamping()
      time.sleep(1)
   
   rampWorker(mod,lock,ch0,ch1,ch2,ch3)
   resp.headers["Access-Control-Allow-Origin"] = "*"

   
@api.route("/stopRamping") 
def stopRamping (req, resp) :
   mod._stopRamping = True
   resp.headers["Access-Control-Allow-Origin"] = "*"

   
if __name__ == "__main__":
   signal.signal(signal.SIGINT,sigintHandler)
   t1 = threading.Thread(target=monitorWorker, args=(mod,lock))
   t1.start()

   t2 = threading.Thread(target=insertWorker, args=(mod,))
   t2.start()

   

   api.run(address="192.168.253.152")
   doMonitor.value = 0
#    from wsgiref import simple_server
#    httpd = simple_server.make_server("127.0.0.1", 8000, api)
#    print('starting')
#    httpd.serve_forever()
  
