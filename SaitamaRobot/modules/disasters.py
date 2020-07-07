import html
import json
import os
from typing import List, Optional

from telegram import Bot, Update, ParseMode, TelegramError
from telegram.ext import CommandHandler, run_async
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher, WHITELIST_USERS, TIGER_USERS, SUPPORT_USERS, SUDO_USERS, DEV_USERS, OWNER_ID, SUPPORT_CHAT
from SaitamaRobot.modules.helper_funcs.chat_status import whitelist_plus, dev_plus, sudo_plus
from SaitamaRobot.modules.helper_funcs.extraction import extract_user
from SaitamaRobot.modules.log_channel import gloggable

ELEVATED_USERS_FILE = os.path.join(os.getcwd(), 'SaitamaRobot/elevated_users.json')


def check_user_id(user_id: int, bot: Bot) -> Optional[str]:
    if not user_id:
        reply = "Bu ... bir sohbet! Baka ka omae?"

    elif user_id == bot.id:
        reply = "Bu böyle çalışmıyor."

    else:
        reply = None
    return reply

#I added extra new lines
disasters = """ Aphrodite, "" Afet Seviyeleri olarak adlandırdığımız bot erişim seviyelerine sahiptir"*
\n*Heroes Association * - Bot sunucusuna erişebilen ve bot kodunu çalıştırabilen, düzenleyebilen, değiştirebilen geliştiriciler. Diğer Afetleri de yönetebilir
\n*Tanrı * - Sadece bir tane var, bot sahibi.
Sahibinin Aphrodite'de ki sohbetlerdeki bot yönetimi de dahil olmak üzere tam bot erişimi vardır.
\n*Ejderhalar * - Süper kullanıcı erişimine sahip olabilir, gban yapabilir, felaketleri onlardan daha düşük yönetebilir ve Aphrodite'de yöneticiler olabilir.
\n*Şeytanlar * - Erişimi Aphrodite genelinde küresel olarak yasaklamak gidin.
\n*Kaplanlar * - Kurtlarla aynıdır, ancak yasaklandığında kendilerini yasaklayabilirler.
\n*Wolves* - Yasaklanamaz, sessiz sel tekmelenir, ancak yöneticiler tarafından manuel olarak yasaklanabilir.
\n*Feragat *: Aphrodite'deki afet seviyeleri sorun giderme, destek ve potansiyel dolandırıcıların yasaklanması için hazırdır.
Kötüye kullanımı bildirin veya bu konuda bize daha fazla bilgi sorun: [Aphrodite Support](https://t.me/AphroditeSupport).
"""
# do not async, not a handler 
def send_disasters(update):
    update.effective_message.reply_text(disasters, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@run_async
@dev_plus
@gloggable
def addsudo(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        message.reply_text("Bu üye zaten bir Ejderha Felaketi")
        return ""

    if user_id in SUPPORT_USERS:
        rt += "HA'dan Ejderhaya Şeytan Afetini tanıtmasını istedi."
        data['supports'].remove(user_id)
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        rt += "HA'dan Ejderhaya Kurt Felaketini Teşvik Etmesini İstedi."
        data['whitelists'].remove(user_id)
        WHITELIST_USERS.remove(user_id)

    data['sudos'].append(user_id)
    SUDO_USERS.append(user_id)

    with open(ELEVATED_USERS_FILE, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + "\n{} Afet seviyesini başarıyla Dragon olarak ayarlayın!".format(user_member.first_name))

    log_message = (f"#SUDO\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                   f"<b>Kullanıcı:</b> {mention_html(user_member.id, user_member.first_name)}")

    if chat.type != 'private':
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@run_async
@sudo_plus
@gloggable
def addsupport(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        rt += "HA'dan bu Ejderhayı Şeytan'a deomote etmesini istedi"
        data['sudos'].remove(user_id)
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        message.reply_text("Bu kullanıcı zaten bir Şeytan Felaketi.")
        return ""

    if user_id in WHITELIST_USERS:
        rt += "HA'dan bu Kurt Felaketini Şeytan'a tanıtmasını istedi"
        data['whitelists'].remove(user_id)
        WHITELIST_USERS.remove(user_id)

    data['supports'].append(user_id)
    SUPPORT_USERS.append(user_id)

    with open(ELEVATED_USERS_FILE, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(rt + f"\n{user_member.first_name} İblis Felaketi olarak eklendi!")

    log_message = (f"#SUPPORT\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                   f"<b>Kullanıcı:</b> {mention_html(user_member.id, user_member.first_name)}")

    if chat.type != 'private':
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@run_async
@sudo_plus
@gloggable
def addwhitelist(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        rt += "Bu üye bir Ejderha Felaketidir, Kurt'a düşkündür."
        data['sudos'].remove(user_id)
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        rt += "Bu kullanıcı zaten bir Demon Felaketi, Kurt Demoting."
        data['supports'].remove(user_id)
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        message.reply_text("Bu kullanıcı zaten bir Kurt Felaketi.")
        return ""

    data['whitelists'].append(user_id)
    WHITELIST_USERS.append(user_id)

    with open(ELEVATED_USERS_FILE, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\nSuccessfully promoted {user_member.first_name} kurt felaketi!")

    log_message = (f"#WHITELIST\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)} \n"
                   f"<b>Türkçe:</b> {mention_html(user_member.id, user_member.first_name)}")

    if chat.type != 'private':
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@run_async
@sudo_plus
@gloggable
def addtiger(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        rt += "Bu üye Tiger'a Adanan Ejderha Felaketi."
        data['sudos'].remove(user_id)
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        rt += "Bu kullanıcı zaten Tiger'a indirgeyen bir Demon Felaketi."
        data['supports'].remove(user_id)
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        rt += "Bu kullanıcı zaten Tiger'a Adanan bir Kurt Felaketi."
        data['whitelists'].remove(user_id)
        WHITELIST_USERS.remove(user_id)

    if user_id in TIGER_USERS:
        message.reply_text("Bu kullanıcı zaten bir Tiger.")
        return ""

    data['tigers'].append(user_id)
    TIGER_USERS.append(user_id)

    with open(ELEVATED_USERS_FILE, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\nBaşarıyla tanıtıldı {user_member.first_name} Kaplan Felaketine!")

    log_message = (f"#TIGER\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)} \n"
                   f"<b>Kullanıcı:</b> {mention_html(user_member.id, user_member.first_name)}")

    if chat.type != 'private':
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@run_async
@dev_plus
@gloggable
def removesudo(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        message.reply_text("HA'dan bu kullanıcıyı Sivil'e indirmesini istedi")
        SUDO_USERS.remove(user_id)
        data['sudos'].remove(user_id)

        with open(ELEVATED_USERS_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (f"#UNSUDO\n"
                       f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                       f"<b>Kullanıcı:</b> {mention_html(user_member.id, user_member.first_name)}")

        if chat.type != 'private':
            log_message = "<b>{}:</b>\n".format(html.escape(chat.title)) + log_message

        return log_message

    else:
        message.reply_text("Bu kullanıcı bir Ejderha Felaketi değil!")
        return ""


@run_async
@sudo_plus
@gloggable
def removesupport(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUPPORT_USERS:
        message.reply_text("HA'dan bu kullanıcıyı Sivil'e indirmesini istedi")
        SUPPORT_USERS.remove(user_id)
        data['supports'].remove(user_id)

        with open(ELEVATED_USERS_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (f"#UNSUPPORT\n"
                       f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                       f"<b>Kullanıcı:</b> {mention_html(user_member.id, user_member.first_name)}")

        if chat.type != 'private':
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message

    else:
        message.reply_text("Bu kullanıcı Demon seviyesinde bir Felaket değil!")
        return ""


@run_async
@sudo_plus
@gloggable
def removewhitelist(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in WHITELIST_USERS:
        message.reply_text("Normal kullanıcıya indirgeme")
        WHITELIST_USERS.remove(user_id)
        data['whitelists'].remove(user_id)

        with open(ELEVATED_USERS_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (f"#UNWHITELIST\n"
                       f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                       f"<b>Kullanıcı:</b> {mention_html(user_member.id, user_member.first_name)}")

        if chat.type != 'private':
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("Bu kullanıcı bir kurt felaketi değil!")
        return ""


@run_async
@sudo_plus
@gloggable
def removetiger(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in TIGER_USERS:
        message.reply_text("Normal kullanıcıya indirgeme")
        TIGER_USERS.remove(user_id)
        data['tigers'].remove(user_id)

        with open(ELEVATED_USERS_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (f"#UNTIGER\n"
                       f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                       f"<b>Kullanıcı:</b> {mention_html(user_member.id, user_member.first_name)}")

        if chat.type != 'private':
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("Bu kullanıcı Tiger Afet değil!")
        return ""


@run_async
@whitelist_plus
def whitelistlist(bot: Bot, update: Update):
    reply = "<b>Bilinen Kurt Afetleri🐺:</b>\n"
    for each_user in WHITELIST_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)

            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


@run_async
@whitelist_plus
def tigerlist(bot: Bot, update: Update):
    reply = "<b>Bilinen Tiger Afetleri 🐯:</b>\n"
    for each_user in TIGER_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


@run_async
@whitelist_plus
def supportlist(bot: Bot, update: Update):
    reply = "<b>Bilinen Demon Afetleri 👹:</b>\n"
    for each_user in SUPPORT_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


@run_async
@whitelist_plus
def sudolist(bot: Bot, update: Update):
    true_sudo = list(set(SUDO_USERS) - set(DEV_USERS))
    reply = "<b>Bilinen Ejderha Felaketleri 🐉:</b>\n"
    for each_user in true_sudo:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


@run_async
@whitelist_plus
def devlist(bot: Bot, update: Update):
    true_dev = list(set(DEV_USERS) - {OWNER_ID})
    reply = "<b>Kahraman Derneği Üyeleri ⚡️:</b>\n"
    for each_user in true_dev:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


__help__ = f"""
 • `/heroes`*:* Tüm Hero Association üyelerini listeler.
 • `/dragons`*:* Tüm Dragon felaketlerini listeler.
 • `/demons`*:* Tüm Demon felaketlerini listeler.
 • `/tigers`*:* Tüm Kaplan felaketlerini listeler.
 • `/wolves`*:* Tüm Wolf felaketlerini listeler.
 *Note:* Bu komutlar, özel bot ayrıcalıklarına sahip kullanıcıları listeler ve yalnızca onlar tarafından kullanılabilir.
 Ziyaret edebilirsin {SUPPORT_CHAT} bunlar hakkında daha fazla sorgulamak için.
"""

SUDO_HANDLER = CommandHandler(("addsudo", "adddragon"), addsudo, pass_args=True)
SUPPORT_HANDLER = CommandHandler(("addsupport", "adddemon"), addsupport, pass_args=True)
TIGER_HANDLER = CommandHandler(("addtiger"), addtiger, pass_args=True)
WHITELIST_HANDLER = CommandHandler(("addwhitelist", "addwolf"), addwhitelist, pass_args=True)
UNSUDO_HANDLER = CommandHandler(("removesudo", "removedragon"), removesudo, pass_args=True)
UNSUPPORT_HANDLER = CommandHandler(("removesupport", "removedemon"), removesupport, pass_args=True)
UNTIGER_HANDLER = CommandHandler(("removetiger"), removetiger, pass_args=True)
UNWHITELIST_HANDLER = CommandHandler(("removewhitelist", "removewolf"), removewhitelist, pass_args=True)

WHITELISTLIST_HANDLER = CommandHandler(["whitelistlist", "wolves"], whitelistlist)
TIGERLIST_HANDLER = CommandHandler(["tigers"], tigerlist)
SUPPORTLIST_HANDLER = CommandHandler(["supportlist", "demons"], supportlist)
SUDOLIST_HANDLER = CommandHandler(["sudolist", "dragons"], sudolist)
DEVLIST_HANDLER = CommandHandler(["devlist", "heroes"], devlist)

dispatcher.add_handler(SUDO_HANDLER)
dispatcher.add_handler(SUPPORT_HANDLER)
dispatcher.add_handler(TIGER_HANDLER)
dispatcher.add_handler(WHITELIST_HANDLER)
dispatcher.add_handler(UNSUDO_HANDLER)
dispatcher.add_handler(UNSUPPORT_HANDLER)
dispatcher.add_handler(UNTIGER_HANDLER)
dispatcher.add_handler(UNWHITELIST_HANDLER)

dispatcher.add_handler(WHITELISTLIST_HANDLER)
dispatcher.add_handler(TIGERLIST_HANDLER)
dispatcher.add_handler(SUPPORTLIST_HANDLER)
dispatcher.add_handler(SUDOLIST_HANDLER)
dispatcher.add_handler(DEVLIST_HANDLER)

__mod_name__ = "Disasters"
__handlers__ = [SUDO_HANDLER, SUPPORT_HANDLER, TIGER_HANDLER, WHITELIST_HANDLER, 
                UNSUDO_HANDLER, UNSUPPORT_HANDLER, UNTIGER_HANDLER, UNWHITELIST_HANDLER,
                WHITELISTLIST_HANDLER, TIGERLIST_HANDLER, SUPPORTLIST_HANDLER,
                SUDOLIST_HANDLER, DEVLIST_HANDLER]
