import html
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, \
InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, CallbackQueryHandler, run_async
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher, WHITELIST_USERS, TIGER_USERS
from SaitamaRobot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict, \
bot_admin, user_admin_no_reply, connection_status
from SaitamaRobot.modules.log_channel import loggable
from SaitamaRobot.modules.sql import antiflood_sql as sql

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message
    log_message = ""

    if not user:  # ignore channels
        return log_message

    # ignore admins and whitelists
    if (is_user_admin(chat, user.id) 
            or user.id in WHITELIST_USERS
            or user.id in TIGER_USERS):
        sql.update_flood(chat.id, None)
        return log_message

    should_mute = sql.update_flood(chat.id, user.id)
    if not should_mute:
        return ""

    try:
        bot.restrict_chat_member(
            chat.id,
            user.id,
            can_send_messages=False
        )
        
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Unmute", callback_data="unmute_flooder({})".format(user.id))]]
        )
        bot.send_message(chat.id,
            f"{mention_html(user.id, user.first_name)} gruba flood nedeniyle susturuldu!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
            

        return "<b>{}:</b>" \
               "\n#MUTED" \
               "\n<b>User:</b> {}" \
               "\nGruba lood Attı.\nYönetici sesini açana kadar sessize alındı".format(html.escape(chat.title),
                                             mention_html(user.id, user.first_name))

    except BadRequest:
        msg.reply_text("Burada insanları susturamıyorum, önce bana izin ver! O zamana kadar antifloodu devre dışı bırakacağım.")
        sql.set_flood(chat.id, 0)
        log_message = ("<b>{chat.title}:</b>\n"
                       "#INFO\n"
                       "Tekme izinleriniz yok, bu nedenle antiflood otomatik olarak devre dışı bırakıldı.")

        return log_message


@run_async
@user_admin_no_reply
@bot_admin
def flood_button(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    match = re.match(r"unmute_flooder\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat.id
        try:
            bot.restrict_chat_member(
                chat,
                int(user_id),
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
            update.effective_message.edit_text(
                f"Unmuted by {mention_html(user.id, user.first_name)}.",
                parse_mode="HTML"
            )
        except:
            pass


@run_async
@user_admin
@can_restrict
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""

    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    if update_chat_title == message_chat_title:
        chat_name = ""
    else:
        chat_name = f" in <b>{update_chat_title}</b>"

    if len(args) >= 1:

        val = args[0].lower()

        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat.id, 0)
            message.reply_text("Antiflood devre dışı bırakıldı{}.".format(chat_name), parse_mode=ParseMode.HTML)

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                message.reply_text("Antiflood devre dışı bırakıldı{}.".format(chat_name), parse_mode=ParseMode.HTML)
                log_message = (f"<b>{html.escape(chat.title)}:</b>\n"
                               f"#SETFLOOD\n"
                               f"<b>Admin</b>: {mention_html(user.id, user.first_name)}\n"
                               f"Kapalı antiflood.")

                return log_message
            elif amount < 3:
                message.reply_text("Antiflood has to be either 0 (disabled), or a number bigger than 3!")
                return log_message

            else:
                sql.set_flood(chat.id, amount)
                message.reply_text("Antiflood güncellendi ve {}{}".format(amount, chat_name),
                                   parse_mode=ParseMode.HTML)
                log_message = (f"<b>{html.escape(chat.title)}:</b>\n"
                               f"#SETFLOOD\n"
                               f"<b>Admin</b>: {mention_html(user.id, user.first_name)}\n"
                               f"Antifloodu ayarla <code>{amount}</code>.")

                return log_message
        else:
            message.reply_text("Tanınmayan argüman - lütfen bir sayı kullanın, 'off', or 'no'.")

    return log_message


@run_async
@connection_status
def flood(bot: Bot, update: Update):
    chat = update.effective_chat
    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    if update_chat_title == message_chat_title:
        chat_name = ""
    else:
        chat_name = f" in <b>{update_chat_title}</b>"

    limit = sql.get_flood_limit(chat.id)

    if limit == 0:
        update.effective_message.reply_text(f"Şu anda taşkın kontrolünü zorlamıyorum{chat_name}!",
                                            parse_mode=ParseMode.HTML)
    else:
        update.effective_message.reply_text(f"Flood Ayarı 0 ise kapalı olur 3 ten büyük olmalı "
                                            f"more than {limit} consecutive messages{chat_name}.",
                                            parse_mode=ParseMode.HTML)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "*Şu anda * taşkın kontrolünü zorlamıyor."
    else:
        return "Antiflood şuna ayarlandı `{}` messages.".format(limit)


__help__ = """
 • `/flood`*:*Geçerli taşkın kontrolü ayarını alma

*Admins only:*
 • `/setflood <int/'no'/'off'>`*:* taşkın kontrolünü etkinleştirir veya devre dışı bırakır
 *Örnek:* `/setflood 10`
Bu, kullanıcıları arka arkaya 10'dan fazla mesaj gönderirse susturur, botlar yok sayılır.
"""

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
FLOOD_QUERY_HANDLER = CallbackQueryHandler(flood_button, pattern=r"unmute_flooder")
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args=True, filters=Filters.group)
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(FLOOD_QUERY_HANDLER)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)

__mod_name__ = "AntiFlood"
__handlers__ = [(FLOOD_BAN_HANDLER, FLOOD_GROUP), SET_FLOOD_HANDLER, FLOOD_HANDLER]
dispatcher.add_handler(FLOOD_HANDLER)
