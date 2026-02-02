# --- Глобальная переменная для хранения состояния ---
import hw
import G

import logic.tag

# TAGs for data sending to web
TAG_TEMPERATURE = logic.tag.RealOutputTag("th", "{:-.2f}")
TAG_HEATER_STATUS = logic.tag.DiscreteOutputTag("heater_status")

last_normal_output = "User task ещё не запускался."

def normal(dt_ms): # <-- Принимает время в миллисекундах с прошлого вызова
    global last_normal_output
    output_string = f"User task normal operation, time since last call: {dt_ms} ms"
    TAG_TEMPERATURE.VALUE = hw.htu21d_sensor.temperature
    last_normal_output = output_string # <-- Сохраняем строку в глобальной переменной

def get_last_output():
    """Функция для получения последнего состояния из app.py"""
    global last_normal_output
    return last_normal_output

def onstart():
    print("User task start")

def onstop():
    print("User task stop")

