from datetime import datetime
from functools import wraps

from SaitamaRobot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Bot, Update, ParseMode
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, run_async, JobQueue
    from telegram.utils.helpers import escape_markdown

    from SaitamaRobot import dispatcher, LOGGER, GBAN_LOGS
    from SaitamaRobot.modules.helper_funcs.chat_status import user_admin
    from SaitamaRobot.modules.sql import log_channel_sql as sql


    def loggable(func):
        @wraps(func)
        def log_action(bot: Bot, update: Update, job_queue: JobQueue = None, *args, **kwargs):

            if not job_queue:
                result = func(bot, update, *args, **kwargs)
            else:
                result = func(bot, update, job_queue, *args, **kwargs)

            chat = update.effective_chat
            message = update.effective_message

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += f"\n<b>Etkinlik Damgası</b>: <code>{datetime.utcnow().strftime(datetime_fmt)}</code>"

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    send_log(bot, log_chat, chat.id, result)
            elif result == "" or not result:
                pass
            else:
                LOGGER.warning("%s kaydedilebilir olarak ayarlandı, ancak iade bildirimi yoktu.", func)

            return result

        return log_action


    def gloggable(func):
        @wraps(func)
        def glog_action(bot: Bot, update: Update, *args, **kwargs):

            result = func(bot, update, *args, **kwargs)
            chat = update.effective_chat
            message = update.effective_message

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += "\n<b>Etkinlik Damgası</b>: <code>{}</code>".format(datetime.utcnow().strftime(datetime_fmt))

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = str(GBAN_LOGS)
                if log_chat:
                    send_log(bot, log_chat, chat.id, result)
            elif result == "" or not result:
                pass
            else:
                LOGGER.warning("%s gbanlogs için kaydedilebilir olarak ayarlandı, ancak iade bildirimi yoktu.", func)

            return result

        return glog_action


    def send_log(bot: Bot, log_chat_id: str, orig_chat_id: str, result: str):

        try:
            bot.send_message(log_chat_id, result, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except BadRequest as excp:
            if excp.message == "Sohbet Bulunamadı":
                bot.send_message(orig_chat_id, "Bu günlük kanalı silindi - ayar kaldırılıyor.")
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("Ayrıştırılamadı")

                bot.send_message(log_chat_id, result + "\n\nBeklenmedik bir hata nedeniyle biçimlendirme devre dışı bırakıldı.")


    @run_async
    @user_admin
    def logging(bot: Bot, update: Update):

        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            message.reply_text(f"Bu grupta günlüklerinin tümü var:"
                               f" {escape_markdown(log_channel_info.title)} (`{log_channel}`)",
                               parse_mode=ParseMode.MARKDOWN)

        else:
            message.reply_text("Bu grup için günlük kanalı ayarlanmadı!")


    @run_async
    @user_admin
    def setlog(bot: Bot, update: Update):

        message = update.effective_message
        chat = update.effective_chat
        if chat.type == chat.CHANNEL:
            message.reply_text("Şimdi /setlog dosyasını bu kanalı bağlamak istediğiniz gruba yönlendirin!")

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Silinecek mesaj bulunamadı":
                    pass
                else:
                    LOGGER.exception("Günlük kanalındaki mesaj silinirken hata oluştu. Yine de çalışmalı.")

            try:
                bot.send_message(message.forward_from_chat.id,
                                 f"Bu kanal, için günlük kanalı olarak ayarlandı {chat.title or chat.first_name}.")
            except Unauthorized as excp:
                if excp.message == "Yasak: bot kanal sohbetinin bir üyesi değil":
                    bot.send_message(chat.id, "Günlük kanalı başarıyla ayarlandı!")
                else:
                    LOGGER.exception("Günlük kanalının ayarlanmasında HATA.")

            bot.send_message(chat.id, "Günlük kanalı başarıyla ayarlandı!")

        else:
            message.reply_text("Bir günlük kanalı ayarlama adımları:\n"
                               " - botu istediğiniz kanala ekleyin\n"
                               " - kanala gönder /setlog ayarla\n"
                               " - /setlog dosyasını gruba iletme\n")


    @run_async
    @user_admin
    def unsetlog(bot: Bot, update: Update):

        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(log_channel, f"Kanalın bağlantısı kaldırıldı {chat.title}")
            message.reply_text("Günlük kanalı ayarlanmadı.")

        else:
            message.reply_text("Henüz bir günlük kanalı ayarlanmadı!")


    def __stats__():
        return f"{sql.num_logchannels()} günlük kanalları seti."


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return f"Bu grupta günlüklerinin tümü var: {escape_markdown(log_channel_info.title)} (`{log_channel}`)"
        return "Bu grup için günlük kanalı ayarlanmadı!"


    __help__ = """
*Admins only:*
• `/logchannel`*:* günlük kanalı bilgisi al
• `/setlog`*:* günlük kanalını ayarlayın.
• `/unsetlog`*:* günlük kanalını çıkartın..

Günlük kanalının ayarlanması:
• botu istenen kanala ekleme (yönetici olarak!)
•kanalda `/setlog` gönderme
• gruba ilet `/setlog`bununla
"""

    __mod_name__ = "Log Channels"

    LOG_HANDLER = CommandHandler("logchannel", logging)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func


    def gloggable(func):
        return func
