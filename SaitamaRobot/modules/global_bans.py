import html
import time
from datetime import datetime
from io import BytesIO
from typing import List

from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async
from telegram.utils.helpers import mention_html

import SaitamaRobot.modules.sql.global_bans_sql as sql
from SaitamaRobot import dispatcher, OWNER_ID, SUDO_USERS, DEV_USERS, SUPPORT_USERS, TIGER_USERS, WHITELIST_USERS, STRICT_GBAN, GBAN_LOGS, SUPPORT_CHAT
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin, is_user_admin, support_plus
from SaitamaRobot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from SaitamaRobot.modules.helper_funcs.misc import send_to_list
from SaitamaRobot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir",
    "Sohbet Bulunamadı",
    "İçin yeterli hak yok restrict/unrestrict sohbet üyesinin",
    "Kullanıcı_katılımcı_değil",
    "Eş_kimliği_geçersiz",
    "Grup sohbeti devre dışı bırakıldı",
    "Temel bir gruptan tekme atmak için kullanıcının davetli olması gerekir",
    "Sohbet_yöneticisi_gerekli",
    "Yalnızca temel bir grubun yaratıcısı grup yöneticilerini tekmeleyebilir",
    "Özel_kanal",
    "Sohbette değil",
    "Sohbet sahibi kaldırılamıyor",
}

UNGBAN_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir",
    "Sohbet Bulunamadı",
    "İçin yeterli hak yok restrict/unrestrict sohbet üyesinin",
    "Kullanıcı_katılımcı_değil",
    "Yöntem yalnızca üst grup ve kanal sohbetleri için kullanılabilir",
    "Sohbette değilt",
    "Özel_kanal",
    "Sohbet_yöneticisi_gerekli",
    "Eş_kimliği_geçersiz",
    "Kullanıcı bulunamadı",
}


@run_async
@support_plus
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return

    if int(user_id) in DEV_USERS:
        message.reply_text("Bu kullanıcı Derneğin bir parçasıdır\nKendimize karşı hareket edemiyorum.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Küçük gözümle casusluk yapıyorum ... bir felaket! Neden birbirinizi açıyorsunuz?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH birisi bir Demon Felaketi yakalamaya çalışıyor! * patlamış mısır yakalar*")
        return

    if int(user_id) in TIGER_USERS:
        message.reply_text("Bu bir Kaplan! Yasaklanamazlar!")
        return

    if int(user_id) in WHITELIST_USERS:
        message.reply_text("Bu bir Kurt! Yasaklanamazlar!")
        return

    if user_id == bot.id:
        message.reply_text("Kendimi gruptan atmamı mı istiyorsun?")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Bu kullanıcıyı bulamıyorum.")
            return ""
        else:
            return

    if user_chat.type != 'private':
        message.reply_text("Bu bir kullanıcı değil!")
        return

    if sql.is_user_gbanned(user_id):

        if not reason:
            message.reply_text("Bu kullanıcı zaten gbanned; Sebebini değiştirirdim, ama bana bir tane vermedin...")
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("Bu kullanıcı aşağıdaki nedenlerden dolayı zaten yetkilidir:\n"
                               "<code>{}</code>\n"
                               "Gittin ve yeni sebebinle güncelledim!".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)

        else:
            message.reply_text("Bu kullanıcı zaten yetkilendirilmiş, ancak herhangi bir neden belirtilmemiş; Gittim ve güncelledim!")

        return

    message.reply_text("Üstünde!")

    start_time = time.time()
    datetime_fmt = "%Y-%m-%dT%H:%M"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != 'private':
        chat_origin = "<b>{} ({})</b>\n".format(html.escape(chat.title), chat.id)
    else:
        chat_origin = "<b>{}</b>\n".format(chat.id)

    log_message = (f"#GBANNED\n"
                   f"<b>Menşei:</b> <code>{chat_origin}</code>\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                   f"<b>Banlanan Kullanıcı:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
                   f"<b>Banlanan Kullanıcı ID:</b> <code>{user_chat.id}</code>\n"
                   f"<b>Etkinlik Damgası:</b> <code>{current_time}</code>")

    if reason:
        if chat.type == chat.SUPERGROUP and chat.username:
            log_message += f"\n<b>Sebep:</b> <a href=\"http://telegram.me/{chat.username}/{message.message_id}\">{reason}</a>"
        else:
            log_message += f"\n<b>Sebep:</b> <code>{reason}</code>"

    if GBAN_LOGS:
        try:
            log = bot.send_message(GBAN_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(GBAN_LOGS,
                                   log_message + "\n\nBeklenmedik bir hata nedeniyle biçimlendirme devre dışı bırakıldı.")

    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, log_message, html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    gbanned_chats = 0

    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
            gbanned_chats += 1

        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text(f"Could not gban due to: {excp.message}")
                if GBAN_LOGS:
                    bot.send_message(GBAN_LOGS, f"Could not gban due to {excp.message}",
                                     parse_mode=ParseMode.HTML)
                else:
                    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, f"Nedeniyle gban olamazdı: {excp.message}")
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    if GBAN_LOGS:
        log.edit_text(log_message + f"\n<b>Chats affected:</b> <code>{gbanned_chats}</code>", parse_mode=ParseMode.HTML)
    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, f"Gban tamamlandı! (Kullanıcı yasaklandı<code>{gbanned_chats}</code> chats)", parse_mode=ParseMode.HTML)

    end_time = time.time()
    gban_time = round((end_time - start_time), 2)

    if gban_time > 60:
        gban_time = round((gban_time / 60), 2)
        message.reply_text(f"Bitti! Bu gban etkilendi <code>{gbanned_chats}</code> chats, Took {gban_time} min", parse_mode=ParseMode.HTML)
    else:
        message.reply_text(f"Bitti! Bu gban etkilendi <code>{gbanned_chats}</code> chats, Took {gban_time} sec", parse_mode=ParseMode.HTML)

    try:
        bot.send_message(user_id,
                         "Yönetici izinlerine sahip olduğum tüm gruplardan küresel olarak yasaklandınız."
                         "Sebebini görmek için tıklayın /info"
                         f"Bunun bir hata olduğunu düşünüyorsanız, burada yasağa itiraz edebilirsiniz: {SUPPORT_CHAT}",
                         parse_mode=ParseMode.HTML)
    except:
        pass  # bot probably blocked by user


@run_async
@support_plus
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz veya belirtilen kimlik yanlış..")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Bu bir kullanıcı değil!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Bu kullanıcı bağlı değil!")
        return

    message.reply_text(f"I'll give {user_chat.first_name} dünya çapında ikinci bir şans.")

    start_time = time.time()
    datetime_fmt = "%Y-%m-%dT%H:%M"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != 'private':
        chat_origin = f"<b>{html.escape(chat.title)} ({chat.id})</b>\n"
    else:
        chat_origin = f"<b>{chat.id}</b>\n"

    log_message = (f"#UNGBANNED\n"
                   f"<b>Menşei:</b> <code>{chat_origin}</code>\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                   f"<b>Banı Kalkan Kullanıcı:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
                   f"<b>Banı Kalkan Kullanıcı ID:</b> <code>{user_chat.id}</code>\n"
                   f"<b>Etkinlik Damgası:</b> <code>{current_time}</code>")

    if GBAN_LOGS:
        try:
            log = bot.send_message(GBAN_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(GBAN_LOGS,
                                   log_message + "\n\nBeklenmedik bir hata nedeniyle biçimlendirme devre dışı bırakıldı.")
    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, log_message, html=True)

    chats = get_all_chats()
    ungbanned_chats = 0

    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat_id, user_id)
                ungbanned_chats += 1

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text(f"Nedeniyle gban kaldırılamadı: {excp.message}")
                if GBAN_LOGS:
                    bot.send_message(GBAN_LOGS, f"Could not un-gban due to: {excp.message}",
                                     parse_mode=ParseMode.HTML)
                else:
                    bot.send_message(OWNER_ID, f"Nedeniyle gban kaldırılamadı: {excp.message}")
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    if GBAN_LOGS:
        log.edit_text(log_message + f"\n<b>Etkilenen sohbetler:</b> {ungbanned_chats}", parse_mode=ParseMode.HTML)
    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "gban tamamlanmadı!")
    end_time = time.time()
    ungban_time = round((end_time - start_time), 2)

    if ungban_time > 60:
        ungban_time = round((ungban_time / 60), 2)
        message.reply_text(f"Kişi yasaklanmamış. aldı {ungban_time} min")
    else:
        message.reply_text(f"Kişi yasaklanmamış. aldı {ungban_time} sec")


@run_async
@support_plus
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("Sınırsız kullanıcı yok! Sen beklediğimden daha naziksin...")
        return

    banfile = 'Vida bu adamlar.\n'
    for user in banned_users:
        banfile += f"[x] {user['name']} - {user['user_id']}\n"
        if user["reason"]:
            banfile += f"Sebep: {user['reason']}\n"

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="İşte şu an gbanned kullanıcıları listesi.")


def check_and_ban(update, user_id, should_message=True):
    
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("<b>Alert:</b> Bu kullanıcı küresel olarak yasaklandı.\n"
                                                "<code>*onları buradan yasakla*.</code>\n"
                                                f"Sohbete itiraz et: {SUPPORT_CHAT}", parse_mode=ParseMode.HTML)


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user
        chat = update.effective_chat
        msg = update.effective_message

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)
            return

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)
        
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Bu grupta gbans'ı etkinleştirdim. Bu sizi korumaya yardımcı olacaktır "
                                                "spam gönderenler, hoş olmayan karakterler ve en büyük trollerden.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Bu gruptaki gbansları devre dışı bıraktım. GBans kullanıcılarınızı etkilemez "
                                                "Artık. Herhangi bir trol ve spam göndericisinden daha az korunacaksınız "
                                                "rağmen!")
    else:
        update.effective_message.reply_text("Bir ayar seçmem için bana bazı argümanlar verin! on/off, yes/no!\n\n"
                                            "Geçerli ayarınız: {}\n"
                                            "True olduğunda, grubunuzda gerçekleşen herhangi bir gbans da gerçekleşir. "
                                            "Yanlış olduğunda, sizi olası merhametine bırakmazlar. "
                                            "spammers.".format(sql.does_chat_gban(update.effective_chat.id)))


def __stats__():
    return f"{sql.num_gbanned_users()} gbanned kullanıcıları."


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "Küresel olarak yasaklandı: <b>{}</b>"
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += f"\n<b>Sebep:</b> <code>{html.escape(user.reason)}</code>"
        text += f"\n<b>Sohbete İtiraz Et:</b> {SUPPORT_CHAT}"
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"Bu sohbet * gbans'ı zorunlu kılıyor*: `{sql.does_chat_gban(chat_id)}`."


__help__ = f"""
*Admins only:*
 • `/gbanstat <on/off/yes/no>`*:* Global yasakların grubunuz üzerindeki etkisini devre dışı bırakır veya mevcut ayarlarınızı döndürür.

Küresel yasaklar olarak da bilinen Gbans, bot sahipleri tarafından spam göndericileri tüm gruplarda yasaklamak için kullanılır. Bu korumaya yardımcı olur \
spam gruplarını olabildiğince çabuk kaldırarak siz ve gruplarınız. Arayarak grubunuz için devre dışı bırakılabilirler \
`/gbanstat`
*Note:* Kullanıcılar gbans'a itiraz edebilir veya {SUPPORT_CHAT}
"""

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True)
GBAN_LIST = CommandHandler("gbanlist", gbanlist)

GBAN_STATUS = CommandHandler("gbanstat", gbanstat, pass_args=True, filters=Filters.group)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

__mod_name__ = "Global Bans"
__handlers__ = [GBAN_HANDLER, UNGBAN_HANDLER, GBAN_LIST, GBAN_STATUS]

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
    __handlers__.append((GBAN_ENFORCER, GBAN_ENFORCE_GROUP))
