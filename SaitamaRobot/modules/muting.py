import html

from typing import Optional, List

from telegram import Bot, Chat, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher, LOGGER, TIGER_USERS
from SaitamaRobot.modules.helper_funcs.chat_status import (bot_admin, user_admin, is_user_admin, can_restrict,
                                                     connection_status)
from SaitamaRobot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from SaitamaRobot.modules.helper_funcs.string_handling import extract_time
from SaitamaRobot.modules.log_channel import loggable


def check_user(user_id: int, bot: Bot, chat: Chat) -> Optional[str]:
    if not user_id:
        reply = "Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış.."
        return reply

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı bulunamadı":
            reply = "Bu kullanıcıyı bulamıyorum"
            return reply
        else:
            raise

    if user_id == bot.id:
        reply = "Kendimi MUTE yapmayacağım, ne kadar yükseksiniz?"
        return reply

    if is_user_admin(chat, user_id, member) or user_id in TIGER_USERS:
        reply = "Keşke yöneticileri susturabilseydim ... Belki bir yumruk?"
        return reply

    return None


@run_async
@connection_status
@bot_admin
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = extract_user_and_text(message, args)
    reply = check_user(user_id, bot, chat)

    if reply:
        message.reply_text(reply)
        return ""

    member = chat.get_member(user_id)

    log = (f"<b>{html.escape(chat.title)}:</b>\n"
           f"#MUTE\n"
           f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
           f"<b>Kullanıcı:</b> {mention_html(member.user.id, member.user.first_name)}")

    if reason:
        log += f"\n<b>Sebep:</b> {reason}"

    if member.can_send_messages is None or member.can_send_messages:
        bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
        bot.sendMessage(chat.id, f"Muted <b>{html.escape(member.user.first_name)}</b> son kullanma tarihi yok!",
                        parse_mode=ParseMode.HTML)
        return log

    else:
        message.reply_text("Bu kullanıcının sesi zaten kapatıldı!")

    return ""


@run_async
@connection_status
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Yoksaymaktan vazgeçmek için bana bir kullanıcı adı vermeniz veya sessize alınmaması için birine cevap vermeniz gerekecek.")
        return ""

    member = chat.get_member(int(user_id))

    if member.status != 'kicked' and member.status != 'left':
        if (member.can_send_messages
                and member.can_send_media_messages
                and member.can_send_other_messages
                and member.can_add_web_page_previews):
            message.reply_text("Bu kullanıcının zaten konuşma hakkı var.")
        else:
            bot.restrict_chat_member(chat.id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)
            bot.sendMessage(chat.id, f"İzin vereceğim <b>{html.escape(member.user.first_name)}</b>Metne!",
                            parse_mode=ParseMode.HTML)
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#UNMUTE\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"<b>ullanıcı:</b> {mention_html(member.user.id, member.user.first_name)}")
    else:
        message.reply_text("Bu kullanıcı sohbette bile değil, sesi kapatmak, onlardan daha fazla konuşmasına neden olmaz "
                           "zaten yap!")

    return ""


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = extract_user_and_text(message, args)
    reply = check_user(user_id, bot, chat)

    if reply:
        message.reply_text(reply)
        return ""

    member = chat.get_member(user_id)

    if not reason:
        message.reply_text("Bu kullanıcıyı sessize almak için bir zaman belirtmediniz!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = (f"<b>{html.escape(chat.title)}:</b>\n"
           f"#TEMP MUTED\n"
           f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
           f"<b>Kullanıcı:</b> {mention_html(member.user.id, member.user.first_name)}\n"
           f"<b>Zaman:</b> {time_val}")
    if reason:
        log += f"\n<b>Sebep:</b> {reason}"

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, until_date=mutetime, can_send_messages=False)
            bot.sendMessage(chat.id, f"Muted <b>{html.escape(member.user.first_name)}</b> for {time_val}!",
                            parse_mode=ParseMode.HTML)
            return log
        else:
            message.reply_text("Bu kullanıcının sesi zaten kapatıldı.")

    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text(f"İçin kapatıldı {time_val}!", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("HATA sessize alınan kullanıcır %s sohbette %s (%s) Nedeniyle %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, bu kullanıcıyı susturamıyorum.")

    return ""


__help__ = """
*Admins only:*
 • `/mute <userhandle>`*:* kullanıcıyı susturur. Yanıtlanan kullanıcının sesini kısarak yanıt olarak da kullanılabilir.
 • `/tmute <userhandle> x(m/h/d)`*:* bir kullanıcıyı x kez susturur. (tanıtıcı veya yanıtla). `m` = `dakika`, `h` = `saat`, `d` = `gün`.
 • `/unmute <userhandle>`*:* kullanıcının sesini açar. Yanıtlanan kullanıcının sesini kısarak yanıt olarak da kullanılabilir.
"""

MUTE_HANDLER = CommandHandler("mute", mute, pass_args=True)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, pass_args=True)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, pass_args=True)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)

__mod_name__ = "Muting"
__handlers__ = [MUTE_HANDLER, UNMUTE_HANDLER, TEMPMUTE_HANDLER]
