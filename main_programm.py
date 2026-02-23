import asyncio

import time, os
import time_sync  # импортируем модуль синхронизации времени
from machine import Pin, SoftI2C, RTC

# global broker
# from primitives.broker import broker

from logic import DOut
import hw, g
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
except ImportError as e:
    print("Пользовательский код не найден  или некорректен, пропускаем.")
    print(e)
    pass  # нет пользовательского кода

# запуск датчика HTU21D
# scl_pin = Pin(22, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
# sda_pin = Pin(23, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
# i2c = I2C(1, scl=Pin(4), sda=Pin(5), freq=100000)
# hw.htu21d_sensor = HTU21D(i2c, read_delay=10)  # read_delay=60 for normal operation

hw.LAMP = DOut(27, invert=False)

# -------- запуск пользовательского кода ----------
if user_code_loaded:
    usercode.onstart()
    

# --- синхронизации времени с аппаратными часами ---
# from hal.ds1307 import DS1307
# i2c0 = SoftI2C(scl=Pin(17), sda=Pin(16), freq=100000)
# ds1307rtc = DS1307(i2c0, 0x68)
# def _set_RTC_time_from_ds():
#     year, month, day, hours, minutes, seconds, weekday, _ = ds1307rtc.datetime
#     # RTC time tuple is
#     # year, month, day, weekday, hours, minutes, seconds, subseconds
#     RTC().datetime((year, month, day, weekday, hours, minutes, seconds, 0))
# print('\n LOCAL WALLCLOCK TIME: ')
# print('year, month, day, hours, minutes, seconds, weekday')
# print(ds1307rtc.datetime)
# _set_RTC_time_from_ds()

# --- Задача синхронизации времени ---
time_sync_task = asyncio.create_task(time_sync.sync_time_ntp())

from mdot_schedule import ScheduleApp
from schedule import Schedule
if 'schedule.hex' in os.listdir():
    print("Расписание найдено, пытаемся загрузить")
    try:
        with open('schedule.hex', 'r') as f:
            hex_data = f.read().strip()
            g.schedule = Schedule.from_hex(hex_data)
            print(f"Загружено расписание: {len(g.schedule)} активных минут")
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        g.schedule = Schedule()
else:
    g.schedule = Schedule()

sch_app = ScheduleApp(g.schedule)  # SubApp for schedule control
# ----------- создаём веб-сервер ----------
web_app = build_web_app()
web_app.mount(sch_app.app, '/schedule')
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
