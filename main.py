#
print("Main starting")

import uasyncio as asyncio
import struct
import gc
import network
import machine
import time
import ntptime
import esp32
import onewire
import ds18x20
import dht
from tempsheet import t_sheet
from wserver import create_app

import array

# === Настройки логгера ===
LOG_INTERVAL_SEC = 15 * 60  # 15 минут
MAX_RECORDS = 7 * 24 * 4   # 7 дней по 4 измерения в час

# Буферы: timestamp (I), temp (h), hum (h)
log_timestamps = array.array('I', [0] * MAX_RECORDS)  # unsigned int (4 байта)
log_temps = array.array('h', [0] * MAX_RECORDS)       # signed short (2 байта)
log_hums = array.array('h', [0] * MAX_RECORDS)        # signed short (2 байта)

log_index = 0      # текущая позиция для записи
log_count = 0      # сколько записей реально есть
last_log_time = 0  # время последней записи (в секундах)


def log_measurement(temp, hum):
    global log_index, log_count, last_log_time
    now = time.time()  # Unix timestamp

    # Сохраняем в десятых долях
    temp_int = int(round(temp * 10)) if temp is not None else -32768  # min для 'h'
    hum_int = int(round(hum * 10)) if hum is not None else -32768

    log_timestamps[log_index] = now
    log_temps[log_index] = temp_int
    log_hums[log_index] = hum_int

    log_index = (log_index + 1) % MAX_RECORDS
    if log_count < MAX_RECORDS:
        log_count += 1

    last_log_time = now
    print(f"Logged: {now} → T={temp}, H={hum}")

    save_log()


def get_history():
    """Возвращает последние записи в виде списка [[ts, temp, hum], ...]"""
    history = []
    start_idx = (log_index - log_count) % MAX_RECORDS if log_count > 0 else 0
    for i in range(log_count):
        idx = (start_idx + i) % MAX_RECORDS
        ts = log_timestamps[idx]
        temp = round(log_temps[idx] / 10.0, 1) if log_temps[idx] != -32768 else None
        hum = round(log_hums[idx] / 10.0, 1) if log_hums[idx] != -32768 else None
        history.append([ts, temp, hum])
    return history

# Пины
HEATER = machine.Pin(11, machine.Pin.OUT)
LIGHT = machine.Pin(12, machine.Pin.OUT)
HEATER.off()
LIGHT.on()

# Датчики
my_dht = dht.DHT22(machine.Pin(6))
ds_sensor = ds18x20.DS18X20(onewire.OneWire(machine.Pin(7)))
roms = ds_sensor.scan()

print('Found DS devices: ', roms)
if len(roms):
    ds_sensor.convert_temp()
    time.sleep_ms(300)
else:
    print("No temperature sensors found!")

# Глобальные данные (доступны из веб-обработчиков)
state = {
    "temp_dht": None,
    "hum_dht": None,
    "temp_ds": None,
    "mcu_temp": None,
    "heater_on": False,
    "light_on": False,
    "setpoint": 5.0,
    "synced": False,
    "datetime": (0, 0, 0, 0, 0, 0, 0, 0),
}


# Время включения света
ON_TIME = set(range(7, 22))  # 7–21 включительно

wlan = network.WLAN(network.STA_IF)
rtc = machine.RTC()

# зачем две следущие строки?
TEMP_SETPOINT = 5.
SYNCED = False

def get_setpoint(ymd):
    "уставка в соответствии с графиком повышения температуры"
    return(t_sheet.get(ymd, 5.0))  # if date is not in range use default setpoint 5

async def measure_sensors():
    """Опрос датчиков"""
    try:
        my_dht.measure()
        state["temp_dht"] = my_dht.temperature()
        state["hum_dht"] = my_dht.humidity()
    except Exception as e:
        print("DHT error:", e)
        state["temp_dht"] = None
        state["hum_dht"] = None

    if roms:
        try:
            ds_sensor.convert_temp()
            await asyncio.sleep_ms(800)  # DS18B20 требует до 750 мс
            state["temp_ds"] = ds_sensor.read_temp(roms[0])
        except Exception as e:
            print("DS18B20 error:", e)
            state["temp_ds"] = None
    else:
        state["temp_ds"] = None

    state["mcu_temp"] = esp32.mcu_temperature()

gisteresys_counter = 2  # переносим из main()

async def control_loop():
    print('Запуск цикла управления...')
    global gisteresys_counter
    while True:
        await measure_sensors()

        # Обновляем время и уставку
        state["datetime"] = rtc.datetime()
        year, month, day = state["datetime"][0:3]
        state["setpoint"] = get_setpoint((year, month, day))

        # >>> ДОБАВЛЕНО: местное время как строка <<<
        (y, mo, d, wd, h, mi, s, ss) = state["datetime"]
        local_h = (h + 4) % 24
        state["local_time_str"] = f"{y}-{mo:02d}-{d:02d} {local_h:02d}:{mi:02d}:{s:02d}"

        # Управление нагревателем
        temp = state["temp_dht"]
        if temp is not None:
            if temp > state["setpoint"] and state["heater_on"]:
                gisteresys_counter += 1
            elif temp < state["setpoint"] and not state["heater_on"]:
                gisteresys_counter -= 1

            if gisteresys_counter > 3:
                HEATER.off()
                state["heater_on"] = False
            elif gisteresys_counter < 1:
                HEATER.on()
                state["heater_on"] = True

        # Управление светом
        local_hour = (state["datetime"][4] + 4) % 24
        if state["synced"] and local_hour in ON_TIME:
            LIGHT.on()
            state["light_on"] = True
        else:
            LIGHT.off()
            state["light_on"] = False

        # Синхронизация один раз в час

        minutes = state["datetime"][5]
        if h==0 and minutes == 30 and wlan.isconnected():
            await sync_time(force=True)

        # === ЛОГИРОВАНИЕ КАЖДЫЕ 15 МИНУТ ===
        current_time = time.time()
        if current_time - last_log_time >= LOG_INTERVAL_SEC:
            log_measurement(state["temp_dht"], state["hum_dht"])

        # Отладка
        print("State:", state["temp_dht"], state["heater_on"], state["setpoint"])
        print("Free mem:", free())

        # Ждём ~60 секунд
        await asyncio.sleep(60)

def free(full=False):
    gc.collect()
    F = gc.mem_free()
    A = gc.mem_alloc()
    T = F+A
    P = '{0:.2f}%'.format(F/T*100)
    if not full: return P
    else : return ('Total:{0} Free:{1} ({2})'.format(T,F,P))


async def sync_time(force = False):
    if not force and state["synced"]:
        return
    print("Syncing time...")
    for _ in range(3):
        try:
            ntptime.settime()
            state["synced"] = True
            print("Time synced!")
            return
        except Exception as e:
            print("NTP error:", e)
            await asyncio.sleep(5)
    print("Failed to sync time")

app = create_app(state, get_history)
async def web_server():
    print('Запуск WEB сервера...')
    app.run(host='0.0.0.0', port=80, loop_forever=False)

def save_log():
    try:
        # Вычисляем общий размер данных
        # log_count (2) + timestamps (4*N) + temps (2*N) + hums (2*N)
        total_size = 2 + (4 + 2 + 2) * MAX_RECORDS
        buf = bytearray(total_size)

        # Записываем log_count
        struct.pack_into('<H', buf, 0, log_count)

        # Записываем массивы
        offset = 2
        for i in range(MAX_RECORDS):
            struct.pack_into('<I', buf, offset, log_timestamps[i])
            offset += 4
        for i in range(MAX_RECORDS):
            struct.pack_into('<h', buf, offset, log_temps[i])
            offset += 2
        for i in range(MAX_RECORDS):
            struct.pack_into('<h', buf, offset, log_hums[i])
            offset += 2

        with open('/log.bin', 'wb') as f:
            f.write(buf)
        print("Log saved")
    except Exception as e:
        print("Save log error:", e)

def load_log():
    global log_index, log_count
    try:
        with open('/log.bin', 'rb') as f:
            data = f.read()

        if len(data) < 2 + (4 + 2 + 2) * MAX_RECORDS:
            raise ValueError("File too small")

        # Читаем log_count
        log_count = struct.unpack_from('<H', data, 0)[0]
        if not (0 <= log_count <= MAX_RECORDS):
            log_count = 0

        # Читаем массивы
        offset = 2
        for i in range(MAX_RECORDS):
            log_timestamps[i] = struct.unpack_from('<I', data, offset)[0]
            offset += 4
        for i in range(MAX_RECORDS):
            log_temps[i] = struct.unpack_from('<h', data, offset)[0]
            offset += 2
        for i in range(MAX_RECORDS):
            log_hums[i] = struct.unpack_from('<h', data, offset)[0]
            offset += 2

        log_index = log_count % MAX_RECORDS
        print(f"Loaded {log_count} records")
    except Exception as e:
        print("No saved log or load error:", e)
        # Сбрасываем буферы
        for i in range(MAX_RECORDS):
            log_timestamps[i] = 0
            log_temps[i] = 0
            log_hums[i] = 0
        log_count = 0
        log_index = 0

async def main():
    # Запускаем задачи
    load_log()
    asyncio.create_task(web_server())
    await sync_time(force=True)
    asyncio.create_task(control_loop())

    # Бесконечный цикл (можно добавить watchdog и т.п.)
    while True:
        await asyncio.sleep(10)

# Запуск
print("Starting async main...")
asyncio.run(main())
