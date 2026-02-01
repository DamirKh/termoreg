# --- Глобальная переменная для хранения состояния ---
import hw

last_normal_output = "User task ещё не запускался."

def normal(dt_ms): # <-- Принимает время в миллисекундах с прошлого вызова
    global last_normal_output
    output_string = f"User task normal operation, time since last call: {dt_ms} ms"
    # print(output_string) # <-- Закомментируем или удалим print
    last_normal_output = output_string # <-- Сохраняем строку в глобальной переменной

def get_last_output():
    """Функция для получения последнего состояния из app.py"""
    global last_normal_output
    return last_normal_output

def onstart():
    print("User task start")

def onstop():
    print("User task stop")

