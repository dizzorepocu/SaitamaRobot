import html
import re

import telegram
from telegram import Bot, Update
from telegram import ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, DispatcherHandlerStop, run_async
from telegram.utils.helpers import escape_markdown

from SaitamaRobot import dispatcher, LOGGER, SUPPORT_CHAT
from SaitamaRobot.modules.blacklist import infinite_loop_check
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin, connection_status
from SaitamaRobot.modules.helper_funcs.extraction import extract_text
from SaitamaRobot.modules.helper_funcs.filters import CustomFilters
from SaitamaRobot.modules.helper_funcs.regex_helper import infinite_loop_check, regex_searcher
from SaitamaRobot.modules.helper_funcs.misc import build_keyboard
from SaitamaRobot.modules.helper_funcs.string_handling import split_quotes, button_markdown_parser
from SaitamaRobot.modules.sql import cust_filters_sql as sql

HANDLER_GROUP = 10


@run_async
@connection_status
def list_handlers(bot: Bot, update: Update):
    chat = update.effective_chat
    all_handlers = sql.get_chat_triggers(chat.id)

    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    if update_chat_title == message_chat_title:
        BASIC_FILTER_STRING = "<b>Filters in this chat:</b>\n"
    else:
        BASIC_FILTER_STRING = f"<b>Filters in {update_chat_title}</b>:\n"

    if not all_handlers:
        if update_chat_title == message_chat_title:
            update.effective_message.reply_text("Burada etkin filtre yok!")
        else:
            update.effective_message.reply_text(f"Etkin filtre yok <b>{update_chat_title}</b>!",
                                                parse_mode=telegram.ParseMode.HTML)
        return

    filter_list = ""
    for keyword in all_handlers:
        entry = f" - <code>{html.escape(keyword)}</code>\n"
        if len(entry) + len(filter_list) + len(BASIC_FILTER_STRING) > telegram.MAX_MESSAGE_LENGTH:
            filter_list = BASIC_FILTER_STRING + html.escape(filter_list)
            update.effective_message.reply_text(filter_list, parse_mode=telegram.ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == BASIC_FILTER_STRING:
        filter_list = BASIC_FILTER_STRING + filter_list
        update.effective_message.reply_text(filter_list, parse_mode=telegram.ParseMode.HTML)


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@connection_status
@user_admin
def filters(bot: Bot, update: Update):
    chat = update.effective_chat
    msg = update.effective_message
    args = msg.text.split(None, 1)

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])
    if len(extracted) < 1:
        return
    # set trigger -> lower, so as to avoid adding duplicate filters with different cases
    keyword = extracted[0]
    is_sticker = False
    is_document = False
    is_image = False
    is_voice = False
    is_audio = False
    is_video = False
    buttons = []

    # determine what the contents of the filter are - text, image, sticker, etc
    if len(extracted) >= 2:
        offset = len(extracted[1]) - len(msg.text)  # set correct offset relative to command + notename
        content, buttons = button_markdown_parser(extracted[1], entities=msg.parse_entities(), offset=offset)
        content = content.strip()
        if not content:
            msg.reply_text("Not mesajı yok - SADECE düğmeleriniz olamaz, onunla gitmek için bir mesaja ihtiyacınız var!")
            return

    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        is_sticker = True

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        is_document = True

    elif msg.reply_to_message and msg.reply_to_message.photo:
        content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
        is_image = True

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        is_audio = True

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        is_voice = True

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        is_video = True

    else:
        msg.reply_text("Ne ile cevap vereceğinizi belirtmediniz!")
        return
    if infinite_loop_check(keyword):
        msg.reply_text("Korkarım şu normal ifadeyi ekleyemiyorum")
        return
    # Add the filter
    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, HANDLER_GROUP)

    sql.add_filter(chat.id, keyword, content, is_sticker, is_document, is_image, is_audio, is_voice, is_video,
                   buttons)

    msg.reply_text("'{}' İşleyicisi eklendi!".format(keyword))
    raise DispatcherHandlerStop


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@connection_status
@user_admin
def stop_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    msg = update.effective_message
    args = msg.text.split(None, 1)

    if len(args) < 2:
        return

    chat_filters = sql.get_chat_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("Burada etkin filtre yok!")
        return

    for keyword in chat_filters:
        if keyword == args[1]:
            sql.remove_filter(chat.id, args[1])
            msg.reply_text("Evet, buna cevap vermeyi bırakacağım.")
            raise DispatcherHandlerStop

    msg.reply_text("Bu geçerli bir filtre değil - tüm etkin filtreler için çalıştır /filters.")

@run_async
def reply_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message
    to_match = extract_text(message)

    if not to_match:
        return

    chat_filters = sql.get_chat_triggers(chat.id)
    for keyword in chat_filters:
        pattern = r"( |^|[^\w])" + keyword + r"( |$|[^\w])"
        match = regex_searcher(pattern, to_match)
        if not match:
            #Skip to next item
            continue
        if match:
            filt = sql.get_filter(chat.id, keyword)
            if filt.is_sticker:
                message.reply_sticker(filt.reply)
            elif filt.is_document:
                message.reply_document(filt.reply)
            elif filt.is_image:
                message.reply_photo(filt.reply)
            elif filt.is_audio:
                message.reply_audio(filt.reply)
            elif filt.is_voice:
                message.reply_voice(filt.reply)
            elif filt.is_video:
                message.reply_video(filt.reply)
            elif filt.has_markdown:
                buttons = sql.get_buttons(chat.id, filt.keyword)
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                try:
                    message.reply_text(filt.reply, parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True,
                                       reply_markup=keyboard)
                except BadRequest as excp:
                    if excp.message == "Desteklenmeyen URL protokolü":
                        message.reply_text("Desteklenmeyen bir URL protokolü kullanmaya çalışıyor gibi görünüyorsunuz. Telegram "
                                           "bazı protokoller için düğmeleri desteklemiyor, gibi tg://. Please try "
                                           f"tekrar, ya da sor {SUPPORT_CHAT} yardım için.")
                    elif excp.message == "Yanıt mesajı bulunamadı":
                        bot.send_message(chat.id, filt.reply, parse_mode=ParseMode.MARKDOWN,
                                         disable_web_page_preview=True,
                                         reply_markup=keyboard)
                    else:
                        message.reply_text("Bu not yanlış biçimlendirildiği için gönderilemedi. Sor"
                                           f"{SUPPORT_CHAT} nedenini anlayamıyorsan!")
                        LOGGER.warning("%S iletisi ayrıştırılamadı", str(filt.reply))
                        LOGGER.exception("%S sohbetindeki %s filtresi ayrıştırılamadı", str(filt.keyword), str(chat.id))

            else:
                # LEGACY - all new filters will have has_markdown set to True.
                message.reply_text(filt.reply)
            break


def __stats__():
    return "{} filtreler {} sohbetler.".format(sql.num_filters(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    cust_filters = sql.get_chat_triggers(chat_id)
    return "Şu anda burada  `{}`özel filtre var.".format(len(cust_filters))


__help__ = """
 • `/filters`*:* bu sohbetteki tüm etkin filtreleri listele.

*Admins only:*
 • `/filter <keyword> <reply message>`*:* bu sohbete bir filtre ekler. Bot artık 'anahtar kelime' olduğunda bu iletiyi yanıtlayacaktır\
belirtilir. Bir anahtar kelimeye sahip bir çıkartmaya yanıt verirseniz, bot bu çıkartmayla yanıt verir. \
Anahtar kelimenizin cümle olmasını istiyorsanız tırnak işareti kullanın. 
*Örnek:* `/filter "hey orada "Nasılsın?`
 • `/stop <filter keyword>`*:* bu filtreyi durdur.
Note: Filtreler artık normal ifadeye sahip olduğundan, mevcut tüm filtreler varsayılan olarak büyük / küçük harfe duyarlı değildir.\
Büyük / küçük harfe duyarlı olmayan normal ifadeyi kullanmak için\
`/filter "(?i) tetikleyici kelimem "davayı yok sayan cevabım`\
Daha gelişmiş regex yardımına ihtiyacınız varsa, lütfen bize ulaşın @ElsaSupport. 
"""

FILTER_HANDLER = CommandHandler("filter", filters)
STOP_HANDLER = CommandHandler("stop", stop_filter)
LIST_HANDLER = DisableAbleCommandHandler("filters", list_handlers, admin_ok=True)
CUST_FILTER_HANDLER = MessageHandler(CustomFilters.has_text, reply_filter)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CUST_FILTER_HANDLER, HANDLER_GROUP)

__mod_name__ = "Filters"
__handlers__ = [FILTER_HANDLER, STOP_HANDLER, LIST_HANDLER, (CUST_FILTER_HANDLER, HANDLER_GROUP)]
