# @filename storeDAta.py
# Create : 2020-10-07 12:25:12 JST (ota)
# Last Modified : 2020-10-08 10:49:53 JST (ota)
from dbstore import dbstore 
import time

class json_dbstore (dbstore) :
   def __init__(self,dbpath) :
      super().__init__(dbpath)
      self.__dataType = "json"
      self.__version = "1.0"
      self.__table = "json_table"
      self.__items = ["ts" ,"type", "data"];

   @property
   def table(self) :
      return self.__table
   @table.setter
   def table(self, table) :
      self.__table = table

   def createTableIfNot (self) :
      print(self.execute("select * from sqlite_master where type = 'table' and name = '%s';" % self.table))
      if self.cursor.fetchone() is None :
         self.execute("create table %s (id integer primary key autoincrement, %s);" % (self.table, ",".join(self.__items)))
         
   def insert (self, type, data) :
      ts  = time.time() # epoch or unix time
      sql = "insert into %s (ts, type, data) values ('%s', '%s', '%s')" % (self.table, ts, type, data)
      print("inserting %s" % sql)
      self.execute(sql)
      self.commit()
   def updateOrInsert (self, type, data) :
      ts  = time.time() # epoch or unix time
      self.execute("select * from %s where type = '%s'" % (self.table,type))
      doUpdate = False if self.cursor.fetchone() is None else True
      sql = ""
      if doUpdate :
         sql = "update %s set ts = '%s', data = '%s' where type = '%s'" % (self.table,ts,data,type)
      else :
         sql = "insert into %s (ts, type, data) values ('%s', '%s', '%s')" % (self.table, ts, type, data)
      self.execute(sql)
      self.commit()
   

if __name__ == "__main__" :
   db = json_dbstore()
   db.dbpath = "test.db"
   db.createTableIfNot()
   db.commit()

