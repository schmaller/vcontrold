#!/usr/bin/python
import sqlite3
from sqlite3 import Error
import time
import datetime
import syslog
import json
import subprocess

figureDefs = [ dict(vitoCmd=None,                  vcType=None,   dbCol='TS',        dbType = 'TIMESTAMP',   dbColOpt = 'PRIMARY KEY NOT NULL')
             , dict(vitoCmd='getTempA',            vcType='',     dbCol='TEMP_OD',   dbType = 'DECIMAL(2,1)')
             , dict(vitoCmd='getTempWWist',        vcType='',     dbCol='TEMP_WW',   dbType = 'DECIMAL(2,1)')
             , dict(vitoCmd='getTempKist',         vcType='',     dbCol=None)
             , dict(vitoCmd='getTempKsoll',        vcType='',     dbCol=None)
             , dict(vitoCmd='getTempVLsollM2',     vcType='',     dbCol=None)
             , dict(vitoCmd='getBrennerStarts',    vcType='',     dbCol='CNT_IGN',   dbType='DECIMAL(10)')
             , dict(vitoCmd='getUmschaltventil',   vcType='R',    dbCol=None)
             , dict(vitoCmd='getEntlueftBefuell',  vcType='R',    dbCol=None)
             , dict(vitoCmd=None,                  vcType=None,   dbCol='CNT_FILL',  dbType='DECIMAL(10)')
             , dict(vitoCmd='getBetriebArt',       vcType='R',    dbCol=None)
            ]

_DB_FILE='home/pi/vito_data.db'
_CYCLE_OFF_TIME=10 
_CYCLE_DB_TIME=600
_MIN_ON_WW_TEMP_IST=35
_MIN_ON_K_TEMP_DIFF=3
_MAX_OFF_K_TEMP_DIFF=15
_MIN_ON_REPEAT=6*60
_MAX_ON_TEMP_A=20
_MIN_BEFUELL_DURATION=30
_MAX_BEFUELL_DURATION=150 

# Initialisierungen: DB erstellen, Tabelle anlegen, Startwerte auslesen
def init():
   ddl = map(lambda fig : {fig.dbCol, fig.dbType, fig.dbColOpt}.join(' '), filter(lambda fig : fig.dbCol , figureDefs))
   print(ddl)

# Werte auslesen und nach definierten Intervallen in die DB schreiben
def readValues():
   global writtenTs,db
   retry = 3

   while True:
      retry = retry - 1
      try:
         sData = subprocess.check_output(['/usr/bin/vclient', '-t', '/etc/vcontrold/json.tmpl', '-c',  'getTempA,getTempKsoll,getTempKist,getTempWWist,getEntlueftBefuell,getUmschaltventil,getBetriebArt,getBrennerStarts,getTempVLsollM2'],
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

   jData = json.loads(sData)
   jData['ts'] = str(datetime.datetime.now())
   now=time.time()
   # write to db every n seconds
   if now - writtenTs > _CYCLE_DB_TIME:
         db.insert(jData)
         writtenTs=now
   print('Current values: TempKsoll=' + jData['getTempKsoll'] + ', TempKist='   + jData['getTempKist'] +     ', TempWWist='     + jData['getTempWWist'] +
                        ', TempA='     + jData['getTempA'] +     ', TempVLsoll=' + jData['getTempVLsollM2'] + ', BrennerStarts=' + jData['getBrennerStarts'] + ' - ' + jData['ts'])
   return jData

def befuellung():
   global startBefuellung
   global kSoll

   out = subprocess.check_output(['/usr/bin/vclient', '-c', 'setEntlueftBefuell Befuellung'])
   startBefuellung=time.time()

   while True:
      time.sleep(_CYCLE_OFF_TIME)
      jData = readValues()
      now = time.time()
      if now - startBefuellung >= _MIN_BEFUELL_DURATION and ( \
         now - startBefuellung >= _MAX_BEFUELL_DURATION or \
         float(jData['getTempKist']) - kSoll >= _MAX_OFF_K_TEMP_DIFF):
         #      if now - startBefuellung >= _MIN_BEFUELL_DURATION:
         break

   out = subprocess.check_output(['/usr/bin/vclient', '-c', 'setEntlueftBefuell NA'])
   syslog.syslog('Ende Befuellung : ' + str(jData))

# Endlosschleife: Werte lesen, prüfen und ggf. Aktion starten
def loop():
   writtenTs=0
   startBefuellung=0
   kSoll=0

   while True:

      jData = readValues()

      # check conditions for "Befuellung"
      if float(jData['getTempWWist']) >= _MIN_ON_WW_TEMP_IST and \
         float(jData['getTempA']) <= _MAX_ON_TEMP_A and \
         float(jData['getTempKsoll']) - float(jData['getTempKist']) >= _MIN_ON_K_TEMP_DIFF and \
         jData['getUmschaltventil'] == 'Heizen' and \
         time.time() - startBefuellung >= _MIN_ON_REPEAT:
   #   if float(jData['getTempWWist']) >= _MIN_ON_WW_TEMP_IST:

         syslog.syslog('Start Befuellung : ' + str(jData))
         kSoll = float(jData['getTempKsoll'])
         befuellung()

      time.sleep(_CYCLE_ON_TIME)

## MAIN
# Create DB / connection
db = None
try:
   db = sqlite3.connect(_DB_FILE)
   db.execute("PRAGMA synchronous = OFF")
except Error as e:
   print(e)
finally:
   if db:
      db.close()

syslog.openlog(ident='vito_watcher', logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

init()
# mainLoop()

