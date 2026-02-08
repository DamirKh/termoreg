# schedule/daily.py
from datetime import time
from typing import List, Tuple, Optional


class Period:
    """Период в расписании: [start, end)"""
    
    def __init__(self, start: time, end: time, state: bool):
        self.start = start
        self.end = end
        self.state = state
    
    def __repr__(self):
        return f"Period({self.start}-{self.end}: {int(self.state)})"


class DailySchedule:
    """
    Кольцевое расписание на сутки, гранулярность 1 минута.
    Оперирует периодами, а не точками.
    """
    
    MINUTES_IN_DAY = 1440
    
    def __init__(self, default: bool = False):
        self._default = default
        # Храним периоды явно
        self._periods: List[Tuple[int, int, bool]] = []  # (start_min, end_min, state)
    
    def _to_minutes(self, t: time) -> int:
        return t.hour * 60 + t.minute
    
    def add_period(self, start: time, end: time, state: bool) -> None:
        """
        Добавить период [start, end).
        При пересечении с существующими — новый период имеет приоритет.
        """
        start_m = self._to_minutes(start)
        end_m = self._to_minutes(end)
        
        # Нормализуем: если start > end, значит через полночь
        # Разбиваем на два периода или храним как (start, end) с флагом?
        # Пока просто добавляем, нормализация потом
        
        self._periods.append((start_m, end_m, state))
        self._normalize()
    
    def _normalize(self) -> None:
        """Применить периоды к плоскому массиву"""
        # Создаём массив
        data = bytearray(self.MINUTES_IN_DAY)
        default_val = 1 if self._default else 0
        for i in range(self.MINUTES_IN_DAY):
            data[i] = default_val
        
        # Применяем периоды (поздние перекрывают ранние)
        for start_m, end_m, state in sorted(self._periods, key=lambda x: x[0]):
            val = 1 if state else 0
            
            if start_m < end_m:
                # Обычный период
                for i in range(start_m, end_m):
                    data[i] = val
            else:
                # Через полночь
                for i in range(start_m, self.MINUTES_IN_DAY):
                    data[i] = val
                for i in range(0, end_m):
                    data[i] = val
        
        self._data = data
    
    def get(self, t: time) -> bool:
        """O(1) чтение"""
        if not hasattr(self, '_data'):
            self._normalize()
        minute = self._to_minutes(t)
        return bool(self._data[minute])
    
    def periods(self) -> List[Period]:
        """Вернуть список периодов"""
        result = []
        for start_m, end_m, state in self._periods:
            start = time(start_m // 60, start_m % 60)
            end = time(end_m // 60, end_m % 60)
            result.append(Period(start, end, state))
        return result
    
    def __repr__(self):
        return f"Schedule({len(self._periods)} periods)"
    