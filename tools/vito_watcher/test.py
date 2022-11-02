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
