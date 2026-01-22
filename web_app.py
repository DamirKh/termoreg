from microdot import Microdot, send_file
import ujson
import gc
import aioprof

import hw


# Импортируем usercode, чтобы получить доступ к get_last_output
import usercode


def build_web_app(sensor):
    app = Microdot()

    @app.get('/favicon.ico')
    async def favicon(request):
        return send_file('/www/favicon.ico.gz', compressed=True)

    @app.get('/')
    async def index(request):
        return send_file('/www/index.html.gz', compressed=True)
    
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
    <!-- Добавляем строку состояния из app.normal -->
    <li>Состояние User task: {user_task_status}</li>
  </ul>
  <a href="/">На главную</a>
</body>
</html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    @app.get('/api/data')
    async def api_data(request):
        # sensor – это живой HTU21D, поля уже обновляются в фоне
        return ujson.dumps({
            'temperature': sensor.temperature,
            'humidity': sensor.humidity
        })
    
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
