# @filename storeDAta.py
# Create : 2020-10-07 15:44:32 JST (ota)
# Last Modified : 2020-10-09 01:54:22 JST (ota)

import json
import responder
import threading
import signal
import time
import datetime
from multiprocessing import Value
from json_dbstore import json_dbstore
from gto_scaler import gto_scaler

mod = gto_scaler()
doMonitor = Value('i',1)
lock = threading.Lock()
lock_sql = threading.Lock()


def sigintHandler ():
    doMonitor.value = 0
    time.sleep(1)


def monitorWorker(mod) :
   while doMonitor.value == 1 :
       lock.acquire()
       mod.data()
       lock.release()
       time.sleep(1)

def insertWorker(mod) :
    dbpath = "/home/exp/db/%s_gto_scaler.db" % datetime.datetime.now().strftime('%Y%m%d%H%M%S')    
    db = json_dbstore(dbpath)

    db.createTableIfNot()
    db.commit()
    while doMonitor.value == 1 :
        data = json.dumps(mod.cache)
        type = "gto_scaler"
        lock_sql.acquire()
        db.insert(type,data)
        lock_sql.release()
        time.sleep(1)
    db.close()
######################################################################
# API definitions
######################################################################
api = responder.API()

@api.route("/monitor/gto_scaler.json")
def monitor(req, resp) :
    resp.text = json.dumps(mod.cache)
    resp.headers["Access-Control-Allow-Origin"] = "*"

@api.route("/control/clear_scaler")
def clear_scaler(req, resp) :
    lock.acquire()
    mod.clear()
    lock.release()
    resp.headers["Access-Control-Allow-Origin"] = "*"

@api.route("/control/init_scaler")
def clear_scaler(req, resp) :
    lock.acquire()
    mod.init()
    lock.release()
    resp.headers["Access-Control-Allow-Origin"] = "*"


if __name__ == "__main__":
    mod.address = "10.32.8.92"
    signal.signal(signal.SIGINT,sigintHandler)    
    t1 = threading.Thread(target=monitorWorker, args=(mod,))
    t1.start()
    
    t2 = threading.Thread(target=insertWorker, args=(mod,))
    t2.start()
    
    api.run(address="0.0.0.0",port=5043)
    doMonitor.value = 0

