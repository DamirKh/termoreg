import hw
import g
# import time_sync

from logic import ON, OFF
from logic import Timer
from logic import Counter
from logic import Seq
from logic import Spark
from logic import Revert
from logic import OneShoot, JK
import time

# from logic import tag
# from logic import PID

# ##############################  timers, counters, sparks
T_Light = Timer(preset=10_000)
MyLAMP = JK()

#  расписание для лампы: включать с 7:00 до 23:00, иначе по умолчанию выключено
# g.schedule

# Глобальная переменная для хранения последнего вывода функции normal
last_normal_output = "User task ещё не запускался."

# переменные, которые хотим сохранять между вызовами normal
last_temp = None


def normal(dt_ms):  # <-- Принимает время в миллисекундах с прошлого вызова
    global last_normal_output, last_temp
    # Управление лампой
    nh = time.localtime()[3] + 4  # локальные часы
    nm = time.localtime()[4]  # минуты

    lamp_schedule_state = g.schedule.is_active(nh, nm)
    #print(f"Lamp schedule state: {'ON' if lamp_schedule_state else 'OFF'}")

    MyLAMP.JUMP = g.DWTAG_COMMAND_LAMP_ON.VALUE
    MyLAMP.KILL = g.DWTAG_COMMAND_LAMP_OFF.VALUE or T_Light.DN
    g.UPTAG_COUNTDOWN_TIMER.VALUE = (T_Light.PRE - T_Light.ACC) / 1000 + 1
    T_Light.EN = MyLAMP.STATE
    hw.LAMP.STATE = MyLAMP.STATE or lamp_schedule_state
    g.UPTAG_LAMP_STATE.VALUE = hw.LAMP.STATE

    output_string = f"User task normal operation, time since last call: {dt_ms} ms"
    last_normal_output = output_string  # <-- Сохраняем строку в глобальной переменной

    g.DWTAG_COMMAND_LAMP_ON.VALUE = False  # Сброс команды после обработки
    g.DWTAG_COMMAND_LAMP_OFF.VALUE = False  # Сброс команды после обработки


def get_last_output():
    """Функция для получения последнего состояния из app.py"""
    global last_normal_output
    return last_normal_output


def onstart():
    print("User task start")


def onstop():
    print("User task stop")
