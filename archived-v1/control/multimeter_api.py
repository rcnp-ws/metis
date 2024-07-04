# @filename 
# Create : 
# Last Modified : 

import json
import responder
import threading
import signal
import time
import datetime
from multiprocessing import Value
from json_dbstore import json_dbstore
from multimeter import multimeter

mod = multimeter()
doMonitor = Value('i',1)
lock = threading.Lock()
lock_sql = threading.Lock()


def sigintHandler ():
    doMonitor.value = 0
    time.sleep(1)


def monitorWorker(mod) :
    dbpath = "/home/exp/db/%s_multimeter.db" % datetime.datetime.now().strftime('%Y%m%d%H%M%S')    
    db = json_dbstore(dbpath)

    db.createTableIfNot()
    db.commit()
    while doMonitor.value == 1 :
       lock.acquire()
       type = "multimeter"
       print(mod.data())
       data = json.dumps(mod.data())
       db.insert(type,data)       
       lock.release()
       time.sleep(10)
    db.close()

######################################################################
# API definitions
######################################################################
api = responder.API()

@api.route("/monitor/multimeter.json")
def monitor(req, resp) :
    resp.text = json.dumps(mod.cache)
    resp.headers["Access-Control-Allow-Origin"] = "*"

#@api.route("/control/clear_scaler")
#def clear_scaler(req, resp) :
#    lock.acquire()
#    mod.clear()
#    lock.release()
#    resp.headers["Access-Control-Allow-Origin"] = "*"
#
#@api.route("/control/init_scaler")
#def clear_scaler(req, resp) :
#    lock.acquire()
#    mod.init()
#    lock.release()
#    resp.headers["Access-Control-Allow-Origin"] = "*"


if __name__ == "__main__":
    mod.address = "10.32.8.152"
    signal.signal(signal.SIGINT,sigintHandler)    
    t1 = threading.Thread(target=monitorWorker, args=(mod,))
    t1.start()
    
    api.run(address="0.0.0.0",port=5555)
    doMonitor.value = 0

