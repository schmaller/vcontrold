#!/bin/bash
# extract the recent 50 records
jq '[._default[]][-50:]' ~/vclient_db.json
