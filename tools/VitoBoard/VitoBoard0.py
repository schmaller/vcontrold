#!/usr/bin/env python3
from flask import Flask,render_template,request,redirect,url_for
from json2html import *
import os
import subprocess
import json
from datetime import datetime
from time import strftime,localtime,mktime,sleep,time

WW_TEMP=[42,60]    # warm and hot
WEEKDAYS=['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def main():
    data={}
    if request.method == "POST" and request.form.get('call')=="heat" and request.form.get('parm'):
       makeItHot(request.form.get('parm'))
       return redirect("/")

    if request.method == "POST" and \
       ( request.form.get('call')=="set_norm" or request.form.get('call')=="set_red" ) and \
       request.form.get('parm'):
       data = getTemps()
       setRaumTemp(request.form.get('call'), request.form.get('parm'), data)

    data.update(getTemps())
    
    # read last entry from vclient_db.json file
    try:
      sData = subprocess.check_output(['/usr/bin/jq', '[._default[]][-1:][]', '/home/pi/vclient_db.json'], text=True, stderr=subprocess.STDOUT)
      if 'SRV ERR' in sData:
         print('Error occured: ' + sData[0:50] + '...')
    except subprocess.CalledProcessError as e:
      print('Error calling jq:')
      print(e)

    data['vclient'] = json2html.convert(json=sData, clubbing='off')
    
    # render page
    return render_template('main.html', data=data)
                            
@app.route("/test")
def layout():
    data = {'getTempA': 15.3, 'getTempWWist':45.5, 'getTempRaumNorSollM2':25, 'getBrennerStatus': 1.0, 'getBrennerStarts': 536414, 'getTempRaumRedSollM2': 16.0}
    return render_template('main.html', data=data)
                            
# read figures from the controller and return the JSON data                            
def getTemps():
   try:
      sData = subprocess.check_output(['/usr/bin/vclient', '-j', '-c',  'getTempA,getTempWWist,getTempRaumNorSollM2,getTempRaumRedSollM2,getBrennerStatus,getBrennerStarts'], text=True, stderr=subprocess.STDOUT)
      if 'SRV ERR' in sData:
         print('Error occured: ' + sData[0:50] + '...')
   except subprocess.CalledProcessError as e:
      print('Error calling vclient:')
      print(e)
      
   data = json.loads(sData)
   data['time'] = strftime("%Y-%m-%d %H:%M", localtime())
   data['last60'] = readLast60()
   return data

# change the Soll temperatures by one step
def setRaumTemp(call, parm, data):
   if call == "set_norm":
      vcmd = "setTempRaumNorSollM2"
      vval = data['getTempRaumNorSollM2']
   if call == "set_red":
      vcmd = "setTempRaumRedSollM2"
      vval = data['getTempRaumRedSollM2']
   if parm == "up":
      vval = vval + 1
   if parm == "down":
      vval = vval - 1

   if vcmd and vval <= 25 and vval >= 15:
      sData = subprocess.check_output(['/usr/bin/vclient', '-c', f"{vcmd} {vval:.0f}"], text=True, stderr=subprocess.STDOUT)
      if 'SRV ERR' in sData:
         raise Exception('Error calling vclient setting Soll temperatures ' + sData)
      data['msg']="Temperatur wurde geändert"
   else:
      data['msg']="Temperaturgrenze 15° bis 25°"


# heat up the hot water boiler
def makeItHot(temp):
   # set current device time from system
   now = localtime()
   nowsec = mktime(now)
   tsString = strftime("%Y-%m-%dT%H:%M:%S%z", now)
   tStart = strftime("%H:%M", localtime(nowsec - 12*60))
   sData = subprocess.check_output(['/usr/bin/vclient', '-c', 'setSystemTime '+ tsString], text=True, stderr=subprocess.STDOUT)
   if 'SRV ERR' in sData:
      raise Exception('Error calling vclient setting time: ' + sData)

   then = localtime(nowsec + 12*60)
   tStop = strftime("%H:%M", then)
   weekday = WEEKDAYS[int(strftime("%w", now))]
   
   # Start heating
   wwidx = 0
   if temp == "hot":
     wwidx = 1
   sData = subprocess.check_output(['/usr/bin/vclient', '-c', 'setTempWWsoll ' + str(WW_TEMP[wwidx])], text=True, stderr=subprocess.STDOUT)
   if 'SRV ERR' in sData:
      raise Exception('Error calling vclient setting WWTemp: ' + sData)
      
   sData = subprocess.check_output(['/usr/bin/vclient', '-c', 'setTimerWW'+weekday + ' ' + tStart + ' ' + tStop], text=True, stderr=subprocess.STDOUT)
   if 'SRV ERR' in sData:
      raise Exception('Error calling vclient setting WW timer: ' + sData)
   
   sleep(60)
   sData = subprocess.check_output(['/usr/bin/vclient', '-c', 'setTimerWW'+weekday + ' -- --'], text=True, stderr=subprocess.STDOUT)
   if 'SRV ERR' in sData:
      raise Exception('Error calling vclient resetting WW timer: ' + sData)

# Ermittelt 1x täglich den Zeitpunkt der letzten WW Erhitzung auf min. 60°
def readLast60():
   file='/tmp/last60'
   fst=None

   try:
      fst=os.stat(file)
   except:
      pass

   if fst == None or fst.st_mtime < time() - 60*60*24:
      with open(file, mode='w') as fd:
         subprocess.run(['jq', '[._default[] | select(.getTempWWist>"60.00000")][-1]', '/home/pi/vclient_db.json'], stdout=fd)
    
   data=None
   with open(file) as fd:
      try:
         data=json.load(fd)
      except:
         data=None

   return data.get('ts')[0:16] if data else '1970-01-01 00:00:00.000000'
   

''' MAIN '''
if __name__ == "__main__":
   # makeItHot()
   app.run()
