# @filename runinfo_api.py
# Create : 2020-10-07 15:44:32 JST (ota)
# Last Modified : 2020-10-25 12:49:47 JST (ota)
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
    ret = info.getconfig(doUpdate=True)
    if 'error' in ret :
        resp.text = ret
        resp.headers["Access-Control-Allow-Origin"] = "*"
        lock.release()
        return
    state = "START"
    if "runinfo" not in ret or "runstatus" not in ret["runinfo"] :
        # error has occurred
        # should tell ...?
        return
    if ret["runinfo"]["runstatus"] == "NSSTA" : 
        state = "NSSTA"
    resp.text = json.dumps(info.getinfo("stop",ender,doUpdate=True))
    info.getconfig(doUpdate=True)
    info.getevtnumber(doUpdate=True)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    print(resp.text)
    if 'error' in resp.text :
        lock.release()
        return
#    if 'error' in resp.text :
#        print("return with error in response from babirl")
#        lock.release()
#        return
    if state == "NSSTA" :
        print("end for NSSTA")
        lock.release()
        return
    db = json_dbstore(dbpath)
    db.createTableIfNot()
    db.commit()
    count = 0
    ret = info.getconfig(doUpdate=True)
    if 'error' in ret :
        resp.text = ret
        resp.headers["Access-Control-Allow-Origin"] = "*"
        lock.release()
        return
    while count < 3 and ret["runinfo"]["runstatus"] == "START" : 
        time.sleep(1)
        ret = info.getconfig(doUpdate=True)
        count = count + 1
    ret = info.getconfig(doUpdate=True)
    type = ret["runinfo"]["runname"] + str(ret["runinfo"]["runnumber"]).zfill(4)
    ret.update(info.getevtnumber())
    print(ret)
    db.updateOrInsert(type,json.dumps(ret))
    db.commit()
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
    count = 0
    ret = info.getconfig(doUpdate=True)
    if "runinfo" not in ret or "runstatus" not in ret["runinfo"] :
        # error has occurred
        # should tell ...?
        return
    while count < 3 and ret["runinfo"]["runstatus"] == "IDLE" : 
        time.sleep(1)
        ret = info.getconfig(doUpdate=True)
        count = count + 1
    ret = info.getconfig()
    print(ret)
    type = ret["runinfo"]["runname"] + str(ret["runinfo"]["runnumber"]).zfill(4)
    db.updateOrInsert(type,json.dumps(ret))
    db.commit()
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
    info = runinfo("sels-fs01")
    dbpath = "/home/exp/db/h445_3_runinfo.db"
    t1 = threading.Thread(target=monitorWorker)
    t1.start()

    api.run(address="0.0.0.0",port=5042)
    doMonitor.value = 0
    
