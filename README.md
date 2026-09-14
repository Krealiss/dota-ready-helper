# Dota Ready Helper

[![GitHub release](https://img.shields.io/github/v/release/Krealiss/dota-ready-helper)](https://github.com/Krealiss/dota-ready-helper/releases)
[![License](https://img.shields.io/github/license/Krealiss/dota-ready-helper)](LICENSE.txt)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/Krealiss/dota-ready-helper)](https://github.com/Krealiss/dota-ready-helper/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Krealiss/dota-ready-helper)](https://github.com/Krealiss/dota-ready-helper/issues)
[![tests](https://github.com/Krealiss/dota-ready-helper/actions/workflows/tests.yml/badge.svg)](https://github.com/Krealiss/dota-ready-helper/actions/workflows/tests.yml)

🎮 Automatic match acceptance helper for Dota 2 with Telegram bot control

[Українська версія](#ukrainian-version) | [English](#english-version)

---

## English Version

### Features

- ✅ Automatic "Accept" button recognition when match is found
- 🤖 Remote control via Telegram bot (start/stop search)
- ⌨️ Hotkeys for quick control
- 📊 Comprehensive event logging
- 🔒 Secure token storage in `.env`
- 🎯 Optimized search (grayscale, central region)
- 📈 Match statistics tracking

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Krealiss/dota-ready-helper.git
cd dota-ready-helper
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run:**
```bash
python main.py
```

On the first run a setup window opens and writes the `.env` file for you.
Fine-tune recognition thresholds there later if needed.

### Telegram Bot Setup

1. Create a bot via [@BotFather](https://t.me/botfather) and copy the token
2. Send any message to your new bot
3. Start the helper — the setup window asks for the token and fills in the
   chat ID by itself, then sends a test message to confirm everything works

To change the token or chat ID later:

```bash
python main.py --setup
```

Without PyQt6 installed the same wizard runs in the console.

### Calibration

Right after the Telegram setup, a calibration wizard opens and walks you
through capturing the search button, the "searching" indicator and the stop
button from your own Dota client — so recognition works no matter your
interface language, UI scale, or color theme. It appears automatically the
first time no calibration exists yet.

If your Dota window resolution changes later, the saved calibration is
rescaled automatically in the background — you are not interrupted for it.

Skipping the wizard (or closing it) is a supported choice: match accepting
keeps working either way, because the Accept button is found by its color,
not by a saved template. The only thing you lose by skipping is remote
start/stop of the game search from Telegram.

To reopen the wizard at any time:

```bash
python main.py --calibrate
```

### Controls

#### Telegram Commands
- `/start` or `/menu` — show control menu
- `/status` — check bot status

#### Hotkeys
- `F6` — pause/resume
- `F7` — exit
- `F8` — start game search
- `F9` — stop game search

### Configuration

All settings can be adjusted in `.env`:
- `SCAN_INTERVAL` — screen check frequency (seconds)
- `CONFIDENCE_*` — recognition confidence thresholds (0.0-1.0)
- `CLICK_COOLDOWN` — pause after click (seconds)
- `MESSAGE_COOLDOWN` — minimum time between Telegram messages (seconds)
- `NO_GAME_POLL_INTERVAL` — pause between checks while Dota is not running (seconds)
- `ACCEPT_COLOR_FALLBACK` — detect the green Accept button by color (`1`/`0`)

### Accept Button Variants

Dota 2 shows several versions of the ready popup (plain button, or the full
"Your game is ready / ALL PICK" panel with match quality details). The helper
handles them in two ways:

1. **Templates** — every `assets/prinyat*.png` file is tried. To add a variant,
   crop just the button from a screenshot and save it as e.g.
   `assets/prinyat_allpick.png`.
2. **Color fallback** — if no template matches, the green button is located by
   its color and shape inside the center region. This works without any template.

To check what the bot currently sees, open the ready popup and run:

```bash
python image_recognition.py
```

It prints the result of every detection method and saves an annotated screenshot
to `logs/accept_debug.png`.

### Project Structure

```
dota-ready-helper/
├── main.py              # Entry point
├── config.py            # Configuration loader
├── logger.py            # Logging system
├── telegram_bot.py      # Telegram bot handler
├── dota_helper.py       # Core logic
├── image_recognition.py # Image recognition
├── stats_tracker.py     # Statistics tracking
├── error_handler.py     # Error handling
├── report_exporter.py   # Report export (CSV/JSON/HTML/TXT)
├── setup_dialog.py      # First-run setup wizard (writes .env)
├── calibration.py       # Calibration storage and auto-detection logic
├── calibration_wizard.py        # Pure detection helpers (no Qt)
├── calibration_wizard_dialog.py # Calibration wizard UI (PyQt6)
├── .env.example         # Environment template
├── requirements.txt     # Dependencies
├── requirements-dev.txt # Dependencies for running tests
├── tests/               # Test suite
└── assets/              # Reference images
    ├── prinyat.png      # Accept button (add prinyat_*.png for more variants)
    ├── search_game.png
    ├── is_searching_game.png
    └── stop.png
```

### Building Executable

Build files are not kept in the repository, so pass the options directly:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "assets;assets" main.py
```

The executable will be in the `dist/` folder.

### Running Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests -v
```

The suite covers accept-button detection (all popup variants, plus false
positives on a normal game screen), Telegram authorization and match
statistics. It runs on every push and pull request via GitHub Actions.

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

### Disclaimer

This tool is for educational purposes. Use at your own risk. The authors are not responsible for any consequences of using this software.

---

## Ukrainian Version

### Можливості

- ✅ Автоматичне розпізнавання кнопки "Прийняти" при знаходженні матчу
- 🤖 Керування через Telegram бот (запуск/зупинка пошуку)
- ⌨️ Гарячі клавіші для швидкого керування
- 📊 Логування всіх подій
- 🔒 Безпечне зберігання токенів у `.env`
- 🎯 Оптимізований пошук (grayscale, центральний регіон)
- 📈 Відстеження статистики матчів

### Встановлення

1. **Клонуйте репозиторій:**
```bash
git clone https://github.com/Krealiss/dota-ready-helper.git
cd dota-ready-helper
```

2. **Встановіть залежності:**
```bash
pip install -r requirements.txt
```

3. **Запустіть:**
```bash
python main.py
```

При першому запуску відкриється вікно налаштування, яке саме створить файл
`.env`. Пороги розпізнавання можна підправити там же пізніше.

### Налаштування Telegram бота

1. Створіть бота через [@BotFather](https://t.me/botfather) і скопіюйте токен
2. Напишіть своєму боту будь-яке повідомлення
3. Запустіть програму — вікно налаштування запитає токен, саме визначить
   chat ID і надішле тестове повідомлення для перевірки

Щоб змінити токен або chat ID пізніше:

```bash
python main.py --setup
```

Без встановленого PyQt6 той самий майстер працює у консолі.

### Калібрування

Одразу після налаштування Telegram відкривається майстер калібрування: він
проведе через знімання кнопки пошуку, індикатора «йде пошук» і кнопки
скасування з твого власного клієнта Dota — так розпізнавання працює
незалежно від мови інтерфейсу, масштабу чи кольорової теми. Майстер
з'являється автоматично, коли калібрування ще немає.

Якщо потім зміниться розмір вікна Dota, збережене калібрування
перераховується автоматично у фоні — це не переривує роботу програми.

Пропустити майстер (або просто закрити його) — це підтримуваний варіант:
приймання матчів працює в обох випадках, бо кнопка «Прийняти» шукається за
кольором, а не за збереженим шаблоном. Пропуск вимикає лише дистанційний
запуск і зупинку пошуку гри через Telegram.

Щоб відкрити майстер знову в будь-який момент:

```bash
python main.py --calibrate
```

### Керування

#### Команди Telegram
- `/start` або `/menu` — показати меню керування
- `/status` — перевірити статус бота

#### Гарячі клавіші
- `F6` — пауза/продовження
- `F7` — вихід
- `F8` — запустити пошук гри
- `F9` — зупинити пошук гри

### Налаштування

Всі параметри можна змінити у `.env`:
- `SCAN_INTERVAL` — частота перевірки екрана (секунди)
- `CONFIDENCE_*` — пороги впевненості розпізнавання (0.0-1.0)
- `CLICK_COOLDOWN` — пауза після кліку (секунди)
- `MESSAGE_COOLDOWN` — мінімальний час між Telegram повідомленнями (секунди)
- `NO_GAME_POLL_INTERVAL` — пауза між перевірками, коли Dota не запущена (секунди)
- `ACCEPT_COLOR_FALLBACK` — пошук зеленої кнопки за кольором (`1`/`0`)

### Варіанти кнопки "Прийняти"

Dota 2 показує кілька версій вікна прийняття: просту кнопку або повну панель
«Ваша гра готова / ALL PICK» з деталями якості матчу. Бот обробляє їх двома
способами:

1. **Шаблони** — перебираються всі файли `assets/prinyat*.png`. Щоб додати новий
   варіант, виріжте зі скриншота саму кнопку та збережіть, наприклад, як
   `assets/prinyat_allpick.png`.
2. **Пошук за кольором** — якщо жоден шаблон не збігся, зелена кнопка шукається
   за кольором і формою в центральній області екрана. Працює без шаблону взагалі.

Щоб перевірити, що саме бачить бот, відкрийте вікно прийняття та запустіть:

```bash
python image_recognition.py
```

Команда виведе результат кожного способу пошуку та збереже скриншот з розміткою
у `logs/accept_debug.png`.

### Збірка виконуваного файлу

Файли збірки не зберігаються у репозиторії, тому передайте параметри напряму:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "assets;assets" main.py
```

Виконуваний файл буде у папці `dist/`.

### Запуск тестів

```bash
pip install -r requirements-dev.txt
python -m pytest tests -v
```

Тести покривають розпізнавання кнопки "Прийняти" (усі варіанти вікна та
відсутність хибних спрацювань на звичайному ігровому екрані), авторизацію
Telegram і облік матчів. Вони запускаються на кожен push і pull request
через GitHub Actions.

### Внесок у проект

Ми вітаємо внески! Будь ласка, не соромтеся надсилати Pull Request.

1. Зробіть Fork репозиторію
2. Створіть гілку для вашої функції (`git checkout -b feature/AmazingFeature`)
3. Закомітьте зміни (`git commit -m 'Add some AmazingFeature'`)
4. Відправте у гілку (`git push origin feature/AmazingFeature`)
5. Відкрийте Pull Request

### Ліцензія

Цей проект ліцензовано під MIT License - дивіться файл [LICENSE.txt](LICENSE.txt) для деталей.

### Застереження

Цей інструмент призначений для освітніх цілей. Використовуйте на свій ризик. Автори не несуть відповідальності за будь-які наслідки використання цього програмного забезпечення.
