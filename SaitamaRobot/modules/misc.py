import html
import re
from typing import List

import requests
from telegram import Bot, Update, MessageEntity, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, DEV_USERS, TIGER_USERS, WHITELIST_USERS
from SaitamaRobot.__main__ import STATS, USER_INFO, TOKEN
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin, sudo_plus
from SaitamaRobot.modules.helper_funcs.extraction import extract_user


MARKDOWN_HELP = f"""
Markdown, telgraf tarafından desteklenen çok güçlü bir biçimlendirme aracıdır. {dispatcher.bot.first_name} emin olmak için bazı geliştirmeler var \
kaydedilen mesajlar doğru şekilde ayrıştırılır ve düğmeler oluşturmanıza olanak tanır.

• <code>_italic_</code>*:* metni kaydırma '_' italik metin üretecek
• <code>*bold*</code>*:* metni kaydırma '*' kalın metin üretecek
• <code>`code`</code>*:* metni kaydırma '`' olarak da bilinen tek aralıklı metin üretecek 'code'
• <code>[sometext](someURL)</code>*:* bu bir bağlantı oluşturur - mesaj sadece gösterilir <code>sometext</code>, \
üzerine dokunduğunuzda sayfanın <code>someURL</code>.
<b>Örnek:</b>Örnek:<b>Örnek:</b> <code>[test](example.com)</code>

• <code>[buttontext](buttonurl:someURL)</code>*:* bu, kullanıcıların telgraf yapmasına izin veren özel bir geliştirmedir \
kendi markdown düğmeleri. <code>buttontext</code> düğmede görüntülenen şey olacak ve <code>someurl</code> \
açılan url olacak.
<b>Örnek:</b> <code>[This is a button](buttonurl:example.com)</code>

Aynı satırda birden fazla düğme istiyorsanız, şunu kullanın:h:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
Bu, satır başına bir düğme yerine tek bir satırda iki düğme oluşturur.

Mesajınızın <b>MUST</b> sadece düğme dışında bir metin içeriyor!
"""


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    chat = update.effective_chat
    msg = update.effective_message
    user_id = extract_user(msg, args)

    if user_id:

        if msg.reply_to_message and msg.reply_to_message.forward_from:

            user1 = message.reply_to_message.from_user
            user2 = message.reply_to_message.forward_from

            msg.reply_text(f"Orijinal gönderen, {html.escape(user2.first_name)},"
                           f" has an ID of <code>{user2.id}</code>.\n"
                           f"The forwarder, {html.escape(user1.first_name)},"
                           f" has an ID of <code>{user1.id}</code>.",
                           parse_mode=ParseMode.HTML)

        else:

            user = bot.get_chat(user_id)
            msg.reply_text(f"{html.escape(user.first_name)}'s id is <code>{user.id}</code>.",
                           parse_mode=ParseMode.HTML)

    else:

        if chat.type == "private":
            msg.reply_text(f"Kimliğin <code>{chat.id}</code>.",
                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(f"Bu grup's id is <code>{chat.id}</code>.",
                           parse_mode=ParseMode.HTML)


@run_async
def gifid(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.animation:
        update.effective_message.reply_text(f"Gif ID:\n<code>{msg.reply_to_message.animation.file_id}</code>",
                                            parse_mode=ParseMode.HTML)
    else:
        update.effective_message.reply_text("Kimliğini almak için lütfen bir gif'e yanıt verin.")


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    chat = update.effective_chat
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not message.reply_to_message and not args:
        user = message.from_user

    elif not message.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not message.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        message.reply_text("Bundan bir kullanıcı çıkaramıyorum.")
        return

    else:
        return

    text = (f"<b>Characteristics:</b>\n"
            f"ID: <code>{user.id}</code>\n"
            f"First Name: {html.escape(user.first_name)}")

    if user.last_name:
        text += f"\nLast Name: {html.escape(user.last_name)}"

    if user.username:
        text += f"\nUsername: @{html.escape(user.username)}"

    text += f"\nPermanent user link: {mention_html(user.id, 'link')}"

    disaster_level_present = False

    if user.id == OWNER_ID:
        text += "\nBu kişinin afet seviyesi 'Tanrı'."
        disaster_level_present = True
    elif user.id in DEV_USERS:
        text += "\nBu üye 'Kahraman Derneği''."
        disaster_level_present = True
    elif user.id in SUDO_USERS:
        text += "\nBu kişinin afet seviyesi 'Ejderha'."
        disaster_level_present = True
    elif user.id in SUPPORT_USERS:
        text += "\nBu kişinin afet seviyesi 'Şeytan''."
        disaster_level_present = True
    elif user.id in TIGER_USERS:
        text += "\nBu kişinin afet seviyesi 'Kaplan'."
        disaster_level_present = True
    elif user.id in WHITELIST_USERS:
        text += "\nBu kişinin afet seviyesi 'Kurt'."
        disaster_level_present = True

    if disaster_level_present:
        text += ' [<a href="http://t.me/{}?start=disasters">?</a>]'.format(bot.username)

    try:
        user_member = chat.get_member(user.id)
        if user_member.status == 'administrator':
            result = requests.post(f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={chat.id}&user_id={user.id}")
            result = result.json()["result"]
            if "custom_title" in result.keys():
                custom_title = result['custom_title']
                text += f"\n\nBu kullanıcı unvanı elinde tutuyor <b>{custom_title}</b> here."
    except BadRequest:
        pass

    for mod in USER_INFO:
        try:
            mod_info = mod.__user_info__(user.id).strip()
        except TypeError:
            mod_info = mod.__user_info__(user.id, chat.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@run_async
@user_admin
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message

    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)

    message.delete()


@run_async
def markdown_help(bot: Bot, update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("Aşağıdaki mesajı bana iletmeyi deneyin, göreceksiniz!")
    update.effective_message.reply_text("/save test Bu bir markdown testidir. _italics_, *bold*, `code`, "
                                        "[URL](example.com) [button](buttonurl:github.com) "
                                        "[button2](buttonurl://google.com:same)")


@run_async
@sudo_plus
def stats(bot: Bot, update: Update):
    stats = "Current stats:\n" + "\n".join([mod.__stats__() for mod in STATS])
    result = re.sub(r'(\d+)', r'<code>\1</code>', stats)
    update.effective_message.reply_text(result, parse_mode=ParseMode.HTML)


__help__ = """
 • `/id`*:* geçerli grup kimliğini al. Bir iletiyi yanıtlayarak kullanılırsa, kullanıcının kimliğini alır.
 • `/gifid`*:* size dosya kimliğini söylemek için bir gif cevap.
 • `/info`*:* bir kullanıcı hakkında bilgi al.
 • `/markdownhelp`*:* işaretlemenin telgrafta nasıl çalıştığının hızlı bir özeti - yalnızca özel sohbetlerde çağrılabilir.
"""

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
GIFID_HANDLER = DisableAbleCommandHandler("gifid", gifid)
INFO_HANDLER = DisableAbleCommandHandler(["info", "appraise", "appraisal"], info, pass_args=True)
ECHO_HANDLER = DisableAbleCommandHandler("echo", echo, filters=Filters.group)
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)
STATS_HANDLER = CommandHandler("stats", stats)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(GIFID_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)

__mod_name__ = "Misc"
__command_list__ = ["id", "info", "echo"]
__handlers__ = [ID_HANDLER, GIFID_HANDLER, INFO_HANDLER, ECHO_HANDLER, MD_HELP_HANDLER, STATS_HANDLER]
