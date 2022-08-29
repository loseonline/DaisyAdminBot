import html
import random
import re
import time
from functools import partial

import DAİSY.modules.sql.welcome_sql as sql
from DAİSY import (DEV_USERS, LOGGER, OWNER_ID, DRAGONS, DEMONS, TIGERS,
                          WOLVES, sw, dispatcher, JOIN_LOGGER)
from DAİSY.modules.helper_funcs.chat_status import (
    is_user_ban_protected,
    user_admin,
)
from DAİSY.modules.helper_funcs.misc import build_keyboard, revert_buttons
from DAİSY.modules.helper_funcs.msg_types import get_welcome_type
from DAİSY.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
    markdown_parser,
)
from DAİSY.modules.log_channel import loggable
from DAİSY.modules.sql.global_bans_sql import is_user_gbanned
from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    run_async,
)
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

VALID_WELCOME_FORMATTERS = [
    "first",
    "last",
    "fullname",
    "username",
    "id",
    "count",
    "chatname",
    "mention",
]

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
}

VERIFIED_USER_WAITLIST = {}


# do not async
def send(update, message, keyboard, backup_message):
    chat = update.effective_chat
    cleanserv = sql.clean_service(chat.id)
    reply = update.message.message_id
    # Clean service welcome
    if cleanserv:
        try:
            dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False
    try:
        msg = update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=reply,
        )
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            msg = update.effective_message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
                quote=False)
        elif excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message +
                    "\nNote: the current message has an invalid url "
                    "in one of its buttons. Please update."),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(
                markdown_parser(backup_message +
                                "\nNote: the current message has buttons which "
                                "use url protocols that are unsupported by "
                                "telegram. Please update."),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message +
                    "\nNote: the current message has some bad urls. "
                    "Please update."),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! got invalid url host errors")
        elif excp.message == "Have no rights to send a message":
            return
        else:
            msg = update.effective_message.reply_text(
                markdown_parser(backup_message +
                                "\nNote: An error occured when sending the "
                                "custom message. Please update."),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
            LOGGER.exception()
    return msg


@run_async
@loggable
def new_member(update: Update, context: CallbackContext):
    bot, job_queue = context.bot, context.job_queue
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    should_welc, cust_welcome, cust_content, welc_type = sql.get_welc_pref(
        chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)

    new_members = update.effective_message.new_chat_members

    for new_mem in new_members:

        welcome_log = None
        res = None
        sent = None
        should_mute = True
        welcome_bool = True
        media_wel = False

        if sw is not None:
            sw_ban = sw.get_ban(new_mem.id)
            if sw_ban:
                return

        if should_welc:

            reply = update.message.message_id
            cleanserv = sql.clean_service(chat.id)
            # Clean service welcome
            if cleanserv:
                try:
                    dispatcher.bot.delete_message(chat.id,
                                                  update.message.message_id)
                except BadRequest:
                    pass
                reply = False

            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text(
                    "Oh, Genos? Nice to see you here!.",
                    reply_to_message_id=reply)
                welcome_log = (f"{html.escape(chat.title)}\n"
                               f"#USER_JOINED\n"
                               f"TEAM LEGENDS OWNER JUST JOINED ")
                continue

            # Welcome Devs
            elif new_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "Whoa! A member of the TEAM DAİSY MEMBER just joined!",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome Sudos
            elif new_mem.id in DRAGONS:
                update.effective_message.reply_text(
                    "Huh! A Dragon disaster just joined! Stay Alert!",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome Support
            elif new_mem.id in DEMONS:
                update.effective_message.reply_text(
                    "Huh! Someone with a Demon disaster level just joined!",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome Whitelisted
            elif new_mem.id in TIGERS:
                update.effective_message.reply_text(
                    "Oof! A Tiger disaster just joined!",
                    reply_to_message_id=reply)
                continue

            # Welcome Tigers
            elif new_mem.id in WOLVES:
                update.effective_message.reply_text(
                    "Oof! A Wolf disaster just joined!",
                    reply_to_message_id=reply)
                continue

            # Welcome yourself
            elif new_mem.id == bot.id:
                creator = None
                for x in bot.bot.get_chat_administrators(
                        update.effective_chat.id):
                    if x.status == 'creator':
                        creator = x.user
                        break
                if creator:
                    bot.send_message(
                        JOIN_LOGGER,
                        "#NEW_GROUP\nGroup name: {}\nID: {}\nCreator: {}"
                        .format(
                            html.escape(chat.title), chat.id,
                            html.escape(creator)),
                        parse_mode=ParseMode.HTML)
                else:
                    bot.send_message(
                        JOIN_LOGGER,
                        "#NEW_GROUP\nGroup name: {}\nID: {}"
                        .format(html.escape(chat.title), chat.id),
                        parse_mode=ParseMode.HTML)
                update.effective_message.reply_text(
                    "Watashi ga kita!", reply_to_message_id=reply)
                continue

            else:
                buttons = sql.get_welc_buttons(chat.id)
                keyb = build_keyboard(buttons)

                if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                    media_wel = True

                first_name = (
                    new_mem.first_name or "PersonWithNoName"
                )  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if cust_welcome == sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(
                            sql.DEFAULT_WELCOME_MESSAGES).format(
                                first=escape_markdown(first_name))

                    if new_mem.last_name:
                        fullname = escape_markdown(
                            f"{first_name} {new_mem.last_name}")
                    else:
                        fullname = escape_markdown(first_name)
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id,
                                               escape_markdown(first_name))
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(
                        cust_welcome, VALID_WELCOME_FORMATTERS)
                    res = valid_format.format(
                        first=escape_markdown(first_name),
                        last=escape_markdown(new_mem.last_name or first_name),
                        fullname=escape_markdown(fullname),
                        username=username,
                        mention=mention,
                        count=count,
