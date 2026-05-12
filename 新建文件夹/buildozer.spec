[app]

title = 我的闹钟
package.name = myalarm
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,mp3,otf,ttf,json

requirements = python3,kivy,plyer,pyjnius,ffpyplayer

android.permissions = INTERNET, WAKE_LOCK, VIBRATE
android.minapi = 21
android.wakelock = True
android.log_level = 2

fullscreen = 1
orientation = portrait

[buildozer]
log_level = 2
warn_on_root = 1