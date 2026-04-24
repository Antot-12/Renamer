# ✨ Перейменувач / Renamer

> Перетягни файли ➡️ обери шаблон ➡️ натисни 🚀 — готово!  
> Drag & drop ➡️ choose template ➡️ press 🚀 — done!

---

## 📸 Приклад / Quick Look

| Стара назва | ➡️ | Нова назва |
|----------|----|----------|
| `01‑Track.mp3` | | `Coldplay - Yellow.mp3` |
| `IMG_20250728.jpg` | | `Відпустка в Іспанії.jpg` |
| `report_final.pdf` | | `01 - report_final.pdf` |

<br>

<img src="pic.png" alt="Renamer preview" width="1920"/>

---

## 🌟 Можливості / Features

- 🎧 **Розумні аудіо теги** — автоматично бере Виконавця і Назву з ID3 / FLAC / тощо
- ✍️ **Шаблони** — `Виконавець - Назва`, `Назва (Виконавець)`, `## - Назва`, `ВЕЛИКІ ЛІТЕРИ`, `малі літери`
- ✂️ **Префікс / суфікс + знайти/замінити** — швидке масове редагування
- 🏷️ **Будь-які типи файлів**: аудіо, зображення, документи, відео, архіви, код, ігри, презентації
- 🚚 **Переміщення або копіювання** — збережи оригінали
- 🎯 **Цільова папка** — зберігай всі файли в одному місці
- 🖱️ **Контекстне меню** — перейменуй окремий файл, видали, очисти список
- 🔄 **Перетягування папок** — автоматичне сканування підпапок
- ⚙️ **Сторінка налаштувань** — налаштуй під себе без постійних підтверджень
- 🗒️ **Живий журнал** — бач що зроблено ✅ або що не вдалося ❌
- 🌑 **Темна тема** з `ttkbootstrap`
- 📦 **Портативний EXE** — просто запусти, Python не потрібен

---

## 💻 Вимоги / Requirements

| Інструмент | Версія |
|------------|--------|
| Python | 3.9 - 3.12 |
| Windows | 10 / 11 |
| macOS | 10.15+ |
| Linux | Ubuntu 20.04+ |

---

## 🚀 Встановлення / Installation

### Windows (найпростіший спосіб)

```powershell
# 1) Клонуй репозиторій
git clone https://github.com/Antot-12/Renamer.git
cd Renamer

# 2) Запусти install.bat (встановить залежності)
install.bat

# 3) Запусти програму
run.bat
```

### Windows / macOS / Linux (з venv)

```bash
# 1) Клонуй репозиторій
git clone https://github.com/Antot-12/Renamer.git
cd Renamer

# 2) Створи віртуальне середовище
python -m venv .venv

# 3) Активуй його
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4) Встанови залежності
pip install -r requirements.txt

# 5) Запусти
python run.py
```

### Швидкий старт (без venv)

```bash
pip install mutagen Pillow tkinterdnd2 ttkbootstrap
python run.py
```

---

## 📦 Створення EXE / Build EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=ico.ico --name=Renamer run.py
```

Готовий файл буде в папці `dist/Renamer.exe`

---

## ⌨️ Гарячі клавіші / Hotkeys

| Клавіша | Дія |
|---------|-----|
| `Ctrl+A` | Вибрати все |
| `Ctrl+D` | Зняти вибір |
| `Delete` | Видалити вибране |
| `Double-click` на "Нова назва" | Редагувати ім'я |
| `Double-click` на зображенні | Перегляд |

---

## 📁 Структура проекту / Project Structure

```
Renamer/
├── renamer/              # Головний пакет
│   ├── __init__.py
│   ├── app.py           # GUI програми
│   ├── constants.py     # Константи та налаштування
│   ├── metadata.py      # Витягування метаданих
│   └── file_ops.py      # Операції з файлами
├── tests/               # Тести
├── run.py              # Точка входу
├── run.bat             # Запуск для Windows
├── install.bat         # Встановлення для Windows
├── requirements.txt    # Залежності
└── pyproject.toml      # Конфігурація пакету
```

---

## 🐛 Проблеми / Troubleshooting

**ModuleNotFoundError: No module named 'tkinterdnd2'**
```bash
pip install tkinterdnd2 ttkbootstrap mutagen Pillow
```

**Linux: tkinter not found**
```bash
sudo apt install python3-tk
```

**macOS: tkinter issues**
```bash
brew install python-tk
```

---

## 📜 Ліцензія / License

MIT License - використовуй як хочеш!
