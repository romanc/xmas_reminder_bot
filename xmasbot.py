# -*- coding: utf-8 -*-

import configparser
import datetime as dt

from pytz import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler,\
    ConversationHandler, PicklePersistence, Updater

# emojis
E_alarm = "\U000023F0"
E_gear = "\U00002699"
E_restart = "\U0001F7E2"
E_santa = "\U0001F385"
E_stop = "\U0001F6D1"
E_xmas = "\U0001F384"

CHOOSE, HANDLE_XMAS, HANDLE_REMINDER = range(3)


def remove_jobs_by_name(name, context):
    """Removes the job with the given name. Returns true iff a
    job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    print("Jobs found: " + str(len(current_jobs)))
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def reminder(context):
    print("sending reply")
    job = context.job
    today = dt.date.today()
    diff = dt.date(today.year, 12, 24) - today
    context.bot.send_message(
        job.context,
        text="Only %s days left until christmas %s" % (diff.days, E_xmas))


def start(update, context):
    chat_id = update.message.chat_id
    # remove old job, if it exists
    remove_jobs_by_name(str(chat_id), context)

    # set new job
    here = timezone('Europe/Berlin')
    mytime = dt.datetime.combine(dt.date.today(), dt.time(23, 20, 0))
    print(here.localize(mytime))
    localized = here.localize(mytime)
    context.job_queue.run_daily(reminder, localized, context=chat_id,
                                name=str(chat_id))

    reply = E_santa + "Ho ho ho!\n\n"\
        "Santa's bot works out of the box, but you can use /settings to "\
        "configure " + E_gear + " almost everything.\n\n"\
        "You can also /stop the daily reminders " + E_stop + " or /restart "\
        "if you ever stopped receiving them."
    update.message.reply_text(reply)


def stop_cmd(update, context):
    chat_id = update.message.chat_id
    # remove old job, if it exists
    removed = remove_jobs_by_name(str(chat_id), context)

    if removed:
        update.message.reply_text(
            E_stop + " All reminders removed. If you change "
            "your mind use /restart to re-enable them.")
        return

    update.message.reply_text("No reminders found to remove.")


def restart_cmd(update, context):
    chat_id = update.message.chat_id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if len(current_jobs) > 0:
        update.message.reply_text("You already have a reminder configured.")
        return

    # set new job
    here = timezone('Europe/Berlin')
    mytime = dt.datetime.combine(dt.date.today(), dt.time(23, 22, 0))
    print(here.localize(mytime))
    localized = here.localize(mytime)
    context.job_queue.run_daily(reminder, localized, context=chat_id,
                                name=str(chat_id))
    update.message.reply_text(E_restart + " Restarted your jobs")


def help_cmd(update, context):
    help_text = E_santa + "Ho ho ho!\n\nChosse " + E_gear + " /settings to "\
        "configure almost everything. You can also /stop the daily reminders "\
        + E_stop + " if you don't want them anymore."
    update.message.reply_text(help_text)


def cancel(update, context):
    update.message.reply_text("Okay. Gotta go, bye! \U0001F44B")
    return ConversationHandler.END


def settings(update, context):
    keyboard = [[InlineKeyboardButton(E_xmas + " day",
                                      callback_data="xmas_day"),
                 InlineKeyboardButton(E_alarm + " time",
                                      callback_data="reminder_time")]]

    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(E_santa + "Ho ho ho!\n\nWhat do you want to configure?",
                              reply_markup=markup)

    return CHOOSE


def chooseSetting(update, context):
    query = update.callback_query
    query.answer()

    if (query.data == "xmas_day"):
        keyboard = [[InlineKeyboardButton("24th", callback_data='24'),
                     InlineKeyboardButton("25th", callback_data='25')]]

        query.edit_message_text(text="Okay, let's set Christmas day. Which day"
                                " is Christmas day for you?",
                                reply_markup=InlineKeyboardMarkup(keyboard))
        return HANDLE_XMAS
    elif (query.data == "reminder_time"):
        keyboard = [[InlineKeyboardButton("8 AM", callback_data="08:00"),
                     InlineKeyboardButton("Noon", callback_data="12:00"),
                     InlineKeyboardButton("6 PM", callback_data="18:00")]]
        query.edit_message_text(text="Okay, let's set the reminder time."
                                "When should I remind you?",
                                reply_markup=InlineKeyboardMarkup(keyboard))

        return HANDLE_REMINDER

    query.edit_message_text(text="I'm sorry, I can't find this setting.")
    return ConversationHandler.END


def xmasday(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['xmas_day'] = query.data

    reply = "Set Christmas %s to the %sth of December!" % (E_xmas, query.data)
    query.edit_message_text(reply)
    return ConversationHandler.END


def handleReminderTime(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['reminder_time'] = query.data

    reply = "Set %s reminder time to %s" % (E_alarm, query.data)
    query.edit_message_text(reply)
    return ConversationHandler.END


def xmas_bot(token):
    pp = PicklePersistence(filename="xmas_reminder_bot_data")
    updater = Updater(token, persistence=pp, use_context=True)

    myDispatcher = updater.dispatcher

    myDispatcher.add_handler(CommandHandler(
        "start", start, pass_job_queue=True))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('settings', settings)],

        states={
            CHOOSE: [CallbackQueryHandler(chooseSetting)],
            HANDLE_XMAS: [CallbackQueryHandler(xmasday)],
            HANDLE_REMINDER: [CallbackQueryHandler(handleReminderTime)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    myDispatcher.add_handler(conv_handler)

    myDispatcher.add_handler(CommandHandler("cancel", cancel))
    myDispatcher.add_handler(CommandHandler("help", help_cmd))
    myDispatcher.add_handler(CommandHandler("stop", stop_cmd))
    myDispatcher.add_handler(CommandHandler("restart", restart_cmd))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")

    xmas_bot(config['api.telegram.org']['token'])
