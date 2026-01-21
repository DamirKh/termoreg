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
    def favicon(request):
        return send_file('/www/favicon.ico')

    @app.get('/')
    def index(request):
        return send_file('/www/index.html')
    
    @app.get('/hw') # <-- Новый маршрут для hw.html
    def hw_page(request):
        return send_file('/www/hw.html') # <-- Сервим файл hw.html

    @app.get('/prof') # <-- Новый маршрут для prof.html
    def profiler_page(request):
        return send_file('/www/prof.html') # <-- Сервим файл prof.html

    @app.route('/diag')
    def diag(req):
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
    def api_data(request):
        # sensor – это живой HTU21D, поля уже обновляются в фоне
        return ujson.dumps({
            'temperature': sensor.temperature,
            'humidity': sensor.humidity
        })
    
    @app.get('/api/hw')
    def api_hw(request):
        # Получаем все атрибуты модуля hw через его __dict__
        hw_dict = hw.__dict__
        # Фильтруем, исключая служебные имена (__name__, __file__, и т.д.)
        filtered_hw_dict = {k: v for k, v in hw_dict.items() if not k.startswith('__')}
        # Преобразуем значения к строке
        hw_info = {k: str(v) for k, v in filtered_hw_dict.items()}

        # Возвращаем весь отфильтрованный и преобразованный словарь
        return ujson.dumps(hw_info)
    
    @app.get('/api/prof')
    def api_prof(request):
        # Используем timing напрямую из aioprof
        timing_data = aioprof.timing # <-- Получаем словарь {name: [count, ms, max_ms, last]}

        if not timing_data:
            # Если нет данных
            return ujson.dumps({
                "headings": ["function name", "count", "ms", "max", "last exec"],
                "details": [],
                "sorted_by": "name" # или "time", указываем, как отсортировано
            })

        # --- Сбор данных, аналогично aioprof.report(), но с сортировкой ---
        headings = ["function name", "count", "ms", "max", "last exec"]

        sort_param = request.args.get('sort', 'time') # По умолчанию сортируем по времени

        items_to_sort = list(timing_data.items())

        if sort_param == 'name':
            # Сортировка по имени (первый элемент кортежа)
            sorted_items = sorted(items_to_sort, key=lambda i: i[0])
        else: # по умолчанию или если sort=time
            # Сортировка по времени (ms, второй элемент внутреннего списка, т.е. i[1][1])
            sorted_items = sorted(items_to_sort, key=lambda i: i[1][1])
            # aioprof.report() использует reversed для сортировки по убыванию времени
            sorted_items = list(reversed(sorted_items))


        details = []
        for name, (count, ms, max_ms, last) in sorted_items:
            formatted_name = name.replace("generator object", "fn")
            details.append([formatted_name, str(count), str(ms), str(max_ms), str(last)])

        # Возвращаем JSON-объект с заголовками, данными и информацией о сортировке
        return ujson.dumps({
            "headings": headings,
            "details": details,
            "sorted_by": sort_param # Указываем, как отсортировано
        })

    @app.get('/api/profiler') # <-- Новый маршрут
    def api_profiler(request):
        # Возвращает "сырую" JSON-строку из aioprof.json()
        # aioprof.json() использует модуль json, но возвращает строку.
        # ujson.dumps() может не справиться с этой строкой правильно.
        # aioprof.json() уже возвращает строку в формате JSON.
        raw_json_str = aioprof.json()
        # Чтобы microdot корректно вернул JSON-строку как тело ответа,
        # нужно указать тип содержимого.
        return raw_json_str, 200, {'Content-Type': 'application/json'}

    return app
