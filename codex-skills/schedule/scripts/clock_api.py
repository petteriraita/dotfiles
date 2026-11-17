#!/usr/bin/env python3
"""Control Clock Local API over existing Termux SSH; no ADB or phone UI automation."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys


def call(method, data=None):
    args=['/system/bin/app_process','/','local.pt.schedule.ScheduleClient',method,json.dumps(data or {},separators=(',',':'))]
    command='unset LD_LIBRARY_PATH LD_PRELOAD; export CLASSPATH="$HOME/.local/share/phone-schedule/schedule-client.jar"; '+shlex.join(args)
    try:
        r=subprocess.run(['ssh','-F',str(Path.home()/'.ssh/config'),'-o','BatchMode=yes','-o','ConnectTimeout=10','android-phone',command],capture_output=True,text=True,timeout=25)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Phone command timed out; report immediately. If it was a write, inspect before retrying; outcome is unknown.') from None
    if r.returncode:
        raise RuntimeError('Phone/API command failed. No automatic retries.\n'+(r.stderr.strip() or r.stdout.strip()))
    try: result=json.loads(r.stdout)
    except ValueError:raise RuntimeError('No valid API response; inspect before retrying a write.') from None
    if not result.get('ok'):raise RuntimeError(result.get('error','API request failed'))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('check');sub.add_parser('list')
    for command in ('get','cancel'):
        parser=sub.add_parser(command);parser.add_argument('--id',type=int,required=True)
    create=sub.add_parser('create');create.add_argument('--at',required=True,help='ISO date/time with UTC offset, today or tomorrow on phone')
    create.add_argument('--label',required=True);create.add_argument('--key')
    a=p.parse_args()
    try:
        if a.command=='create':
            target=datetime.fromisoformat(a.at)
            if target.tzinfo is None:raise ValueError('Time needs a UTC offset.')
            if not a.label.strip() or len(a.label)>200:raise ValueError('Action label must have 1–200 characters.')
            millis=int(target.timestamp()*1000)
            ready=call('check')
            if millis<=ready['nowMillis']+5000:raise ValueError('Alarm time must be in the future.')
            key=a.key or hashlib.sha256((a.label+'|'+str(millis)).encode()).hexdigest()
            result=call('create',{'atMillis':millis,'label':a.label,'key':key})
            verified=call('get',{'id':result['id']})
            expected={'atMillis':millis,'label':a.label,'vibrate':True,'silent':True,'enabled':True,'oneShot':True}
            if any(verified.get(k)!=v for k,v in expected.items()):raise RuntimeError('Alarm was requested but stored-record verification failed. Inspect; do not blindly retry.')
            result['storedRecordVerified']=True;result['readback']=verified
        elif a.command in ('get','cancel'):result=call(a.command,{'id':a.id})
        else:result=call(a.command)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,RuntimeError) as e:
        print(str(e),file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
