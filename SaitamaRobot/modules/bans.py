import html
from typing import List

from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, run_async
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher, LOGGER, DEV_USERS, SUDO_USERS, TIGER_USERS
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import (bot_admin, user_admin, is_user_ban_protected, can_restrict,
                                                     is_user_admin, is_user_in_chat, connection_status, can_delete, user_can_ban)
from SaitamaRobot.modules.helper_funcs.extraction import extract_user_and_text
from SaitamaRobot.modules.helper_funcs.string_handling import extract_time
from SaitamaRobot.modules.log_channel import loggable, gloggable


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bunun bir kullanıcı olduğundan şüpheliyim.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamıyor":
            message.reply_text("Bu kişiyi bulamıyorum.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Oh evet, kendimi yasakla, çaylak!")
        return log_message

    # dev users to bypass whitelist protection incase of abuse
    if is_user_ban_protected(chat, user_id, member) and user not in DEV_USERS:
        message.reply_text("Bu kullanıcının dokunulmazlığı var - onları yasaklayamam.")
        return log_message

    log = (f"<b>{html.escape(chat.title)}:</b>\n"
           f"#BANNED\n"
           f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
           f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}")
    if reason:
        log += "\n<b>Sebep:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(chat.id, "Bananan Kullanıcı {}.".format(mention_html(member.user.id, member.user.first_name)),
                        parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text('Banned!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR yasaklayan kullanıcı %s sohbette %s (%s) Nedeniyle %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Ahh ... bu işe yaramadı...")

    return log_message


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bunun bir kullanıcı olduğundan şüpheliyim.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı bulamıyorum.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Kendimi Banlamayacağım, deli misin?")
        return log_message

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Öyle hissetmiyorum.")
        return log_message

    if not reason:
        message.reply_text("Bu kullanıcıyı yasaklamak için bir zaman belirtmediniz!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (f"<b>{html.escape(chat.title)}:</b>\n"
           "#TEMP BANNED\n"
           f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
           f"<b>Kullanıcı:</b> {mention_html(member.user.id, member.user.first_name)}\n"
           f"<b>Zaman:</b> {time_val}")
    if reason:
        log += "\n<b>Sebep:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(chat.id, f"Banlandı! Kullanıcı {mention_html(member.user.id, member.user.first_name)} "
                                 f"will be banned for {time_val}.",
                        parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text(f"Yasaklı! Kullanıcının yasaklanması {time_val}.", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR yasaklayan kullanıcı %s sohbette %s (%s) Nedeniyle %s",
                             user_id, chat.title, chat.id, excp.message)
            message.reply_text("Kahretsin, bu kullanıcıyı yasaklayamam.")

    return log_message


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def punch(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bunun bir kullanıcı olduğundan şüpheliyim.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı bulamıyorum.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Evet bunu yapmayacağım.")
        return log_message

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Keşke bu kullanıcıyı yumruklayabilseydim....")
        return log_message

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(chat.id, f"Bir Tekmeli! {mention_html(member.user.id, member.user.first_name)}.",
                        parse_mode=ParseMode.HTML)
        log = (f"<b>{html.escape(chat.title)}:</b>\n"
               f"#KICKED\n"
               f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
               f"<b>Kullanıcı:</b> {mention_html(member.user.id, member.user.first_name)}")
        if reason:
            log += f"\n<b>Sebep:</b> {reason}"

        return log

    else:
        message.reply_text("Kahretsin, bu kullanıcıyı yumruklayamam.")

    return log_message


@run_async
@bot_admin
@can_restrict
def punchme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Keşke yapabilseydim ... ama sen bir yöneticisin.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("*seni gruptan çıkarır*")
    else:
        update.effective_message.reply_text("Ha? Yapamam :/")


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bunun bir kullanıcı olduğundan şüpheliyim.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı bulamıyorum.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Burada olmasaydım kendimi nasıl kaldırabilirim?")
        return log_message

    if is_user_in_chat(chat, user_id):
        message.reply_text("Bu kişi zaten burada değil mi??")
        return log_message

    chat.unban_member(user_id)
    message.reply_text("Evet, bu kullanıcı katılabilir!")

    log = (f"<b>{html.escape(chat.title)}:</b>\n"
           f"#UNBANNED\n"
           f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
           f"<b>Kullanıcı:</b> {mention_html(member.user.id, member.user.first_name)}")
    if reason:
        log += f"\n<b>Sebep:</b> {reason}"

    return log


@run_async
@connection_status
@bot_admin
@can_restrict
@gloggable
def selfunban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user

    if user.id not in SUDO_USERS or user.id not in TIGER_USERS:
        return

    try:
        chat_id = int(args[0])
    except:
        message.reply_text("Geçerli bir sohbet kimliği verin.")
        return

    chat = bot.getChat(chat_id)

    try:
        member = chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı bulamıyorum.")
            return
        else:
            raise

    if is_user_in_chat(chat, user.id):
        message.reply_text("Zaten sohbette değil misiniz??")
        return

    chat.unban_member(user.id)
    message.reply_text("Evet, seni yasakladım.")

    log = (f"<b>{html.escape(chat.title)}:</b>\n"
           f"#UNBANNED\n"
           f"<b>Kullanıcı:</b> {mention_html(member.user.id, member.user.first_name)}")

    return log


__help__ = """
 • `/punchme`*:* komutu veren kullanıcı gruptan kendini atar

*Admins only:*
 • `/ban <yanıtla>`*:* bir kullanıcıyı yasaklar. (tanıtıcı veya yanıtla)
 • `/tban <yanıtla> x(m/h/d)`*:* bir kullanıcıyı "x" süresi için yasaklar. (tanıtıcı veya yanıt yoluyla)). `m` = `dakika`, `h` = `saat`, `d` = `gün`.
 • `/unban <yanıtla>`*:* kullanıcının engellemesini kaldırır. (tanıtıcı veya yanıtla)
 • `/punch <yanıtla>`*:* Bir kullanıcıyı gruptan çıkarır (tanıtıcı veya yanıtla))
"""

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True)
PUNCH_HANDLER = CommandHandler("punch", punch, pass_args=True)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True)
ROAR_HANDLER = CommandHandler("roar", selfunban, pass_args=True)
PUNCHME_HANDLER = DisableAbleCommandHandler("punchme", punchme, filters=Filters.group)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(PUNCH_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(ROAR_HANDLER)
dispatcher.add_handler(PUNCHME_HANDLER)

__mod_name__ = "Bans"
__handlers__ = [BAN_HANDLER, TEMPBAN_HANDLER, PUNCH_HANDLER, UNBAN_HANDLER, ROAR_HANDLER, PUNCHME_HANDLER]
