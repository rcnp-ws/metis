# @filename runinfo_api.py
# Create : 2020-10-07 15:44:32 JST (ota)
# Last Modified : 2020-10-08 10:55:43 JST (ota)
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
from wrap_babicmdjson import runinfo

doMonitor = Value('i',1)
lock = threading.Lock()
info = None
data = {}
dbpath = ""


def sigintHandler ():
    doMonitor.value = 0
    time.sleep(1)

def monitorWorker() :
    while doMonitor.value == 1 :
        lock.acquire()
        info.getconfig(doUpdate = True)
        time.sleep(0.01)
        info.getevtnumber(doUpdate = True)
        lock.release()
        time.sleep(1)
#
#######################################################################
## API definitions
#######################################################################
api = responder.API()

@api.route("/monitor/runinfo.json")
def monitor(req, resp) :
    ret = info.getconfig()
    ret.update(info.getevtnumber())
    resp.text = json.dumps(ret)
    resp.headers["Access-Control-Allow-Origin"] = "*"

@api.route("/control/stop/ender={ender}")
def stop(req, resp, ender) :
    lock.acquire()
    resp.text = json.dumps(info.getinfo("stop",ender,doUpdate=True))
    info.getconfig(doUpdate=True)
    info.getevtnumber(doUpdate=True)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    if 'error' in resp.text :
        lock.release()
        return
    db = json_dbstore(dbpath)
    db.createTableIfNot()
    db.commit()
    ret = info.getconfig()
    type = ret["runinfo"]["runname"] + str(ret["runinfo"]["runnumber"]).zfill(4)
    ret.update(info.getevtnumber())
    db.updateOrInsert(type,json.dumps(ret))
    db.close()
    lock.release()
    print('run stopped')
    

@api.route("/control/start/header={header}")
def start(req, resp, header) : 
    lock.acquire()
    info.getinfo("wth",header,doUpdate=True)
    resp.text = json.dumps(info.getinfo("start","",doUpdate=True))
    resp.headers["Access-Control-Allow-Origin"] = "*"
    if 'error' in resp.text :
        lock.release()
        return
    db = json_dbstore(dbpath)
    db.createTableIfNot()
    db.commit()
    ret = info.getconfig()
    print(ret)
    type = ret["runinfo"]["runname"] + str(ret["runinfo"]["runnumber"]).zfill(4)
    ret.update(info.getevtnumber())
    db.updateOrInsert(type,json.dumps(ret))
    db.close()
    lock.release()
    print('run started')

@api.route("/control/nssta") 
def nssta(req, resp) : 
    lock.acquire()
    resp.text = json.dumps(info.getinfo("nssta","",doUpdate=True))
    resp.headers["Access-Control-Allow-Origin"] = "*"
    lock.release()
    print('run started in no-save mode')


######################################################################
# option parser
######################################################################
from argparse import ArgumentParser
    
if __name__ == "__main__":
    info = runinfo("astd01")
    dbpath = "/home/daq/cyric2020a/cyric2020a_runinfo.db"
    t1 = threading.Thread(target=monitorWorker)
    t1.start()

    api.run(address="192.168.253.152",port=5044)
    doMonitor.value = 0
    
