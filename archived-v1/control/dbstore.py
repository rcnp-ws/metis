# @filename storeDAta.py
# Create : 2020-10-07 12:25:12 JST (ota)
# Last Modified : 2020-10-08 10:15:06 JST (ota)
import sqlite3
import os

class dbstore (object) :

   def __init__(self,dbpath) :
      self.__dbpath = dbpath
      self.__connection = None
      self.__cursor = None

   def __del__(self) :
      self.close()

   @property
   def connection(self) :
      if self.__connection is None and len(self.dbpath) != 0 : 
         self.__connection = sqlite3.connect(self.dbpath)
         print("connected to %s" % self.dbpath)
      return self.__connection

   @property
   def cursor(self) :
      if self.__cursor is not None :
         return self.__cursor
      if self.connection is not None :
         self.__cursor = self.connection.cursor()
      return self.__cursor

   def close(self) :
      if self.__connection is not None :
         self.__connection.close()
         self.__connection = None

   def commit(self) :
      return None if self.connection is None else self.connection.commit()

   def execute(self,sql) :
      # print("executing query %s" % sql)
      return None if self.cursor is None else self.cursor.execute(sql)

   @property
   def dbpath(self):
      return self.__dbpath;  

   @dbpath.setter
   def dbpath(self, path) :
      None if not os.path.dirname(path) else os.makedirs(os.path.dirname(path),exist_ok = True)
      self.__dbpath = path

if __name__ == "__main__" :
   db = dbstore("test.db")
   db.execute('create table persons (id integer primary key autoincrement, name string)')
   db.commit()
   
