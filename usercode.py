import hw
import g
import time_sync

# Глобальная переменная для хранения последнего вывода функции normal
last_normal_output = "User task ещё не запускался."

# переменные, которые хотим сохранять между вызовами normal
last_temp = None

def normal(dt_ms): # <-- Принимает время в миллисекундах с прошлого вызова
    global last_normal_output, last_temp
    output_string = f"User task normal operation, time since last call: {dt_ms} ms"
    g.TAG_TEMPERATURE.VALUE = hw.htu21d_sensor.temperature
    if last_temp is not None:
        output_string += f", ΔT: {hw.htu21d_sensor.temperature - last_temp:.2f} °C" 
        if hw.htu21d_sensor.temperature-last_temp < 0:
            g.TAG_HEATER_STATUS.VALUE = False  # Выключаем нагреватель
        if hw.htu21d_sensor.temperature-last_temp > 0:
            g.TAG_HEATER_STATUS.VALUE = True   # Включаем нагреватель
    last_temp = hw.htu21d_sensor.temperature
    last_normal_output = output_string # <-- Сохраняем строку в глобальной переменной

def get_last_output():
    """Функция для получения последнего состояния из app.py"""
    global last_normal_output
    return last_normal_output

def onstart():
    print("User task start")

def onstop():
    print("User task stop")

