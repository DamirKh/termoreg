import os
import asyncio
from time import localtime
from microdot import Microdot, send_file
from microdot.websocket import with_websocket
import ujson
import gc
import aioprof

import hw


# Импортируем usercode, чтобы получить доступ к get_last_output
import usercode


def build_web_app(sensor):
    app = Microdot()

    @app.route('/ws/tags')
    @with_websocket
    async def tags_ws(request, ws):
        """
        Send current server tags every second: temperature, time label
        """
        try:
            while True:
                t = localtime()
                payload = {
                    "th": sensor.temperature,
                    "timeLabel": "{:02}:{:02}:{:02}".format(t[3], t[4], t[5])
                }
                print(ujson.dumps(payload))
                await ws.send(ujson.dumps(payload))
                await asyncio.sleep(1)
        except Exception as e:
            print("WebSocket /ws/tags closed:", e)
            # client disconnected
            pass

    @app.get('/favicon.ico')
    async def favicon(request):
        return send_file('/www/favicon.ico.gz', compressed=True)

    @app.get('/')
    async def index(request):
        return send_file('/www/index.html.gz', compressed=True)
    
    @app.get('/ui')
    async def ui_page(request):
        return send_file('/www/interactive_example.svg')

    @app.get('/hw')
    async def hw_page(request):
        return send_file('/www/hw.html.gz', compressed=True)
    
    @app.get('/prof')
    async def profiler_page(request):
        return send_file('/www/prof.html.gz', compressed=True)
        # return send_file('/www/prof.html')
 
    @app.route('/diag')
    async def diag(req):
        # температура кристалла
        temp = sensor.temperature
        # свободная память
        free_mem = gc.mem_free()
        # IP клиента
        client_ip = req.client_addr[0]
        # заголовок браузера
        user_agent = req.headers.get('User-Agent', 'неизвестен')

        # --- Получаем строку из app.normal() ---
        user_task_status = usercode.get_last_output()

        # --- Проверяем состояние флага WDT ---
        wdt_enabled = 'wdt.flag' in os.listdir()
        wdt_status_text = "ВКЛЮЧЕН" if wdt_enabled else "ОТКЛЮЧЕН"
        wdt_button_text = "СБРОСИТЬ (Отключить WDT)" if wdt_enabled else "УСТАНОВИТЬ (Включить WDT)"
        wdt_action_param = "unset" if wdt_enabled else "set"

        html = f"""<!doctype html>
        <html>
        <head>
        <meta charset="utf-8">
        <title>Диагностика</title>
        <link rel="icon" href="/favicon.ico">
        </head>
        <body>
        <h1>Диагностика ESP32</h1>
        <ul>
            <li>Температура чипа: {temp:.1f} °C</li>
            <li>Свободная RAM: {free_mem} байт</li>
            <li>IP клиента: {client_ip}</li>
            <li>User-Agent: {user_agent}</li>
            <li>Состояние User task: {user_task_status}</li>
            <!-- Добавляем состояние WDT -->
            <li>Состояние WDT: <strong>{wdt_status_text}</strong></li>
        </ul>
        <!-- Форма для переключения состояния WDT -->
        <form action="/remove_wdt" method="get" style="margin-top: 10px;">
            <input type="hidden" name="action" value="{wdt_action_param}">
            <button type="submit">{wdt_button_text}</button>
        </form>
        <!-- Старая форма для теста (опционально) -->
        <form action="/api/wdt_test" method="post" style="margin-top: 20px;">
            <button type="submit">Trigger WDT Test (DANGEROUS!)</button>
        </form>
        <a href="/">На главную</a>
        </body>
        </html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    # --- НОВЫЙ маршрут для диагностики WDT ---
    @app.post('/api/wdt_test') # Используем POST для действий, изменяющих состояние
    def api_wdt_test(request):
        print("Получен запрос для диагностики WDT!")
        # Устанавливаем флаг
        hw._wdt_test_flag = True
        # Возвращаем ответ
        return {"status": "WDT test flag set. ESP32 should restart soon due to WDT timeout."}, 200, {'Content-Type': 'application/json'}


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

    @app.get('/api/data')
    async def api_data(request):
        # sensor – это живой HTU21D, поля уже обновляются в фоне
        return ujson.dumps({
            'temperature': sensor.temperature,
            'humidity': sensor.humidity
        }), 200, {'Content-Type': 'application/json'}
    
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
    
    @app.get('/api/profiler')
    async def api_profiler(request):
        raw_json_str = ujson.dumps(aioprof.timing)
        if request.args.get('reset', '').lower() == 'true':
            print("Сброс данных aioprof по запросу API.")  # Логирование
            aioprof.reset()
        # Чтобы microdot корректно вернул JSON-строку как тело ответа,
        # нужно указать тип содержимого.
        return raw_json_str, 200, {'Content-Type': 'application/json'}

    return app
