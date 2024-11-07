import argparse
import zipfile
import os
import sys
import io
from tkinter import *
from tkinter.scrolledtext import ScrolledText


class VShell:
    def __init__(self, zip_path):
        self.zip_path = zip_path
        self.current_directory = '/'
        self.filesystem = {}

        # Чтение содержимого zip-файла
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for zip_info in zip_ref.infolist():
                if not zip_info.is_dir():
                    self.filesystem[zip_info.filename] = zip_ref.read(zip_info.filename).decode('utf-8')

    def pwd(self):
        return self.current_directory

    def ls(self):
        path = self._abs_path(self.current_directory)
        return [name[len(path):] for name in self.filesystem if name.startswith(path) and len(name) > len(path)]

    def cd(self, path):
        new_path = self._abs_path(path)
        if any(name.startswith(new_path) for name in self.filesystem):
            self.current_directory = new_path
        else:
            raise FileNotFoundError(f"Directory {path} not found.")

    def cat(self, filename):
        file_path = self._abs_path(filename)
        if file_path in self.filesystem:
            return self.filesystem[file_path]
        else:
            raise FileNotFoundError(f"File {filename} not found.")

    def mkdir(self, directory):
        new_dir = self._abs_path(directory) + "/"
        if not any(name.startswith(new_dir) for name in self.filesystem):
            self.filesystem[new_dir] = ''
            self._write_to_zip()
            return f"Directory {directory} created."
        else:
            return f"Directory {directory} already exists."

    def nano(self, filename, content):
        file_path = self._abs_path(filename)
        self.filesystem[file_path] = content
        self._write_to_zip()
        return f"File {filename} created/updated."

    def tree(self, path=None, prefix=""):
        if path is None:
            path = self.current_directory
        abs_path = self._abs_path(path)

        # Получаем все подкаталоги и файлы внутри указанного каталога
        entries = [name[len(abs_path):] for name in self.filesystem if name.startswith(abs_path) and name != abs_path]
        entries = sorted(set(entry.split("/")[0] for entry in entries if entry))  # Уникальные подкаталоги и файлы

        for i, entry in enumerate(entries):
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            print(prefix + connector + entry)

            # Если entry — это каталог, рекурсивно выводим его содержимое
            full_path = os.path.join(abs_path, entry)
            if any(name.startswith(full_path + "/") for name in self.filesystem):
                new_prefix = prefix + ("    " if is_last else "│   ")
                self.tree(full_path, new_prefix)

    def mv(self, src, dst):
        src_path = self._abs_path(src)
        dst_path = self._abs_path(dst)

        if src_path in self.filesystem:
            content = self.filesystem.pop(src_path)
            self.filesystem[dst_path] = content
            self._write_to_zip()
            return f"Moved {src} to {dst}"
        else:
            raise FileNotFoundError(f"File {src} not found.")

    def _write_to_zip(self):
        with zipfile.ZipFile(self.zip_path, 'w') as zip_ref:
            for file_name, content in self.filesystem.items():
                zip_ref.writestr(file_name, content)

    def _abs_path(self, path):
        if path.startswith('/'):
            return path.lstrip('/')
        return os.path.join(self.current_directory, path).lstrip('/')


class ShellGUI:
    def __init__(self, shell):
        self.shell = shell
        self.window = Tk()
        self.window.title("Virtual Shell Emulator")

        # Text widget for displaying output
        self.output = ScrolledText(self.window, wrap=WORD, height=20, width=80)
        self.output.pack(padx=10, pady=10)

        # Entry widget for command input
        self.entry = Entry(self.window, width=80)
        self.entry.pack(padx=10, pady=(0, 10))
        self.entry.bind("<Return>", self.execute_command)

    def execute_command(self, event=None):
        command = self.entry.get()
        self.entry.delete(0, END)
        try:
            result = self.handle_command(command)
            self.output.insert(END, f"{self.shell.pwd()}$ {command}\n{result}\n\n")
            self.output.see(END)
        except Exception as e:
            self.output.insert(END, f"Error: {e}\n\n")
            self.output.see(END)

    def handle_command(self, command):
        parts = command.split()
        cmd = parts[0]
        args = parts[1:]

        if cmd == "pwd":
            return self.shell.pwd()
        elif cmd == "ls":
            return "\n".join(self.shell.ls())
        elif cmd == "cd":
            self.shell.cd(args[0])
            return ""
        elif cmd == "cat":
            return self.shell.cat(args[0])
        elif cmd == "mkdir":
            return self.shell.mkdir(args[0])
        elif cmd == "nano":
            filename, content = args[0], ' '.join(args[1:])
            return self.shell.nano(filename, content)
        elif cmd == "tree":
            return self.shell.tree()
        elif cmd == "mv":
            return self.shell.mv(args[0], args[1])
        elif cmd == "exit":
            self.window.quit()
            return "Exiting..."
        else:
            return f"Command {cmd} not found."

    def run(self):
        self.window.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Virtual Shell Emulator with GUI")
    parser.add_argument("zip_file", help="C:\\Users\\pasha\\PycharmProjects\\Konfig_1")
    args = parser.parse_args()

    shell = VShell(args.zip_file)
    gui = ShellGUI(shell)
    gui.run()


if __name__ == "__main__":
    main()
