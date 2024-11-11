import os
import zipfile
import argparse
import tkinter as tk
from tkinter import Entry, END, WORD
from tkinter.scrolledtext import ScrolledText
import threading
import xml.etree.ElementTree as ET

class VShell:
    def __init__(self, zip_path):
        self.zip_path = zip_path
        self.current_directory = '/'
        self.filesystem = {}
        self._load_from_zip()
        print("Файловая система успешно загружена.")

    def _load_from_zip(self):
        if not os.path.exists(self.zip_path):
            raise FileNotFoundError(f"ZIP-файл '{self.zip_path}' не найден. Пожалуйста, укажите существующий ZIP-файл.")

        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                path = '/' + file_info.filename.replace('\\', '/').strip('/')
                if file_info.is_dir():
                    self._create_directory(path)
                else:
                    # Попытка декодировать содержимое как UTF-8. Если не удается, сохраняем в байтах.
                    try:
                        content = zip_ref.read(file_info.filename).decode('utf-8')
                    except UnicodeDecodeError:
                        content = zip_ref.read(file_info.filename).decode('utf-8', errors='ignore')
                    self._create_file(path, content)
        if not self.filesystem:
            print("В ZIP-файле нет файловой системы.")
        else:
            print("Файловая система загружена:")
            for path in sorted(self.filesystem.keys()):
                print(f" - {path}")

    def _write_to_zip(self):
        with zipfile.ZipFile(self.zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for path, content in self.filesystem.items():
                zip_path = path.lstrip('/')
                if path.endswith('/'):
                    # Добавляем директорию
                    zip_info = zipfile.ZipInfo(zip_path)
                    zip_ref.writestr(zip_info, '')
                else:
                    zip_ref.writestr(zip_path, content)
        print("Файловая система записана в ZIP-файл.")

    def _create_directory(self, path):
        """Создает директорию в файловой системе"""
        if not path.endswith('/'):
            path += '/'
        if path not in self.filesystem:
            self.filesystem[path] = {}
            print(f"Директория создана: {path}")

    def _create_file(self, path, content):
        """Создает файл в файловой системе"""
        self.filesystem[path] = content
        print(f"Файл создан: {path}")

    def _abs_path(self, path):
        """Возвращает абсолютный путь на основе текущего местоположения"""
        if os.path.isabs(path):
            normalized = os.path.normpath(path).replace('\\', '/')
        else:
            combined = os.path.join(self.current_directory, path)
            normalized = os.path.normpath(combined).replace('\\', '/')
        if not normalized.startswith('/'):
            normalized = '/' + normalized
        return normalized if path.endswith('/') else normalized.rstrip('/')

    def pwd(self):
        print(f"Текущая директория: {self.current_directory}")
        return self.current_directory

    def ls(self):
        """Возвращает список файлов и директорий в текущей директории"""
        current_dir = self.current_directory.rstrip('/') + '/'
        entries = []
        for path in self.filesystem:
            if path.startswith(current_dir) and path != current_dir:
                relative_path = path[len(current_dir):]
                if '/' not in relative_path.strip('/'):
                    if path.endswith('/'):
                        entries.append(relative_path + '/')
                    else:
                        entries.append(relative_path)
        print(f"ls в {self.current_directory}: {entries}")
        return sorted(entries)

    def cd(self, path):
        """Меняет текущую директорию"""

        abs_path = self._abs_path(path)
        if not abs_path.endswith('/'):
            abs_path += '/'
        if abs_path in self.filesystem and isinstance(self.filesystem[abs_path], dict):
            self.current_directory = abs_path
            print(f"Текущая директория изменена на: {self.current_directory}")
        else:
            raise FileNotFoundError(f"Нет такой директории: {path}")

    def cat(self, filename):
        """Возвращает содержимое файла"""
        abs_path = self._abs_path(filename)
        if abs_path in self.filesystem and not abs_path.endswith('/'):
            content = self.filesystem[abs_path]
            print(f"cat {filename}:\n{content}")
            return content
        else:
            raise FileNotFoundError(f"Нет такого файла: {filename}")

    def mkdir(self, dirname):
        """Создает новую директорию"""
        abs_path = self._abs_path(dirname)
        if not abs_path.endswith('/'):
            abs_path += '/'
        if abs_path in self.filesystem:
            raise FileExistsError(f"Директория уже существует: {dirname}")
        self.filesystem[abs_path] = {}
        print(f"Директория '{dirname}' создана.")
        return f"Директория '{dirname}' создана."

    def nano(self, filename, content):
        """Создает или редактирует файл с указанным содержимым"""
        abs_path = self._abs_path(filename)
        if abs_path.endswith('/'):
            raise IsADirectoryError(f"'{filename}' является директорией.")
        parent_dir = os.path.dirname(abs_path).replace('\\', '/') + '/'
        if parent_dir not in self.filesystem or not isinstance(self.filesystem[parent_dir], dict):
            raise FileNotFoundError(f"Родительская директория не существует: {parent_dir}")
        self.filesystem[abs_path] = content
        print(f"Файл '{filename}' обновлен содержимым: {content}")
        return f"Файл '{filename}' обновлен."

    def tree_helper(self, current_dir, prefix=''):
        """Рекурсивно строит структуру дерева относительно current_dir"""
        tree_str = ""
        # Получаем все пути, которые начинаются с current_dir, но не равны ему
        entries = sorted([
            path for path in self.filesystem
            if path.startswith(current_dir) and path != current_dir
        ], key=lambda x: x.count('/'))

        subdirs = {}
        files = []
        for path in entries:
            # Относительный путь
            relative_path = path[len(current_dir):].lstrip('/')
            parts = relative_path.split('/')
            if len(parts) > 1:
                subdir = parts[0] + '/'
                if subdir not in subdirs:
                    subdirs[subdir] = []
                subdirs[subdir].append(path)
            else:
                files.append(path)

        # Сортируем поддиректории и файлы вместе
        all_entries = sorted(list(subdirs.keys()) + files)
        for idx, name in enumerate(all_entries):
            is_last = idx == len(all_entries) - 1
            connector = "└── " if is_last else "├── "
            # Если это директория, отображаем имя без '/' на конце
            display_name = name[:-1] if name.endswith('/') else os.path.basename(name)
            tree_str += f"{prefix}{connector}{display_name}\n"
            if name.endswith('/'):
                # Определяем новый префикс для вложенных элементов
                extension = "    " if is_last else "│   "
                # Рекурсивный вызов для поддиректории
                tree_str += self.tree_helper(os.path.join(current_dir, name), prefix + extension)
        return tree_str

    def tree(self):
        """Отображает древовидную структуру текущей директории"""
        if not self.filesystem:
            print("Файловая система пуста.")
            return "Файловая система пуста."

        # Получаем текущую директорию
        current_dir = self.current_directory
        # Отображаем имя текущей директории (опционально)
        tree_structure = f"{current_dir}\n"
        # Добавляем дерево начиная с текущей директории
        tree_structure += self.tree_helper(current_dir)
        print(tree_structure)
        return tree_structure

    def mv(self, source, destination):
        """Перемещает файл или директорию"""
        abs_source = self._abs_path(source)
        abs_destination = self._abs_path(destination)

        if abs_source not in self.filesystem:
            raise FileNotFoundError(f"Нет такого файла или директории: {source}")
        if abs_destination in self.filesystem:
            raise FileExistsError(f"Пункт назначения уже существует: {destination}")

        # Перемещаем основной файл или директорию
        self.filesystem[abs_destination] = self.filesystem.pop(abs_source)

        # Если перемещается директория, необходимо обновить пути вложенных файлов
        if abs_destination.endswith('/'):
            prefix = abs_source.rstrip('/') + '/'
            new_prefix = abs_destination
            keys_to_update = [key for key in self.filesystem.keys() if key.startswith(prefix)]
            for key in keys_to_update:
                new_key = new_prefix + key[len(prefix):]
                self.filesystem[new_key] = self.filesystem.pop(key)
        print(f"Перемещено '{source}' в '{destination}'.")
        return f"Перемещено '{source}' в '{destination}'."


class ShellGUI:
    def __init__(self, shell):
        self.shell = shell
        self.window = tk.Tk()
        self.window.title("Виртуальный Эмулятор Shell")

        self.output = ScrolledText(self.window, wrap=WORD, height=20, width=80, state='disabled')
        self.output.pack(padx=10, pady=10)

        self.entry = Entry(self.window, width=80)
        self.entry.pack(padx=10, pady=(0, 10))
        self.entry.bind("<Return>", self.execute_command)
        self.entry.focus()

        # Инициализируем вывод текущего пути
        self._append_output(f"{self.shell.pwd()}$ ")

    def execute_command(self, event=None):
        command = self.entry.get()
        self.entry.delete(0, END)
        if not command.strip():
            return
        threading.Thread(target=self._execute_command_thread, args=(command,)).start()

    def _execute_command_thread(self, command):
        try:
            result = self.handle_command(command)
            prompt = f"{self.shell.pwd()}$ {command}\n"
            if result:
                self._append_output(f"{prompt}{result}\n")
            else:
                self._append_output(f"{prompt}")
        except Exception as e:
            self._append_output(f"Ошибка: {e}\n")

    def _append_output(self, text):
        def append():
            self.output.configure(state='normal')
            self.output.insert(END, text)
            self.output.configure(state='disabled')
            self.output.see(END)
        self.output.after(0, append)

    def handle_command(self, command):
        parts = command.strip().split()
        if not parts:
            return ""

        cmd = parts[0]
        args = parts[1:]

        try:
            if cmd == "pwd":
                return self.shell.pwd()
            elif cmd == "ls":
                output = "\n".join(self.shell.ls())
                return output if output else "Нет файлов или директорий."
            elif cmd == "cd":
                if len(args) < 1:
                    return "cd: отсутствует аргумент."
                self.shell.cd(args[0])
                return ""
            elif cmd == "cat":
                if len(args) < 1:
                    return "cat: отсутствует аргумент."
                return self.shell.cat(args[0])
            elif cmd == "mkdir":
                if len(args) < 1:
                    return "mkdir: отсутствует аргумент."
                return self.shell.mkdir(args[0])
            elif cmd == "nano":
                if len(args) < 2:
                    return "nano: недостаточно аргументов. Использование: nano <файл> <содержимое>"
                filename = args[0]
                content = ' '.join(args[1:])
                return self.shell.nano(filename, content)
            elif cmd == "tree":
                output = self.shell.tree()
                return output if output else "Файловая система пуста."
            elif cmd == "mv":
                if len(args) < 2:
                    return "mv: недостаточно аргументов. Использование: mv <источник> <назначение>"
                return self.shell.mv(args[0], args[1])
            elif cmd == "exit":
                self.shell._write_to_zip()
                self.window.quit()
                return "Выход..."
            else:
                return f"Команда '{cmd}' не найдена."
        except Exception as e:
            return f"Ошибка при выполнении команды '{command}': {e}"

    def run(self):
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()

    def on_close(self):
        self.shell._write_to_zip()
        self.window.destroy()

def load_config(xml_path):
    """Загружает настройки из XML-файла."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    config = {
        "computer_name": root.findtext("computer_name", default="VShell"),
        "zip_file_path": root.findtext("zip_file_path"),
        "startup_script_path": root.findtext("startup_script_path"),
    }

    # Проверка наличия всех необходимых параметров
    if not config["zip_file_path"]:
        raise ValueError("XML-конфигурация должна содержать элемент 'zip_file_path'.")

    return config


def execute_startup_script(shell, script_path):
    """Выполняет команды из стартового скрипта."""
    if not os.path.exists(script_path):
        print(f"Стартовый скрипт '{script_path}' не найден.")
        return

    with open(script_path, 'r') as f:
        commands = f.readlines()

    for command in commands:
        command = command.strip()
        if command:
            print(f"Выполняется команда из скрипта: {command}")
            try:
                shell.handle_command(command)
            except Exception as e:
                print(f"Ошибка при выполнении команды '{command}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Виртуальный Эмулятор Shell с GUI")
    parser.add_argument("config_file", help="C:\\Users\\pasha\\PycharmProjects\\Konfig_1\\config.xml")
    args = parser.parse_args()

    # Загрузка конфигурации из XML-файла
    try:
        config = load_config(args.config_file)
    except (ET.ParseError, ValueError) as e:
        print(f"Ошибка при чтении конфигурационного файла: {e}")
        return

    # Проверка наличия ZIP-файла
    zip_file_path = config["zip_file_path"]
    if not zip_file_path.lower().endswith('.zip'):
        print("Ошибка: Указанный файл не является ZIP-архивом.")
        return
    if not os.path.exists(zip_file_path):
        print(f"Ошибка: ZIP-файл '{zip_file_path}' не найден.")
        return

    # Создание виртуальной файловой системы на основе ZIP-файла
    try:
        shell = VShell(zip_file_path)
        shell.computer_name = config["computer_name"]  # Устанавливаем имя компьютера
    except zipfile.BadZipFile:
        print(f"Ошибка: Файл '{zip_file_path}' поврежден или не является корректным ZIP-файлом.")
        return

    # Выполнение команд из стартового скрипта
    startup_script_path = config["startup_script_path"]
    if startup_script_path:
        execute_startup_script(shell, startup_script_path)

    # Запуск GUI
    gui = ShellGUI(shell)
    gui.run()


if __name__ == "__main__":
    main()
