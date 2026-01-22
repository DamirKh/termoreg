import gzip
import os
import os.path

print("Сжатие www")
print("Текущая рабочая директория:")
print(os.getcwd())

www_path = 'www'
if not os.path.exists(www_path):
    print(f"Директория '{www_path}' не найдена!")
    exit(1)

www_files = os.listdir(www_path)

for filename in www_files:
    if filename.endswith('.html') or filename.endswith('.css') or filename.endswith('.js') or filename.endswith('.ico'):
        full_path = os.path.join(www_path, filename)
        gz_path = full_path + '.gz'
        print(f"Сжатие {full_path} в {gz_path}...")

        with open(full_path, 'rb') as f_in:
            with gzip.open(gz_path, 'wb') as f_out:
                f_out.writelines(f_in)
        print(f"Сжатие {filename} успешно.")