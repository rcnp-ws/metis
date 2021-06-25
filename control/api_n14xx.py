import json
import responder
from n14xx import n14xx
import threading
import signal
import time
from multiprocessing import Value
#from json_dbstore import json_dbstore
import datetime
import socket

mod = n14xx("/dev/ttyUSB0")
doMonitor = Value('i',1)
lock = threading.Lock()
lock_sql = threading.Lock()

def sigintHandler ():
   doMonitor.value = 0
   time.sleep(1)

def monitorWorker(mod,lock):
   while doMonitor.value == 1:
      lock.acquire()
      mod.monch(0,"VMON")
      mod.monch(0,"IMON")
      mod.monch(0,"VSET")
      mod.monch(0,"ISET")
      mod.monch(0,"STAT")
      lock.release()
      time.sleep(1.)
#def insertWorker(mod) :
#   db = json_dbstore()
#   db.dbpath = "/home/daq/cyric2020a/%s_mhv4.db" % datetime.datetime.now().strftime('%Y%m%d%H%M%S')
#   db.createTableIfNot()
#   db.commit()
#   while doMonitor.value == 1 :
#      data = json.dumps(mod.getChache())
#      type = "n14xx"
#      lock_sql.acquire()
#      db.insert(type,data)
#      lock_sql.release()
#      time.sleep(1)
#   db.close()
#      
api = responder.API()
#
@api.route("/monitor/json")
def monitor (req, resp):
   resp.text = json.dumps(mod.getChache())
   resp.headers["Access-Control-Allow-Origin"] = "*"
#
@api.route("/set/{bd}/{ch}/{par}/{val}")
def set (req, resp, bd, ch, par, val):
   lock.acquire()
   mod.setch(bd,ch,par,val)
   lock.release()
   resp.headers["Access-Control-Allow-Origin"] = "*"
@api.route("/on/{bd}/{ch}")
def on (req, resp, bd, ch):
   lock.acquire()
   mod.onch(bd,ch)
   lock.release()
   resp.headers["Access-Control-Allow-Origin"] = "*"
@api.route("/off/{bd}/{ch}")
def off (req, resp, bd, ch):
   lock.acquire()
   mod.offch(bd,ch)
   lock.release()
   resp.headers["Access-Control-Allow-Origin"] = "*"

   #
#@api.route("/setv/{ch0}:{ch1}:{ch2}:{ch3}")
#def setv (req, resp, ch0, ch1, ch2, ch3):
#   if mod.isRamping() :
#      mod.stopRamping()
#      time.sleep(1)
#      lock.acquire()
#      mod.setch(0,0,"SETV",ch0)
#      mod.setch(0,0,"SETV",ch1)
#      mod.setch(0,0,"SETV",ch2)
#      mod.setch(0,0,"SETV",ch3)
#   rampWorker(mod,lock,ch0,ch1,ch2,ch3)
#   resp.headers["Access-Control-Allow-Origin"] = "*"
#
#   
#@api.route("/stopRamping") 
#def stopRamping (req, resp) :
#   mod._stopRamping = True
#   resp.headers["Access-Control-Allow-Origin"] = "*"

@api.route("/test")
def test(req, resp) :
   resp.text = "hello"
   resp.headers["Access-Control-Allow-Origin"] = "*"



   
if __name__ == "__main__":
   signal.signal(signal.SIGINT,sigintHandler)
   t1 = threading.Thread(target=monitorWorker, args=(mod,lock))
   t1.start()
#
#   t2 = threading.Thread(target=insertWorker, args=(mod,))
#   t2.start()

   api.run(address="192.168.10.109")
   doMonitor.value = 0
#    from wsgiref import simple_server
#    httpd = simple_server.make_server("127.0.0.1", 8000, api)
#    print('starting')
#    httpd.serve_forever()
  
