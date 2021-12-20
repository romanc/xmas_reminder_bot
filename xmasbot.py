# -*- coding: utf-8 -*-

import configparser
import datetime as dt
import logging
import random

from pathlib import Path
from pytz import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler,\
    ConversationHandler, Filters, MessageHandler, PicklePersistence, Updater

# configure logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

# emojis
E_alarm = "\U000023F0"
E_blush = "\U0001F60A"
E_calendar = "\U0001F4C5"
E_cookies = "\U0001F36A"
E_gear = "\U00002699"
E_grin = "\U0001F604"
E_notes = "\U0001F3B6"
E_present = "\U0001F381"
E_restart = "\U0001F7E2"
E_rocket = "\U0001F680"
E_santa = "\U0001F385"
E_stop = "\U0001F6D1"
E_tada = "\U0001F389"
E_wave = "\U0001F44B"
E_wink = "\U0001F609"
E_world0 = "\U0001F30D"
E_world1 = "\U0001F30E"
E_world2 = "\U0001F30F"
E_xmas = "\U0001F384"

CHOOSE, HANDLE_XMAS, HANDLE_REMINDER = range(3)

CURRENT_VERSION = "1.3.0"

Whats_new = {"1.3.0":
             ["Send a %s, get a tree" % (E_xmas),
              "Added /about command"],
             "1.2.0":
             ["At any time of the year, use /howlong to ask Santa's bot how "
              "many days remain until Christmas.",
              "Improved /help menu and minor text corrections."],
             "1.1.1":
             ["During the year, Santa's Bot will only send reminders %s on "
              "important dates %s like 350 days until Christmas %s." % (
                  E_alarm, E_calendar, E_xmas),
              "Daily reminders %s will be back starting 50 days before "
              "Christmas %s." % (E_alarm, E_xmas)],
             "1.1.0":
             ["Special messages between Christmas %s and "
              "New Year's Eve" % E_xmas,
              "What's new messages %s" % E_grin,
              "Some code cleanup"]}


def santaSay(text):
    return E_santa + "Ho ho ho!\n\n" + text


def santaSayEscaped(text):
    return E_santa + "Ho ho ho\!\n\n" + text


def newerVersionExists(userVersion):
    (major, minor, patch) = userVersion.split(".")
    (cMajor, cMinor, cPatch) = CURRENT_VERSION.split(".")
    return major < cMajor or (major == cMajor and (
        minor < cMinor or (minor == cMinor and patch < cPatch)))


def setDefaultUserData(context, key, value):
    if key not in context.user_data:
        context.user_data[key] = value


def remove_jobs_by_name(name, context):
    """Removes the job with the given name. Returns true iff a
    job was removed."""
    context.user_data["reminders"] = "off"
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def setup_new_job(chat_id, context):
    here = timezone('Europe/Berlin')
    (hours, minutes) = context.user_data['reminder_time'].split(":")
    localized = here.localize(dt.datetime.combine(
        dt.date.today(), dt.time(int(hours), int(minutes), 0)))

    context.user_data["reminders"] = "on"
    context.job_queue.run_daily(
        reminder, localized, context={
            "chat_id": chat_id, "xmas_day": context.user_data["xmas_day"]},
        name=str(chat_id))


def update_job(chat_id, context):
    remove_jobs_by_name(str(chat_id), context)
    setup_new_job(chat_id, context)


def whatsNewMessage(context):
    ctx = context.job.context
    context.bot.send_message(ctx["chat_id"], text=ctx["text"])


def reminder(context):
    ctx = context.job.context
    today = dt.date.today()
    new_year = today.day == 1 and today.month == 1
    diff = dt.date(today.year, 12, int(ctx["xmas_day"])) - today

    # default message
    message = "Only %s days left until Christmas %s" % (diff.days, E_xmas)

    # Special days
    if diff.days == 0:
        # Christmas
        message = "Merry Christmas %s" % E_xmas
    elif diff.days == 1:
        # the day before Christmas
        message = "Are you ready for Christmas %s? Did you buy presents %s?"\
            "Tomorrow is Christmas %s" % (E_xmas, E_present, E_blush)
    elif diff.days == -1:
        # the day after Christmas
        message = "It's still Christmas %s today %s" % (E_xmas, E_tada)
    elif diff.days < 0:
        # between Xmas and New Year's Eve
        message = "It's still Christmas %s as long as there are Christmas "\
            "cookies %s left. %s" % (E_xmas, E_cookies, E_wink)
    elif new_year:
        default_message = message
        message = "New year, new Christmas %s! %s Oh, and happy new year!" % (
            E_xmas, default_message)

    if new_year or diff.days <= 50 or diff.days % 50 == 0:
        # - send a special message if the year starts
        # - send daily reminders 50 days before Xmas
        # - during the rest of the year, only send reminders for
        #   350, 300, 250, 200, 150, 100, and 50 until Christmas
        context.bot.send_message(
            ctx["chat_id"],
            text=santaSay(message))


def about_cmd(update, context):
    about = "Do you already know Santa\'s "\
        "[blog](https://cattaneo.coffee/santas_bot/)\?\n\n"\
        "Santa\'s bot is an "\
        "[open\-source](https://github.com/romanc/xmas_reminder_bot/) "\
        "project\. It is only made possible by the awesome "\
        "[Python Telegram Bot API](https://github.com/python-telegram-bot)\. "\
        "Kudos and keep up the nice work\!\n\n"\
        "This service is provided \'as is\', without warranty of any kind\."

    update.message.reply_text(
        text=santaSayEscaped(about), parse_mode="MarkdownV2")


def start_cmd(update, context):
    # setting default values
    setDefaultUserData(context, "xmas_day", "24")
    setDefaultUserData(context, "reminder_time", "20:56")
    setDefaultUserData(context, "reminders", "on")
    setDefaultUserData(context, "version", CURRENT_VERSION)

    # setup a new reminder job
    chat_id = update.message.chat_id
    remove_jobs_by_name(str(chat_id), context)
    setup_new_job(chat_id, context)

    # write a nice reply
    reply = "Santa's bot works out of the box, but you can use /settings to "\
        "configure " + E_gear + " almost everything.\n\n"\
        "Just type /help in case you need assistance with anything."
    update.message.reply_text(santaSay(reply))


def stop_cmd(update, context):
    reply = "No reminders found to remove."
    removed = remove_jobs_by_name(str(update.message.chat_id), context)

    if removed:
        reply = E_stop + " All reminders removed. If you change "\
            "your mind use /restart to re-enable them."

    update.message.reply_text(santaSay(reply))


def restart_cmd(update, context):
    chat_id = update.message.chat_id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if len(current_jobs) > 0:
        reply = "You already have reminders configured. Looks like Santa's "\
            "Bot has nothing to do here."
        update.message.reply_text(santaSay(reply))
        return

    setup_new_job(chat_id, context)
    update.message.reply_text(
        santaSay(E_restart + " Restarted your reminders."))


def help_cmd(update, context):
    help_text = "Santa's bot will send you periodic reminders how many days "\
        "are left until Christmas " + E_xmas + ". During the year, there "\
        "will be less reminders than right before Christmas " + E_xmas + \
        " when timing is more curcial for Santa.\n\n"\
        "At any time, use /howlong to ask how long you (or others) need to "\
        "wait for Christmas " + E_xmas + " to arrive.\n\n"\
        "Chosse " + E_gear + " /settings to "\
        "configure almost everything. In particular, you can /stop reminders "\
        + E_stop + " if you don't want them anymore and /restart them once "\
        "you change your mind."
    update.message.reply_text(santaSay(help_text))


def howlong_cmd(update, context):
    today = dt.date.today()
    diff = dt.date(today.year, 12, int(context.user_data["xmas_day"])) - today

    reply = "%s days left until Christmas %s" % (diff.days, E_xmas)

    update.message.reply_text(santaSay(reply))


def cancel_cmd(update, context):
    update.message.reply_text(santaSay("Okay. Gotta go, bye! \U0001F44B"))
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

    current_settings = "Your current configuration looks like this:\n\n"\
        "\t\U00002022 Reminders: %s\n"\
        "\t\U00002022 Christmas day: %s\n"\
        "\t\U00002022 Reminder time: %s\n\n"\
        "What do you want to configure? If these settings look good, use the "\
        "cancel button." % (
            "on " + E_restart if len(jobs) > 0 else "off " + E_stop,
            context.user_data["xmas_day"],
            context.user_data["reminder_time"])

    update.message.reply_text(santaSay(current_settings),
                              reply_markup=markup)
    return CHOOSE


def chooseSetting(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "xmas_day":
        keyboard = [[InlineKeyboardButton("24th", callback_data='24'),
                     InlineKeyboardButton("25th", callback_data='25')]]

        text = "Okay, let's set Christmas day. When is Christmas day for you?"
        query.edit_message_text(text=santaSay(text),
                                reply_markup=InlineKeyboardMarkup(keyboard))
        return HANDLE_XMAS
    elif query.data == "reminder_time":
        keyboard = [[InlineKeyboardButton("8 AM", callback_data="08:00"),
                     InlineKeyboardButton("Noon", callback_data="12:00"),
                     InlineKeyboardButton("6 PM", callback_data="18:00")]]
        text = "Okay, let's set the reminder time. When should I remind you?"\
            " (Times are given in CET)"
        query.edit_message_text(text=santaSay(text),
                                reply_markup=InlineKeyboardMarkup(keyboard))

        return HANDLE_REMINDER
    elif query.data == "cancel":
        query.edit_message_text(text=santaSay(
            "Keeping your settings as is. %s" % E_blush))
        return ConversationHandler.END

    query.edit_message_text(text=santaSay(
        "I'm sorry, I can't find this setting."))
    return ConversationHandler.END


def handleXmasDay(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['xmas_day'] = query.data
    update_job(query.message.chat_id, context)

    reply = "Christmas day %s is now configured to the %sth of December!" % (
        E_xmas, query.data)
    query.edit_message_text(santaSay(reply))
    return ConversationHandler.END


def handleReminderTime(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['reminder_time'] = query.data
    update_job(query.message.chat_id, context)

    reply = "Daily reminders %s are sent at %s from now on!" % (
        E_alarm, query.data)
    query.edit_message_text(santaSay(reply))
    return ConversationHandler.END


def chatWithSanta(update, context):
    # send a tree, get a tree
    message = update.message
    hasTree = message.text and message.text.find(E_xmas) > -1
    hasSticker = message.sticker
    isTreeSticker = hasSticker and message.sticker.emoji.find(E_xmas) > -1
    isTreeSet = hasSticker and message.sticker.set_name == "ElkaTree"
    if hasTree or isTreeSticker or isTreeSet:
        text = "Thank you for this nice Xmas tree. "\
            "Here's a random %s tree for you from my collection." % E_xmas

        trees = Path("./trees").glob("tree*.jpg")
        context.bot.send_photo(
            chat_id=update.message.chat_id,
            caption=santaSay(text),
            photo=open(random.choice(list(trees)), "rb")
        )

    # rocket santa
    hasRocket = message.text and message.text.find(E_rocket) > -1
    isRocketSticker = hasSticker and message.sticker.emoji.find(E_rocket) > -1
    if hasRocket or isRocketSticker:
        context.bot.send_photo(
            chat_id=update.message.chat_id,
            caption="%s I'm a rocket man ... " % E_notes,
            photo=open(Path("./trees/santa-0.jpg"), "rb")
        )

    # hello world
    hasHelloWorld = message.text and (message.text.find(E_wave) > -1
                                      or message.text.find(E_world0) > -1
                                      or message.text.find(E_world1) > -1
                                      or message.text.find(E_world2) > -1)
    hasHWSticker = hasSticker and (message.sticker.emoji.find(E_wave) > -1
                                   or message.sticker.emoji.find(E_world0) > -1
                                   or message.sticker.emoji.find(E_world1) > -1
                                   or message.sticker.emoji.find(E_world2) > -1)
    if hasHelloWorld or hasHWSticker:
        update.message.reply_text(
            parse_mode="MarkdownV2",
            text="```python\nprint('Hello, world!')\n```")


def xmas_bot(token):
    pp = PicklePersistence(filename="xmas_reminder_bot_data")
    updater = Updater(token, persistence=pp, use_context=True)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('settings', settings_cmd)],

        states={
            CHOOSE: [CallbackQueryHandler(chooseSetting)],
            HANDLE_XMAS: [CallbackQueryHandler(handleXmasDay)],
            HANDLE_REMINDER: [CallbackQueryHandler(handleReminderTime)]
        },

        fallbacks=[CommandHandler('cancel', cancel_cmd)]
    )

    myDispatcher = updater.dispatcher
    myDispatcher.add_handler(conv_handler)
    myDispatcher.add_handler(CommandHandler("about", about_cmd))
    myDispatcher.add_handler(CommandHandler("cancel", cancel_cmd))
    myDispatcher.add_handler(CommandHandler("help", help_cmd))
    myDispatcher.add_handler(CommandHandler("howlong", howlong_cmd))
    myDispatcher.add_handler(CommandHandler("start", start_cmd))
    myDispatcher.add_handler(CommandHandler("stop", stop_cmd))
    myDispatcher.add_handler(CommandHandler("restart", restart_cmd))

    # message handler for send a tree, get a tree
    myDispatcher.add_handler(MessageHandler(
        Filters.sticker | (Filters.text & ~Filters.command), chatWithSanta))

    # stored user data
    user_data = pp.get_user_data()

    for item in pp.get_chat_data().items():
        chat_id = item[0]
        this_user = user_data[chat_id]
        if this_user.get("reminders", "off") == "on":
            # new job
            here = timezone('Europe/Berlin')
            (hours, minutes) = this_user['reminder_time'].split(":")
            localized = here.localize(dt.datetime.combine(
                dt.date.today(), dt.time(int(hours), int(minutes), 0)))
            updater.job_queue.run_daily(
                reminder, localized, context={
                    "chat_id": chat_id, "xmas_day": this_user["xmas_day"]},
                name=str(chat_id))

        if newerVersionExists(this_user.get("version", "1.0.2")):
            # we have a newer version -> show what's new
            text = "Santa has been innovating. Here's what's new in "\
                "version %s %s\n\n" % (CURRENT_VERSION, E_tada)
            for note in Whats_new[CURRENT_VERSION]:
                text = text + ("\t\U00002022 %s\n" % note)

            # send a what's new message
            updater.job_queue.run_once(whatsNewMessage, 2, context={
                "chat_id": chat_id, "text": santaSay(text)},
                name="new%s" % str(chat_id))

            # then, update current version
            myDispatcher.user_data[chat_id]["version"] = CURRENT_VERSION

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logger.info("Parsing configfile")
    config = configparser.ConfigParser()
    config.read("config.ini")

    logger.info("Running Xmas Trash Bot")
    xmas_bot(config['api.telegram.org']['token'])
