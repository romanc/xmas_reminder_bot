# -*- coding: utf-8 -*-

import configparser
import datetime as dt

from pytz import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler,\
    ConversationHandler, PicklePersistence, Updater

# notes to myself
# - this bot works, unless you restart
# - jobs won't "survive" restarts of the bot
# - one option to resolve the issue is to save the on/off state of reminders
#   and the chat_id in the file and then re-add the jobs when the bot starts

# emojis
E_alarm = "\U000023F0"
E_gear = "\U00002699"
E_restart = "\U0001F7E2"
E_santa = "\U0001F385"
E_stop = "\U0001F6D1"
E_xmas = "\U0001F384"
E_blush = "\U0001F60A"

CHOOSE, HANDLE_XMAS, HANDLE_REMINDER = range(3)


def remove_jobs_by_name(name, context):
    """Removes the job with the given name. Returns true iff a
    job was removed."""
    context.user_data["reminders"] = "off"
    current_jobs = context.job_queue.get_jobs_by_name(name)
    print("Jobs found: " + str(len(current_jobs)))
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def setup_new_job(chat_id, context):
    context.user_data["reminders"] = "on"
    here = timezone('Europe/Berlin')
    (hours, minutes) = context.user_data['reminder_time'].split(":")
    mytime = dt.datetime.combine(
        dt.date.today(), dt.time(int(hours), int(minutes), 0))
    print(here.localize(mytime))
    localized = here.localize(mytime)
    context.job_queue.run_daily(
        reminder, localized, context={
            "chat_id": chat_id, "xmas_day": context.user_data["xmas_day"]},
        name=str(chat_id))


def update_job(chat_id, context):
    remove_jobs_by_name(str(chat_id), context)
    setup_new_job(chat_id, context)


def reminder(context):
    ctx = context.job.context
    today = dt.date.today()
    diff = dt.date(today.year, 12, int(ctx["xmas_day"])) - today
    # todo: if diff.days == 0 -> Merry christmas!
    # todo: if diff.days == 1 -> Tomorrow is christmas
    if diff.days < 0:
        diff = dt.date(today.year + 1, 12, int(ctx["xmas_day"])) - today
    context.bot.send_message(
        ctx["chat_id"],
        text="Only %s days left until christmas %s" % (diff.days, E_xmas))


def start_cmd(update, context):
    # setting default values
    if "xmas_day" not in context.user_data:
        context.user_data['xmas_day'] = "24"
    if "reminder_time" not in context.user_data:
        context.user_data["reminder_time"] = "00:01"
    if "reminders" not in context.user_data:
        context.user_data["reminders"] = "on"

    chat_id = update.message.chat_id
    remove_jobs_by_name(str(chat_id), context)
    setup_new_job(chat_id, context)

    reply = E_santa + "Ho ho ho!\n\n"\
        "Santa's bot works out of the box, but you can use /settings to "\
        "configure " + E_gear + " almost everything.\n\n"\
        "You can also /stop the daily reminders " + E_stop + " or /restart "\
        "if you ever stopped receiving them."
    update.message.reply_text(reply)


def stop_cmd(update, context):
    removed = remove_jobs_by_name(str(update.message.chat_id), context)

    if removed:
        update.message.reply_text(
            E_stop + " All reminders removed. If you change "
            "your mind use /restart to re-enable them.")
    else:
        update.message.reply_text("No reminders found to remove.")


def restart_cmd(update, context):
    chat_id = update.message.chat_id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if len(current_jobs) > 0:
        update.message.reply_text("You already have a reminder configured.")
        return

    setup_new_job(chat_id, context)
    update.message.reply_text(E_restart + " Restarted your reminders.")


def help_cmd(update, context):
    help_text = E_santa + "Ho ho ho!\n\nChosse " + E_gear + " /settings to "\
        "configure almost everything. You can also /stop the daily reminders "\
        + E_stop + " if you don't want them anymore."
    update.message.reply_text(help_text)


def cancel_cmd(update, context):
    update.message.reply_text("Okay. Gotta go, bye! \U0001F44B")
    return ConversationHandler.END


def settings_cmd(update, context):
    keyboard = [[InlineKeyboardButton(E_xmas + " day",
                                      callback_data="xmas_day"),
                 InlineKeyboardButton(E_alarm + " time",
                                      callback_data="reminder_time"),
                 InlineKeyboardButton("cancel",
                                      callback_data="cancel")]]
    markup = InlineKeyboardMarkup(keyboard)

    jobs = context.job_queue.get_jobs_by_name(str(update.message.chat_id))
    update.message.reply_text(
        E_santa + "Ho ho ho!\n\n"
        "Your current configuration looks like this:\n\n"
        "\t\U00002022 Reminders: " +
        ("on " + E_restart if len(jobs) > 0 else "off " + E_stop) + "\n"
        "\t\U00002022 Christmas day: " +
        context.user_data["xmas_day"] + "\n"
        "\t\U00002022 Reminder time: " +
        context.user_data["reminder_time"] + "\n\n"
        "What do you want to configure? If these settings look good, use "
        "/cancel to abort.",
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
    elif (query.data == "cancel"):
        query.edit_message_text(text="Keeping your settings as is. " + E_blush)
        return ConversationHandler.END

    query.edit_message_text(text="I'm sorry, I can't find this setting.")
    return ConversationHandler.END


def xmasday(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['xmas_day'] = query.data
    update_job(query.message.chat_id, context)

    reply = "Set Christmas %s to the %sth of December!" % (E_xmas, query.data)
    query.edit_message_text(reply)
    return ConversationHandler.END


def handleReminderTime(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['reminder_time'] = query.data
    update_job(query.message.chat_id, context)

    reply = "Set %s reminder time to %s" % (E_alarm, query.data)
    query.edit_message_text(reply)
    return ConversationHandler.END


def xmas_bot(token):
    pp = PicklePersistence(filename="xmas_reminder_bot_data")
    updater = Updater(token, persistence=pp, use_context=True)

    myDispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('settings', settings_cmd)],

        states={
            CHOOSE: [CallbackQueryHandler(chooseSetting)],
            HANDLE_XMAS: [CallbackQueryHandler(xmasday)],
            HANDLE_REMINDER: [CallbackQueryHandler(handleReminderTime)]
        },

        fallbacks=[CommandHandler('cancel', cancel_cmd)]
    )
    myDispatcher.add_handler(conv_handler)

    myDispatcher.add_handler(CommandHandler("cancel", cancel_cmd))
    myDispatcher.add_handler(CommandHandler("help", help_cmd))
    myDispatcher.add_handler(CommandHandler("start", start_cmd))
    myDispatcher.add_handler(CommandHandler("stop", stop_cmd))
    myDispatcher.add_handler(CommandHandler("restart", restart_cmd))

    # stored user data
    user_data = pp.get_user_data()

    for item in pp.get_chat_data().items():
        print("chat_id", item[0])
        chat_id = item[0]
        this_user = user_data[chat_id]
        print("user_data", this_user)
        if this_user.get("reminders", "off") == "on":
            # new job
            here = timezone('Europe/Berlin')
            (hours, minutes) = this_user['reminder_time'].split(":")
            mytime = dt.datetime.combine(
                dt.date.today(), dt.time(int(hours), int(minutes), 0))
            print(here.localize(mytime))
            localized = here.localize(mytime)
            updater.job_queue.run_daily(
                reminder, localized, context={
                    "chat_id": chat_id, "xmas_day": this_user["xmas_day"]},
                name=str(chat_id))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")

    xmas_bot(config['api.telegram.org']['token'])
