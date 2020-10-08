# @filename runinfo_api.py
# Create : 2020-10-07 15:44:32 JST (ota)
# Last Modified : 2020-10-08 07:58:50 JST (ota)
import sys
import subprocess
import json
import responder
import threading
import signal
import time
import datetime
from multiprocessing import Value
from json_dbstore import json_dbstore
from runinfo import  runinfo

doMonitor = Value('i',1)
lock = threading.Lock()
mod = runinfo()
data = {}


def sigintHandler ():
    doMonitor.value = 0
    time.sleep(1)

def monitorWorker() :
    while doMonitor.value == 1 : 
       lock.acquire()
       mod.exec("getconfig")
       time.sleep(0.01)
       mod.exec("getevtnumber")
       lock.release()
       time.sleep(1)

######################################################################
# API definitions
######################################################################
api = responder.API()

@api.route("/monitor/runinfo.json")
def monitor(req, resp) :
    ret = mod.cache["getconfig"]
    ret.update(mod.cache["getevtnumber"])
    resp.text = json.dumps(ret)
    resp.headers["Access-Control-Allow-Origin"] = "*"

@api.route("/control/stop/ender={ender}")
def stop(req, resp, ender) :
    lock.acquire()
    mod.exec("stop",ender)
    mod.exec("getconfig")
    mod.exec("getevtnumber")
    resp.text = json.dumps(mod.cache["stop"])
    resp.headers["Access-Control-Allow-Origin"] = "*"
#    db = json_dbstore()
#    db.dpath = "/home/daq/cyric2020a/runinfo.db"
#    db.createTableIfNot()
#    db.commit()
#    type = mod.cache.getconfig.runname + mod.cache.getconfig.runnumber
#    ret = mod.cache["getconfig"]
#    ret.update(mod.cache["getevtnumber"])
#    db.updateOrInsert(type,json_dumps(ret))
#    lock.release()
    

@api.route("/control/start/header={header}")
def start(req, resp, header) : 
    lock.acquire()
    mod.exec("start", header)
    resp.text = json.dumps(mod.cache["start"])
    resp.headers["Access-Control-Allow-Origin"] = "*"
    lock.release()

@api.route("/control/nssta") 
def nssta(req, resp) : 
    lock.acquire()
    mod.exec("nssta")
    resp.text = json.dumps(mod.cache["nssta"])
    resp.headers["Access-Control-Allow-Origin"] = "*"
    lock.release()

    
    
if __name__ == "__main__":
    t1 = threading.Thread(target=monitorWorker)
    t1.start()

    api.run(address="192.168.253.152",port=5044)
    doMonitor.value = 0
    
