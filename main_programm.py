import asyncio

import time
import time_sync  # импортируем модуль синхронизации времени
from machine import Pin, I2C

# global broker
# from primitives.broker import broker

from logic import DOut
import hw
# from hal.cpu_temp import CpuTemp
# from hal.htu21d_mc import HTU21D
# from hal.blinker_async import Blinker
from hal.blinker_async_simple import Blinker
from hal.myWDT import wdt
from web_app import build_web_app	# веб-приложение

# --------- загрузка пользовательского кода, если он есть ----------
user_code_loaded = False
try:
    import usercode
    user_code_loaded = True
    print("Пользовательский код загружен.")
except ImportError:
    print("Пользовательский код не найден, пропускаем.")
    pass  # нет пользовательского кода

# запуск датчика HTU21D
# scl_pin = Pin(22, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
# sda_pin = Pin(23, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
# i2c = I2C(1, scl=Pin(4), sda=Pin(5), freq=100000)
# hw.htu21d_sensor = HTU21D(i2c, read_delay=10)  # read_delay=60 for normal operation

hw.LAMP = DOut(27)

# -------- запуск пользовательского кода ----------
if user_code_loaded:
    usercode.onstart()
    

# --- Задача синхронизации времени ---
time_sync_task = asyncio.create_task(time_sync.sync_time_ntp())

# ----------- создаём веб-сервер ----------
web_app = build_web_app()
server_task = asyncio.create_task(
    web_app.start_server(host='0.0.0.0', port=80, debug=True)
)
hw._wdt_test_flag = False

blinker = Blinker(Pin(2, Pin.OUT), interval=0.5)  # Пин 2 для простого блинкера

async def main():
    # ждём первого измерения
    last_call_time = time.ticks_ms() # <-- Запоминаем время старта

    while True:
        await asyncio.sleep_ms(100)
        if not hw._wdt_test_flag:
            wdt.feed()
        else:
            print("Флаг WDT test установлен, не кормим WDT! Скоро сработает таймаут...")
        if user_code_loaded:

            try:
                # print("DEBUG: Calling app.normal()") # <-- Отладка
                usercode.normal(time.ticks_diff(time.ticks_ms(), last_call_time)) # <-- Передаем dt_ms в функцию
                
            except Exception as e:
                print(f"DEBUG: Error calling app.normal(): {e}")
                pass
            last_call_time = time.ticks_ms() # <-- Обновляем время последнего вызова

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Остановлено пользователем")
    blinker.stop()
    web_app.shutdown()
    if user_code_loaded:
         usercode.onstop() # <- Вызов onstop при прерывании
# Очистка ресурсов при необходимости
