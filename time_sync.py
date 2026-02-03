import ntptime
from machine import RTC
import time
import asyncio

rtc = RTC()
TIME_SYNCED = False

# --- Асинхронная задача для синхронизации времени ---
async def sync_time_ntp(ntp_server='pool.ntp.org', sync_interval=3600): # Обновлять раз в час (3600 сек)
    while True:
        try:
            print("Попытка синхронизации времени с NTP...")
            ntptime.host = ntp_server
            ntptime.settime() # Устанавливает время системы из NTP
            asyncio.sleep(1)  # Небольшая пауза, чтобы дать системе время обновить часы
            # Копируем системное время в аппаратный RTC машины
            # tm = time.localtime()   # Получаем текущее время
            # The 8-tuple for RTC has the following format: (year, month, day, weekday, hours, minutes, seconds, subseconds)
            # rtc.datetime(tm)  # Устанавливаем время в аппаратный RTC
            # asyncio.sleep(1)  # Небольшая пауза, чтобы дать системе время обновить часы
            print(f"NTP Sync OK")
            print(f"System time: {time.localtime()}")
            print(f"RTC time: {rtc.datetime()}")
            global TIME_SYNCED
            TIME_SYNCED = True
        except Exception as e:
            print(f"NTP Sync Failed: {e}")
        # Ждем интервал перед следующей синхронизацией
        if TIME_SYNCED:
            await asyncio.sleep(sync_interval)
        else:
            await asyncio.sleep(60)  # Если не синхронизировано, пробуем снова через минуту

