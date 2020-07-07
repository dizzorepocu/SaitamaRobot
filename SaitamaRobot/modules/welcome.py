import html
import random
import re
import time
from typing import List
from functools import partial

from telegram import Update, Bot
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async, CallbackQueryHandler, JobQueue
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import SaitamaRobot.modules.sql.welcome_sql as sql
from SaitamaRobot.modules.sql.global_bans_sql import is_user_gbanned
from SaitamaRobot import dispatcher, OWNER_ID, DEV_USERS, SUDO_USERS, SUPPORT_USERS, TIGER_USERS, WHITELIST_USERS, LOGGER
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin, is_user_ban_protected
from SaitamaRobot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from SaitamaRobot.modules.helper_funcs.msg_types import get_welcome_type
from SaitamaRobot.modules.helper_funcs.string_handling import (markdown_parser,
                                                         escape_invalid_curly_brackets)
from SaitamaRobot.modules.log_channel import loggable

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']

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

VERIFIED_USER_WAITLIST = {}

# do not async
def send(update, message, keyboard, backup_message):
    chat = update.effective_chat
    cleanserv = sql.clean_service(chat.id)
    reply = update.message.message_id
    # Clean service welcome
    if cleanserv:
        try:
            dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False
    try:
        msg = update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard, reply_to_message_id=reply)
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNot: mevcut mesajda geçersiz bir url var "
                                                                      "düğmelerinden birinde. Lütfen güncelle."),
                                                      parse_mode=ParseMode.MARKDOWN, reply_to_message_id=reply)
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNot: geçerli mesajın düğmeleri var"
                                                                      "tarafından desteklenmeyen URL protokollerini kullanın "
                                                                      "telegram. Lütfen güncelle."),
                                                      parse_mode=ParseMode.MARKDOWN, reply_to_message_id=reply)
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNot: mevcut mesajda bazı kötü URL'ler var. "
                                                                      "Lütfen güncelle."),
                                                      parse_mode=ParseMode.MARKDOWN, reply_to_message_id=reply)
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! got invalid url host errors")
        else:
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNot: Gönderilirken bir hata oluştu "
                                                                      "custom message. Please update."),
                                                      parse_mode=ParseMode.MARKDOWN, reply_to_message_id=reply)
            LOGGER.exception()

    return msg


@run_async
@loggable
def new_member(bot: Bot, update: Update, job_queue: JobQueue):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)

    new_members = update.effective_message.new_chat_members

    for new_mem in new_members:

        welcome_log = None
        res = None
        sent = None
        should_mute = True
        welcome_bool = True

        if should_welc:

            reply = update.message.message_id
            cleanserv = sql.clean_service(chat.id)
            # Clean service welcome
            if cleanserv:
                try:
                    dispatcher.bot.delete_message(
                        chat.id, update.message.message_id)
                except BadRequest:
                    pass
                reply = False

            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text("Oh, Genos? Hadi bunu hareket ettirelim.", reply_to_message_id=reply)
                welcome_log = (f"{html.escape(chat.title)}\n"
                               f"#USER_JOINED\n"
                               f"Bot Yetkilisi sohbete katıldı")

            # Welcome Devs
            elif new_mem.id in DEV_USERS:
                update.effective_message.reply_text("Oha! Kahramanlar Derneği üyesi yeni katıldı!", reply_to_message_id=reply)

            # Welcome Sudos
            elif new_mem.id in SUDO_USERS:
                update.effective_message.reply_text("Huh! Bir Ejderha felaketi daha yeni katıldı! Dikkatli ol!", reply_to_message_id=reply)

            # Welcome Support
            elif new_mem.id in SUPPORT_USERS:
                update.effective_message.reply_text("Huh! Demon afet düzeyine sahip biri katıldı!", reply_to_message_id=reply)

            # Welcome Whitelisted
            elif new_mem.id in TIGER_USERS:
                update.effective_message.reply_text("Oof! Bir Tiger felaketi daha yeni katıldı!", reply_to_message_id=reply)

            # Welcome Tigers
            elif new_mem.id in WHITELIST_USERS:
                update.effective_message.reply_text("Oof! Bir kurt felaketi daha yeni katıldı!", reply_to_message_id=reply)

            # Welcome yourself
            elif new_mem.id == bot.id:
                update.effective_message.reply_text("Watashi ga kita!", reply_to_message_id=reply)

            else:
                # If welcome message is media, send with appropriate function
                if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)
                    continue

                # else, move on
                first_name = new_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if cust_welcome == sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(first=escape_markdown(first_name))

                    if new_mem.last_name:
                        fullname = escape_markdown(f"{first_name} {new_mem.last_name}")
                    else:
                        fullname = escape_markdown(first_name)
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(cust_welcome, VALID_WELCOME_FORMATTERS)
                    res = valid_format.format(first=escape_markdown(first_name),
                                              last=escape_markdown(new_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=new_mem.id)
                    buttons = sql.get_welc_buttons(chat.id)
                    keyb = build_keyboard(buttons)

                else:
                    res = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(first=escape_markdown(first_name))
                    keyb = []

                backup_message = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(first=escape_markdown(first_name))
                keyboard = InlineKeyboardMarkup(keyb)

        else:
            welcome_bool = False
            res = None
            keyboard = None
            backup_message = None
            reply = None

        # User exceptions from welcomemutes
        if is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id)) or human_checks:
            should_mute = False
        # Join welcome: soft mute
        if new_mem.is_bot:
            should_mute = False

        if user.id == new_mem.id:
            if should_mute:
                if welc_mutes == "soft":
                    bot.restrict_chat_member(chat.id, new_mem.id,
                                             can_send_messages=True,
                                             can_send_media_messages=False,
                                             can_send_other_messages=False,
                                             can_add_web_page_previews=False,
                                             until_date=(int(time.time() + 24 * 60 * 60)))

                if welc_mutes == "strong":
                    welcome_bool = False
                    VERIFIED_USER_WAITLIST.update({
                        new_mem.id : {
                            "should_welc" : should_welc,
                            "status" : False,
                            "update" : update,
                            "res" : res,
                            "keyboard" : keyboard,
                            "backup_message" : backup_message
                        }
                    })
                    new_join_mem = f"[{escape_markdown(new_mem.first_name)}](tg://user?id={user.id})"
                    message = msg.reply_text(f"{new_join_mem},insan olduğunuzu kanıtlamak için aşağıdaki düğmeyi tıklayın.\n120 saniyeniz var.",
                                             reply_markup=InlineKeyboardMarkup([{InlineKeyboardButton(
                                                 text="Evet ben insanım.",
                                                 callback_data=f"user_join_({new_mem.id})")}]),
                                             parse_mode=ParseMode.MARKDOWN, reply_to_message_id=reply)
                    bot.restrict_chat_member(chat.id, new_mem.id,
                                             can_send_messages=False,
                                             can_send_media_messages=False,
                                             can_send_other_messages=False,
                                             can_add_web_page_previews=False)

                    job_queue.run_once(
                        partial(
                            check_not_bot, new_mem, chat.id, message.message_id
                        ), 120, name="welcomemute"
                    )

        if welcome_bool:
            sent = send(update, res, keyboard, backup_message)

            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

        if welcome_log:
            return welcome_log

        return (f"{html.escape(chat.title)}\n"
                f"#USER_JOINED\n"
                f"<b>Kullanıcı</b>: {mention_html(user.id, user.first_name)}\n"
                f"<b>ID</b>: <code>{user.id}</code>")

    return ""


def check_not_bot(member, chat_id, message_id, bot, job):

    member_dict = VERIFIED_USER_WAITLIST.pop(member.id)
    member_status = member_dict.get("status")
    if not member_status:
        try:
            bot.unban_chat_member(chat_id, member.id)
        except:
            pass

        try:
            bot.edit_message_text("*kullanıcı kicklenen*\nHer zaman yeniden katılabilir ve deneyebilirler.", chat_id=chat_id, message_id=message_id)
        except:
            pass


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)

    if user.id == bot.id:
        return

    if should_goodbye:
        reply = update.message.message_id
        cleanserv = sql.clean_service(chat.id)
        # Clean service welcome
        if cleanserv:
            try:
                dispatcher.bot.delete_message(
                    chat.id, update.message.message_id)
            except BadRequest:
                pass
            reply = False

        left_mem = update.effective_message.left_chat_member
        if left_mem:
            # Dont say goodbyes to gbanned users
            if is_user_gbanned(left_mem.id):
                return

            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("Oi! Genos! O ayrıldı..", reply_to_message_id=reply)
                return

            # Give the devs a special goodbye
            elif left_mem.id in DEV_USERS:
                update.effective_message.reply_text("Daha sonra Kahramanlar Derneği'nde görüşürüz!", reply_to_message_id=reply)
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = left_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if cust_goodbye == sql.DEFAULT_GOODBYE:
                    cust_goodbye = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=escape_markdown(first_name))
                if left_mem.last_name:
                    fullname = escape_markdown(f"{first_name} {left_mem.last_name}")
                else:
                    fullname = escape_markdown(first_name)
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(first=escape_markdown(first_name),
                                          last=escape_markdown(left_mem.last_name or first_name),
                                          fullname=escape_markdown(fullname), username=username, mention=mention,
                                          count=count, chatname=escape_markdown(chat.title), id=left_mem.id)
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name)
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(update, res, keyboard, random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name))


@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    # if no args, show current replies.
    if not args or args[0].lower() == "noformat":
        noformat = True
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(f"Bu sohbette hoş geldiniz ayarı var: `{pref}`.\n"
                                            f"*Karşılama mesajı (doldurmamak {{}}) is:*",
                                            parse_mode=ParseMode.MARKDOWN)

        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            if noformat:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m)

            else:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text("Tamam! Üyeleri katıldıklarında selamlayacağım.")

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text("Etrafta ekmek yapacağım ve o zaman kimseye hoş gelmeyeceğim.")

        else:
            update.effective_message.reply_text("anlıyorum 'on/yes' or 'off/no' sadece!")


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat

    if not args or args[0] == "noformat":
        noformat = True
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(f"Bu sohbette hoşçakal ayarı var: `{pref}`.\n"
                                            f"*Elveda mesajı (dolduramamak {{}}) is:*",
                                            parse_mode=ParseMode.MARKDOWN)

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

            else:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("Ok!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("Ok!")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("Anlıyorum 'on/yes' or 'off/no' Sadece!")


@run_async
@user_admin
@loggable
def set_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Ne ile cevap vereceğinizi belirtmediniz!")
        return ""

    sql.set_custom_welcome(chat.id, content or text, data_type, buttons)
    msg.reply_text("Özel karşılama iletisini başarıyla ayarlayın!")

    return (f"<b>{html.escape(chat.title)}:</b>\n"
            f"#SET_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Karşılama mesajını ayarlama.")


@run_async
@user_admin
@loggable
def reset_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_welcome(chat.id, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text("Karşılama iletisini varsayılana başarıyla sıfırlayın!")

    return (f"<b>{html.escape(chat.title)}:</b>\n"
            f"#RESET_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Karşılama mesajını varsayılana sıfırla.")


@run_async
@user_admin
@loggable
def set_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Ne ile cevap vereceğinizi belirtmediniz!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("Özel veda mesajı başarıyla ayarlandı!")
    return (f"<b>{html.escape(chat.title)}:</b>\n"
            f"#SET_GOODBYE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Güle güle mesajını ayarla.")


@run_async
@user_admin
@loggable
def reset_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text("Güle güle mesajını başarıyla varsayılana sıfırlayın!")

    return (f"<b>{html.escape(chat.title)}:</b>\n"
            f"#RESET_GOODBYE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Güle güle mesajını sıfırla.")


@run_async
@user_admin
@loggable
def welcomemute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            sql.set_welcome_mutes(chat.id, False)
            msg.reply_text("Artık insanları katılma konusunda susturmayacağım!")
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#WELCOME_MUTE\n"
                    f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Hoş geldiniz sessiz modunu değiştirdi <b>OFF</b>.")
        elif args[0].lower() in ["soft"]:
            sql.set_welcome_mutes(chat.id, "soft")
            msg.reply_text("Kullanıcıların 24 saat boyunca medya gönderme iznini kısıtlayacağım.")
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#WELCOME_MUTE\n"
                    f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Hoş geldiniz sessiz modunu değiştirdi <b>SOFT</b>.")
        elif args[0].lower() in ["strong"]:
            sql.set_welcome_mutes(chat.id, "strong")
            msg.reply_text("Artık bot olmadıklarını kanıtlayana kadar insanları susturacağım.\nTekrarlanmadan önce 120 saniye sürecekler.")
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#WELCOME_MUTE\n"
                    f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Hoş geldiniz sessiz modunu değiştirdi <b>STRONG</b>.")
        else:
            msg.reply_text("Lütfen Girin `off`/`no`/`soft`/`strong`!", parse_mode=ParseMode.MARKDOWN)
            return ""
    else:
        curr_setting = sql.welcome_mutes(chat.id)
        reply = (f"\n Bana bir ortam ver!\nŞunlardan birini seçin: `off`/`no` or `soft` or `strong` only! \n"
                 f"şuanki ayarlar: `{curr_setting}`")
        msg.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        return ""


@run_async
@user_admin
@loggable
def clean_welcome(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text("İki güne kadar hoş geldiniz mesajlarını silmeliyim.")
        else:
            update.effective_message.reply_text("Şu anda eski karşılama iletilerini silmiyorum!")
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("Eski karşılama iletilerini silmeye çalışacağım!")
        return (f"<b>{html.escape(chat.title)}:</b>\n"
                f"#CLEAN_WELCOME\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Temiz karşılama geçiş yaptı <code>ON</code>.")
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("Eski karşılama iletilerini silmeyeceğim.")
        return (f"<b>{html.escape(chat.title)}:</b>\n"
                f"#CLEAN_WELCOME\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Temiz karşılama geçiş yaptı <code>OFF</code>.")
    else:
        update.effective_message.reply_text("Anlıyorum 'on/yes' or 'off/no' sadece!")
        return ""

@run_async
@user_admin
def cleanservice(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
            if (var == "no" or var == "off"):
                sql.set_clean_service(chat.id, False)
                update.effective_message.reply_text('Karşılama temiz hizmet : off')
            elif (var == "yes" or var == "on"):
                sql.set_clean_service(chat.id, True)
                update.effective_message.reply_text('Karşılama temiz hizmet : on')
            else:
                update.effective_message.reply_text("Geçersiz seçenek",
                    parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text("Kullanımı on/yes or off/no",
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        curr = sql.clean_service(chat.id)
        if curr:
            update.effective_message.reply_text('Karşılama temiz hizmet : on',
                                                parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text('Karşılama temiz hizmet : off',
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def user_button(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    query = update.callback_query
    match = re.match(r"user_join_\((.+?)\)", query.data)
    message = update.effective_message
    join_user = int(match.group(1))

    if join_user == user.id:
        member_dict = VERIFIED_USER_WAITLIST.pop(user.id)
        member_dict["status"] = True
        VERIFIED_USER_WAITLIST.update({user.id: member_dict})
        query.answer(text="Yeet! Sen bir insansın!")
        bot.restrict_chat_member(chat.id, user.id, can_send_messages=True,
                                 can_send_media_messages=True,
                                 can_send_other_messages=True,
                                 can_add_web_page_previews=True)
        bot.deleteMessage(chat.id, message.message_id)
        if member_dict["should_welc"]:
            sent = send(member_dict["update"], member_dict["res"], member_dict["keyboard"], member_dict["backup_message"])

            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

    else:
        query.answer(text="Bunu yapmanıza izin verilmiyor!")


WELC_HELP_TXT = ("Grubunuzun hoş geldiniz/veda mesajları birden çok şekilde kişiselleştirilebilir. Mesajları istiyorsanız"
                 " ayrı ayrı oluşturulacak, varsayılan hoş geldiniz mesajı gibi * bu * değişkenleri kullanabilirsiniz:\n"
                 " • `{first}`*:* bu kullanıcının *first* name\n"
                 " • `{last}`*:* bu kullanıcının * soyadını gösterir. Varsayılan değeri *first name* kullanıcının hiç numarası yoksa "
                 "Soyadı.\n"
                 " • `{fullname}`*:* bu kullanıcının * tam * adını temsil eder. Kullanıcının numarası yoksa varsayılan olarak * ad * "
                 "Soyadı.\n"
                 " • `{username}`*:* bu kullanıcının * kullanıcı adını * temsil eder. Kullanıcının * sözünü * varsayılan "
                 "kullanıcı adı yoksa ad.\n"
                 " • `{mention}`*:* bu basitçe bir kullanıcıdan * bahseder - onları ilk isimleriyle etiketler.\n"
                 " • `{id}`*:* bu kullanıcının *id*\n"
                 " • `{count}`*:* bu kullanıcının *üye numarası*.\n"
                 " • `{chatname}`*:* bu kullanıcının *mevcut sohbet adı*.\n"
                 "\nHer değişkenin değiştirilmesi gereken `{}` ile çevrelenmesi GEREKİR.\n"
                 "Hoş geldiniz iletileri, işaretlemeyi de destekler, böylece herhangi bir öğeyi yapabilirsiniz bold/italic/code/links. "
                 "Düğmeler de desteklenir, böylece hoş bir girişle karşılamalarınızın harika görünmesini sağlayabilirsiniz. "
                 "buttons.\n"
                 f"Kurallarınıza bağlantı veren bir düğme oluşturmak için bunu kullanın: `[Rules](buttonurl://t.me/{dispatcher.bot.username}?start=group_id)`. "
                 "Group_id" "grubunuzun /id ile elde edebileceğiniz kimliğiyle değiştirir yeterlidir. "
                 "gitmek. Grup kimlikleri genellikle öncesinde “-` işareti; bu gerekli, bu yüzden lütfen yapma "
                 "onu kaldır.\n"
                 "Hatta görüntüleri / gifleri / videoları / sesli mesajları hoş geldiniz mesajı olarak ayarlayabilirsiniz. "
                 "istenen medyayı yanıtlamak ve aramak `/setwelcome`.")

WELC_MUTE_HELP_TXT = (
    "Botun grubunuza katılan yeni kişileri sesini kapatabilir ve böylece spambotların grubunuza su basmasını önleyebilirsiniz.. "
    "Aşağıdaki seçenekler mümkündür:\n"
    "• `/welcomemute yumuşak`*:* yeni üyelerin 24 saat medya göndermesini kısıtlıyor.\n"
    "• `/welcomemute kuvvetli`*:* yeni üyeleri bir düğmeye dokunana kadar susturur ve böylece insan olduklarını doğrular.\n"
    "• `/welcomemute kapalı`*:* turns off welcomemute.\n"
    "*Not:* Güçlü mod, 120 saniye içinde doğrulama yapmazsa bir kullanıcıyı sohbetten başlatır. Yine de her zaman yeniden katılabilirler"
                     )

@run_async
@user_admin
def welcome_help(bot: Bot, update: Update):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


@run_async
@user_admin
def welcome_mute_help(bot: Bot, update: Update):
    update.effective_message.reply_text(WELC_MUTE_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    return "Bu sohbetin hoş geldiniz tercihi olarak ayarlanmış `{}`.\n" \
           "Hoşçakalın tercihi `{}`.".format(welcome_pref, goodbye_pref)


__help__ = """
{}

*Admins only:*
 • `/welcome <on/off>`*:* hoş geldiniz iletilerini etkinleştirme / devre dışı bırakma.
 • `/welcome`*:* geçerli karşılama ayarlarını gösterir.
 • `/welcome noformat`*:* biçimlendirme olmadan geçerli karşılama ayarlarını gösterir - karşılama mesajlarınızı geri dönüştürmek için kullanışlıdır!
 • `/goodbye`*:* ile aynı kullanım ve argümanlar `/welcome`.
 • `/setwelcome <sometext>`*:* özel bir karşılama iletisi ayarlayın. Medyaya yanıt olarak kullanılırsa, bu medyayı kullanır.
 • `/setgoodbye <sometext>`*:*özel bir hoşçakal mesajı ayarlayın. Medyaya yanıt olarak kullanılırsa, bu medyayı kullanır.
 • `/resetwelcome`*:* varsayılan karşılama mesajına sıfırlayın.
 • `/resetgoodbye`*:* varsayılan güle güle mesajına sıfırla.
 • `/cleanwelcome <on/off>`*:* Yeni üyede sohbeti spam etmekten kaçınmak için önceki hoş geldiniz iletisini silmeyi deneyin
 • `/welcomemutehelp`*:* karşılama sessizlikleri hakkında bilgi verir.
 • `/welcomehelp`*:* özel karşılama / veda mesajları için daha fazla biçimlendirme bilgisi görüntüleme.
 • `/cleanservice <on/off`*:* telgraf karşılama / sol servis mesajlarını siler. 
 *Örnek:* kullanıcı sohbete katıldı, kullanıcı sohbeti bıraktı.
""".format(WELC_HELP_TXT)

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member, pass_job_queue=True)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, pass_args=True, filters=Filters.group)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, pass_args=True, filters=Filters.group)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=Filters.group)
WELCOMEMUTE_HANDLER = CommandHandler("welcomemute", welcomemute, pass_args=True, filters=Filters.group)
CLEAN_SERVICE_HANDLER = CommandHandler("cleanservice", cleanservice, pass_args=True, filters=Filters.group)
CLEAN_WELCOME = CommandHandler("cleanwelcome", clean_welcome, pass_args=True, filters=Filters.group)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help)
WELCOME_MUTE_HELP = CommandHandler("welcomemutehelp", welcome_mute_help)
BUTTON_VERIFY_HANDLER = CallbackQueryHandler(user_button, pattern=r"user_join_")

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOME_HELP)
dispatcher.add_handler(WELCOMEMUTE_HANDLER)
dispatcher.add_handler(CLEAN_SERVICE_HANDLER)
dispatcher.add_handler(BUTTON_VERIFY_HANDLER)
dispatcher.add_handler(WELCOME_MUTE_HELP)

__mod_name__ = "Welcomes/Goodbyes"
__command_list__ = []
__handlers__ = [NEW_MEM_HANDLER, LEFT_MEM_HANDLER, WELC_PREF_HANDLER, GOODBYE_PREF_HANDLER,
                SET_WELCOME, SET_GOODBYE, RESET_WELCOME, RESET_GOODBYE, CLEAN_WELCOME,
                WELCOME_HELP, WELCOMEMUTE_HANDLER, CLEAN_SERVICE_HANDLER, BUTTON_VERIFY_HANDLER,
                WELCOME_MUTE_HELP]
