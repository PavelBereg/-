import unittest
import tempfile
import zipfile
import os
from vshell import VShell

class TestVShell(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.zip_path = os.path.join(self.temp_dir, "test.zip")
        with zipfile.ZipFile(self.zip_path, 'w') as zf:
            zf.writestr("file1.txt", "Content of file1")
            zf.writestr("dir1/file2.txt", "Content of file2")
            zf.writestr("dir1/subdir/file3.txt", "Content of file3")
        self.shell = VShell(self.zip_path)

    def test_load_from_zip_empty(self):
        with zipfile.ZipFile(self.zip_path, 'w') as zf:
            pass  # Создаем пустой zip-файл
        shell = VShell(self.zip_path)
        self.assertEqual(shell.filesystem, {})  # Проверяем что файловая система пуста

    def test_load_from_zip_corrupted(self):
        with open(self.zip_path, 'wb') as f:
            f.write(b'This is not a zip file')  # Создаем битый файл
        with self.assertRaises(zipfile.BadZipFile):
            VShell(self.zip_path)

    def test_mkdir_existing(self):
        with zipfile.ZipFile(self.zip_path, 'w') as zf:
            zf.writestr("dir1/file1.txt", "content")
        shell = VShell(self.zip_path)
        with self.assertRaises(FileExistsError):
            shell.mkdir("dir1")

    def test_nano_in_subdir(self):
        with zipfile.ZipFile(self.zip_path, 'w') as zf:
            zf.writestr("dir1/file1.txt", "content")
        shell = VShell(self.zip_path)
        shell.nano("dir1/new_file.txt", "new content")
        self.assertEqual(shell.cat("dir1/new_file.txt"), "new content")

    def test_mv_file_to_subdir(self):
        with zipfile.ZipFile(self.zip_path, 'w') as zf:
            zf.writestr("file1.txt", "content")
            zf.writestr("dir1/", "")
        shell = VShell(self.zip_path)
        shell.mv("file1.txt", "dir1/moved_file.txt")
        self.assertEqual(shell.cat("dir1/moved_file.txt"), "content")

    def test_abs_path_relative(self):
        shell = VShell(self.zip_path)
        shell.current_directory = "/dir1"
        self.assertEqual(shell._abs_path("file.txt"), "/dir1/file.txt")
        self.assertEqual(shell._abs_path("../file.txt"), "/file.txt")
        self.assertEqual(shell._abs_path("/file.txt"), "/file.txt")
    def tearDown(self):
        os.remove(self.zip_path)
        os.rmdir(self.temp_dir)

    # pwd тесты
    def test_pwd_root(self):
        self.assertEqual(self.shell.pwd(), "/")

    def test_pwd_after_mkdir(self):
        self.shell.mkdir("new_dir")
        self.shell.cd("new_dir")
        self.assertEqual(self.shell.pwd(), "/new_dir")

    # ls тесты
    def test_ls_root(self):
        self.assertEqual(sorted(self.shell.ls()), ['dir1', 'file1.txt'])

    def test_ls_subdir(self):
        self.shell.cd("dir1")
        self.assertEqual(sorted(self.shell.ls()), ['file2.txt', 'subdir'])

    # cd тесты
    def test_cd_to_existing_dir(self):
        self.shell.cd("dir1")
        self.assertEqual(self.shell.pwd(), "/dir1")

    def test_cd_to_parent(self):
        self.shell.cd("dir1")
        self.shell.cd("..")
        self.assertEqual(self.shell.pwd(), "/")

    # cat тесты
    def test_cat_existing_file(self):
        self.assertEqual(self.shell.cat("file1.txt"), "Content of file1")

    def test_cat_file_in_subdir(self):
        self.shell.cd("dir1")
        self.assertEqual(self.shell.cat("file2.txt"), "Content of file2")

    # mv тесты
    def test_mv_in_same_dir(self):
        self.shell.mv("file1.txt", "renamed_file.txt")
        self.assertIn("renamed_file.txt", self.shell.ls())
        self.assertNotIn("file1.txt", self.shell.ls())

    def test_mv_between_existing_dirs(self):
        self.shell.mkdir("new_dir")
        self.shell.mv("file1.txt", "new_dir/moved_file.txt")
        self.shell.cd("new_dir")
        self.assertIn("moved_file.txt", self.shell.ls())

    # nano тесты
    def test_nano_create_file(self):
        self.shell.mkdir("test_dir")
        self.shell.cd("test_dir")
        self.shell.nano("new_file.txt", "Test content")
        self.assertEqual(self.shell.cat("new_file.txt"), "Test content")

    def test_nano_overwrite_file(self):
        self.shell.mkdir("test_dir")
        self.shell.cd("test_dir")
        self.shell.nano("file.txt", "First content")
        self.shell.nano("file.txt", "Updated content")
        self.assertEqual(self.shell.cat("file.txt"), "Updated content")

    # tree тесты
    def test_tree_root(self):
        tree_output = self.shell.tree()
        self.assertIn("file1.txt", tree_output)
        self.assertIn("dir1", tree_output)

    def test_tree_with_subdir(self):
        tree_output = self.shell.tree()
        self.assertIn("dir1/file2.txt", tree_output)
        self.assertIn("dir1/subdir/file3.txt", tree_output)

if __name__ == '__main__':
    unittest.main()
