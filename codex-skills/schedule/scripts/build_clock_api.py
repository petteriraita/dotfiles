#!/usr/bin/env python3
"""Build a pinned GPL Fossify Clock with a Termux-only local alarm API."""
import argparse
from pathlib import Path
import shutil
import subprocess

REV = '4ecb9e33c51c0b2096af2379e7ac9dc17c3e07e6'
SKILL = Path(__file__).resolve().parents[1]
ASSETS = SKILL / 'assets/fossify-api'
CACHE = Path.home()/'.cache/phone-schedule'
SOURCE = CACHE/'fossify-clock-source'


def run(args, **kwargs):
    subprocess.run(list(map(str,args)),check=True,**kwargs)


def replace(path, old, new):
    text=path.read_text()
    if new in text:return
    if old not in text:raise RuntimeError(f'Pinned source did not match expected context: {path}')
    path.write_text(text.replace(old,new,1))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk',type=Path,default=Path.home()/'dev/personal/apps/android-alarm-helper/tools')
    p.add_argument('--prepare-only',action='store_true')
    a=p.parse_args();CACHE.mkdir(parents=True,exist_ok=True)
    if not SOURCE.exists():
        run(['git','clone','--no-checkout','https://github.com/FossifyOrg/Clock.git',SOURCE])
        run(['git','checkout','--detach',REV],cwd=SOURCE)
    current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()
    if current!=REV:raise RuntimeError('Build cache is not at the pinned upstream revision; refusing to reset it.')
    kotlin=SOURCE/'app/src/main/kotlin/org/fossify/clock'
    (kotlin/'api').mkdir(exist_ok=True)
    shutil.copyfile(ASSETS/'ScheduleProvider.kt',kotlin/'api/ScheduleProvider.kt')
    manifest=SOURCE/'app/src/main/AndroidManifest.xml'
    replace(manifest,'    <application\n','    <queries><package android:name="com.termux" /></queries>\n\n    <application\n')
    replace(manifest,'android:label="@string/app_launcher_name"','android:label="Clock Local API"')
    replace(manifest,'        <activity\n            android:name=".activities.SplashActivity"',
        '        <provider android:name="org.fossify.clock.api.ScheduleProvider" android:authorities="${applicationId}.schedule.api" android:exported="true" />\n\n        <activity\n            android:name=".activities.SplashActivity"')
    gradle=SOURCE/'app/build.gradle.kts'
    replace(gradle,'applicationIdSuffix = ".debug"','applicationIdSuffix = ".schedule"')
    replace(gradle,'    compileSdk = project.libs.versions.app.build.compileSDKVersion.get().toInt()',
        '    compileSdk = project.libs.versions.app.build.compileSDKVersion.get().toInt()\n    buildToolsVersion = "36.0.0"')
    ctrl=kotlin/'helpers/AlarmController.kt'
    replace(ctrl,'            if (!it.isToday() || it.timeInMinutes > getCurrentDayMinutes()) {',
        '            if (context.getSharedPreferences("local_schedule_api", 0).contains("at:${it.id}") || !it.isToday() || it.timeInMinutes > getCurrentDayMinutes()) {')
    replace(ctrl,'    fun onAlarmTriggered(alarmId: Int) {\n',
        '    fun onAlarmTriggered(alarmId: Int) {\n        context.getSharedPreferences("local_schedule_api", 0).edit().putLong("fired:$alarmId", System.currentTimeMillis()).commit()\n')
    replace(ctrl,'        val triggerTimeMillis = getTimeOfNextAlarm(alarm)?.timeInMillis ?: return',
        '''        val absoluteTime = context.getSharedPreferences("local_schedule_api", 0).getLong("at:${alarm.id}", 0)
        if (absoluteTime > 0 && absoluteTime <= System.currentTimeMillis()) {
            context.cancelAlarmClock(alarm)
            db.updateAlarmEnabledState(alarm.id, false)
            return
        }
        val triggerTimeMillis = if (absoluteTime > 0) absoluteTime else getTimeOfNextAlarm(alarm)?.timeInMillis ?: return''')
    service=kotlin/'services/AlarmService.kt'
    replace(service,'        if (alarm.vibrate) {\n','        if (alarm.vibrate) {\n            getSharedPreferences("local_schedule_api", 0).edit().putLong("vibrated:${alarm.id}", System.currentTimeMillis()).commit()\n')
    (SOURCE/'local.properties').write_text('sdk.dir='+str(a.sdk.resolve())+'\n')
    print('Prepared source:',SOURCE,flush=True)
    if a.prepare_only:return
    if not (a.sdk/'platforms/android-36/android.jar').is_file():raise RuntimeError('Android SDK 36 is required; pass --sdk.')
    run(['./gradlew','--no-daemon',':app:assembleFossDebug'],cwd=SOURCE)
    apk=list((SOURCE/'app/build/outputs/apk/foss/debug').glob('*.apk'))
    if len(apk)!=1:raise RuntimeError('Expected exactly one APK output.')
    dest=CACHE/'fossify-clock-local-api.apk';shutil.copyfile(apk[0],dest)
    client=CACHE/'client';(client/'classes').mkdir(parents=True,exist_ok=True);(client/'dex').mkdir(exist_ok=True)
    jar=a.sdk/'platforms/android-36/android.jar'
    run(['javac','--release','8','-classpath',jar,'-d',client/'classes',ASSETS/'ScheduleClient.java'])
    run(['jar','cf',client/'client.jar','-C',client/'classes','.'])
    run([a.sdk/'build-tools/36.0.0/d8','--lib',jar,'--min-api','26','--output',client/'dex',client/'client.jar'])
    run(['jar','cf',CACHE/'schedule-client.jar','-C',client/'dex','classes.dex'])
    run([a.sdk/'build-tools/36.0.0/apksigner','verify','--print-certs',dest])
    print('APK:',dest);print('Termux client:',CACHE/'schedule-client.jar')


if __name__=='__main__':main()
