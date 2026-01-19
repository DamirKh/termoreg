from microdot import Microdot, send_file
import ujson
import gc


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

    return app