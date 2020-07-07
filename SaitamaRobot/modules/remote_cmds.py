import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher
from SaitamaRobot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from SaitamaRobot.modules.helper_funcs.extraction import extract_user_and_text
from SaitamaRobot.modules.helper_funcs.string_handling import extract_time
from SaitamaRobot.modules.helper_funcs.filters import CustomFilters

RBAN_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir",
    "Sohbet bulunamadı",
    "Sohbet üyelerini restric/unrestric için yeterli hak yok",
    "Kullanıcı_Katılımcı_Değil",
    "Eş_kimliği_geçersiz",
    "Grup sohbeti devre dışı bırakıldı",
    "Temel bir gruptan tekme atmak için kullanıcının davetli olması gerekir",
    "Sohbet_Yöneticisi_Gerekli",
    "Yalnızca temel bir grubun yaratıcısı grup yöneticilerini tekmeleyebilir",
    "Kanal_Özel",
    "Sohbette değil"
}

RUNBAN_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir",
    "Sohbet bulunamadı",
    "Sohbet üyelerini restric/unrestric için yeterli hak yok",
    "Kullanıcı_Katılımcı_Değil",
    "Eş_kimliği_geçersiz",
    "Grup sohbeti devre dışı bırakıldı",
    "Temel bir gruptan tekme atmak için kullanıcının davetli olması gerekir",
    "Sohbet_Yöneticisi_Gerekli",
    "Yalnızca temel bir grubun yaratıcısı grup yöneticilerini tekmeleyebilir",
    "Kanal_Özel",
    "Sohbette değil"
}

RKICK_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir",
    "Sohbet bulunamadı",
    "Sohbet üyelerini restric/unrestric için yeterli hak yok",
    "Kullanıcı_Katılımcı_Değil",
    "Eş_kimliği_geçersiz",
    "Grup sohbeti devre dışı bırakıldı",
    "Temel bir gruptan tekme atmak için kullanıcının davetli olması gerekir",
    "Sohbet_Yöneticisi_Gerekli",
    "Yalnızca temel bir grubun yaratıcısı grup yöneticilerini tekmeleyebilir",
    "Kanal_Özel",
    "Sohbette değil"
}

RMUTE_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir",
    "Sohbet bulunamadı",
    "Sohbet üyelerini restric/unrestric için yeterli hak yok",
    "Kullanıcı_Katılımcı_Değil",
    "Eş_kimliği_geçersiz",
    "Grup sohbeti devre dışı bırakıldı",
    "Temel bir gruptan tekme atmak için kullanıcının davetli olması gerekir",
    "Sohbet_Yöneticisi_Gerekli",
    "Yalnızca temel bir grubun yaratıcısı grup yöneticilerini tekmeleyebilir",
    "Kanal_Özel",
    "Sohbette değil"
}

RUNMUTE_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir",
    "Sohbet bulunamadı",
    "Sohbet üyelerini restric/unrestric için yeterli hak yok",
    "Kullanıcı_Katılımcı_Değil",
    "Eş_kimliği_geçersiz",
    "Grup sohbeti devre dışı bırakıldı",
    "Temel bir gruptan tekme atmak için kullanıcının davetli olması gerekir",
    "Sohbet_Yöneticisi_Gerekli",
    "Yalnızca temel bir grubun yaratıcısı grup yöneticilerini tekmeleyebilir",
    "Kanal_Özel",
    "Sohbette değil"
}

@run_async
@bot_admin
def rban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Bir sohbete / kullanıcıya atıfta bulunmuyorsunuz.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return
    elif not chat_id:
        message.reply_text("Bir sohbete atıfta bulunmuyorsunuz.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "sohbet bulunamadı":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden ve bu sohbetin bir parçası olduğumdan emin olun.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm, ama bu özel bir sohbet!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları kısıtlayamıyorum! Yönetici olduğumdan ve kullanıcıları yasaklayabildiğimden emin olun.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Keşke yöneticileri yasaklayabilseydim...")
        return

    if user_id == bot.id:
        message.reply_text("Kendimi BAN yapmayacağım, deli misin?")
        return

    try:
        chat.kick_member(user_id)
        message.reply_text("Sohbet yasaklandı!")
    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text('Banlandı!', quote=False)
        elif excp.message in RBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR yasaklayan kullanıcı %s sohbette %s (%s) Nedeniyle %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, bu kullanıcıyı yasaklayamam.")

@run_async
@bot_admin
def runban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Bir sohbete / kullanıcıya atıfta bulunmuyorsunuz.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return
    elif not chat_id:
        message.reply_text("Bir sohbete atıfta bulunmuyorsunuz.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Sohbet Bulunamıyor":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden ve bu sohbetin bir parçası olduğumdan emin olun.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm, ama bu özel bir sohbet!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları sınırlayamam! Yönetici olduğumdan ve kullanıcıların yasağını kaldırabildiğimden emin olun.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı orada bulamıyorum")
            return
        else:
            raise

    if is_user_in_chat(chat, user_id):
        message.reply_text("Neden o sohbette olan birinin uzaktan yasağını kaldırmaya çalışıyorsunuz?")
        return

    if user_id == bot.id:
        message.reply_text("Kendimi UNBAN yapmayacağım, orada bir yöneticiyim!")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("Evet, bu kullanıcı sohbete katılabilir!")
    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text('Ban Kalktı!', quote=False)
        elif excp.message in RUNBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR yasağı kaldırılmış kullanıcı %s sohbette %s (%s) nedeniyle %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, bu kullanıcının yasağını kaldıramıyorum.")

@run_async
@bot_admin
def rkick(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Bir sohbete / kullanıcıya atıfta bulunmuyorsunuz.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return
    elif not chat_id:
        message.reply_text("Bir sohbete atıfta bulunmuyorsunuz.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Sohbet Bulunamadı":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden ve bu sohbetin bir parçası olduğumdan emin olun.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm, ama bu özel bir sohbet!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları kısıtlayamıyorum! Yönetici olduğumdan ve kullanıcıları tekmeleyebileceğimden emin olun.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Keşke yöneticileri tekmeleyebilseydim...")
        return

    if user_id == bot.id:
        message.reply_text("Kendimi tekmelemeyeceğim, delirdin mi?")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("Sohbetten Atıldı!")
    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text('Kicklendi!', quote=False)
        elif excp.message in RKICK_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR tekme kullanıcı %s sohbette %s (%s) nedeniyle %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, o kullanıcıyı tekmeleyemem.")

@run_async
@bot_admin
def rmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Bir sohbete / kullanıcıya atıfta bulunmuyorsunuz.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return
    elif not chat_id:
        message.reply_text("Bir sohbete atıfta bulunmuyorsunuz.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Sohbet Bulunamadı":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden ve bu sohbetin bir parçası olduğumdan emin olun.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm, ama bu özel bir sohbet!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları kısıtlayamıyorum! Yönetici olduğumdan ve kullanıcıların sesini kapatabildiğinden emin olun.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Keşke yöneticileri sessize alabilseydim...")
        return

    if user_id == bot.id:
        message.reply_text("Kendimi MUTE yapmayacağım, deli misin?")
        return

    try:
        bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
        message.reply_text("Sohbetten yoksayıldı!")
    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text('Muted!', quote=False)
        elif excp.message in RMUTE_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("HATA sessiz kullanıcı %s sohbette %s (%s) nedeniyle %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, bu kullanıcıyı susturamıyorum.")

@run_async
@bot_admin
def runmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Bir sohbete / kullanıcıya atıfta bulunmuyorsunuz.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return
    elif not chat_id:
        message.reply_text("Bir sohbete atıfta bulunmuyorsunuz.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Sohbet Bulunamadı":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden ve bu sohbetin bir parçası olduğumdan emin olun.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm, ama bu özel bir sohbet!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları sınırlayamam! Yönetici olduğumdan ve kullanıcıların yasağını kaldırabildiğimden emin olun.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı Bulunamadı":
            message.reply_text("Bu kullanıcıyı orada bulamıyorum")
            return
        else:
            raise

    if is_user_in_chat(chat, user_id):
       if member.can_send_messages and member.can_send_media_messages \
          and member.can_send_other_messages and member.can_add_web_page_previews:
        message.reply_text("Bu kullanıcının zaten o sohbette konuşma hakkı var.")
        return

    if user_id == bot.id:
        message.reply_text("Kendimi açmayacağım, orada bir yöneticiyim!")
        return

    try:
        bot.restrict_chat_member(chat.id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)
        message.reply_text("Evet, bu kullanıcı bu sohbette konuşabilir!")
    except BadRequest as excp:
        if excp.message == "Yanıt mesajı bulunamadı":
            # Do not reply
            message.reply_text('Unmuted!', quote=False)
        elif excp.message in RUNMUTE_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("HATA açma susturulmuş kullanıcı %s sohbette %s (%s) nedeniyle %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, bu kullanıcının sesini açamıyorum.")

__help__ = ""

__mod_name__ = "Remote Commands"

RBAN_HANDLER = CommandHandler("rban", rban, pass_args=True, filters=CustomFilters.sudo_filter)
RUNBAN_HANDLER = CommandHandler("runban", runban, pass_args=True, filters=CustomFilters.sudo_filter)
RKICK_HANDLER = CommandHandler("rkick", rkick, pass_args=True, filters=CustomFilters.sudo_filter)
RMUTE_HANDLER = CommandHandler("rmute", rmute, pass_args=True, filters=CustomFilters.sudo_filter)
RUNMUTE_HANDLER = CommandHandler("runmute", runmute, pass_args=True, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(RBAN_HANDLER)
dispatcher.add_handler(RUNBAN_HANDLER)
dispatcher.add_handler(RKICK_HANDLER)
dispatcher.add_handler(RMUTE_HANDLER)
dispatcher.add_handler(RUNMUTE_HANDLER) 
