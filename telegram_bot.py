# bot.py
import importlib
import logging
import sys
import os
import random
import shlex
import shutil
import subprocess
import traceback
from typing import Tuple

import psutil
import telegram
from telegram.ext import Updater
from telegram import (
    ChatAction,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram import Bot
from telegram.parsemode import ParseMode

# import sugaroid_commands as scom
from datetime import datetime
from nltk import word_tokenize
import sugaroid as sug
from sugaroid import sugaroid
from sugaroid import version
from dotenv import load_dotenv
import time
from datetime import timedelta

# get CPU data
process = psutil.Process()
init_cpu_time = process.cpu_percent()

# get the environment variables
load_dotenv()
token = os.getenv("TELEGRAM_TOKEN")

# initialize sugaroid and use discord like spec
sg = sugaroid.Sugaroid()
sg.toggle_discord()

# telegram specific stuff
updater = Updater(token=token, use_context=True)
dispatcher = updater.dispatcher

# get the start time
interrupt_local = False
start_time = datetime.now()

message_length_limit = 4000

bool_keyboard = [
    [
        InlineKeyboardButton("Yes", callback_data="yes"),
        InlineKeyboardButton("No", callback_data="no"),
        InlineKeyboardButton("🤷", callback_data="idk"),
    ]
]


def split_into_packets(response: str) -> Tuple[list, list]:
    messages = []
    for i in range(0, len(response), message_length_limit):
        messages.append(response[i : i + message_length_limit])

    broken_messages = []
    for message in messages:
        broken_messages.extend(message.split("<sugaroid:br>"))

    photos = []
    text_messages = []
    for message in broken_messages:
        print(message, message.strip(), message.strip().startswith("<sugaroid:img>"))
        if message.strip().startswith("<sugaroid:img>"):
            # this is an image
            img_src = message.strip().replace("<sugaroid:img>", "")
            photo = InputMediaPhoto(img_src)
            photos.append(photo)
        else:
            text_messages.append(message.strip())

    photos_groups = []
    for i in range(0, len(photos), 9):
        photos_groups.append(photos[i : i + 9])
    return text_messages, photos_groups


def parse_message_using_sugaroid(
    msg: str, context: CallbackContext, update, is_button=False
) -> None:
    try:
        response = str(sg.parse(msg))
    except Exception:
        # some random error occured. Log it
        error_message = traceback.format_exc(chain=True)
        response = (
            '<pre language="python">'
            "An unhandled exception occurred: " + error_message + "</pre>"
        )
    packets, photos_group = split_into_packets(str(response))
    print(packets)
    for i, packet in enumerate(packets):
        if i == 0:
            # always provide the reply-to
            # for the first message
            if "<sugaroid:yesno>" in packet:
                packet = packet.replace("<sugaroid:yesno>", "")
                reply_markup = InlineKeyboardMarkup(bool_keyboard)
            else:
                reply_markup = None
            if not is_button:
                reply_to_message_id = update.message.message_id
            else:
                reply_to_message_id = None
            context.bot.send_message(
                update.effective_chat.id,
                packet,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        else:
            context.bot.send_message(
                update.effective_chat.id, packet, parse_mode=ParseMode.HTML
            )
    if photos_group:
        logging.info("Found photos group")
        for photos in photos_group:
            if not photos:
                continue
            context.bot.send_message(
                update.effective_chat.id, "Sending a few results! 🚀"
            )
            context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action=ChatAction.UPLOAD_PHOTO,
            )
            logging.info("Sending photo group")
            time.sleep(1)

            context.bot.send_media_group(
                update.effective_chat.id, photos, disable_notification=True
            )


def update_sugaroid(update, context, branch="master"):
    # initiate and announce to the user of the upgrade
    context.bot.send_message(
        update.effective_chat.id, "Updating my brain with new features 😄"
    )

    # execute pip3 install
    pip = shutil.which("pip")
    pip_popen_subprocess = subprocess.Popen(
        shlex.split(
            f"{pip} install --upgrade --force-reinstall --no-deps "
            f"https://github.com/srevinsaju/sugaroid/archive/{branch}.zip"
        ),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    # reload modules
    os.chdir("/")
    importlib.reload(sug)
    importlib.reload(sugaroid)
    importlib.reload(version)

    # updating the bot
    os.chdir(os.path.dirname(sug.__file__))
    git = shutil.which("git")
    # reset --hard
    git_reset_popen_subprocess = subprocess.Popen(
        shlex.split(f"{git} reset --hard origin/master"),
        stdout=sys.stdout,
        stderr=sys.stderr,
    ).wait(500)
    # git pull
    git_pull_popen_subprocess = subprocess.Popen(
        shlex.split(f"{git} pull"), stdout=sys.stdout, stderr=sys.stderr
    )

    context.bot.send_message(
        update.effective_chat.id,
        "Update completed. 😄, Restarting myself  💤",
        parse_mode=ParseMode.HTML,
    )
    sys.exit(1)


def on_ready():
    os.chdir(os.path.dirname(sug.__file__))


def on_akinator_yesno(update, context: telegram.ext.CallbackContext) -> None:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    query.edit_message_text(
        text=f"{query.message.text}\n<i><b>{query.from_user.first_name}</b> selected option: {query.data}</i>",
        parse_mode=ParseMode.HTML,
    )
    context.bot.send_chat_action(
        chat_id=update.effective_message.chat_id, action=ChatAction.TYPING
    )
    parse_message_using_sugaroid(query.data, context, update, is_button=True)


def on_message(update, context: telegram.ext.CallbackContext):
    # if message.author == client.user:
    #    print("Ignoring message sent by another Sugaroid Instance")
    #     return
    global interrupt_local

    if update.effective_message.chat_id not in [
        -1001464483235,
        -1001281270626,
        -1001177507995,
        -435464711,
    ]:
        print("Message from invalid chat ID", update.effective_message.chat_id)
        return

    if (
        update.message is not None
        and update.message.text is not None
        and any(
            (
                update.message.text.startswith(f"@{context.bot.getMe().username}"),
                update.message.text.startswith("!S"),
            )
        )
    ):
        # make the user aware that Sugaroid received the message
        # send the typing status
        context.bot.send_chat_action(
            chat_id=update.effective_message.chat_id, action=ChatAction.TYPING
        )

        # clean the message
        msg = (
            update.message.text.replace(f"@{context.bot.getMe().username}", "")
            .replace("!S", "")
            .strip()
        )
        parse_message_using_sugaroid(msg, context, update)


from telegram.ext import MessageHandler, Filters

on_message_handler = MessageHandler(Filters.text & (~Filters.command), on_message)
dispatcher.add_handler(on_message_handler)
dispatcher.add_handler(CallbackQueryHandler(on_akinator_yesno))
updater.start_polling()
updater.idle()
