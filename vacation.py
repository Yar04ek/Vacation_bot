# vacation.py
# Telegram Vacation Bot
# Features: team registration/switch, add/view/edit/delete various leave types (Отпуск, Отгулы, ОЗС, Командировка),
# 28-day limit per calendar year only for Отпуск, global search, custom command /vacabot

import os
import logging
import datetime
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)

# Команда /vacabot — регистрация или показ меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    if cid not in TEAM_NAMES:
        await update.message.reply_text(
            "👋 Введите название команды (существующая или новая):"
        )
        context.user_data['register_team'] = True
    else:
        await show_main_menu(update)


# Logging config
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TEAM_NAMES = {}  # chat_id -> active team
TEAMS = set()  # known teams
VACATION_PATH = "vacations_{}.txt"

# Conversation states
NAME, START_DATE, END_DATE = range(3)
DEL_NAME, DEL_SELECT, DEL_CONFIRM = range(3)
EDIT_NAME, EDIT_SELECT, EDIT_NEW_START, EDIT_NEW_END = range(4)
SEARCH_NAME = 0


# Utility functions

def write_vacation(team: str, name: str, start: datetime.date, end: datetime.date, leave_type: str):
    with open(VACATION_PATH.format(team), "a", encoding="utf-8") as f:
        f.write(f"{name}: {start.strftime('%d.%m.%Y')} – {end.strftime('%d.%m.%Y')} [{leave_type}]\n")


def read_vacations(team: str) -> list:
    try:
        with open(VACATION_PATH.format(team), "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        return []


def save_vacations(team: str, lines: list):
    with open(VACATION_PATH.format(team), "w", encoding="utf-8") as f:
        f.writelines(lines)


def calculate_days(start: datetime.date, end: datetime.date) -> int:
    return (end - start).days + 1


def total_days_this_year(team: str, name: str, year: int) -> int:
    total = 0
    for line in read_vacations(team):
        if line.startswith(name + ":"):
            try:
                period = line.split(":", 1)[1]
                s_str, e_str = period.split("–")
                s = datetime.datetime.strptime(s_str.strip(), "%d.%m.%Y").date()
                e = datetime.datetime.strptime(e_str.split('[')[0].strip(), "%d.%m.%Y").date()
                if s.year == year:
                    total += calculate_days(s, e)
            except:
                continue
    return total


# Keyboards

def get_main_menu() -> ReplyKeyboardMarkup:
    buttons = [
        ["➕ Отпуск", "➕ Отгулы", "➕ ОЗС", "➕ Командировка"],
        ["📅 Отпуска", "✏️ Редактировать", "❌ Удалить", "ℹ️ Помощь"],
        ["🔄 Сменить команду", "🔍 Поиск"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def show_main_menu(update: Update):
    """
    Показывает приветственное сообщение с инструкцией и главное меню бота.
    """
    # Инструкция по использованию
    help_text = (
        "Я бот для учёта отпусков и других видов отсутствий.\n"
        "➕ Отпуск — добавить отпуск (лимит 28 дней/год);\n"
        "➕ Отгулы — добавить отгулы (без ограничений);\n"
        "➕ ОЗС — добавить отпуск за свой счёт (без ограничений);\n"
        "➕ Командировка — добавить командировку (без ограничений);\n"
        "📅 Отпуска — просмотреть все записи;\n"
        "✏️ Редактировать — изменить существующую запись;\n"
        "❌ Удалить — удалить запись;\n"
        "ℹ️ Помощь — показать этот список команд;\n"
        "🔄 Сменить команду — переключиться между командами;\n"
        "🔍 Поиск — глобальный поиск по имени коллеги."
    )
    # Показываем инструкцию и меню
    await update.message.reply_text(help_text)
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


# Add flow
async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Определяем тип отсутствия из нажатой кнопки
    btn = update.message.text.strip()
    leave_map = {
        "➕ Отпуск": "Отпуск",
        "➕ Отгулы": "Отгулы",
        "➕ ОЗС": "Отпуск за свой счет",
        "➕ Командировка": "Командировка"
    }
    context.user_data['leave_type'] = leave_map.get(btn, 'Отпуск')
    await update.message.reply_text("Введите ваше имя и фамилию:")
    return NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("Введите дату начала (ДД.MM.YYYY):")
    return START_DATE


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['start'] = datetime.datetime.strptime(update.message.text.strip(), "%d.%m.%Y").date()
        await update.message.reply_text("Введите дату окончания (ДД.MM.YYYY):")
        return END_DATE
    except ValueError:
        await update.message.reply_text("Неверный формат. Повторите дату начала:")
        return START_DATE


async def add_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        end = datetime.datetime.strptime(update.message.text.strip(), "%d.%m.%Y").date()
        start = context.user_data.get('start')
        if not start:
            await update.message.reply_text("Сначала введите дату начала через соответствующую команду.")
            return ConversationHandler.END
        if end < start:
            await update.message.reply_text("Дата окончания раньше начала.")
            return END_DATE
        chat_key = str(update.effective_chat.id)
        team = TEAM_NAMES.get(chat_key)
        if not team:
            await update.message.reply_text("Сначала зарегистрируйте или выберите команду через /vacabot.")
            return ConversationHandler.END
        name = context.user_data.get('name')
        if not name:
            await update.message.reply_text("Сначала введите имя и фамилию через соответствующую команду.")
            return ConversationHandler.END
        lt = context.user_data.get('leave_type', 'Отпуск')
        days = calculate_days(start, end)
        # enforce limit only for regular vacations
        if lt == 'Отпуск':
            used = total_days_this_year(team, name, start.year)
            if used + days > 28:
                await update.message.reply_text(f"🚫 Лимит 28 дн./год. Уже {used}, запрошено {days}.")
                context.user_data.pop('leave_type', None)
                return ConversationHandler.END
        write_vacation(team, name, start, end, lt)
        await update.message.reply_text(f"✅ {lt} сохранён ({days} дн.)")
        context.user_data.pop('leave_type', None)
        await show_main_menu(update)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат. Повторите дату окончания:")
        return END_DATE
        await update.message.reply_text("Неверный формат. Повторите дату окончания:")
        return END_DATE


# Delete flow
async def start_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ФИО для удаления:")
    return DEL_NAME


async def delete_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    team = TEAM_NAMES[str(update.effective_chat.id)]
    opts = [v for v in read_vacations(team) if v.startswith(name + ":")]
    if not opts:
        await update.message.reply_text("Не найдено.")
        return ConversationHandler.END
    context.user_data['del_opts'] = opts
    kb = [[InlineKeyboardButton(opt.strip(), callback_data=str(i))] for i, opt in enumerate(opts)]
    await update.message.reply_text("Выберите запись:", reply_markup=InlineKeyboardMarkup(kb))
    return DEL_SELECT


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    idx = int(q.data)
    context.user_data['del_idx'] = idx
    await q.edit_message_text(f"Удалить? {context.user_data['del_opts'][idx]}")
    await q.message.reply_text("да/нет")
    return DEL_CONFIRM


async def finish_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ans = update.message.text.strip().lower()
    team = TEAM_NAMES[str(update.effective_chat.id)]
    if ans == 'да':
        opts = context.user_data['del_opts']
        idx = context.user_data['del_idx']
        lines = read_vacations(team)
        lines.remove(opts[idx])
        save_vacations(team, lines)
        await update.message.reply_text("✅ Удалено")
    else:
        await update.message.reply_text("❌ Отмена")
    await show_main_menu(update)
    return ConversationHandler.END


# Edit flow
async def start_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ФИО для редактирования:")
    return EDIT_NAME


async def edit_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    team = TEAM_NAMES[str(update.effective_chat.id)]
    opts = [v for v in read_vacations(team) if v.startswith(name + ":")]
    if not opts:
        await update.message.reply_text("Не найдено.")
        return ConversationHandler.END
    context.user_data['edit_opts'] = opts
    kb = [[InlineKeyboardButton(opt.strip(), callback_data=str(i))] for i, opt in enumerate(opts)]
    await update.message.reply_text("Выберите запись:", reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_SELECT


async def ask_new_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data['edit_idx'] = int(q.data)
    await q.edit_message_text("Новая дата начала (ДД.MM.YYYY):")
    return EDIT_NEW_START


async def ask_new_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['start'] = datetime.datetime.strptime(update.message.text.strip(), "%d.%m.%Y").date()
        await update.message.reply_text("Новая дата окончания (ДД.MM.YYYY):")
        return EDIT_NEW_END
    except ValueError:
        await update.message.reply_text("Неверный формат. Повторите дату начала:")
        return EDIT_NEW_START


async def finish_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        end = datetime.datetime.strptime(update.message.text.strip(), "%d.%m.%Y").date()
        start = context.user_data['start']
        if end < start:
            await update.message.reply_text("Ошибка: дата окончания раньше начала.")
            return EDIT_NEW_END
        opts = context.user_data['edit_opts']
        idx = context.user_data['edit_idx']
        old = opts[idx]
        name = old.split(":", 1)[0]
        team = TEAM_NAMES[str(update.effective_chat.id)]
        lt = context.user_data.get('leave_type', 'Отпуск')
        if lt == 'Отпуск':
            period = old.split(":", 1)[1]
            s_str, e_str = period.split("–")
            old_s = datetime.datetime.strptime(s_str.strip(), "%d.%m.%Y").date()
            old_e = datetime.datetime.strptime(e_str.split('[')[0].strip(), "%d.%m.%Y").date()
            used = total_days_this_year(team, name, start.year) - calculate_days(old_s, old_e)
            new_days = calculate_days(start, end)
            if used + new_days > 28:
                await update.message.reply_text("🚫 Лимит 28 дн./год превышен.")
                context.user_data.pop('leave_type', None)
                return ConversationHandler.END
        lines = read_vacations(team)
        lines.remove(old)
        write_vacation(team, name, start, end, lt)
        save_vacations(team, lines)
        await update.message.reply_text("✅ Обновлено")
        context.user_data.pop('leave_type', None)
        await show_main_menu(update)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат. Повторите дату окончания:")
        return EDIT_NEW_END


# Global search
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ФИО коллеги для поиска:")
    return SEARCH_NAME


async def finish_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    results = []
    for team in sorted(TEAMS):
        lines = [l for l in read_vacations(team) if l.startswith(name + ":")]
        if lines:
            results.append(f"Команда {team}:\n{''.join(lines)}")
    if not results:
        await update.message.reply_text(f"Не найдено записей для {name}.")
    else:
        await update.message.reply_text("\n".join(results))
    await show_main_menu(update)
    return ConversationHandler.END


# Message router
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    txt = update.message.text.strip()

    # Шаг 1. Если ждём ввода названия команды
    if context.user_data.get('register_team'):
        team = txt
        path = VACATION_PATH.format(team)
        # Если такая команда уже известна или есть файл — просто присоединяемся
        if team in TEAMS or os.path.exists(path):
            TEAMS.add(team)
            TEAM_NAMES[cid] = team
            open(path, 'a').close()
            await update.message.reply_text(f"✅ Присоединились к команде '{team}'")
            context.user_data.pop('register_team')
            await show_main_menu(update)
        else:
            # Иначе предлагаем создать
            await update.message.reply_text(f"Команда '{team}' не найдена. Создать? (да/нет)")
            context.user_data['confirm_team'] = team
            context.user_data.pop('register_team')
        return

    # Шаг 2. Обработка ответа на предложение создания новой команды
    if context.user_data.get('confirm_team'):
        ans = txt.lower()
        team = context.user_data.pop('confirm_team')
        if ans in ['да', 'yes']:
            TEAMS.add(team)
            TEAM_NAMES[cid] = team
            # создаём файл на диске сразу
            open(VACATION_PATH.format(team), 'a').close()
            await update.message.reply_text(f"✅ Команда '{team}' создана и выбрана")
            await show_main_menu(update)
        else:
            # повторный ввод
            await update.message.reply_text("Хорошо, введите название команды снова:")
            context.user_data['register_team'] = True
        return

    # Если пользователь вообще не в команде
    if cid not in TEAM_NAMES:
        await update.message.reply_text("Введите /vacabot для регистрации или выбора команды.")
        return

    # Далее уже стандартные действия по кнопкам…
    if txt == "🔄 Сменить команду":
        # "выходим" из текущей, но не удаляем её
        TEAM_NAMES.pop(cid, None)
        context.user_data['register_team'] = True
        await update.message.reply_text("🔄 Введите название команды для переключения:")
        return

    leave_map = {
        "➕ Отпуск": "Отпуск",
        "➕ Отгулы": "Отгулы",
        "➕ ОЗС": "Отпуск за свой счёт",
        "➕ Командировка": "Командировка"
    }
    if txt in leave_map:
        context.user_data['leave_type'] = leave_map[txt]
        return await start_add(update, context)

    if txt == "📅 Отпуска":
        team = TEAM_NAMES[cid]
        vs = read_vacations(team)
        if not vs:
            await update.message.reply_text("Список пуст.")
        else:
            sorted_vs = sorted(
                vs,
                key=lambda l: datetime.datetime.strptime(
                    l.split(":",1)[1].split("–")[0].strip(), "%d.%m.%Y"
                )
            )
            await update.message.reply_text("📅 Отпуска:\n" + "".join(sorted_vs))
        return

    if txt == "✏️ Редактировать":
        return await start_edit(update, context)

    if txt == "❌ Удалить":
        return await start_delete(update, context)

    if txt == "ℹ️ Помощь":
        help_text = (
            "ℹ️ Команды:\n"
            "➕ Отпуск/Отгулы/ОЗС/Командировка — добавить запись\n"
            "📅 Отпуска — список по дате\n"
            "✏️ Редактировать — изменить запись\n"
            "❌ Удалить — удалить запись\n"
            "🔄 Сменить команду — переключиться\n"
            "🔍 Поиск — глобальный поиск по имени"
        )
        await update.message.reply_text(help_text)
        return

    if txt == "🔍 Поиск":
        return await start_search(update, context)

    # Всё остальное игнорируем
    return
# Message router
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    txt = update.message.text.strip()

    # Шаг 1. Если ждём ввода названия команды
    if context.user_data.get('register_team'):
        team = txt
        path = VACATION_PATH.format(team)
        # Если такая команда уже известна или есть файл — просто присоединяемся
        if team in TEAMS or os.path.exists(path):
            TEAMS.add(team)
            TEAM_NAMES[cid] = team
            open(path, 'a').close()
            await update.message.reply_text(f"✅ Присоединились к команде '{team}'")
            context.user_data.pop('register_team')
            await show_main_menu(update)
        else:
            # Иначе предлагаем создать
            await update.message.reply_text(f"Команда '{team}' не найдена. Создать? (да/нет)")
            context.user_data['confirm_team'] = team
            context.user_data.pop('register_team')
        return

    # Шаг 2. Обработка ответа на предложение создания новой команды
    if context.user_data.get('confirm_team'):
        ans = txt.lower()
        team = context.user_data.pop('confirm_team')
        if ans in ['да', 'yes']:
            TEAMS.add(team)
            TEAM_NAMES[cid] = team
            # создаём файл на диске сразу
            open(VACATION_PATH.format(team), 'a').close()
            await update.message.reply_text(f"✅ Команда '{team}' создана и выбрана")
            await show_main_menu(update)
        else:
            # повторный ввод
            await update.message.reply_text("Хорошо, введите название команды снова:")
            context.user_data['register_team'] = True
        return

    # Если пользователь вообще не в команде
    if cid not in TEAM_NAMES:
        await update.message.reply_text("Введите /vacabot для регистрации или выбора команды.")
        return

    # Далее уже стандартные действия по кнопкам…
    if txt == "🔄 Сменить команду":
        # "выходим" из текущей, но не удаляем её
        TEAM_NAMES.pop(cid, None)
        context.user_data['register_team'] = True
        await update.message.reply_text("🔄 Введите название команды для переключения:")
        return

    leave_map = {
        "➕ Отпуск": "Отпуск",
        "➕ Отгулы": "Отгулы",
        "➕ ОЗС": "Отпуск за свой счёт",
        "➕ Командировка": "Командировка"
    }
    if txt in leave_map:
        context.user_data['leave_type'] = leave_map[txt]
        return await start_add(update, context)

    if txt == "📅 Отпуска":
        team = TEAM_NAMES[cid]
        vs = read_vacations(team)
        if not vs:
            await update.message.reply_text("Список пуст.")
        else:
            sorted_vs = sorted(
                vs,
                key=lambda l: datetime.datetime.strptime(
                    l.split(":",1)[1].split("–")[0].strip(), "%d.%m.%Y"
                )
            )
            await update.message.reply_text("📅 Отпуска:\n" + "".join(sorted_vs))
        return

    if txt == "✏️ Редактировать":
        return await start_edit(update, context)

    if txt == "❌ Удалить":
        return await start_delete(update, context)

    if txt == "ℹ️ Помощь":
        help_text = (
            "ℹ️ Команды:\n"
            "➕ Отпуск/Отгулы/ОЗС/Командировка — добавить запись\n"
            "📅 Отпуска — список по дате\n"
            "✏️ Редактировать — изменить запись\n"
            "❌ Удалить — удалить запись\n"
            "🔄 Сменить команду — переключиться\n"
            "🔍 Поиск — глобальный поиск по имени"
        )
        await update.message.reply_text(help_text)
        return

    if txt == "🔍 Поиск":
        return await start_search(update, context)

    # Всё остальное игнорируем
    return



# Entry point
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Хендлер старта бота
    app.add_handler(CommandHandler("vacabot", start))

    # Разговоры по добавлению
    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("➕ Отпуск|➕ Отгулы|➕ ОЗС|➕ Командировка"), start_add)],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
                START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_start)],
                END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_end)],
            },
            fallbacks=[]
        )
    )

    # Разговор по удалению
    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("❌ Удалить"), start_delete)],
            states={
                DEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_by_name)],
                DEL_SELECT: [CallbackQueryHandler(confirm_delete, pattern="^\\d+$")],
                DEL_CONFIRM: [MessageHandler(filters.Regex("^(да|нет)$"), finish_delete)],
            },
            fallbacks=[]
        )
    )

    # Разговор по редактированию
    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("✏️ Редактировать"), start_edit)],
            states={
                EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_by_name)],
                EDIT_SELECT: [CallbackQueryHandler(ask_new_start, pattern="^\\d+$")],
                EDIT_NEW_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_new_end)],
                EDIT_NEW_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_edit)],
            },
            fallbacks=[]
        )
    )

    # Разговор по глобальному поиску
    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("🔍 Поиск"), start_search)],
            states={SEARCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_search)]},
            fallbacks=[]
        )
    )

    # Роутер на все остальные входящие сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    print("✅ Бот запущен...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
