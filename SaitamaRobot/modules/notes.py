import re
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import SaitamaRobot.modules.sql.notes_sql as sql
from SaitamaRobot import dispatcher, MESSAGE_DUMP, LOGGER, SUPPORT_CHAT
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin
from SaitamaRobot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from SaitamaRobot.modules.helper_funcs.msg_types import get_note_type

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# Do not async
def get(bot, update, notename, show_none=True, no_format=False):
    chat_id = update.effective_chat.id
    note = sql.get_note(chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id

        if note.is_reply:
            if MESSAGE_DUMP:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=MESSAGE_DUMP, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Yönlendirme mesajı bulunamadı":
                        message.reply_text("Bu mesaj kaybolmuş gibi görünüyor - kaldıracağım "
                                           "not listenizden.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=chat_id, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Yönlendirme mesajı bulunamadı":
                        message.reply_text("Bu notun orijinal göndereni silinmiş gibi görünüyor "
                                           "onların mesajı - üzgünüm! Bot yöneticinizi bir "
                                           "Bunu önlemek için mesaj dökümü. Bu notum "
                                           "kayıtlı notun.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
        else:
            text = note.value
            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(chat_id, notename)
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    bot.send_message(chat_id, text, reply_to_message_id=reply_id,
                                     parse_mode=parseMode, disable_web_page_preview=True,
                                     reply_markup=keyboard)
                else:
                    ENUM_FUNC_MAP[note.msgtype](chat_id, note.file, caption=text, reply_to_message_id=reply_id,
                                                parse_mode=parseMode, disable_web_page_preview=True,
                                                reply_markup=keyboard)

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text("Daha önce hiç görmediğim birinden bahsetmeye çalıştığın anlaşılıyor. Eğer gerçekten "
                                       "onlardan bahsetmek istiyorum, mesajlarından birini bana ilet, ben de "
                                       "etiketlemek için!")
                elif FILE_MATCHER.match(note.value):
                    message.reply_text("Bu not başka bir bottan yanlış içe aktarılmış bir dosyaydı - kullanamıyorum "
                                       "o. Gerçekten ihtiyacınız varsa, tekrar kaydetmeniz gerekir. İçinde "
                                       "bu arada not listenizden kaldıracağım.")
                    sql.rm_note(chat_id, notename)
                else:
                    message.reply_text("Bu not yanlış biçimlendirildiği için gönderilemedi. Ask in "
                                       f"{SUPPORT_CHAT} nedenini anlayamıyorsan!")
                    LOGGER.exception("#%S mesajı sohbette ayrıştırılamadı %s", notename, str(chat_id))
                    LOGGER.warning("Mesaj önceki değeri: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("Bu not mevcut değil")


@run_async
def cmd_get(bot: Bot, update: Update, args: List[str]):
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(bot, update, args[0].lower(), show_none=True, no_format=True)
    elif len(args) >= 1:
        get(bot, update, args[0].lower(), show_none=True)
    else:
        update.effective_message.reply_text("Rekt al")


@run_async
def hash_get(bot: Bot, update: Update):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:].lower()
    get(bot, update, no_hash, show_none=False)


@run_async
@user_admin
def save(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)
    note_name = note_name.lower()
    if data_type is None:
        msg.reply_text("Dostum, not yok")
        return

    sql.add_note_to_db(chat_id, note_name, text, data_type, buttons=buttons, file=content)

    msg.reply_text(f"Evet Eklendi {note_name}.\nİle al /get {note_name}, or #{note_name}")

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text("Bir bottan mesaj kaydetmeye çalıştığınız anlaşılıyor. ne yazık ki, "
                           "botlar bot mesajlarını iletemez, bu yüzden tam mesajı kaydedemiyorum. "
                           "\nYapabileceğim tüm metni kaydedeceğim, ama daha fazlasını istiyorsan, "
                           "mesajı kendiniz iletin ve kaydedin.")
        else:
            msg.reply_text("Botlar telgrafla biraz özürlü ve botların "
                           "diğer botlarla etkileşime geçtiğinden bu mesajı kaydedemiyorum "
                           "genellikle yaptığım gibi - iletmeyi ve "
                           "sonra bu yeni mesaj kaydedilsin mi? Teşekkürler!")
        return


@run_async
@user_admin
def clear(bot: Bot, update: Update, args: List[str]):
    chat_id = update.effective_chat.id
    if len(args) >= 1:
        notename = args[0].lower()

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("Not başarıyla kaldırıldı.")
        else:
            update.effective_message.reply_text("Bu benim veritabanımda bir not değil!")


@run_async
def list_notes(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)

    msg = "*Notes in chat:*\n"
    for note in note_list:
        note_name = escape_markdown(f" - {note.name.lower()}\n")
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if msg == "*Sohbette notlar:*\n":
        update.effective_message.reply_text("No notes in this chat!")

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get('extra', {}).items():
        match = FILE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end():].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(chat_id, document=output, filename="failed_imports.txt",
                                         caption="Bu dosyalar /photos kaynak nedeniyle içe aktarılamadı "
                                                 "başka bir bottan. Bu bir telgraf API kısıtlamasıdır ve yapamaz "
                                                 "kaçınılmalıdır. rahatsızlıktan dolayı özür dileriz!")


def __stats__():
    return f"{sql.num_notes()} notes, across {sql.num_chats()} chats."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return f"There are `{len(notes)}`bu sohbetteki notlar."


__help__ = """
 • `/get <notename>`*:* notename ile not al
 • `#<notename>`*:* ile aynı /get
 • `/notes` yada `/saved`*:* bu sohbette kaydedilen tüm notları listele

Herhangi bir biçimlendirme olmadan notun içeriğini almak istiyorsanız, kullan `/get <notename> noformat`. Bu \
güncel bir not güncellenirken faydalı olabilir.

*Admins only:*
 • `/save <notename> <notedata>`*:*notedata adını notename adlı bir not olarak kaydeder
Standart işaretleme bağlantısı sözdizimi kullanılarak bir nota bir düğme eklenebilir - bağlantıya yalnızca \
`buttonurl:` bölüm gibi: `[somelink](buttonurl:example.com)`. kontrol `/markdownhelp` daha fazla bilgi için.
 • `/save <notename>`*:* cevaplanan mesajı notename adıyla bir not olarak kaydet
 • `/clear <notename>`*:* bu isimle net not
 *Note:* Not adları büyük / küçük harfe duyarlı değildir ve kaydedilmeden önce otomatik olarak küçük harfe dönüştürülür.
"""

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
