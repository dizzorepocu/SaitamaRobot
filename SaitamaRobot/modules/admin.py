import html
from typing import List

import requests
from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, run_async
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher, TOKEN, SUDO_USERS
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin, connection_status
from SaitamaRobot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from SaitamaRobot.modules.log_channel import loggable


@run_async
@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    log_message = ""

    promoter = chat.get_member(user.id)
    
    if not (promoter.can_promote_members or promoter.status == "creator") and not user.id in SUDO_USERS:
        message.reply_text("Bunu yapmak için gerekli haklara sahip değilsiniz!")
        return ""

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return log_message

    try:
        user_member = chat.get_member(user_id)
    except:
        return log_message

    if user_member.status == 'administrator' or user_member.status == 'creator':
        message.reply_text("Zaten yönetici olan birini tanıtmayı nasıl amaçlıyorum?")
        return log_message

    if user_id == bot.id:
        message.reply_text("Kendimi tanıtamıyorum! Benim için yapacak bir yönetici edinin.")
        return log_message

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    try:
        bot.promoteChatMember(chat.id, user_id,
                              can_change_info=bot_member.can_change_info,
                              can_post_messages=bot_member.can_post_messages,
                              can_edit_messages=bot_member.can_edit_messages,
                              can_delete_messages=bot_member.can_delete_messages,
                              can_invite_users=bot_member.can_invite_users,
                              # can_promote_members=bot_member.can_promote_members,
                              can_restrict_members=bot_member.can_restrict_members,
                              can_pin_messages=bot_member.can_pin_messages)
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            message.reply_text("Grupta olmayan birini tanıtamam.")
            return log_message
        else:
            message.reply_text("Tanıtım yapılırken bir hata oluştu.")
            return log_message

    bot.sendMessage(chat.id, f"Başarıyla terfi etti <b>{user_member.user.first_name or user_id}</b>!",
                    parse_mode=ParseMode.HTML)

    log_message += (f"<b>{html.escape(chat.title)}:</b>\n"
                    "#PROMOTED\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}")

    return log_message


@run_async
@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    log_message = ""

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return log_message

    try:
        user_member = chat.get_member(user_id)
    except:
        return log_message

    if user_member.status == 'creator':
        message.reply_text("Bu kişi sohbeti YARATTI, nasıl tenzil edeyim")
        return log_message

    if not user_member.status == 'administrator':
        message.reply_text("Tanıtılamayanları indiremezsiniz!")
        return log_message

    if user_id == bot.id:
        message.reply_text("Kendimi küçültemem! Benim için yapacak bir yönetici edinin.")
        return log_message

    try:
        bot.promoteChatMember(chat.id, user_id,
                              can_change_info=False,
                              can_post_messages=False,
                              can_edit_messages=False,
                              can_delete_messages=False,
                              can_invite_users=False,
                              can_restrict_members=False,
                              can_pin_messages=False,
                              can_promote_members=False)

        bot.sendMessage(chat.id, f"Başarıyla düşürüldü <b>{user_member.user.first_name or user_id}</b>!",
                        parse_mode=ParseMode.HTML)

        log_message += (f"<b>{html.escape(chat.title)}:</b>\n"
                        f"#DEMOTED\n"
                        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                        f"<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}")

        return log_message
    except BadRequest:
        message.reply_text("Düşürülemedi. Yönetici olmayabilirim veya yönetici durumu başka biri tarafından atanmış olabilir"
                           " kullanıcı, bu yüzden onlara hareket edemiyorum!")
        return log_message


# Until the library releases the method
@run_async
@connection_status
@bot_admin
@can_promote
@user_admin
def set_title(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    message = update.effective_message

    user_id, title = extract_user_and_text(message, args)
    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return

    if user_member.status == 'creator':
        message.reply_text("Bu kişi sohbeti YARATTI, onun için nasıl özel başlık ayarlayabilirim?")
        return

    if not user_member.status == 'administrator':
        message.reply_text("Yönetici olmayanlar için başlık ayarlanamaz!\nÖzel başlık ayarlamak için önce onları tanıtın!")
        return

    if user_id == bot.id:
        message.reply_text("Kendi başlığımı kendim belirleyemiyorum! Beni yönetici yapmasını sağlayanı benim için yapsın.")
        return

    if not title:
        message.reply_text("Boş başlık ayarlamak hiçbir şey yapmaz!")
        return

    if len(title) > 16:
        message.reply_text("Başlık uzunluğu 16 karakterden uzun.\n16 karaktere kısaltma.")

    result = requests.post(f"https://api.telegram.org/bot{TOKEN}/setChatAdministratorCustomTitle"
                           f"?chat_id={chat.id}"
                           f"&user_id={user_id}"
                           f"&custom_title={title}")
    status = result.json()["ok"]

    if status is True:
        bot.sendMessage(chat.id, f"İçin başlığı başarıyla ayarlandı <code>{user_member.user.first_name or user_id}</code> "
                                 f"to <code>{title[:16]}</code>!", parse_mode=ParseMode.HTML)
    else:
        description = result.json()["description"]
        if description == "Bad Request:kullanıcının özel başlığını değiştirmek için yeterli hak yok":
            message.reply_text("Tanıtmadığım yöneticiler için özel başlık ayarlayamıyorum!")


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user
    chat = update.effective_chat

    is_group = chat.type != "private" and chat.type != "channel"
    prev_message = update.effective_message.reply_to_message

    is_silent = True
    if len(args) >= 1:
        is_silent = not (args[0].lower() == 'notify' or args[0].lower() == 'loud' or args[0].lower() == 'violent')

    if prev_message and is_group:
        try:
            bot.pinChatMessage(chat.id, prev_message.message_id, disable_notification=is_silent)
        except BadRequest as excp:
            if excp.message == "Chat_not_modified":
                pass
            else:
                raise
        log_message = (f"<b>{html.escape(chat.title)}:</b>\n"
                       f"#PINNED\n"
                       f"<b>Admin:</b> {mention_html(user.id, user.first_name)}")

        return log_message


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    log_message = (f"<b>{html.escape(chat.title)}:</b>\n"
                   f"#UNPINNED\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)}")

    return log_message


@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
    chat = update.effective_chat

    if chat.username:
        update.effective_message.reply_text(chat.username)
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            update.effective_message.reply_text(invitelink)
        else:
            update.effective_message.reply_text("Davet bağlantısına erişimim yok, izinlerimi değiştirmeyi deneyin!")
    else:
        update.effective_message.reply_text("Size sadece üst gruplar ve kanallar için davet bağlantıları verebilirim, üzgünüm!")


@run_async
@connection_status
def adminlist(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user

    chat_id = chat.id
    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    administrators = bot.getChatAdministrators(chat_id)

    if update_chat_title == message_chat_title:
        chat_name = "this chat"
    else:
        chat_name = update_chat_title

    text = f"Admins in *{chat_name}*:"

    for admin in administrators:
        user = admin.user
        name = f"[{user.first_name + (user.last_name or '')}](tg://user?id={user.id})"
        text += f"\n - {name}"

    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def __chat_settings__(chat_id, user_id):
    return "You are *admin*: `{}`".format(dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


__help__ = """
 • `/adminlist`*:* sohbetteki yöneticilerin listesi

*Admins only:*
 • `/pin`*:* cevaplanan iletiyi sessizce sabitler - kullanıcılara bildirim vermek için `` yüksek sesle '' veya `` bildir '' ekle.
 • `/unpin`*:*o anda sabitlenmiş olan mesajı kaldırır
 • `/invitelink`*:* davet bağlantısı alır
 • `/promote`*:* Kullanıcıya rütbe verir
 • `/demote`*:* Kullanıcın rütbesini düşürür
 • `/settitle`*:* botun tanıttığı bir yönetici için özel bir başlık belirler
"""

ADMINLIST_HANDLER = DisableAbleCommandHandler(["adminlist", "admins"], adminlist)

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.group)

INVITE_HANDLER = DisableAbleCommandHandler("invitelink", invite, filters=Filters.group)

PROMOTE_HANDLER = DisableAbleCommandHandler("promote", promote, pass_args=True)
DEMOTE_HANDLER = DisableAbleCommandHandler("demote", demote, pass_args=True)

SET_TITLE_HANDLER = CommandHandler("settitle", set_title, pass_args=True)

dispatcher.add_handler(ADMINLIST_HANDLER)
dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(SET_TITLE_HANDLER)

__mod_name__ = "Admin"
__command_list__ = ["adminlist", "admins", "invitelink", "promote", "demote"]
__handlers__ = [ADMINLIST_HANDLER, PIN_HANDLER, UNPIN_HANDLER,
                INVITE_HANDLER, PROMOTE_HANDLER, DEMOTE_HANDLER, SET_TITLE_HANDLER]
