# Dota Ready Helper

[![GitHub release](https://img.shields.io/github/v/release/Krealiss/dota-ready-helper)](https://github.com/Krealiss/dota-ready-helper/releases)
[![License](https://img.shields.io/github/license/Krealiss/dota-ready-helper)](LICENSE.txt)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/Krealiss/dota-ready-helper)](https://github.com/Krealiss/dota-ready-helper/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Krealiss/dota-ready-helper)](https://github.com/Krealiss/dota-ready-helper/issues)

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

3. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Add your Telegram bot token and chat ID
   - Adjust recognition thresholds if needed

4. **Run:**
```bash
python main.py
```

### Telegram Bot Setup

1. Create a bot via [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Get your chat ID (send a message to your bot, then visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`)
4. Add both to `.env` file

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
├── gui.py               # GUI interface
├── .env.example         # Environment template
├── requirements.txt     # Dependencies
└── assets/              # Reference images
    ├── prinyat.png
    ├── search_game.png
    ├── is_searching_game.png
    └── stop.png
```

### Building Executable

```bash
pyinstaller build.spec
```

The executable will be in the `dist/` folder.

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

3. **Налаштуйте оточення:**
   - Скопіюйте `.env.example` в `.env`
   - Додайте токен Telegram бота та chat ID
   - За потреби налаштуйте пороги розпізнавання

4. **Запустіть:**
```bash
python main.py
```

### Налаштування Telegram бота

1. Створіть бота через [@BotFather](https://t.me/botfather)
2. Отримайте токен бота
3. Отримайте ваш chat ID (надішліть повідомлення боту, потім відвідайте `https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates`)
4. Додайте обидва значення у файл `.env`

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

### Збірка виконуваного файлу

```bash
pyinstaller build.spec
```

Виконуваний файл буде у папці `dist/`.

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
