import os
import asyncio
import time
import machine # <-- Добавить импорт для доступа к RTC
from micropython import const
from primitives.broker import broker
from microdot import Microdot, send_file
from microdot.websocket import with_websocket
import ujson
import gc
# import aioprof

import hw
import g

# Импортируем usercode, чтобы получить доступ к get_last_output
# import usercode

EPOCH_2000_TO_1970 = const(946684800)

# callback, который брокер будет звать при публикации
async def sender_callback(tag, val, ws):
    print(f'WS sending tag {tag} val {val}')
    try:
        payload = {}
        payload['tag'] = tag
        payload['val'] = val
        payload['ts'] = time.time() + EPOCH_2000_TO_1970 # <-- Преобразуем к эпохе 1970
        await ws.send(ujson.dumps(payload))
    except Exception as e:
        print('WS send error:', e)
        pass   # сокет мёртв – удалим ниже

def build_web_app():
    app = Microdot()

    @app.route('/ws/tags')
    @with_websocket
    async def tags_ws(request, ws):
        """
        Клиент сам выбирает теги:
        +tag_name  - подписаться
        -tag_name  - отписаться
        """
        global broker
        my_topics = set()          # теги, на которые подписан этот сокет

        try:
            while True:
                raw = await ws.receive()          # '+TagName' / '-TagName'
                if not raw or len(raw) < 2:
                    continue
                op, topic = raw[0], raw[1:]
                if op == '+':                     # подписаться
                    if topic not in my_topics:
                        print(f'WS subscribing to topic: {topic}')
                        broker.subscribe(topic, sender_callback, ws)
                        my_topics.add(topic)
                elif op == '-':                   # отписаться
                    if topic in my_topics:
                        broker.unsubscribe(topic, sender_callback, ws)
                        my_topics.discard(topic)
                g.trigger_all_tags()  # сразу шлём актуальные значения
        except Exception as e:
            print('WS client gone:', e)
        finally:
            # отписываемся от всего при отключении клиента
            for t in my_topics:
                broker.unsubscribe(t, sender_callback, ws)

    # @app.get('/favicon.ico')
    # async def favicon(request):
    #     return send_file('/www/favicon.ico.gz', compressed=True)

    @app.get('/')
    async def index(request):
        return send_file('/www/index.html.gz', compressed=True)
    
    # @app.get('/ui')
    # async def ui_page(request):
    #     return send_file('/www/interactive_example.svg')

    # @app.get('/hw')
    # async def hw_page(request):
    #     return send_file('/www/hw.html.gz', compressed=True)
    
    # @app.get('/prof')
    # async def profiler_page(request):
    #     return send_file('/www/prof.html.gz', compressed=True)
    #     # return send_file('/www/prof.html')
 
    # @app.route('/diag')
    # async def diag(req):
    #     # температура кристалла
    #     temp = hw.htu21d_sensor.temperature
    #     # свободная память
    #     free_mem = gc.mem_free()
    #     # IP клиента
    #     client_ip = req.client_addr[0]
    #     # заголовок браузера
    #     user_agent = req.headers.get('User-Agent', 'неизвестен')

    #     # --- Получаем строку из app.normal() ---
    #     user_task_status = usercode.get_last_output()

    #     # --- Проверяем состояние флага WDT ---
    #     wdt_enabled = 'wdt.flag' in os.listdir()
    #     wdt_status_text = "ВКЛЮЧЕН" if wdt_enabled else "ОТКЛЮЧЕН"
    #     wdt_button_text = "СБРОСИТЬ (Отключить WDT)" if wdt_enabled else "УСТАНОВИТЬ (Включить WDT)"
    #     wdt_action_param = "unset" if wdt_enabled else "set"

    #     html = f"""<!doctype html>
    #     <html>
    #     <head>
    #     <meta charset="utf-8">
    #     <title>Диагностика</title>
    #     <link rel="icon" href="/favicon.ico">
    #     </head>
    #     <body>
    #     <h1>Диагностика ESP32</h1>
    #     <ul>
    #         <li>Температура чипа: {temp:.1f} °C</li>
    #         <li>Свободная RAM: {free_mem} байт</li>
    #         <li>IP клиента: {client_ip}</li>
    #         <li>User-Agent: {user_agent}</li>
    #         <li>Состояние User task: {user_task_status}</li>
    #         <!-- Добавляем состояние WDT -->
    #         <li>Состояние WDT: <strong>{wdt_status_text}</strong></li>
    #     </ul>
    #     <!-- Форма для переключения состояния WDT -->
    #     <form action="/remove_wdt" method="get" style="margin-top: 10px;">
    #         <input type="hidden" name="action" value="{wdt_action_param}">
    #         <button type="submit">{wdt_button_text}</button>
    #     </form>
    #     <!-- Старая форма для теста (опционально) -->
    #     <form action="/api/wdt_test" method="post" style="margin-top: 20px;">
    #         <button type="submit">Trigger WDT Test (DANGEROUS!)</button>
    #     </form>
    #     <a href="/">На главную</a>
    #     </body>
    #     </html>"""
    #     return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    # # --- НОВЫЙ маршрут для диагностики WDT ---
    # @app.post('/api/wdt_test') # Используем POST для действий, изменяющих состояние
    # def api_wdt_test(request):
    #     print("Получен запрос для диагностики WDT!")
    #     # Устанавливаем флаг
    #     hw._wdt_test_flag = True
    #     # Возвращаем ответ
    #     return {"status": "WDT test flag set. ESP32 should restart soon due to WDT timeout."}, 200, {'Content-Type': 'application/json'}

    # --- маршрут GET для управления wdt.flag ---
    @app.get('/remove_wdt')
    def manage_wdt_flag(request):
        print("Получен запрос GET для управления WDT (wdt.flag).")
        
        # Получаем параметр action из строки запроса
        action = request.args.get('action', '').lower()

        # Определяем, что делать
        flag_exists = 'wdt.flag' in os.listdir()

        if action == 'set':
            # Цель: установить флаг
            if flag_exists:
                # Флаг уже установлен
                print("Флаг wdt.flag уже установлен.")
                html_response = """<!DOCTYPE html>
                    <html>
                    <head><title>WDT Already Enabled</title></head>
                    <body>
                    <h1>WDT Already Enabled</h1>
                    <p>The file 'wdt.flag' already exists.</p>
                    <a href="/diag">Go back to Diag</a>
                    </body>
                    </html>"""
                return html_response, 200, {'Content-Type': 'text/html; charset=utf-8'}
            else:
                # Флага нет, нужно создать
                try:
                    # Создаем файл wdt.flag (пустой)
                    with open('wdt.flag', 'w') as f:
                        f.write("""This file is the flag to start Watch Dog Timer
                            Content of this file does not matter, only it's name.
                            if "wdt.flag" exist - Watch Dog Timer will be started.
                            To remove this flag during microdot server is running go to
                            http://<IP_ADRESS>/remove_wdt
                                """)
                    print("Флаг wdt.flag установлен.")
                    html_response = """<!DOCTYPE html>
                        <html>
                        <head><title>WDT Enabled</title></head>
                        <body>
                        <h1>WDT Enabled Successfully</h1>
                        <p>The file 'wdt.flag' has been created.</p>
                        <p>Please restart the ESP32 for changes to take effect.</p>
                        <a href="/diag">Go back to Diag</a>
                        </body>
                        </html>"""
                    return html_response, 200, {'Content-Type': 'text/html; charset=utf-8'}
                except OSError as e:
                    print(f"Ошибка при создании wdt.flag: {e}")
                    html_response = f"""<!DOCTYPE html>
                        <html>
                        <head><title>Error Enabling WDT</title></head>
                        <body>
                        <h1>Error Enabling WDT</h1>
                        <p>Failed to create 'wdt.flag': {e}</p>
                        <a href="/diag">Go back to Diag</a>
                        </body>
                        </html>"""
                    return html_response, 500, {'Content-Type': 'text/html; charset=utf-8'}

        else: # если action не 'set', то предполагаем, что это 'unset'
            # Цель: сбросить флаг
            if flag_exists:
                # Флаг есть, нужно удалить
                try:
                    os.unlink('wdt.flag')
                    print("Флаг wdt.flag сброшен (файл удален).")
                    html_response = """<!DOCTYPE html>
                        <html>
                        <head><title>WDT Disabled</title></head>
                        <body>
                        <h1>WDT Disabled Successfully</h1>
                        <p>The file 'wdt.flag' has been deleted.</p>
                        <p>Please restart the ESP32 for changes to take effect.</p>
                        <a href="/diag">Go back to Diag</a>
                        </body>
                        </html>"""
                    return html_response, 200, {'Content-Type': 'text/html; charset=utf-8'}
                except OSError as e:
                    print(f"Ошибка при удалении wdt.flag: {e}")
                    html_response = f"""<!DOCTYPE html>
                        <html>
                        <head><title>Error Disabling WDT</title></head>
                        <body>
                        <h1>Error Disabling WDT</h1>
                        <p>Failed to delete 'wdt.flag': {e}</p>
                        <a href="/diag">Go back to Diag</a>
                        </body>
                        </html>"""
                    return html_response, 500, {'Content-Type': 'text/html; charset=utf-8'}
            else:
                # Флага нет, он уже "сброшен"
                print("Флаг wdt.flag уже сброшен (файл не найден).")
                html_response = """<!DOCTYPE html>
                    <html>
                    <head><title>WDT Already Disabled</title></head>
                    <body>
                    <h1>WDT Was Already Disabled</h1>
                    <p>The file 'wdt.flag' was not found.</p>
                    <a href="/diag">Go back to Diag</a>
                    </body>
                    </html>"""
                return html_response, 200, {'Content-Type': 'text/html; charset=utf-8'}

    # @app.get('/api/data')
    # async def api_data(request):
    #     # hw.htu21d_sensor – это живой HTU21D, поля уже обновляются в фоне
    #     return ujson.dumps({
    #         'temperature': hw.htu21d_sensor.temperature,
    #         'humidity': hw.htu21d_sensor.humidity
    #     }), 200, {'Content-Type': 'application/json'}
    
    @app.get('/api/hw')
    async def api_hw(request):
        # Получаем все атрибуты модуля hw через его __dict__
        hw_dict = hw.__dict__
        # Фильтруем, исключая служебные имена (__name__, __file__, и т.д.)
        filtered_hw_dict = {k: v for k, v in hw_dict.items() if not k.startswith('__')}
        # Преобразуем значения к строке
        hw_info = {k: str(v) for k, v in filtered_hw_dict.items()}

        # Возвращаем весь отфильтрованный и преобразованный словарь
        return ujson.dumps(hw_info)
    
    # @app.get('/api/profiler')
    # async def api_profiler(request):
    #     raw_json_str = ujson.dumps(aioprof.timing)
    #     if request.args.get('reset', '').lower() == 'true':
    #         print("Сброс данных aioprof по запросу API.")  # Логирование
    #         aioprof.reset()
    #     # Чтобы microdot корректно вернул JSON-строку как тело ответа,
    #     # нужно указать тип содержимого.
    #     return raw_json_str, 200, {'Content-Type': 'application/json'}

    # --- маршрут для установки времени ---
    @app.post('/set_time_from_hmi')
    async def set_time_from_hmi(request):
        try:
            # Ожидаем JSON с полем 'timestamp' (в формате JavaScript, т.е. миллисекунды с 1970)
            # Пример: {"timestamp": 1704067200000} (это 01.01.2024 00:00:00 UTC в мс)
            data = request.json
            if not data or 'timestamp' not in data:
                return {"error": "Missing 'timestamp' in request body"}, 400

            js_timestamp_ms = data['timestamp']

            # Преобразуем миллисекунды в секунды
            js_timestamp_s = js_timestamp_ms / 1000.0

            # Преобразуем timestamp из эпохи 1970 в эпоху 2000 для ESP32
            esp_timestamp_s = js_timestamp_s - EPOCH_2000_TO_1970

            # Проверим, что результат разумный (например, не отрицательный)
            if esp_timestamp_s < 0:
                return {"error": "Calculated ESP timestamp is negative"}, 400
            # Устанавливаем время в RTC
            rtc = machine.RTC()
            # time.gmtime возвращает (year, month, day, hour, minute, second, weekday, yearday)
            # weekday: 0 - Monday
            # rtc.datetime принимает (year, month, day, weekday, hour, minute, second, subsecond)
            # weekday: 0 - Monday
            # Порядок отличается: gmtime: (y, m, d, h, min, sec, wd, yd) -> rtc.datetime: (y, m, d, wd, h, min, sec, ss)
            tm = time.gmtime(int(esp_timestamp_s))
            rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))

            print(f"Time set via HMI: {time.localtime(int(esp_timestamp_s))}")
            return {"status": "success", "new_time_esp_epoch_s": int(esp_timestamp_s)}

        except ValueError as ve:
            print(f"ValueError in set_time_from_hmi: {ve}")
            return {"error": f"Invalid timestamp value: {ve}"}, 400
        except OSError as oe:
            # Может возникнуть, если RTC не доступен или переданы неправильные значения
            print(f"OSError in set_time_from_hmi: {oe}")
            return {"error": f"Failed to set RTC: {oe}"}, 500
        except Exception as e:
            print(f"Unexpected error in set_time_from_hmi: {e}")
            return {"error": "Internal server error"}, 500
    
    @app.post('/set_lamp_state')
    async def set_lamp_state(request):
        try:
            data = request.json
            if not data or 'state' not in data:
                return {"error": "Missing 'state' in request body"}, 400

            state = data['state']
            if not isinstance(state, bool):
                return {"error": "'state' must be a boolean"}, 400
            
            if state:
                g.DWTAG_COMMAND_LAMP_ON.VALUE = True
                print(f"Lamp state set to ON:")
                return {"status": "success", "lamp_state": True}
            else:
                g.DWTAG_COMMAND_LAMP_OFF.VALUE = True
                print(f"Lamp state set to OFF")
                return {"status": "success", "lamp_state": False}
        except Exception as e:
            print(f"Unexpected error in set_lamp_state: {e}")
            return {"error": "Internal server error"}, 500


    return app
