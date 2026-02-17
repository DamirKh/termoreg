"""
Schedule Web App - MicroDot-based web interface for Schedule management.
Optimized for MicroPython, works on CPython for development.
"""

try:
    # MicroPython
    from microdot import Microdot, Response, redirect, send_file
    # from microdot.websocket import with_websocket
    import ujson as json
    import uasyncio as asyncio
    MICROPYTHON = True
except ImportError:
    # CPython (development)
    # from microdot import Microdot, Response, redirect
    # try:
    #     from microdot.websocket import with_websocket
    # except ImportError:
    #     with_websocket = None
    import json
    import asyncio
    MICROPYTHON = False

from schedule import Schedule


class ScheduleApp:
    def __init__(self, schedule: Schedule = None, filename='/schedule.hex'):
        self.schedule = schedule or Schedule()
        self.filename = filename
        self.app = Microdot()
        self.setup_routes()

    def _save_to_file(self):
        try:
            with open(self.filename, 'w') as f:
                f.write(self.schedule.to_hex())
            print(f"Auto-saved to {self.filename}")
        except Exception as e:
            print(f"Auto-save failed: {e}")

    def setup_routes(self):
        @self.app.route('/')
        async def index(request):
            # return Response(body=HTML_TEMPLATE, headers={'Content-Type': 'text/html'})
            # return send_file('www/schedule.html')
            return send_file('www/schedule.html.gz', compressed=True)

        @self.app.route('/api/schedule', methods=['GET'])
        async def get_schedule(request):
            return {
                # 'minutes': minutes,
                'hex': self.schedule.to_hex(),
                'active_count': len(self.schedule),
                'intervals_5min': 288  # Indicate 5-min granularity
            }

        @self.app.route('/api/schedule/hex', methods=['POST'])
        async def set_schedule_hex_only(request):
            """Set schedule from hex string only - updates existing object."""
            try:
                data = json.loads(request.body)
                hex_str = data.get('hex', '').strip()

                if len(hex_str) != 360:  # 180 bytes * 2 hex chars
                    return {'error': f'Expected 360 hex chars, got {len(hex_str)}'}, 400

                # Update existing schedule object in-place
                self.schedule.update_from_hex(hex_str)
                self._save_to_file()  # Auto-save if configured

                return {
                    'success': True,
                    'active_count': len(self.schedule)
                }
            except Exception as e:
                return {'error': str(e)}, 400

        @self.app.route('/api/clear', methods=['POST'])
        async def clear_schedule(request):
            """Clear entire schedule."""
            self.schedule.clear()
            return {'success': True, 'hex': self.schedule.to_hex()}

        @self.app.route('/api/fill', methods=['POST'])
        async def fill_schedule(request):
            """Fill entire schedule."""
            try:
                data = json.loads(request.body) if request.body else {}
                self.schedule.fill(data.get('active', True))
                return {'success': True, 'hex': self.schedule.to_hex()}
            except Exception as e:
                return {'error': str(e)}, 400
