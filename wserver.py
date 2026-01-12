# wserver.py — ИСПРАВЛЕННАЯ ВЕРСИЯ
import tinyweb

def create_app(shared_state, get_history_func):
    app = tinyweb.webserver()

    @app.route('/')
    async def index(request, response):
        await response.start_html()
        # СТАТИЧЕСКИЙ HTML — НИКАКИХ f-строк!
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>ESP32 Climate</title>
            <script src="/chart.min.js"></script>
        </head>
        <body>
            <h2>Live Data</h2>
            <div id="current">Loading...</div>

            <h2>History (last 7 days)</h2>
            <canvas id="chart" width="600" height="300"></canvas>

<script>
    let chart = null;

    function updateData() {
        // Обновляем текущие данные
        fetch('/api/state')
            .then(r => r.json())
            .then(data => {
                const temp_s = (data.temp_ds != null) ? data.temp_ds + '°C' : '—';
                const temp = (data.temp_dht != null) ? data.temp_dht + '°C' : '—';
                const hum = (data.hum_dht != null) ? data.hum_dht + '%' : '—';
                const timeStr = data.local_time_str || '—';
                document.getElementById('current').innerHTML = `
                    <p><strong>Time:</strong> ${timeStr}</p>
                    <p><strong>Температура щупа:</strong> ${temp_s}</p>
                    <p><strong>Температура:</strong> ${temp}, <strong>Влажность:</strong> ${hum}</p>
                    <p><strong>Нагреватель:</strong> ${data.heater_on ? 'ON' : 'OFF'}</p>
                    <p><strong>Текущая уставка:</strong> ${data.setpoint}°C</p>
                `;
            })
            .catch(err => console.error("State error:", err));

        // Обновляем историю и график
        fetch('/api/history')
            .then(r => r.json())
            .then(rows => {
                const labels = rows.map(r => new Date(r[0] * 1000).toLocaleString());
                const temps = rows.map(r => r[1]);
                const hums = rows.map(r => r[2]);

                if (!chart) {
                    // Первый запуск — создаём график
                    const ctx = document.getElementById('chart').getContext('2d');
                    chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Temperature (°C)',
                                 temps,
                                borderColor: 'red',
                                tension: 0.1
                            }, {
                                label: 'Humidity (%)',
                                 hums,
                                borderColor: 'blue',
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                x: { display: false }
                            },
                            animation: { duration: 0 }
                        }
                    });
                } else {
                    // Обновляем существующий график
                    chart.data.labels = labels;
                    chart.data.datasets[0].data = temps;
                    chart.data.datasets[1].data = hums;
                    chart.update('none'); // мгновенное обновление без анимации
                }
            })
            .catch(err => console.error("History error:", err));
    }

    // Первый запуск
    updateData();

    // Обновляем каждые 30 секунд
    setInterval(updateData, 30000);
</script>
        </body>
        </html>
        """
        await response.send(html)

    @app.route('/api/state')
    async def api_state(request, response):
        import json
        await response.send(json.dumps(shared_state))

    @app.route('/api/history')
    async def api_history(request, response):
        import json
        await response.send(json.dumps(get_history_func()))

    @app.route('/chart.min.js')
    async def serve_chart_js(request, response):
        try:
            with open('chart.min.js', 'rb') as f:
                # Отправляем как есть — tinyweb по умолчанию отправит text/html,
                # но браузер всё равно выполнит JS, если тег <script> указывает на .js
                await response.send(f.read())
        except OSError:
            await response.send("404: chart.min.js not found")

    return app
