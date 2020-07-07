from typing import Optional

from telegram import Message, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown

import SaitamaRobot.modules.sql.rules_sql as sql
from SaitamaRobot import dispatcher
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin
from SaitamaRobot.modules.helper_funcs.string_handling import markdown_parser


@run_async
def get_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# Do not async - not from a handler
def send_rules(update, chat_id, from_pm=False):
    bot = dispatcher.bot
    user = update.effective_user  # type: Optional[User]
    try:
        chat = bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message == "Chat not found" and from_pm:
            bot.send_message(user.id, "Bu sohbet için kurallar kısayolu doğru şekilde ayarlanmamış! Yöneticilerden şunu isteyin: "
                                      "bunu tamir et.")
            return
        else:
            raise

    rules = sql.get_rules(chat_id)
    text = f"The rules for *{escape_markdown(chat.title)}* are:\n\n{rules}"

    if from_pm and rules:
        bot.send_message(user.id, text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    elif from_pm:
        bot.send_message(user.id, "Grup yöneticileri bu sohbet için henüz bir kural belirlemedi. "
                                  "Bu muhtemelen kanunsuz olduğu anlamına gelmez...!")
    elif rules:
        update.effective_message.reply_text("Bu grubun kurallarını almak için PM'de bana ulaşın.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="Rules",
                                                                       url=f"t.me/{bot.username}?start={chat_id}")]]))
    else:
        update.effective_message.reply_text("Grup yöneticileri bu sohbet için henüz bir kural belirlemedi. "
                                            "Bu muhtemelen kanunsuz olduğu anlamına gelmez...!")


@run_async
@user_admin
def set_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
    if len(args) == 2:
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)

        sql.set_rules(chat_id, markdown_rules)
        update.effective_message.reply_text("Bu grup için kurallar başarıyla ayarlandı.")


@run_async
@user_admin
def clear_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_rules(chat_id, "")
    update.effective_message.reply_text("Kurallar başarıyla temizlendi!")


def __stats__():
    return f"{sql.num_chats()} sohbetler için kurallar ayarlandı."


def __import_data__(chat_id, data):
    # set chat rules
    rules = data.get('info', {}).get('rules', "")
    sql.set_rules(chat_id, rules)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"Bu sohbette kurallar belirlenmiş: `{bool(sql.get_rules(chat_id))}`"


__help__ = """
 • `/rules`*:* bu sohbet için kuralları al.

*Admins only:*
 • `/setrules <your rules here>`*:* bu sohbet için kuralları belirle.
 • `/clearrules`*:* bu sohbetin kurallarını temizle.
"""

__mod_name__ = "Rules"

GET_RULES_HANDLER = CommandHandler("rules", get_rules, filters=Filters.group)
SET_RULES_HANDLER = CommandHandler("setrules", set_rules, filters=Filters.group)
RESET_RULES_HANDLER = CommandHandler("clearrules", clear_rules, filters=Filters.group)

dispatcher.add_handler(GET_RULES_HANDLER)
dispatcher.add_handler(SET_RULES_HANDLER)
dispatcher.add_handler(RESET_RULES_HANDLER)
