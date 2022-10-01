# @file api_mrc1.py
# @brief api for mrc1
# Created       : 2021-01-16 16:30:19 JST (ota)
# Last Modified : 2021-07-03 15:26:56 JST (ota)

import sys
import json
import responder
import threading
import signal
import time
import datetime
import socket

from multiprocessing import Value
from mrc1 import MRC1

api = responder.API(
   title='Web Service',
   version='1.0',
   openapi='3.0.2',
   description='This is a sample server for a pet store.',
   terms_of_service='http://example.com/terms/',
   contact={
       'name': "API Support",
       'url': 'http://www.example.com/support',
       'email': 'support@example.com',
   },
   license={
       'name': 'Apache 2.0',
       'url': 'https://www.apache.org/licenses/LICENSE-2.0.html',
   },
   docs_route='/docs',
)

mod = ""
doMonitor = Value('i',1)
lock = threading.Lock()

@api.route("/api/mrc1/status.json")
def monitor (req, resp) :
    resp.text = json.dumps(mod.cache)
    resp.headers["Access-Control-Allow-Origin"] = "*"

@api.route("/api/mrc1/control/setv")
async def mhv4_setv (req, resp):
    text = await req.media(format="json")
    print("api" + str(text))
    mod.ramp(text)
    resp.media = "doing"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    

def monitorWorker(mod, lock) :
    global doMonitor
    while doMonitor.value == 1 :
        lock.acquire()
        mod.monitor()
        lock.release()

if __name__ == "__main__" :
    args = sys.argv
    doMonitor.value = 1
    mod = MRC1(args[1])
    api.run(address = "0.0.0.0", port=5040)
    mod.stopPolling()
    doMonitor.value = 0
