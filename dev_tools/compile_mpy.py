# compile_mpy.py
import subprocess
import sys
import os
from pathlib import Path

MPY_CROSS_PATH = r"C:\Users\CPC2\AppData\Local\Programs\Python\Python313\Scripts\mpy-cross.exe" # Windows path format
MPREMOTE_PATH = r"C:\Users\CPC2\AppData\Roaming\Python\Python313\Scripts\mpremote.exe" # Путь к mpremote

# Директории, которые нужно игнорировать
IGNORE_DIRS = {'__pycache__', 'dev_tools', '.git'}

def ensure_dir_on_device(mpremote_path, dir_path):
    """Пытается создать директорию на устройстве с помощью mpremote."""
    # mpremote fs mkdir :dir_path
    # Используем '/' как разделитель для путей на устройстве, независимо от ОС хоста
    remote_dir_path = ':' + dir_path.replace('\\', '/').replace('//', '/')
    print(f"Проверка/создание директории на устройстве: {remote_dir_path}")
    try:
        # mpremote fs mkdir может возвращать ошибку, если директория уже существует
        # Это не фатальная ошибка, просто продолжаем.
        subprocess.run([mpremote_path, "fs", "mkdir", remote_dir_path], check=False, capture_output=True)
        # capture_output=True, чтобы не засорять stdout/stderr при ожидаемой ошибке "exists"
        # check=False, чтобы не прерывать выполнение, если mkdir не удался (например, уже существует)
        print(f"  -> Директория {remote_dir_path} готова (создана или уже существовала)")
    except subprocess.CalledProcessError as e:
        print(f"  -> Ошибка при создании директории {remote_dir_path}: {e}")
        # Продолжаем, возможно, директория уже была создана ранее или ошибка не критична

def main():
    # Проверяем, существует ли mpy-cross
    if not os.path.isfile(MPY_CROSS_PATH):
        print(f"Error: {MPY_CROSS_PATH} не найден.", file=sys.stderr)
        sys.exit(1)

    # Проверяем, существует ли mpremote
    if not os.path.isfile(MPREMOTE_PATH):
        print(f"Error: {MPREMOTE_PATH} не найден.", file=sys.stderr)
        sys.exit(1)

    print(f"Используется mpy-cross: {MPY_CROSS_PATH}")
    print(f"Используется mpremote: {MPREMOTE_PATH}")

    # Список скомпилированных файлов для загрузки
    compiled_files_to_upload = []

    # Получаем корневую директорию проекта (на уровень вверх от dev_tools)
    project_root = Path(__file__).resolve().parent.parent

    print(f"Корневая директория проекта: {project_root}")

    # Найдем все .py файлы в корне проекта и поддиректориях
    for py_path in project_root.rglob('*.py'):
        # Проверяем, находится ли какой-либо компонент пути в IGNORE_DIRS
        if any(part in IGNORE_DIRS for part in py_path.parts):
            print(f"Пропускается {py_path} (в игнорируемой директории)")
            continue

        # Пропускаем файлы в скрытых директориях (начинающихся с точки)
        if any(part.startswith('.') for part in py_path.parts):
            continue

        # Проверяем, не является ли py_path частью пути к mpy-cross или mpremote
        try:
            relative_to_project = py_path.relative_to(project_root)
        except ValueError:
            print(f"Пропускается {py_path} (вне корневой директории проекта)")
            continue

        # Путь для .mpy файла (локально)
        mpy_path = py_path.with_suffix('.mpy')

        print(f"Компилируется {py_path} -> {mpy_path}")

        try:
            # Запускаем mpy-cross
            result = subprocess.run([MPY_CROSS_PATH, str(py_path)], check=True)
            if result.returncode != 0:
                 print(f"Ошибка при компиляции {py_path}", file=sys.stderr)
            else:
                # Если компиляция успешна, добавляем .mpy файл в список для загрузки
                compiled_files_to_upload.append((mpy_path, relative_to_project))
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при компиляции {py_path}: {e}", file=sys.stderr)

    print("Компиляция завершена.")

    # --- Загрузка скомпилированных файлов на ESP32 с сохранением структуры ---
    if compiled_files_to_upload:
        print("\n--- Загрузка .mpy файлов на ESP32 с сохранением структуры ---")
        uploaded_dirs = set() # Для отслеживания уже созданных директорий

        for mpy_file_local, relative_path_py in compiled_files_to_upload:
            # relative_path_py - это путь к .py файлу относительно корня проекта
            relative_path_mpy = relative_path_py.with_suffix('.mpy')
            # remote_mpy_path станет :relative_path_mpy (с префиксом :, используем /)
            remote_mpy_path = ':' + relative_path_mpy.as_posix() # as_posix() конвертирует \ в /

            # Определяем удаленную директорию
            remote_dir = relative_path_mpy.parent.as_posix()
            if remote_dir != '.': # Если файл в корне, не нужно создавать директорию
                remote_dir_path = ':' + remote_dir
                if remote_dir_path not in uploaded_dirs:
                    ensure_dir_on_device(MPREMOTE_PATH, remote_dir) # Создаем директорию
                    uploaded_dirs.add(remote_dir_path) # Отмечаем, что создали
            else:
                # Если файл в корне ('.'), убедимся, что корень отмечен (хотя это избыточно)
                if ':' not in uploaded_dirs:
                    uploaded_dirs.add(':') # Корень всегда "существует" или "создан"

            print(f"Загружается {mpy_file_local} -> {remote_mpy_path} ...")
            try:
                # mpremote fs cp local_file :relative_remote_path
                result = subprocess.run([MPREMOTE_PATH, "fs", "cp", str(mpy_file_local), remote_mpy_path], check=True)
                if result.returncode != 0:
                    print(f"Ошибка при загрузке {mpy_file_local} -> {remote_mpy_path}", file=sys.stderr)
                else:
                    print(f"  -> Успешно загружен как {remote_mpy_path}")
            except subprocess.CalledProcessError as e:
                print(f"Ошибка при загрузке {mpy_file_local} -> {remote_mpy_path}: {e}", file=sys.stderr)

        print("\nЗагрузка завершена.")
    else:
        print("\nНет скомпилированных файлов для загрузки.")


if __name__ == "__main__":
    main()
