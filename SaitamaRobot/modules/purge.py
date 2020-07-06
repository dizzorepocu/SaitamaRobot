import html
from typing import List

from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import Filters, run_async
from telegram.utils.helpers import mention_html

from SaitamaRobot import dispatcher, LOGGER
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin, can_delete
from SaitamaRobot.modules.log_channel import loggable


@run_async
@user_admin
@loggable
def purge(bot: Bot, update: Update, args: List[str]) -> str:
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if can_delete(chat, bot.id):

        if msg.reply_to_message:

            message_id = msg.reply_to_message.message_id
            start_message_id = message_id - 1
            delete_to = msg.message_id - 1

            if args and args[0].isdigit():
                new_del = message_id + int(args[0])
                # No point deleting messages which haven't been written yet.
                if new_del < delete_to:
                    delete_to = new_del
        else:

            if args and args[0].isdigit():
                messages_to_delete = int(args[0])

            if messages_to_delete < 1:
                msg.reply_text("1 iletiden daha azını temizleyemiyorum.")
                return ""

            delete_to = msg.message_id - 1
            start_message_id = delete_to - messages_to_delete

        for m_id in range(delete_to, start_message_id, -1):  # Reverse iteration over message ids

            try:
                bot.deleteMessage(chat.id, m_id)
            except BadRequest as err:
                if err.message == "Mesaj silinemez":
                    bot.send_message(chat.id, "Tüm mesajlar silinemiyor. Mesajlar çok eski olabilir, "
                                              "silme haklarına sahip değilsiniz veya bu bir üst grup olmayabilir.")

                elif err.message != "Silinecek mesaj bulunamadı":
                    LOGGER.exception("Sohbet mesajlarını temizlerken hata oluştu.")

        try:
            msg.delete()
        except BadRequest as err:
            if err.message == "Mesaj silinemez":
                bot.send_message(chat.id, "Tüm mesajlar silinemiyor. Mesajlar çok eski olabilir, "
                                          "silme haklarına sahip değilsiniz veya bu bir super grup olmayabilir.")

            elif err.message != "Silinecek mesaj bulunamadı":
                LOGGER.exception("Sohbet mesajlarını temizlerken hata oluştu.")

        bot.send_message(chat.id, f"Temizle <code>{delete_to - start_message_id}</code> mesajları.",
                         parse_mode=ParseMode.HTML)
        return (f"<b>{html.escape(chat.title)}:</b>\n"
                f"#PURGE\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Temizlendi <code>{delete_to - start_message_id}</code> mesajlar.")

    return ""


@run_async
@user_admin
@loggable
def del_message(bot: Bot, update: Update) -> str:
    if update.effective_message.reply_to_message:
        user = update.effective_user
        chat = update.effective_chat
        if can_delete(chat, bot.id):
            update.effective_message.reply_to_message.delete()
            update.effective_message.delete()
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#DEL\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Mesaj silindi.")
    else:
        update.effective_message.reply_text("Whadya silmek istiyor musunuz?")

    return ""


__help__ = """
*Admins only:*
 • `/del`*:* cevapladığınız mesajı siler
 • `/purge`*:* bu mesajla cevaplanan mesaj arasındaki tüm mesajları siler.
 • `/purge <integer X>`*:* cevaplanan mesajı ve bir mesaja cevap verildiğinde onu takip eden X mesajları siler.
 • `/purge <integer X>`*:* aşağıdan başlayarak mesaj sayısını siler. (Manuel olarak silinen iletileri de sayar)
"""

DELETE_HANDLER = DisableAbleCommandHandler("del", del_message, filters=Filters.group)
PURGE_HANDLER = DisableAbleCommandHandler("purge", purge, filters=Filters.group, pass_args=True)

dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PURGE_HANDLER)

__mod_name__ = "Purges"
__command_list__ = ["del", "purge"]
__handlers__ = [DELETE_HANDLER, PURGE_HANDLER]
