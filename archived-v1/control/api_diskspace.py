# @file api_mrc1.py
# @brief api for mrc1
# Created       : 2022-02-12 01:14:27 JST (ota)

import json
import responder
import threading
import signal
import time
import datetime
import subprocess
from multiprocessing import Value
import sys
import os

api = responder.API(
#   title='Web Service',
#   version='1.0',
#   openapi='3.0.2',
#   description='This is a sample server for a pet store.',
#   terms_of_service='http://example.com/terms/',
#   contact={
#       'name': "API Support",
#       'url': 'http://www.example.com/support',
#       'email': 'support@example.com',
#   },
#   license={
#       'name': 'Apache 2.0',
#       'url': 'https://www.apache.org/licenses/LICENSE-2.0.html',
#   },
#   docs_route='/docs',
)

cacheGetdaq02 = []
cacheSelsfs01 = []
doMonitor = Value('i',1)



def monitorWorker() :
    global doMonitor
    global cacheGetdaq02
    global cacheSelsfs01
    while doMonitor.value == 1 :
        command = ["df","/getdaq02"]
        res = subprocess.run(command,stdout=subprocess.PIPE)
        cacheGetdaq02 = res.stdout.decode().splitlines()[1].split()
        command = ["df","/sels-fs01"]
        res2 = subprocess.run(command,stdout=subprocess.PIPE)
        cacheSelsfs01 = res2.stdout.decode().splitlines()[1].split()
#        print(cacheGetdaq02)
#        print(cacheSelsfs01)
        time.sleep(1)


def sigintHandler ():
   doMonitor.value = 0
   time.sleep(1)

@api.route("/api/getdaq02status.json")
def status (req, resp) :
    resp.text = json.dumps(cacheGetdaq02)
    
#    resp.text = json.dumps("hoge")
    resp.headers["Access-Control-Allow-Origin"] = "*"

@api.route("/api/selsfs01status.json")
def status (req, resp) :
    resp.text = json.dumps(cacheSelsfs01)
#    print(cacheSelsfs01)
#    resp.text = json.dumps("hoge")
    resp.headers["Access-Control-Allow-Origin"] = "*"

if __name__ == "__main__" :
    doMonitor.value = 1
    args = sys.argv
    if len(args) != 2 :
        print('Error: request one argument [port]')
        print(args)
        sys.exit()

    os.environ["LANG"] = "C"

    signal.signal(signal.SIGINT,sigintHandler)
    t1 = threading.Thread(target=monitorWorker)
    t1.start()
        
    api.run(address = "0.0.0.0",port=int(args[1]))
    doMonitor.value = 0

    
