import json
import responder
from nhq import nhq
import threading
import signal
import time
from multiprocessing import Value
#from json_dbstore import json_dbstore
import datetime
import socket
import sys

mod = None
doMonitor = Value('i',1)
lock = threading.Lock()
qlock_sql = threading.Lock()

def sigintHandler ():
   doMonitor.value = 0
   time.sleep(1)

def monitorWorker(mod,lock):
   while doMonitor.value == 1:
      lock.acquire()
      mod.getModuleIdentifier()
      mod.monvolt("D")
      mod.monvolt("U")
      mod.moncurrent("I")
      mod.monvolt("V")
      lock.release()
      time.sleep(1.)

api = responder.API()
#
@api.route("/monitor/json")
def monitor (req, resp):
   resp.text = json.dumps(mod.getCache())
   resp.headers["Access-Control-Allow-Origin"] = "*"
#
@api.route("/set/{ch}/{val}")
def set (req, resp, ch, val):
   lock.acquire()
   mod.setvolt(ch,val)
   lock.release()
   resp.headers["Access-Control-Allow-Origin"] = "*"

#@api.route("/setr/{ch}/{val}")
#def setr (req, resp, ch, val):
#   lock.acquire()
#   mod.setramp(ch,val)
#   lock.release()
#   resp.headers["Access-Control-Allow-Origin"] = "*"

@api.route("/test")
def test(req, resp) :
   resp.text = "hello"
   resp.headers["Access-Control-Allow-Origin"] = "*"


# requires two arguments
# 0 : usb tty device for n14xx
# 1 : port to be served
if __name__ == "__main__":
   args = sys.argv
   if len(args) != 3 :
      print('Error: Requires two arguments /dev/ttyUSBx, and port number except for the filename')
      print(args)
      sys.exit()
      
   mod = nhq(args[1])
   port = int(args[2])
   
   signal.signal(signal.SIGINT,sigintHandler)
   t1 = threading.Thread(target=monitorWorker, args=(mod,lock))
   t1.start()

   api.run(address="0.0.0.0", port = port)
   doMonitor.value = 0
#    from wsgiref import simple_server
#    httpd = simple_server.make_server("127.0.0.1", 8000, api)
#    print('starting')
#    httpd.serve_forever()
  
