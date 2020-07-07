import html
from typing import Optional, List
import re
from telegram import Message, Chat, Update, Bot, User, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, RegexHandler, run_async, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html

from SaitamaRobot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from SaitamaRobot.modules.log_channel import loggable
from SaitamaRobot.modules.sql import reporting_sql as sql
from SaitamaRobot import dispatcher, LOGGER, SUDO_USERS, TIGER_USERS, WHITELIST_USERS

REPORT_GROUP = 12
REPORT_IMMUNE_USERS = SUDO_USERS + TIGER_USERS + WHITELIST_USERS

@run_async
@user_admin
def report_setting(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    msg = update.effective_message

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text("Raporlama etkinleştirildi! Birisi bir şey raporladığında bildirim alırsınız.")

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Raporlama kapatıldı! Rapor almazsın.")
        else:
            msg.reply_text(f"Your current report preference is: `{sql.user_should_report(chat.id)}`",
                           parse_mode=ParseMode.MARKDOWN)

    else:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text("Raporlama etkinleştirildi! Raporları açmış olan yöneticilere, /report "
                               "veya @admin denir.")

            elif args[0] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text("Raporlama kapatıldı! Hiçbir yöneticiye bildirilmez /report yada @admin.")
        else:
            msg.reply_text(f"Bu grubun geçerli ayarı: `{sql.chat_should_report(chat.id)}`",
                           parse_mode=ParseMode.MARKDOWN)


@run_async
@user_not_admin
@loggable
def report(bot: Bot, update: Update) -> str:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()
        message = update.effective_message

        if user.id == reported_user.id:
            message.reply_text("Ah evet, emin misin ... çok mu?")
            return ""

        if user.id == bot.id:
            message.reply_text("İyi deneme.")
            return ""

        if reported_user.id in REPORT_IMMUNE_USERS:
            message.reply_text("Ah? Beyaz listeye eklenmiş kullanıcıları mı rapor ediyorsunuz?")
            return ""

        if chat.username and chat.type == Chat.SUPERGROUP:
            

            reported = f"{mention_html(user.id, user.first_name)} reported {mention_html(reported_user.id, reported_user.first_name)} to the admins!"

            msg = (f"<b>⚠️ Report: </b>{html.escape(chat.title)}\n"
                   f"<b> • Reportlayan:</b> {mention_html(user.id, user.first_name)}(<code>{user.id}</code>)\n"
                   f"<b> • Reporlanan kullanıcı:</b> {mention_html(reported_user.id, reported_user.first_name)} (<code>{reported_user.id}</code>)\n")
            link = f'<b> • Reporlanan Mesaj:</b> <a href="https://t.me/{chat.username}/{message.reply_to_message.message_id}">click here</a>'
            should_forward = False
            keyboard = [
                [InlineKeyboardButton(u"➡ Message", url=f"https://t.me/{chat.username}/{message.reply_to_message.message_id}")],
                [InlineKeyboardButton(u"⚠ Kick",
                                      callback_data=f"report_{chat.id}=kick={reported_user.id}={reported_user.first_name}"),
                 InlineKeyboardButton(u"⛔️ Ban",
                                      callback_data=f"report_{chat.id}=banned={reported_user.id}={reported_user.first_name}")],
                [InlineKeyboardButton(u"❎ Delete Message",
                                      callback_data=f"report_{chat.id}=delete={reported_user.id}={message.reply_to_message.message_id}")]
                        ]
            reply_markup = InlineKeyboardMarkup(keyboard)            
        else:
            reported = f"{mention_html(user.id, user.first_name)} raporlandı" \
                       f"{mention_html(reported_user.id, reported_user.first_name)} to the admins!"

            msg = f'{mention_html(user.id, user.first_name)} içindeki yöneticileri arıyor "{html.escape(chat_name)}"!'
            link = ""
            should_forward = True

        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    if not chat.type == Chat.SUPERGROUP:
                        bot.send_message(admin.user.id, msg + link, parse_mode=ParseMode.HTML)

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)
                    if not chat.username:
                        bot.send_message(admin.user.id, msg + link, parse_mode=ParseMode.HTML)

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                    if chat.username and chat.type == Chat.SUPERGROUP:
                        bot.send_message(admin.user.id, msg + link, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("Kullanıcıyı bildirirken istisna")

        message.reply_to_message.reply_text(f"{mention_html(user.id, user.first_name)} mesajı yöneticilere bildirdi.",parse_mode=ParseMode.HTML)
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(bot, update, chat, chatP, user):
    return f"Bu sohbet, kullanıcı raporlarını yöneticilere gönderecek şekilde ayarlandı, ,üzerinden /report ve @admin: `{sql.chat_should_report(chat_id)}`"

def __user_settings__(bot, update, user):
    if sql.user_should_report(user.id) == True:
        text = "Yönetici olduğunuz sohbetlerden rapor alacaksınız."
        keyboard = [[InlineKeyboardButton(text="Raporlamayı devre dışı bırak", callback_data="panel_reporting_U_disable")]]
    else:
        text = "Yönetici olduğunuz sohbetlerden * rapor * almayacaksınız."
        keyboard = [[InlineKeyboardButton(text="Raporlamayı etkinleştir", callback_data="panel_reporting_U_enable")]]

    return text, keyboard

    
def buttons(bot: Bot, update):
    query = update.callback_query
    splitter = query.data.replace("report_", "").split("=")
    if splitter[1] == "kick":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            bot.unbanChatMember(splitter[0], splitter[2])
            query.answer("✅ Başarıyla kicklendi")
            return ""
        except Exception as err:
            query.answer("🛑 kicklenmedi")
            bot.sendMessage(text=f"Hata: {err}",chat_id=query.message.chat_id,parse_mode=ParseMode.HTML)
    elif splitter[1] == "banned":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            query.answer("✅  Başarıyla Yasaklandı")
            return ""
        except Exception as err:
            bot.sendMessage(text=f"Error: {err}",chat_id=query.message.chat_id,parse_mode=ParseMode.HTML)
            query.answer("🛑 Yasaklanmadı")
    elif splitter[1] == "delete":
        try:
            bot.deleteMessage(splitter[0], splitter[3])
            query.answer("✅ Mesaj silindi")
            return ""
        except Exception as err:
            bot.sendMessage(text=f"Error: {err}",chat_id=query.message.chat_id,parse_mode=ParseMode.HTML)
            query.answer("🛑 Mesaj silinemedi!")


__help__ = """
 • `/report <reason>`*:* yöneticilere bildirmek için bir iletiyi yanıtlayın.
 • `@admin`*:* yöneticilere bildirmek için iletiyi yanıtlayın.
*NOTE:* Yöneticiler tarafından kullanılırsa bunların hiçbiri tetiklenmez.

*Admins only:*
 • `/reports <on/off>`*:* rapor ayarını değiştirme veya geçerli durumu görüntüleme.
   • Öğleden sonra yapılırsa, durumunuzu değiştirir.
   • Gruptaysa, bu grupların durumunu değiştirir.
"""

SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report)

report_button_user_handler = CallbackQueryHandler(buttons, pattern=r"report_")
dispatcher.add_handler(report_button_user_handler)

dispatcher.add_handler(SETTING_HANDLER)
dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)

__mod_name__ = "Reporting"
__handlers__ = [(REPORT_HANDLER, REPORT_GROUP), (ADMIN_REPORT_HANDLER, REPORT_GROUP), (SETTING_HANDLER)]
