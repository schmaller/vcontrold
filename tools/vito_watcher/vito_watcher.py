#!/usr/bin/python
from tinydb import TinyDB,Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware
import time
import datetime
import syslog
import json
import subprocess

_CYCLE_ON_TIME=120
_CYCLE_OFF_TIME=10 
_CYCLE_DB_TIME=600
_MIN_ON_WW_TEMP_IST=47
_MIN_ON_K_TEMP_DIFF=3.5
_MAX_OFF_K_TEMP_DIFF=20
_MIN_ON_REPEAT=10*60
_MAX_ON_TEMP_A=21
_MIN_BEFUELL_DURATION=30
_MAX_BEFUELL_DURATION=120

syslog.openlog(ident='vito_watcher', logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)
db = TinyDB('/home/pi/vclient_db.json')
# db = TinyDB('/home/pi/vclient_db.json', storage=CachingMiddleware(JSONStorage))
# table = db.table('table_name', cache_size=30)
writtenTs=0
startBefuellung=0

def readValues():
      global writtenTs,db
      sData = subprocess.check_output(['/usr/bin/vclient', '-t', '/etc/vcontrold/json.tmpl', '-c',  'getTempA,getTempKsoll,getTempKist,getTempWWist,getEntlueftBefuell,getUmschaltventil,getBetriebArt,getBrennerStarts'])
      jData = json.loads(sData)
      jData['ts'] = str(datetime.datetime.now())
      now=time.time()
      # write to db every n seconds
      if now - writtenTs > _CYCLE_DB_TIME:
            db.insert(jData)
            writtenTs=now
            print('Written to DB: TempKsoll=' + jData['getTempKsoll'] + ', TempKist=' + jData['getTempKist'] +', TempA=' + jData['getTempA'] + ' - ' + jData['ts'])
      return jData

def befuellung():
   global startBefuellung

   out = subprocess.check_output(['/usr/bin/vclient', '-c', 'setEntlueftBefuell Befuellung'])
   startBefuellung=time.time()
      
   while True:
      time.sleep(_CYCLE_OFF_TIME)
      jData = readValues()
      now = time.time()
      if now - startBefuellung >= _MIN_BEFUELL_DURATION and ( \
         now - startBefuellung >= _MAX_BEFUELL_DURATION or \
         float(jData['getTempKist']) - float(jData['getTempKsoll']) >= _MAX_OFF_K_TEMP_DIFF):
#      if now - startBefuellung >= _MIN_BEFUELL_DURATION:
         break
      
   out = subprocess.check_output(['/usr/bin/vclient', '-c', 'setEntlueftBefuell NA'])
   syslog.syslog('Ende Befuellung : ' + str(jData))
   
## MAIN
while True:

      jData = readValues()

      # check conditions for "Befuellung"
      if float(jData['getTempWWist']) >= _MIN_ON_WW_TEMP_IST and \
         float(jData['getTempA']) <= _MAX_ON_TEMP_A and \
         float(jData['getTempKsoll']) - float(jData['getTempKist']) >= _MIN_ON_K_TEMP_DIFF and \
         jData['getUmschaltventil'] == 'Heizen' and \
         time.time() - startBefuellung >= _MIN_ON_REPEAT:
#      if float(jData['getTempWWist']) >= _MIN_ON_WW_TEMP_IST:

         syslog.syslog('Start Befuellung : ' + str(jData))
         befuellung()
      
      time.sleep(_CYCLE_ON_TIME)


      