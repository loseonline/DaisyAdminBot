import wikipedia
from DAİSY import dispatcher
from DAİSY.modules.disable import DisableAbleCommandHandler
from telegram import ParseMode, Update
from telegram.ext import CallbackContext, run_async
from wikipedia.exceptions import DisambiguationError, PageError


@run_async
def wiki(update: Update, context: CallbackContext):
    msg = update.effective_message.reply_to_message if update.effective_message.reply_to_message else update.effective_message
    res = ""
    if msg == update.effective_message:
        search = msg.text.split(" ", maxsplit=1)[1]
    else:
        search = msg.text
    try:
        res = wikipedia.summary(search)
    except DisambiguationError as e:
        update.message.reply_text(
            "Disambiguated pages found! Adjust your query accordingly.\n{}"
            .format(e),
            parse_mode=ParseMode.HTML)
    except PageError as e:
        update.message.reply_text(
            "{}".format(e), parse_mode=ParseMode.HTML)
    if res:
        result = f"{search}\n\n"
        result += f"{res}\n"
        result += f"""Read more..."""
        if len(result) > 4000:
            with open("result.txt", 'w') as f:
                f.write(f"{result}\n\nUwU OwO OmO UmU")
            with open("result.txt", 'rb') as f:
                context.bot.send_document(
                    document=f,
                    filename=f.name,
                    reply_to_message_id=update.message.message_id,
                    chat_id=update.effective_chat.id,
                    parse_mode=ParseMode.HTML)
        else:
            update.message.reply_text(
                result,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)


WIKI_HANDLER = DisableAbleCommandHandler("wiki", wiki)
dispatcher.add_handler(WIKI_HANDLER)
