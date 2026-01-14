# **README.md — Project Dumper**

# Project Dumper

**Project Dumper** is a developer tool built with **PyQt6** that allows you to instantly obtain a structured “snapshot” of a project: directory tree, file contents, a highlighted diff viewer with click-to-copy, and export to `txt`, `md`, and `json`.

The project is especially useful for:

* code reviews,
* documentation preparation,
* analysis of third-party repositories,
* comparison of changes,
* report generation.

---

# 📦 Features

## **General**

* View project structure as a directory tree.
* Read text files with automatic encoding detection.
* Exclude binary files, dependencies, and “junk” directories.
* Export dumps to **`txt` / `md` / `json`**.
* Fully independent dark and light themes (not tied to the system theme).

---

# 🧭 Application Tabs

## 1. **Overview**

Section for browsing the current project:

* selecting the root directory;
* displaying the directory structure;
* displaying file contents;
* fast text search;
* progress bar during scanning.

### Supports:

* excluding hidden files and directories;
* `.gitignore` support (dynamic, with cache);
* file size limits;
* format filters during export.

---

## 2. **Diff**

A functional diff viewer with:

### ✔ Highlighting:

* `+` — green (additions);
* `-` — red (deletions);
* `diff --git` + 3 following lines — gray;
* hunk headers `@@ ... @@` — only the `@@ ... @@` segment is highlighted in gray;
* lines starting with `@@` **without closing** `@@` — only the first two `@` characters are gray.

### ✔ Click-to-copy:

* **Left click** → copies a line with transformation:

  * removal of service headers,
  * removal of the first character of the line,
  * empty `@@` lines are not copied.

* **Click with modifier (Ctrl/Shift/Alt — as configured in settings)**:

  * copies a group:

    * consecutive `+` lines,
    * consecutive `-` lines,
    * consecutive lines starting with spaces/tabs (context block).

### ✔ Copy highlight animation:

The line/group flashes yellow and smoothly fades out over `N` ms (configurable).

### ✔ Simple workflow:

Paste a diff → click **Scan** → the diff is parsed and highlighted.

---

## 3. **Settings**

Divided into two groups:

### **File logic:**

* `ignore_hidden`
* `ignore_dirs` / `ignore_files`
* `follow_symlinks`
* `detect_encoding`
* `max_file_size`
* `binary_threshold`
* `include_collapsed_in_dump`

### **Diff logic:**

* which modifier is used for group copying:
  `Ctrl` / `Shift` / `Alt` / `Ctrl+Shift`;
* highlight animation duration.

### **Theme:**

* 🌞/🌙 toggle, independent of the system theme.

### **Settings storage**

Settings are stored in:

```
~/.project_dumper.json
```

---

# 📋 Examples

## Example input diff:

```diff
diff --git a/app.py b/app.py
index 31c29da..b12afaf 100644
--- a/app.py
+++ b/app.py
@@ -1,5 +1,6 @@
 import os

+print("Hello!")
 def main():
     return 42
```

### How it is highlighted:

* the first 4 lines are gray;
* the `@@ -1,5 +1,6 @@` segment is gray only inside `@@ ... @@`;
* the line `+print("Hello!")` is green;
* the line starting with a space is white (context);
* the line `def main():` remains unstyled.

### How copying works:

#### Regular click:

Clicking:

```
+print("Hello!")
```

places into the clipboard:

```
print("Hello!")
```

#### Ctrl/Shift/Alt + click:

If the diff contains several consecutive `+` lines, they are copied together:

```
print("Hello!")
print("World!")
```

---

# 🧪 Testing

The project is covered with tests (pytest):

```
pytest -q
```

Covered:

* configuration (load/save, corrupted files);
* file reading (binary detection, streaming);
* walker (`skip_dir`, `build_tree`, `iter_files`);
* gitignore logic;
* `DumpBuilder` in all formats;
* diff logic in full:
  `classify_line`, `strip_for_copy`, `find_hunk_header_prefix`, `get_group_indices`;
* GUI smoke tests: tab presence, **Scan** / **New Diff** actions.

---

# 🏗 Project Architecture

```
project_dumper/
  config.py           – settings load/save
  gui.py              – PyQt6 GUI, 3 tabs, diff, highlighting, animations
  diff_logic.py       – pure diff analysis functions
  walker.py           – project tree traversal
  reader.py           – streaming file reader
  formatter.py        – txt/md/json dump generation
  gitignore_cache.py  – .gitignore support with caching
tests/
  test_*.py           – full logic coverage + GUI smoke tests
main.py               – entry point
```

---

# 🚀 Installation

```bash
git clone https://github.com/BangkokToD/project_dumper.git
cd project_dumper
pip install -r requirements.txt
```

---

# ⚡ Quick Start

The recommended way is to use a virtual environment with **Python 3.12**.

## 1. Create virtual environment

Make sure Python 3.12 is installed:

```bash
python3.12 --version
```

Create a virtual environment:

```bash
python3.12 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

## 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Verify

Run the application:

```bash
python -m project_dumper
```

Run tests:

```bash
python -m pytest -q
```

---

# ▶ Run

## Option 1 — module-based (recommended):

```bash
python -m project_dumper
```

## Option 2 — via main.py:

```bash
python main.py
```

---

# 🤝 Feedback

Author: Bangkok

Email: [tigerofdnepr@gmail.com](mailto:tigerofdnepr@gmail.com)

Telegram: @BangkokToD

GitHub: [https://github.com/BangkokToD](https://github.com/BangkokToD)











# **README.md — Project Dumper**

# Project Dumper

**Project Dumper** — это инструмент разработчика на **PyQt6**, позволяющий мгновенно получить структурированный "снимок" проекта: дерево каталогов, содержимое файлов, diff-просмотр с подсветкой и копированием, экспорт в `txt`, `md`, `json`.

Проект особенно полезен для:

* ревью кода,
* подготовки документации,
* анализа чужих репозиториев,
* сравнения изменений,
* формирования отчётов.

---

# 📦 Возможности

### **Общие функции**

* Просмотр структуры проекта в виде дерева.
* Чтение текстовых файлов с автоматическим определением кодировки.
* Исключение бинарных файлов, зависимостей и "мусорных" директорий.
* Экспорт дампа в **`txt` / `md` / `json`**.
* Полная тёмная и светлая темы, независимые от системной.

---

# 🧭 Вкладки приложения

## 1. **Обзор**

Раздел для просмотра текущего проекта:

* выбор корневой директории;
* отображение структуры каталогов;
* отображение содержимого файлов;
* быстрый поиск по тексту;
* прогресс-бар при сканировании.

### Поддерживает:

* исключение скрытых файлов и директорий;
* учёт `.gitignore` (динамический, с кешем);
* ограничения по размеру файлов;
* фильтры форматов при экспорте.

---

## 2. **Diff**

Функциональный diff-просмотр с:

### ✔ Подсветкой:

* `+` — зелёный (добавления);
* `-` — красный (удаления);
* `diff --git` + 3 строки после — серые;
* заголовки `@@ ... @@` — серым выделяется только сегмент `@@ ... @@`;
* строки, начинающиеся с `@@` **без закрывающих** `@@` — серые только первые две `@`.

### ✔ Копированием по клику:

* **клик ЛКМ** → копируется строка с преобразованием:

  * срез служебных хедеров,
  * удаление первого символа строки,
  * пустые `@@` не копируются.
* **клик с модификатором (Ctrl/Shift/Alt — как указано в настройках)**:

  * копируется группа:

    * подряд идущие строки `+`,
    * подряд идущие строки `-`,
    * подряд идущие строки, начинающиеся с пробела/табов (контекстный блок).

### ✔ Анимацией подсветки при копировании:

строка/группа вспыхивает жёлтым и плавно затухает за `N` мс (настраивается).

### ✔ Простой обработкой:

Вставляешь diff → нажимаешь **Сканировать** → diff фиксируется и подсвечивается.

---

## 3. **Настройки**

Разделение на две группы:

### **Файловая логика:**

* ignore_hidden
* ignore_dirs / ignore_files
* follow_symlinks
* detect_encoding
* max_file_size
* binary_threshold
* include_collapsed_in_dump

### **Diff-логика:**

* какой модификатор используется для группового копирования:
  `Ctrl` / `Shift` / `Alt` / `Ctrl+Shift`;
* длительность анимации подсветки.

### **Тема:**

* переключатель 🌞/🌙, работающий независимо от системной темы.

### **Сохранение настроек**

Настройки сохраняются в:

```
~/.project_dumper.json
```

---

# 📋 Примеры

## Пример входного diff:

```diff
diff --git a/app.py b/app.py
index 31c29da..b12afaf 100644
--- a/app.py
+++ b/app.py
@@ -1,5 +1,6 @@
 import os

+print("Hello!")
 def main():
     return 42
```

### Как это подсвечивается:

* первые 4 строки — серые;
* сегмент `@@ -1,5 +1,6 @@` — серый только внутри `@@ ... @@`;
* строка `+print("Hello!")` — зелёная;
* строка с пробелом — белая (контекст);
* строка `def main():` остаётся обычной.

### Как копирование работает:

#### обычный клик:

Клик по:

```
+print("Hello!")
```

в буфер попадёт:

```
print("Hello!")
```

#### Ctrl/Shift/Alt + клик:

Если в diff есть подряд несколько строк `+`, они копируются целиком:

```
print("Hello!")
print("World!")
```

---

# 🧪 Тестирование

Проект покрыт тестами (pytest):

```
pytest -q
```

Покрыто:

* конфигурация (load/save, битые файлы);
* чтение файлов (binary detection, streaming);
* walker (skip_dir, build_tree, iter_files);
* gitignore-логика;
* DumpBuilder во всех форматах;
* diff-логика полностью:
  classify_line, strip_for_copy, find_hunk_header_prefix, get_group_indices;
* smoke-тесты GUI: наличие вкладок, работа Сканировать / Новый дифф.

---

# 🏗 Архитектура проекта

```
project_dumper/
  config.py          – загрузка/сохранение настроек
  gui.py             – PyQt6 GUI, 3 вкладки, diff, подсветка, анимации
  diff_logic.py      – чистые функции для анализа diff
  walker.py          – обход дерева проекта
  reader.py          – потоковое чтение файлов
  formatter.py       – генерация txt/md/json дампа
  gitignore_cache.py – поддержка .gitignore с кешированием
tests/
  test_*.py          – полное покрытие логики + GUI smoke
main.py              – точка входа
```

---

# 🚀 Установка

```bash
git clone https://github.com/BangkokToD/project_dumper.git
cd project_dumper
pip install -r requirements.txt
```

---

# ⚡ Быстрый старт

Рекомендуемый способ — использовать виртуальное окружение с **Python 3.12**.

## 1. Создание виртуального окружения

Убедись, что Python 3.12 установлен:

```bash
python3.12 --version
```

Создай виртуальное окружение:

```bash
python3.12 -m venv .venv
```

Активируй его:

```bash
source .venv/bin/activate
```

## 2. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Проверка

Запуск приложения:

```bash
python -m project_dumper
```

Запуск тестов:

```bash
python -m pytest -q
```

---

# ▶ Запуск

## Вариант 1 — модульный (рекомендуемый):

```bash
python -m project_dumper
```

## Вариант 2 — через main.py:

```bash
python main.py
```

---

# 🤝 Обратная связь

Автор: Бангкок (Bangkok)
Почта: tigerofdnepr@gmail.com
Telegram: @BangkokToD
GitHub: https://github.com/BangkokToD
