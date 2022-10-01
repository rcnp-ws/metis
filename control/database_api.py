# @filename database_api.py
# Create : 2020-10-07 15:44:32 JST (ota)
# Last Modified : 2020-10-25 19:06:12 JST (ota)


import sys
import json
import responder
import signal
import time
import datetime
from json_dbstore import json_dbstore

api = responder.API()

@api.route("/runlist.json")
def runlist(req, resp) :
    dbpath = "/home/exp/db/h445_3_runinfo.db"
    db = json_dbstore(dbpath)
    ret = db.selectAll()
#    print(json.loads(ret[0][0]))
#    resp.text = json.dumps(json.loads(ret[0])
    resp.text = json.dumps(ret)
    resp.headers["Access-Control-Allow-Origin"] = "*"    

if __name__ == "__main__":
#    dbpath = "/home/quser/work/cosmos/2020Oct.db"
#    db = json_dbstore(dbpath)
#    print( db.selectAll())
    api.run(address="0.0.0.0",port=5046)


