# -*- coding: utf-8 -*-

import configparser
import datetime as dt

from pytz import timezone
from telegram.ext import Updater, CommandHandler

def reminder(context):
    print("sending reply")
    job = context.job
    today = dt.date.today()
    diff = dt.date(today.year, 12, 24) - today
    context.bot.send_message(job.context, text='Only %s days until Xmas' % diff.days)

def start(update, context):
    chat_id = update.message.chat_id
    here = timezone('Europe/Berlin')
    mytime = dt.datetime.combine(dt.date.today(), dt.time(21, 2, 0))
    print(here.localize(mytime))
    localized = here.localize(mytime)
    job = context.job_queue.run_daily(reminder, localized, context=chat_id)
    update.message.reply_text("Ho ho ho!\n\nI will tell you once a day how many days are left until Xmas!");


def help_cmd(update, context):
    update.message.reply_text("Confused? Me too! Sorry :/")


def xmas_bot(token):
    updater = Updater(token, use_context=True)

    myDispatcher = updater.dispatcher

    myDispatcher.add_handler(CommandHandler("start", start, pass_args=True, pass_job_queue=True, pass_chat_data=True))
    myDispatcher.add_handler(CommandHandler("help", help_cmd))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")

    xmas_bot(config['api.telegram.org']['token'])


