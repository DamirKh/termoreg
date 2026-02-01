import asyncio
# import aioprof
# aioprof.enable()

import time
from machine import Pin, SoftI2C, I2C

from logic import switch_ladder
from logic import DOut
import hw
from hal.cpu_temp import CpuTemp
from hal.htu21d_mc import HTU21D
from hal.blinker_async import Blinker
from hal.myWDT import wdt
from web_app import build_web_app	# наше веб-приложение

user_code_loaded = False
try:
    import usercode
    user_code_loaded = True
except ImportError:
    print("Пользовательский код не найден, пропускаем.")
    pass  # нет пользовательского кода


# --------- настройка I2C ----------
# Hardware I2C bus
# There are two hardware I2C peripherals with identifiers 0 and 1. Any available output-capable pins can be used for SCL and SDA but the defaults are given below.

#		I2C(0)	I2C(1)
#scl	18		25
#sda	19		26
#i2c = I2C(0)

# --------- запуск датчика температуры кристалла ----------
sensor = CpuTemp(interval=5)

# запуск датчика HTU21D
# scl_pin = Pin(22, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
# sda_pin = Pin(23, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
i2c = I2C(1, scl=Pin(4), sda=Pin(5), freq=100000)
hw.htu21d_sensor = HTU21D(i2c, read_delay=10)  # read_delay=60 for normal operation

# -------- запуск пользовательского кода ----------
if user_code_loaded:
        usercode.onstart()
    
# --------- настройка индикатора ----------
blinker = Blinker(Pin(48, Pin.OUT))

# ----------- создаём веб-сервер ----------
web_app = build_web_app(hw.htu21d_sensor)
server_task = asyncio.create_task(
    web_app.start_server(host='0.0.0.0', port=80, debug=True)
)

# Switches
hw.BTN_ON = switch_ladder.Switch_ladder(Pin(7, Pin.IN), inverted=False)
hw.BTN_OFF = switch_ladder.Switch_ladder(Pin(6, Pin.IN), inverted=False)
hw._wdt_test_flag = False


async def main():
    # ждём первого измерения
    await sensor
    print("Первое измерение готово")
    # await htu21d_sensor
    # print("Первое измерение HTU21D готово")

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