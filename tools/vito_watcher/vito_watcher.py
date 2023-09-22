#!/usr/bin/python
from tinydb import TinyDB,Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware
import time
import datetime
import syslog
import json
import subprocess

_CYCLE_ON_TIME=60
_CYCLE_OFF_TIME=20
_CYCLE_DB_TIME=600
_MIN_ON_WW_TEMP_IST=34
_MIN_ON_K_TEMP_DIFF=1
_MIN_ON_WW_TEMP_DIFF=4
_MAX_OFF_K_TEMP_DIFF=15
_MIN_ON_REPEAT=5*60
_MAX_ON_TEMP_A=21
_MIN_BEFUELL_DURATION=30
_MAX_BEFUELL_DURATION=60*20

syslog.openlog(ident='vito_watcher', logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)
db = TinyDB('/home/pi/vclient_db.json')
# db = TinyDB('/home/pi/vclient_db.json', storage=CachingMiddleware(JSONStorage))
# table = db.table('table_name', cache_size=30)
writtenTs=0
startBefuellung=0
kSoll=0
jData = {}

def readValues():
      global writtenTs,db,jData
      retry = 3

      while True:
         retry = retry - 1

         # full or reduced data request
         now=time.time()
         if now - writtenTs > _CYCLE_DB_TIME:
            writeIt = True
            extraValues = ',getTempA,getBrennerStarts,getTempVLsollM2,getBrennerStunden1'
            tmpl = 'json_long.tmpl'
            writtenTs = now
         else:
            writeIt = False
            extraValues = ''
            tmpl = 'json.tmpl'

         try:
            sData = subprocess.check_output(['/usr/bin/vclient', '-t', '/etc/vcontrold/'+tmpl, '-c',  'getTempKsoll,getTempKist,getUmschaltventil,getBetriebArt,getTempWWist'+extraValues], 
                                            text=True, stderr=subprocess.STDOUT)
            if 'SRV ERR' in sData:
               print('Error occured: ' + sData[0:50] + '...')
            else:
               break
         except subprocess.CalledProcessError as e:
            print('Error calling vclient:')
            print(e)
         if retry < 1:
            break   
         time.sleep(5)

      jData.update(json.loads(sData))
      jData['ts'] = str(datetime.datetime.now())

      # write to db every n seconds
      if writeIt:
         db = TinyDB('/home/pi/vclient_db.json')
         db.insert(jData)
   
      print(', '.join(k+'='+jData[k] for k in jData))
      
      return

def befuellung():
   global startBefuellung
   global kSoll
   global jData
   global db

   out = subprocess.check_output(['/usr/bin/vclient', '-c', 'setEntlueftBefuell Befuellung'])
   startBefuellung=time.time()
      
   # Schreiben mit Umschaltventil=Mittelstellung
   umschaltAlt=jData['getUmschaltventil']
   jData['getUmschaltventil'] = 'Mittelstellung'
   jData['ts'] = str(datetime.datetime.now())
   db = TinyDB('/home/pi/vclient_db.json')
   db.insert(jData)

   while True:
      time.sleep(_CYCLE_OFF_TIME)
      readValues()
      now = time.time()
      if now - startBefuellung >= _MIN_BEFUELL_DURATION and (         # min. Laufzeit erreicht && \
         now - startBefuellung >= _MAX_BEFUELL_DURATION or               # max. Laufzeit erreicht || \
         float(jData['getTempWWist']) < _MIN_ON_WW_TEMP_IST or           # min. WW-Temp unterschritten || \
         float(jData['getTempKist']) - kSoll >= _MAX_OFF_K_TEMP_DIFF or  # K-Soll erreicht und überschritten || \
         jData['getUmschaltventil'] == 'Heizen' ):                       # Steuerung hat Heizen aktiviert 
         break
      pass
      
   out = subprocess.check_output(['/usr/bin/vclient', '-c', 'setEntlueftBefuell NA'])
   syslog.syslog('Ende Befuellung : ' + str(jData))

   # Ende schreiben mit alter Stellung
   jData['getUmschaltventil'] = umschaltAlt
   jData['ts'] = str(datetime.datetime.now())
   db = TinyDB('/home/pi/vclient_db.json')
   db.insert(jData)
   
## MAIN
while True:

   readValues()

   # check conditions for "Befuellung"
   if float(jData['getTempWWist']) >= _MIN_ON_WW_TEMP_IST and \
      float(jData['getTempA']) <= _MAX_ON_TEMP_A and \
      float(jData['getTempKsoll']) - float(jData['getTempKist']) >= _MIN_ON_K_TEMP_DIFF and \
      float(jData['getTempWWist']) - float(jData['getTempKist']) >= _MIN_ON_WW_TEMP_DIFF and \
      jData['getUmschaltventil'] == 'Heizen' and \
      time.time() - startBefuellung >= _MIN_ON_REPEAT:

      syslog.syslog('Start Befuellung : ' + str(jData))
      kSoll = float(jData['getTempKsoll'])
      befuellung()
      
   time.sleep(_CYCLE_ON_TIME)
      