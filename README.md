# Vacation_bot

# Telegram Vacation Bot

This bot helps teams track vacations and other types of absences via Telegram.

## Features

* **Team Registration / Switching**: Register a new team or switch between existing ones using `/vacabot`.
* **Leave Management**:

  * Add, view, edit, and delete various leave types:

    * Отпуск (Vacation) — 28-day limit per calendar year.
    * Отгулы (Time Off) — no limits.
    * ОЗС (Unpaid Leave) — no limits.
    * Командировка (Business Trip) — no limits.
* **Global Search**: Search across all teams by employee name.
* **Interactive Menu**: Custom `/vacabot` command and reply keyboards for intuitive navigation.

## Requirements

* Python 3.8+
* `python-telegram-bot` library

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/telegram-vacation-bot.git
   cd telegram-vacation-bot
   ```
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Rename `.env.example` to `.env` and set your bot token:

   ```env
   TOKEN=YOUR_TELEGRAM_BOT_TOKEN
   ```
2. Ensure write permissions for data files in the working directory.

## Usage

Start the bot:

```bash
python vacation.py
```

### Commands & Menu

| Button / Command   | Description                         |
| ------------------ | ----------------------------------- |
| `/vacabot`         | Register or show main menu          |
| ➕ Отпуск           | Add a vacation (up to 28 days/year) |
| ➕ Отгулы           | Add time off                        |
| ➕ ОЗС              | Add unpaid leave                    |
| ➕ Командировка     | Add a business trip                 |
| 📅 Отпуска         | View all leave records              |
| ✏️ Редактировать   | Edit an existing record             |
| ❌ Удалить          | Delete a record                     |
| ℹ️ Помощь          | Show help text                      |
| 🔄 Сменить команду | Switch between teams                |
| 🔍 Поиск           | Search for a colleague across teams |

## File Structure

```
vacation.py       # Main bot implementation
README.md         # Project documentation
```

## License

This project is licensed under the MIT License. Feel free to use and modify.
