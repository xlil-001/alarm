[app]

title = My Alarm
package.name = myalarm
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ogg,otf,ttf,json

version = 0.1

android.accept_sdk_license = True
android.build_tools_version = 34.0.0
android.python_version = 3.10

requirements = python3,kivy,plyer,pyjnius

android.permissions = INTERNET, WAKE_LOCK, VIBRATE
android.minapi = 21
android.wakelock = True

fullscreen = 1
orientation = portrait

[buildozer]
log_level = 2
warn_on_root = 1