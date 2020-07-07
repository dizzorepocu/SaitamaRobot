import html
import re
from typing import List

from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async
from SaitamaRobot.modules.helper_funcs.regex_helper import infinite_loop_check, regex_searcher
import SaitamaRobot.modules.sql.blacklist_sql as sql
from SaitamaRobot import dispatcher, LOGGER
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin, user_not_admin, connection_status
from SaitamaRobot.modules.helper_funcs.extraction import extract_text
from SaitamaRobot.modules.helper_funcs.misc import split_message

BLACKLIST_GROUP = 11

def infinite_loop_check(regex):
     loop_matches = [r'\((.{1,}[\+\*]){1,}\)[\+\*].', r'[\(\[].{1,}\{\d(,)?\}[\)\]]\{\d(,)?\}', r'\(.{1,}\)\{.{1,}(,)?\}\(.*\)(\+|\* |\{.*\})']
     for match in loop_matches:
          match_1 = re.search(match, regex)
          if match_1: return True

@run_async
@connection_status
@user_admin
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    chat = update.effective_chat

    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    if update_chat_title == message_chat_title:
        base_blacklist_string = "şimdiki <b>blacklisted</b> kelimeler:\n"
    else:
        base_blacklist_string = f"şimdiki <b>blacklisted</b> kelimeler içinde <b>{update_chat_title}</b>:\n"

    all_blacklisted = sql.get_chat_blacklist(chat.id)

    filter_list = base_blacklist_string

    if len(args) > 0 and args[0].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += f"<code>{html.escape(trigger)}</code>\n"
    else:
        for trigger in all_blacklisted:
            filter_list += f" - <code>{html.escape(trigger)}</code>\n"

    split_text = split_message(filter_list)
    for text in split_text:
        if text == base_blacklist_string:
            if update_chat_title == message_chat_title:
                msg.reply_text("Burada kara listeye alınmış mesaj yok!")
            else:
                msg.reply_text(f"İçinde kara listeye alınmış mesaj yok <b>{update_chat_title}</b>!",
                               parse_mode=ParseMode.HTML)
            return
        msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@connection_status
@user_admin
def add_blacklist(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    words = msg.text.split(None, 1)

    if len(words) > 1:
        text = words[1]
        to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))

        for trigger in to_blacklist:
            try:
                re.compile(trigger)
            except Exception as exce:
                msg.reply_text(f"Normal ifade eklenemedi, Error: {exce}")
                return
            check = infinite_loop_check(trigger)
            if not check:
               sql.add_to_blacklist(chat.id, trigger.lower())
            else:
                msg.reply_text("Korkarım şu normal ifadeyi ekleyemiyorum.")
                return

        if len(to_blacklist) == 1:
            msg.reply_text(f"Eklendi <code>{html.escape(to_blacklist[0])}</code> to the blacklist!",
                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(f"Added <code>{len(to_blacklist)}</code> tetikler blacklist.",
                           parse_mode=ParseMode.HTML)

    else:
        msg.reply_text("Bana hangi kelimeleri kaldırmak istediğini söyle blacklist.")


@run_async
@connection_status
@user_admin
def unblacklist(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    words = msg.text.split(None, 1)

    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        successful = 0

        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat.id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text(f"Silindi <code>{html.escape(to_unblacklist[0])}</code> kara listeden!",
                               parse_mode=ParseMode.HTML)
            else:
                msg.reply_text("Bu kara listeye alınan bir tetikleyici değil...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(f"Silindi <code>{successful}</code> tetikler blacklist.", parse_mode=ParseMode.HTML)

        elif not successful:
            msg.reply_text("Bu tetikleyicilerin hiçbiri mevcut olmadığından kaldırılmadı.", parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(f"Silindi <code>{successful}</code> tetikler the blacklist."
                           f" {len(to_unblacklist) - successful} mevcut değildi, bu yüzden kaldırılmadı.",
                           parse_mode=ParseMode.HTML)
    else:
        msg.reply_text(" Bana hangi kelimeleri kaldırmak istediğini söyle blacklist.")


@run_async
@connection_status
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message
    to_match = extract_text(message)
    msg = update.effective_message
    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + trigger + r"( |$|[^\w])"
        match = regex_searcher(pattern, to_match)
        if not match:
            #Skip to next item in blacklist
            continue
        if match:
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Silinecek mesaj bulunamadı":
                    pass
                else:
                    LOGGER.exception("Kara liste mesajı silinirken hata oluştu.")
            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "var {} blacklisted kelimeler.".format(blacklisted)


def __stats__():
    return "{} blacklist tetikleyici, karşısında {} sohbetler.".format(sql.num_blacklist_filters(),
                                                            sql.num_blacklist_filter_chats())


__help__ = """
Kara listeler, bir grupta belirli tetikleyicilerin söylenmesini durdurmak için kullanılır. Tetikleyiciden bahsedildiği her zaman, \
mesaj hemen silinir. İyi bir kombo bazen bunu uyar filtreleriyle eşleştirmektir!
*NOTE:* kara listeler grup yöneticisini etkilemez.

 • `/blacklist`*:* mevcut kara listeye alınan kelimeleri gösterir.

*Admins only:*
 • `/addblacklist <tetikleyici>`*:*Kara listeye bir tetikleyici ekleyin. Her satır bir tetikleyici olarak kabul edilir, bu nedenle farklı \
satırları birden fazla tetikleyici eklemenize izin verir.
 • `/unblacklist <tetikleyici>`*:* Tetikleyicileri kara listeden kaldırın. Aynı yeni satır mantığı burada geçerlidir, böylece kaldırabilirsiniz \
aynı anda birden fazla tetikleyici.
 • `/rmblacklist <tetikleyici>`*:* Yukarıdaki ile aynı.
"""

BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist", blacklist, pass_args=True)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"], unblacklist)
BLACKLIST_DEL_HANDLER = MessageHandler((Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group, del_blacklist, edited_updates=True)
dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)

__mod_name__ = "Blacklist Word"
__handlers__ = [BLACKLIST_HANDLER, ADD_BLACKLIST_HANDLER, UNBLACKLIST_HANDLER, (BLACKLIST_DEL_HANDLER, BLACKLIST_GROUP)]
