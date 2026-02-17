"""
Schedule - компактное хранилище расписания на 24 часа с минутной гранулярностью.
Оптимизировано для чтения, совместимо с CPython и MicroPython.

Память: 1440 бит = 180 байт на экземпляр
"""

try:
    # MicroPython
    from ucollections import namedtuple
    import ustruct as struct
except ImportError:
    # CPython
    from collections import namedtuple
    import struct

# namedtuple для удобного доступа к времени
TimeSlot = namedtuple('TimeSlot', ['hour', 'minute', 'active'])


class Schedule:
    """
    Расписание на сутки (00:00 - 23:59).
    Хранит 1440 минут в виде битовой маски (180 байт).
    """

    MINUTES_PER_DAY = 24 * 60  # 1440
    BYTES_NEEDED = MINUTES_PER_DAY // 8  # 180

    __slots__ = ('_data',)  # Экономия памяти в CPython

    def __init__(self, data=None):
        """
        Args:
            data: bytes (180) или None для пустого расписания
        """
        if data is None:
            self._data = bytearray(self.BYTES_NEEDED)
        elif isinstance(data, (bytes, bytearray)):
            if len(data) != self.BYTES_NEEDED:
                raise ValueError(f"Expected {self.BYTES_NEEDED} bytes, got {len(data)}")
            self._data = bytearray(data)
        else:
            raise TypeError("data must be bytes or bytearray")

    # === Оптимизированные методы чтения ===

    def is_active(self, hour: int, minute: int) -> bool:
        """Проверить состояние в конкретное время. O(1)"""
        idx = hour * 60 + minute
        byte_idx = idx >> 3  # idx // 8
        bit_idx = idx & 0x07  # idx % 8
        return bool(self._data[byte_idx] & (1 << bit_idx))

    def is_active_minute(self, minute_of_day: int) -> bool:
        """Проверить состояние по номеру минуты (0-1439). O(1)"""
        byte_idx = minute_of_day >> 3
        bit_idx = minute_of_day & 0x07
        return bool(self._data[byte_idx] & (1 << bit_idx))

    def get_state(self) -> bytearray:
        """Получить копию внутренних данных."""
        return bytearray(self._data)

    # === Методы записи ===

    def set_active(self, hour: int, minute: int, active: bool = True):
        """Установить состояние в конкретное время."""
        idx = hour * 60 + minute
        byte_idx = idx >> 3
        bit_idx = idx & 0x07
        if active:
            self._data[byte_idx] |= (1 << bit_idx)
        else:
            self._data[byte_idx] &= ~(1 << bit_idx)

    def set_range(self, start_h: int, start_m: int, end_h: int, end_m: int, active: bool = True):
        """Установить состояние для диапазона времени [start, end)."""
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m

        if end <= start:  # Переход через полночь не поддерживаем для простоты
            end = self.MINUTES_PER_DAY

        #Этот цикл желательно оптимизировать.
        for minute in range(start, end):
            byte_idx = minute >> 3
            bit_idx = minute & 0x07
            if active:
                self._data[byte_idx] |= (1 << bit_idx)
            else:
                self._data[byte_idx] &= ~(1 << bit_idx)

    def clear(self):
        """Очистить всё расписание."""
        for i in range(self.BYTES_NEEDED):
            self._data[i] = 0

    def fill(self, active: bool = True):
        """Заполнить всё расписание."""
        value = 0xFF if active else 0x00
        for i in range(self.BYTES_NEEDED):
            self._data[i] = value

    # === Итераторы (ленивые для экономии памяти) ===

    def active_minutes(self):
        """Генератор активных минут (0-1439)."""
        for minute in range(self.MINUTES_PER_DAY):
            if self.is_active_minute(minute):
                yield minute

    def active_slots(self):
        """Генератор активных временных слотов (hour, minute)."""
        for minute in self.active_minutes():
            yield (minute // 60, minute % 60)

    def ranges(self):
        """
        Генератор непрерывных диапазонов активного времени.
        Возвращает кортежи ((start_h, start_m), (end_h, end_m)).
        """
        in_range = False
        start = 0

        for minute in range(self.MINUTES_PER_DAY):
            active = self.is_active_minute(minute)

            if active and not in_range:
                start = minute
                in_range = True
            elif not active and in_range:
                yield ((start // 60, start % 60), (minute // 60, minute % 60))
                in_range = False

        if in_range:
            yield ((start // 60, start % 60), (24, 0))

    # === Сериализация ===

    def to_bytes(self) -> bytes:
        """Сериализовать в bytes (180 байт)."""
        return bytes(self._data)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Schedule':
        """Десериализовать из bytes."""
        return cls(data)

    def to_hex(self) -> str:
        """Сериализовать в hex-строку (360 символов)."""
        # MicroPython совместимость: ручная конвертация
        hex_chars = '0123456789abcdef'
        result = []
        for b in self._data:
            result.append(hex_chars[b >> 4])
            result.append(hex_chars[b & 0x0F])
        return ''.join(result)

    @classmethod
    def from_hex(cls, hex_str: str) -> 'Schedule':
        """Десериализовать из hex-строки."""
        data = bytearray(len(hex_str) // 2)
        for i in range(0, len(hex_str), 2):
            data[i // 2] = int(hex_str[i:i + 2], 16)
        return cls(data)

    def update_from_hex(self, hex_str: str) -> None:
        """Update existing schedule from hex string in-place."""
        if len(hex_str) != 360:
            raise ValueError("Expected 360 hex chars")

        # Direct in-place update without creating bytearray
        for i in range(180):
            # Parse hex chars manually without int(hex, 16) to avoid new objects
            h = hex_str[i * 2]
            l = hex_str[i * 2 + 1]

            # Convert to nibbles: '0'-'9' = 0-9, 'a'-'f' = 10-15
            hv = ord(h) - 48 if h <= '9' else ord(h) - 87
            lv = ord(l) - 48 if l <= '9' else ord(l) - 87

            # Validate
            if hv < 0 or hv > 15 or lv < 0 or lv > 15:
                raise ValueError(f"Invalid hex at position {i * 2}")

            # Write to existing _data directly
            self._data[i] = (hv << 4) | lv

    # === Утилиты ===

    def copy(self) -> 'Schedule':
        """Создать копию."""
        return Schedule(self._data)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Schedule):
            return False
        return self._data == other._data

    def __repr__(self) -> str:
        # Показываем только первые 3 диапазона для краткости
        ranges = list(self.ranges())
        if len(ranges) > 3:
            ranges_str = ', '.join(f'{s[0]:02d}:{s[1]:02d}-{e[0]:02d}:{e[1]:02d}'
                                   for s, e in ranges[:3]) + f'... (+{len(ranges) - 3})'
        else:
            ranges_str = ', '.join(f'{s[0]:02d}:{s[1]:02d}-{e[0]:02d}:{e[1]:02d}'
                                   for s, e in ranges)
        return f'Schedule([{ranges_str}])'

    def __len__(self) -> int:
        """Количество активных минут."""
        count = 0
        for b in self._data:
            # Brian Kernighan's algorithm для подсчёта битов
            while b:
                count += 1
                b &= b - 1
        return count
