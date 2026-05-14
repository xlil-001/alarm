from kivy.app import App
from kivy.core.text import LabelBase
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.properties import ListProperty
from datetime import datetime, timedelta
import json
import os
from plyer import notification, vibrator

# ---------- 字体绝对路径 ----------
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'font.otf')
try:
    LabelBase.register(name='custom', fn_regular=FONT_PATH)
    print(f"✅ 字体已加载: {FONT_PATH}")
except Exception as e:
    print(f"❌ 字体加载失败: {e}")

# ---------- Android 振动 API ----------
ANDROID_VIBE = False
try:
    from jnius import autoclass
    Context = autoclass('android.content.Context')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Vibrator = autoclass('android.os.Vibrator')
    VibrationEffect = autoclass('android.os.VibrationEffect')
    activity = PythonActivity.mActivity
    vibrator_service = activity.getSystemService(Context.VIBRATOR_SERVICE)
    ANDROID_VIBE = True
except:
    pass

DATA_FILE = 'alarms.json'

class Alarm:
    def __init__(self, hour, minute, repeat_days, enabled=True,
                 vibrate=True, vibrate_strength=3,
                 sound=True, snooze_minutes=5, alarm_id=None):
        self.hour = hour
        self.minute = minute
        self.repeat_days = repeat_days
        self.enabled = enabled
        self.vibrate = vibrate
        self.vibrate_strength = vibrate_strength
        self.sound = sound
        self.snooze_minutes = snooze_minutes
        self.id = alarm_id or datetime.now().timestamp()

    def to_dict(self):
        return {
            'id': self.id,
            'hour': self.hour,
            'minute': self.minute,
            'repeat_days': self.repeat_days,
            'enabled': self.enabled,
            'vibrate': self.vibrate,
            'vibrate_strength': self.vibrate_strength,
            'sound': self.sound,
            'snooze_minutes': self.snooze_minutes
        }

    @classmethod
    def from_dict(cls, d):
        return cls(d['hour'], d['minute'], d['repeat_days'],
                   d.get('enabled', True),
                   d.get('vibrate', True),
                   d.get('vibrate_strength', 3),
                   d.get('sound', True),
                   d.get('snooze_minutes', 5),
                   d.get('id'))

class AlarmApp(App):
    alarms = ListProperty([])
    snooze_alarm = None
    sound = None
    vibrating = False

    def build(self):
        self.load_alarms()
        Clock.schedule_interval(self.check_alarms, 1)

    def on_start(self):
        self.refresh_alarm_list()

    def start_vibrate(self, strength):
        if ANDROID_VIBE:
            amp = int(strength * 51)
            timings = [0, 500, 300]
            amplitudes = [0, amp, 0]
            effect = VibrationEffect.createWaveform(timings, amplitudes, 0)
            vibrator_service.vibrate(effect)
            self.vibrating = True
        else:
            duration = strength * 0.2
            vibrator.vibrate(duration)

    def cancel_vibrate(self):
        if ANDROID_VIBE:
            vibrator_service.cancel()
        self.vibrating = False

    def check_alarms(self, dt):
        now = datetime.now()
        cw = now.weekday()
        ch, cm, cs = now.hour, now.minute, now.second
        for alarm in self.alarms:
            if not alarm.enabled:
                continue
            if cw in alarm.repeat_days:
                if alarm.hour == ch and alarm.minute == cm and cs == 0:
                    self.trigger_alarm(alarm)
        if self.snooze_alarm:
            if now >= self.snooze_alarm[1]:
                main_alarm = next((a for a in self.alarms if a.id == self.snooze_alarm[0]), None)
                if main_alarm:
                    self.trigger_alarm(main_alarm)
                self.snooze_alarm = None

    def trigger_alarm(self, alarm):
        if alarm.sound:
            self.play_alarm_sound()
        if alarm.vibrate:
            self.start_vibrate(alarm.vibrate_strength)

        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        content.add_widget(Label(
            text=f'[b]闹钟响了！[/b]\n{alarm.hour:02d}:{alarm.minute:02d}',
            markup=True, font_size='24sp', font_name=FONT_PATH))
        btn_box = BoxLayout(size_hint_y=None, height=50, spacing=10)
        btn_dismiss = Button(text='关闭', on_release=self.dismiss_alarm, font_name=FONT_PATH)
        btn_snooze = Button(text='贪睡', on_release=lambda x: self.snooze(alarm), font_name=FONT_PATH)
        btn_box.add_widget(btn_dismiss)
        btn_box.add_widget(btn_snooze)
        content.add_widget(btn_box)

        popup = Popup(title='闹钟', content=content,
                      size_hint=(0.8, 0.5), auto_dismiss=False,
                      title_font=FONT_PATH)
        popup.bind(on_dismiss=self.stop_ringing)
        popup.open()

    def play_alarm_sound(self):
        if self.sound:
            self.sound.stop()
        try:
            self.sound = SoundLoader.load('alarm.ogg')
            if self.sound:
                self.sound.loop = True
                self.sound.play()
        except:
            self.sound = None

    def stop_ringing(self, *args):
        if self.sound:
            self.sound.stop()
            self.sound = None
        self.cancel_vibrate()

    def dismiss_alarm(self, instance):
        instance.parent.parent.parent.parent.dismiss()
        self.stop_ringing()
        notification.notify(title='闹钟', message='闹钟已关闭')

    def snooze(self, alarm):
        for widget in self.root_window.children:
            if isinstance(widget, Popup):
                widget.dismiss()
        self.stop_ringing()
        delay = timedelta(minutes=alarm.snooze_minutes)
        next_time = datetime.now() + delay
        self.snooze_alarm = (alarm.id, next_time)
        notification.notify(title='贪睡', message=f'将于{next_time.strftime("%H:%M")}再次响铃')

    def refresh_alarm_list(self):
        alarm_list = self.root.ids.alarm_list
        alarm_list.clear_widgets()
        weekdays = '一二三四五六日'
        for alarm in self.alarms:
            item = BoxLayout(size_hint_y=None, height='48dp')
            days_str = ' '.join([weekdays[i] for i in alarm.repeat_days])
            vibe_str = '振动关' if not alarm.vibrate else f'振动{alarm.vibrate_strength}'
            sound_str = '铃声关' if not alarm.sound else '铃声开'
            snooze_info = f' 贪睡{alarm.snooze_minutes}分'
            lbl = Label(
                text=f'[b]{alarm.hour:02d}:{alarm.minute:02d}[/b] {days_str}  {vibe_str} {sound_str}{snooze_info}',
                markup=True, halign='left', valign='middle', size_hint_x=0.6,
                font_name=FONT_PATH)
            switch = Switch(active=alarm.enabled, size_hint_x=0.15)
            switch.bind(active=lambda s, val, a=alarm: self.toggle_alarm(a, val))
            del_btn = Button(text='X', size_hint_x=0.15, font_name=FONT_PATH)
            del_btn.bind(on_release=lambda x, a=alarm: self.delete_alarm(a))
            item.add_widget(lbl)
            item.add_widget(switch)
            item.add_widget(del_btn)
            alarm_list.add_widget(item)

    def toggle_alarm(self, alarm, value):
        alarm.enabled = value
        self.save_alarms()

    def delete_alarm(self, alarm):
        self.alarms.remove(alarm)
        self.save_alarms()
        self.refresh_alarm_list()

    def show_add_dialog(self):
        # 主弹窗内容（可滚动）
        main_content = BoxLayout(orientation='vertical', spacing=5, padding=5)

        scroll_content = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        # 小时
        row_h = BoxLayout(size_hint_y=None, height='42dp')
        row_h.add_widget(Label(text='小时 (0-23)', size_hint_x=0.35, font_name=FONT_PATH))
        hour_input = TextInput(text='7', input_filter='int', multiline=False, font_name=FONT_PATH, size_hint_x=0.65)
        row_h.add_widget(hour_input)
        scroll_content.add_widget(row_h)

        # 分钟
        row_m = BoxLayout(size_hint_y=None, height='42dp')
        row_m.add_widget(Label(text='分钟 (0-59)', size_hint_x=0.35, font_name=FONT_PATH))
        minute_input = TextInput(text='30', input_filter='int', multiline=False, font_name=FONT_PATH, size_hint_x=0.65)
        row_m.add_widget(minute_input)
        scroll_content.add_widget(row_m)

        # 重复日
        row_days = BoxLayout(orientation='vertical', size_hint_y=None, height='75dp', spacing=2)
        lbl_day = Label(text='重复日', size_hint_y=None, height='20dp', font_name=FONT_PATH, halign='left', valign='middle')
        lbl_day.bind(size=lbl_day.setter('text_size'))
        row_days.add_widget(lbl_day)
        days_layout = BoxLayout(spacing=5, size_hint_y=None, height='44dp')
        day_buttons = []
        for i, day in enumerate(['一','二','三','四','五','六','日']):
            btn = Button(text=day, size_hint_y=None, height=40, font_name=FONT_PATH)
            btn.day_index = i
            btn.selected = False
            btn.background_color = (0.7, 0.7, 0.7, 1)
            btn.bind(on_release=self.toggle_day_btn)
            day_buttons.append(btn)
            days_layout.add_widget(btn)
        row_days.add_widget(days_layout)
        scroll_content.add_widget(row_days)

        # 振动
        row_v = BoxLayout(size_hint_y=None, height='42dp')
        row_v.add_widget(Label(text='振动', size_hint_x=0.35, font_name=FONT_PATH))
        vibrate_switch = Switch(active=True, size_hint_x=0.65)
        row_v.add_widget(vibrate_switch)
        scroll_content.add_widget(row_v)

        # 强度
        row_s = BoxLayout(size_hint_y=None, height='42dp')
        row_s.add_widget(Label(text='强度 (1~5)', size_hint_x=0.35, font_name=FONT_PATH))
        strength_slider = Slider(min=1, max=5, value=3, step=1, size_hint_x=0.65)
        row_s.add_widget(strength_slider)
        scroll_content.add_widget(row_s)

        # 铃声
        row_snd = BoxLayout(size_hint_y=None, height='42dp')
        row_snd.add_widget(Label(text='铃声', size_hint_x=0.35, font_name=FONT_PATH))
        sound_switch = Switch(active=True, size_hint_x=0.65)
        row_snd.add_widget(sound_switch)
        scroll_content.add_widget(row_snd)

        # 贪睡时间
        row_snz = BoxLayout(size_hint_y=None, height='42dp')
        row_snz.add_widget(Label(text='贪睡时间 (分)', size_hint_x=0.35, font_name=FONT_PATH))
        snooze_slider = Slider(min=1, max=30, value=5, step=1, size_hint_x=0.65)
        row_snz.add_widget(snooze_slider)
        scroll_content.add_widget(row_snz)

        scroll_view = ScrollView(size_hint_y=0.85)
        scroll_view.add_widget(scroll_content)

        btn_save = Button(text='保存', size_hint_y=0.15, font_name=FONT_PATH)

        main_content.add_widget(scroll_view)
        main_content.add_widget(btn_save)

        popup = Popup(title='新建闹钟', content=main_content,
                      size_hint=(0.9, 0.75), auto_dismiss=False,
                      title_font=FONT_PATH)
        btn_save.bind(on_release=lambda x: self.add_alarm(
            hour_input.text,
            minute_input.text,
            [btn.day_index for btn in day_buttons if btn.selected],
            vibrate_switch.active,
            int(strength_slider.value),
            sound_switch.active,
            int(snooze_slider.value),
            popup
        ))
        popup.open()

    def toggle_day_btn(self, btn):
        btn.selected = not btn.selected
        btn.background_color = (0.2, 0.6, 0.9, 1) if btn.selected else (0.7, 0.7, 0.7, 1)

    def add_alarm(self, hour_str, minute_str, repeat_days, vibrate, vibrate_strength,
                  sound, snooze_minutes, popup):
        try:
            hour = int(hour_str)
            minute = int(minute_str)
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError
        except:
            notification.notify(title='错误', message='小时0-23，分钟0-59')
            return
        new_alarm = Alarm(hour, minute, repeat_days,
                          vibrate=vibrate, vibrate_strength=vibrate_strength,
                          sound=sound, snooze_minutes=snooze_minutes)
        self.alarms.append(new_alarm)
        self.save_alarms()
        self.refresh_alarm_list()
        popup.dismiss()

    def load_alarms(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.alarms = [Alarm.from_dict(d) for d in data]

    def save_alarms(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([a.to_dict() for a in self.alarms], f, indent=2)

if __name__ == '__main__':
    AlarmApp().run()