import os
from machine import WDT

class FakeWDT:
    def feed(self):
        pass

# запускаем WDT только в случае если есть файл "wdt.flag"
if 'wdt.flag' in os.listdir():
    print("Файл wdt.flag найден, запускаем WDT")
    wdt = WDT(timeout=5000)  # 5 секунд
else:
    print("Файл wdt.flag не найден, WDT не запущен")
    wdt = FakeWDT()
