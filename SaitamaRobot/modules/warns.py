import html
import re
from typing import Optional, List

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, DispatcherHandlerStop, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher, BAN_STICKER, WHITELIST_USERS, TIGER_USERS
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import (is_user_admin, bot_admin, user_admin_no_reply, user_admin,
                                                     can_restrict)
from SaitamaRobot.modules.helper_funcs.extraction import extract_text, extract_user_and_text, extract_user
from SaitamaRobot.modules.helper_funcs.filters import CustomFilters
from SaitamaRobot.modules.helper_funcs.misc import split_message
from SaitamaRobot.modules.helper_funcs.string_handling import split_quotes
from SaitamaRobot.modules.log_channel import loggable
from SaitamaRobot.modules.sql import warns_sql as sql

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>Bu sohbetteki mevcut uyarı filtreleri:</b>\n"


# Not async
def warn(user: User, chat: Chat, reason: str, message: Message, warner: User = None) -> str:
    if is_user_admin(chat, user.id):
        # message.reply_text("Damn admins, They are too far to be One Punched!")
        return

    if user.id in TIGER_USERS:
        if warner:
            message.reply_text("Kaplanlar uyarılamaz.")
        else:
            message.reply_text("Tiger otomatik uyarı filtresini tetikledi!\nKaplanları uyaramıyorum ama bunu kötüye kullanmaktan kaçınmalılar.")
        return

    if user.id in WHITELIST_USERS:
        if warner:
            message.reply_text("Kurt felaketleri bağışıklığı uyarıyor.")
        else:
            message.reply_text("Kurt Felaketi otomatik uyarı filtresini tetikledi!\nKolları uyaramıyorum, ancak bunu kötüye kullanmaktan kaçınmaları gerekiyor.")
        return

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "Otomatik uyarı filtresi."

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # punch
            chat.unban_member(user.id)
            reply = f"{limit} warnings, *Punches {mention_html(user.id, user.first_name)} normal bir yumruk ile!* "

        else:  # ban
            chat.kick_member(user.id)
            reply = f"{limit} warnings, *Punches {mention_html(user.id, user.first_name)} normal bir yumruk ile* "

        for warn_reason in reasons:
            reply += f"\n - {html.escape(warn_reason)}"

        message.bot.send_sticker(chat.id, BAN_STICKER)  # Saitama's sticker
        keyboard = []
        log_reason = (f"<b>{html.escape(chat.title)}:</b>\n"
                      f"#WARN_BAN\n"
                      f"<b>Admin:</b> {warner_tag}\n"
                      f"<b>Kulllanıcı:</b> {mention_html(user.id, user.first_name)}\n"
                      f"<b>Sebep:</b> {reason}\n"
                      f"<b>Sayımları:</b> <code>{num_warns}/{limit}</code>")

    else:
        keyboard = InlineKeyboardMarkup([{InlineKeyboardButton("Uyarıyı kaldır",
                                                               callback_data="rm_warn({})".format(user.id))}])

        reply = f"{mention_html(user.id, user.first_name)} has {num_warns}/{limit} warnings... watch out!"
        if reason:
            reply += f"\nSon uyarmanın nedeni:\n{html.escape(reason)}"

        log_reason = (f"<b>{html.escape(chat.title)}:</b>\n"
                      f"#WARN\n"
                      f"<b>Admin:</b> {warner_tag}\n"
                      f"<b>Kullanıcı:</b> {mention_html(user.id, user.first_name)}\n"
                      f"<b>Sebep:</b> {reason}\n"
                      f"<b>Sayımları:</b> <code>{num_warns}/{limit}</code>")

    try:
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
        else:
            raise
    return log_reason


@run_async
@user_admin_no_reply
@bot_admin
@loggable
def button(bot: Bot, update: Update) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        res = sql.remove_warn(user_id, chat.id)
        if res:
            update.effective_message.edit_text(
                "Warn removed by {}.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)
            user_member = chat.get_member(user_id)
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#UNWARN\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"<b>Kullanıcı:</b> {mention_html(user_member.user.id, user_member.user.first_name)}")
        else:
            update.effective_message.edit_text(f"Kullanıcının zaten uyarısı yok.", parse_mode=ParseMode.HTML)

    return ""


@run_async
@user_admin
@can_restrict
@loggable
def warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    warner: Optional[User] = update.effective_user

    user_id, reason = extract_user_and_text(message, args)

    if user_id:
        if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
            return warn(message.reply_to_message.from_user, chat, reason, message.reply_to_message, warner)
        else:
            return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        message.reply_text("Bu benim için geçersiz bir Kullanıcı Kimliği gibi görünüyor.")
    return ""


@run_async
@user_admin
@bot_admin
@loggable
def reset_warns(bot: Bot, update: Update, args: List[str]) -> str:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    user_id = extract_user(message, args)

    if user_id:
        sql.reset_warns(user_id, chat.id)
        message.reply_text("Warns have been reset!")
        warned = chat.get_member(user_id).user
        return (f"<b>{html.escape(chat.title)}:</b>\n"
                f"#RESETWARNS\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>User:</b> {mention_html(warned.id, warned.first_name)}")
    else:
        message.reply_text("Hiçbir kullanıcı belirlenmedi!")
    return ""


@run_async
def warns(bot: Bot, update: Update, args: List[str]):
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn = sql.get_warn_setting(chat.id)

        if reasons:
            text = f"This user has {num_warns}/{limit} aşağıdaki nedenlerle uyarıyor:"
            for reason in reasons:
                text += f"\n - {reason}"

            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg)
        else:
            update.effective_message.reply_text(f"Kullanıcının {num_warns}/{limit} uyarısı var, ancak bunların hiçbir nedeni yok.")
    else:
        update.effective_message.reply_text("Bu kullanıcının uyarısı yok!")


# Dispatcher handler stop - do not async
@user_admin
def add_warn_filter(bot: Bot, update: Update):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message

    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    update.effective_message.reply_text(f"İçin uyarı işleyicisi eklendi '{keyword}'!")
    raise DispatcherHandlerStop


@user_admin
def remove_warn_filter(bot: Bot, update: Update):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message

    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    to_remove = extracted[0]

    chat_filters = sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("Burada aktif uyarı filtresi yok!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
            msg.reply_text("Tamam, bunun için insanları uyarmayı bırakacağım.")
            raise DispatcherHandlerStop

    msg.reply_text("Bu geçerli bir uyarı filtresi değil - tüm aktif uyarı filtreleri için çalıştırma /warnlist.")


@run_async
def list_warn_filters(bot: Bot, update: Update):
    chat: Optional[Chat] = update.effective_chat
    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        update.effective_message.reply_text("Burada aktif uyarı filtresi yok!")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    for keyword in all_handlers:
        entry = f" - {html.escape(keyword)}\n"
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == CURRENT_WARNING_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@run_async
@loggable
def reply_filter(bot: Bot, update: Update) -> str:
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message

    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user: Optional[User] = update.effective_user
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@run_async
@user_admin
@loggable
def set_warn_limit(bot: Bot, update: Update, args: List[str]) -> str:
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    msg: Optional[Message] = update.effective_message

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                msg.reply_text("Minimum uyarı limiti:3!")
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                msg.reply_text("Updated the warn limit to {}".format(args[0]))
                return (f"<b>{html.escape(chat.title)}:</b>\n"
                        f"#SET_WARN_LIMIT\n"
                        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                        f"Uyarı sınırını <code>{args[0]}</code>")
        else:
            msg.reply_text("Arg olarak bana bir numara ver!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)

        msg.reply_text("Geçerli uyarı limiti {}".format(limit))
    return ""


@run_async
@user_admin
def set_warn_strength(bot: Bot, update: Update, args: List[str]):
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    msg: Optional[Message] = update.effective_message

    if args:
        if args[0].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            msg.reply_text("Çok fazla uyarı artık Yasaklama ile sonuçlanacak!")
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Güçlü uyarılar sağlamıştır. Kullanıcılar ciddi şekilde yumruklanacak. (Yasaklandı)")

        elif args[0].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            msg.reply_text("Çok fazla uyarı artık normal bir yumrukla sonuçlanacak! Kullanıcılar daha sonra tekrar katılabilecek.")
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Güçlü yumrukları devre dışı bıraktı. Kullanıcılara normal yumruk kullanacağım.")

        else:
            msg.reply_text("Sadece anlıyorum on/yes/no/off!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if soft_warn:
            msg.reply_text("Uyarılar şu anda sınırları aştığında * yumruk * olarak ayarlanmış durumda.",
                           parse_mode=ParseMode.MARKDOWN)
        else:
            msg.reply_text("Uyarılar şu anda sınırları aştığında * Yasak * olarak ayarlanmış.",
                           parse_mode=ParseMode.MARKDOWN)
    return ""


def __stats__():
    return (f"{sql.num_warns()} overall warns, across {sql.num_warn_chats()} chats.\n"
            f"{sql.num_warn_filters()} warn filters, across {sql.num_warn_filter_chats()} chats.")


def __import_data__(chat_id, data):
    for user_id, count in data.get('warns', {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = sql.get_warn_setting(chat_id)
    return (f"This chat has `{num_warn_filters}` warn filters. "
            f"It takes `{limit}` kullanıcı almadan önce uyarır *{'kicked' if soft_warn else 'banned'}*.")


__help__ = """
 • `/warns <userhandle>`*:* bir kullanıcının sayısını ve nedenini al.
 • `/warnlist`*:* mevcut tüm uyarı filtrelerinin listesi

*Admins only:*
 • `/warn <userhandle>`*:* kullanıcıyı uyar. 3 uyarıdan sonra, kullanıcı gruptan men edilecektir. Cevap olarak da kullanılabilir.
 • `/resetwarn <userhandle>`*:* bir kullanıcı için uyarıları sıfırlar. Cevap olarak da kullanılabilir.
 • `/addwarn <keyword> <reply message>`*:* belirli bir anahtar kelimeye bir uyarı filtresi ayarlayın. Anahtar kelimenizin \
bir cümle olun, tırnak işaretleri içine alın, şöyle: `/ addwarn" çok kızgın "Bu öfkeli bir kullanıcı`. 
 • `/nowarn <keyword>`*:* uyarı filtresini durdurma
 • `/warnlimit <num>`*:* uyarı limitini belirle
 • `/strongwarn <on/yes/off/no>`*:* Açık olarak ayarlanırsa uyarı sınırını aşmak yasakla sonuçlanır. Else, sadece yumruklayacak.
"""

__mod_name__ = "Warnings"

WARN_HANDLER = CommandHandler("warn", warn_user, pass_args=True, filters=Filters.group)
RESET_WARN_HANDLER = CommandHandler(["resetwarn", "resetwarns"], reset_warns, pass_args=True, filters=Filters.group)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn")
MYWARNS_HANDLER = DisableAbleCommandHandler("warns", warns, pass_args=True, filters=Filters.group)
ADD_WARN_HANDLER = CommandHandler("addwarn", add_warn_filter, filters=Filters.group)
RM_WARN_HANDLER = CommandHandler(["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.group)
LIST_WARN_HANDLER = DisableAbleCommandHandler(["warnlist", "warnfilters"], list_warn_filters, filters=Filters.group,
                                              admin_ok=True)
WARN_FILTER_HANDLER = MessageHandler(CustomFilters.has_text & Filters.group, reply_filter)
WARN_LIMIT_HANDLER = CommandHandler("warnlimit", set_warn_limit, pass_args=True, filters=Filters.group)
WARN_STRENGTH_HANDLER = CommandHandler("strongwarn", set_warn_strength, pass_args=True, filters=Filters.group)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
