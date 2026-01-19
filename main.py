import asyncio
import time
from machine import Pin, I2C
from hal.cpu_temp import CpuTemp
from hal.blinker_async import Blinker
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

# --------- запуск датчика ----------
sensor = CpuTemp(interval=5)

if user_code_loaded:
        usercode.onstart()
    
# --------- настройка индикатора ----------
blinker = Blinker(Pin(48, Pin.OUT))

# ----------- создаём веб-сервер ----------
web_app = build_web_app(sensor)
server_task = asyncio.create_task(
    web_app.start_server(host='0.0.0.0', port=80, debug=True)
)

async def main():
    # ждём первого измерения
    await sensor
    print("Первое измерение готово")

    last_call_time = time.ticks_ms() # <-- Запоминаем время старта

    while True:
        await asyncio.sleep_ms(100)
        if user_code_loaded:

            try:
                # print("DEBUG: Calling app.normal()") # <-- Отладка
                usercode.normal(time.ticks_diff(time.ticks_ms(), last_call_time)) # <-- Передаем dt_ms в функцию
                
            except Exception as e:
                print(f"DEBUG: Error calling app.normal(): {e}")
                pass
            last_call_time = time.ticks_ms() # <-- Обновляем время последнего вызова


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановлено пользователем")
        blinker.stop()
        if user_code_loaded:
             usercode.onstop() # <- Вызов onstop при прерывании
    # Очистка ресурсов при необходимости