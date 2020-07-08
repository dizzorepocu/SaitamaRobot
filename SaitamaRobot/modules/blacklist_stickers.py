import html
from typing import Optional, List

import telegram.ext as tg
from telegram import Message, Chat, Update, Bot, ParseMode, User, MessageEntity
from telegram import TelegramError
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html, mention_markdown

import SaitamaRobot.modules.sql.blsticker_sql as sql
from SaitamaRobot import dispatcher, SUDO_USERS, LOGGER, OWNER_ID
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import can_delete, is_user_admin, user_not_admin, user_admin, \
		bot_can_delete, is_bot_admin
from SaitamaRobot.modules.helper_funcs.filters import CustomFilters
from SaitamaRobot.modules.helper_funcs.misc import split_message
from SaitamaRobot.modules.warns import warn
from SaitamaRobot.modules.log_channel import loggable
from SaitamaRobot.modules.sql import users_sql
from SaitamaRobot.modules.connection import connected

from SaitamaRobot.modules.helper_funcs.alternate import send_message


@run_async
def blackliststicker(bot: Bot, update: Update, args: List[str]):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	
		
	conn = connected(bot, update, chat, user.id, need_admin=False)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if chat.type == "private":
			return
		else:
			chat_id = update.effective_chat.id
			chat_name = chat.title
		
	sticker_list = "<b>Şu anda kara listede bulunan etiketleri listele {}:</b>\n".format(chat_name)

	all_stickerlist = sql.get_chat_stickers(chat_id)

	if len(args) > 0 and args[0].lower() == 'copy':
		for trigger in all_stickerlist:
			sticker_list += "<code>{}</code>\n".format(html.escape(trigger))
	elif len(args) == 0:
		for trigger in all_stickerlist:
			sticker_list += " - <code>{}</code>\n".format(html.escape(trigger))

	split_text = split_message(sticker_list)
	for text in split_text:
		if sticker_list == "<b>Şu anda kara listede bulunan etiketleri listele {}:</b>\n".format(chat_name).format(chat_name):
			send_message(update.effective_message, "İçinde kara liste etiketi yok <b>{}</b>!".format(chat_name), parse_mode=ParseMode.HTML)
			return
	send_message(update.effective_message, text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blackliststicker(bot: Bot, update: Update):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	words = msg.text.split(None, 1)

	conn = connected(bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			return
		else:
			chat_name = chat.title

	if len(words) > 1:
		text = words[1].replace('https://t.me/addstickers/', '')
		to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
		added = 0
		for trigger in to_blacklist:
			try:
				get = bot.getStickerSet(trigger)
				sql.add_to_stickers(chat_id, trigger.lower())
				added += 1
			except BadRequest:
				send_message(update.effective_message, "Sticker `{}` bulunamıyor!".format(trigger), parse_mode="markdown")

		if added == 0:
			return

		if len(to_blacklist) == 1:
			send_message(update.effective_message, "Sticker <code>{}</code> içindeki kara liste etiketlerine eklendi <b>{}</b>!".format(html.escape(to_blacklist[0]), chat_name),
				parse_mode=ParseMode.HTML)
		else:
			send_message(update.effective_message, "<code>{}</code> içindeki kara listeye eklenen etiketler <b>{}</b>!".format(added, chat_name), parse_mode=ParseMode.HTML)
	elif msg.reply_to_message:
		added = 0
		trigger = msg.reply_to_message.sticker.set_name
		if trigger == None:
			send_message(update.effective_message, "Sticker geçersizdir!")
			return
		try:
			get = bot.getStickerSet(trigger)
			sql.add_to_stickers(chat_id, trigger.lower())
			added += 1
		except BadRequest:
			send_message(update.effective_message, "Sticker `{}` bulunamıyor!".format(trigger), parse_mode="markdown")

		if added == 0:
			return

		send_message(update.effective_message, "Sticker <code>{}</code> içindeki kara liste etiketlerine eklendi <b>{}</b>!".format(trigger, chat_name), parse_mode=ParseMode.HTML)
	else:
		send_message(update.effective_message, "Kara listeye hangi çıkartmaları eklemek istediğini söyle.")

@run_async
@user_admin
def unblackliststicker(bot: Bot, update: Update):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	words = msg.text.split(None, 1)

	conn = connected(bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			return
		else:
			chat_name = chat.title


	if len(words) > 1:
		text = words[1].replace('https://t.me/addstickers/', '')
		to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
		successful = 0
		for trigger in to_unblacklist:
			success = sql.rm_from_stickers(chat_id, trigger.lower())
			if success:
				successful += 1

		if len(to_unblacklist) == 1:
			if successful:
				send_message(update.effective_message, "Sticker <code>{}</code> içindeki kara listeden silindi <b>{}</b>!".format(html.escape(to_unblacklist[0]), chat_name),
							   parse_mode=ParseMode.HTML)
			else:
				send_message(update.effective_message, "Bu çıkartma kara listede değil...!")

		elif successful == len(to_unblacklist):
			send_message(update.effective_message, "Sticker <code>{}</code> içindeki kara listeden silindi <b>{}</b>!".format(
					successful, chat_name), parse_mode=ParseMode.HTML)

		elif not successful:
			send_message(update.effective_message, "Bu çıkartmaların hiçbiri mevcut değil, bu yüzden çıkarılamazlar.".format(
					successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

		else:
			send_message(update.effective_message, "Sticker <code>{}</code> kara listeden silindi. {} Var olmadı, bu yüzden silinmedi.".format(successful, len(to_unblacklist) - successful),
				parse_mode=ParseMode.HTML)
	elif msg.reply_to_message:
		trigger = msg.reply_to_message.sticker.set_name
		if trigger == None:
			send_message(update.effective_message, "Sticker geçersizdir!")
			return
		success = sql.rm_from_stickers(chat_id, trigger.lower())

		if success:
			send_message(update.effective_message, "Sticker <code>{}</code> içindeki kara listeden silindi <b>{}</b>!".format(trigger, chat_name),
							   parse_mode=ParseMode.HTML)
		else:
			send_message(update.effective_message, "{} kara listeye alınmış çıkartmalarda bulunamadı...!".format(trigger))
	else:
		send_message(update.effective_message, "Kara listeye hangi çıkartmaları eklemek istediğini söyle.")

@run_async
@loggable
@user_admin
def blacklist_mode(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]
	

	conn = connected(bot, update, chat, user.id, need_admin=True)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, "Bu komutu PM değil gruplar halinde yapabilirsiniz")
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	if args:
		if args[0].lower() == 'off' or args[0].lower() == 'nothing' or args[0].lower() == 'no':
			settypeblacklist = 'turn off'
			sql.set_blacklist_strength(chat_id, 0, "0")
		elif args[0].lower() == 'del' or args[0].lower() == 'delete':
			settypeblacklist = 'left, the message will be deleted'
			sql.set_blacklist_strength(chat_id, 1, "0")
		elif args[0].lower() == 'warn':
			settypeblacklist = 'warned'
			sql.set_blacklist_strength(chat_id, 2, "0")
		elif args[0].lower() == 'mute':
			settypeblacklist = 'muted'
			sql.set_blacklist_strength(chat_id, 3, "0")
		elif args[0].lower() == 'kick':
			settypeblacklist = 'kicked'
			sql.set_blacklist_strength(chat_id, 4, "0")
		elif args[0].lower() == 'ban':
			settypeblacklist = 'banned'
			sql.set_blacklist_strength(chat_id, 5, "0")
		elif args[0].lower() == 'tban':
			if len(args) == 1:
				teks = """Kara listeye geçici bir değer ayarlamaya çalıştığınız anlaşılıyor, ama zamanı belirlemedi; kullan `/blstickermode tban <timevalue>`.
                                          Examples of time values: 4m = 4 minute, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
				send_message(update.effective_message, teks, parse_mode="markdown")
				return
			settypeblacklist = 'temporary banned for {}'.format(args[1])
			sql.set_blacklist_strength(chat_id, 6, str(args[1]))
		elif args[0].lower() == 'tmute':
			if len(args) == 1:
				teks = """Kara listeye geçici bir değer ayarlamaya çalıştığınız anlaşılıyor, ama zamanı belirlemedi; kullan `/blstickermode tmute <timevalue>`.
                                          Examples of time values: 4m = 4 minute, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
				send_message(update.effective_message, teks, parse_mode="markdown")
				return
			settypeblacklist = tl(update.effective_message, 'geçici olarak kapatıldı {}').format(args[1])
			sql.set_blacklist_strength(chat_id, 7, str(args[1]))
		else:
			send_message(update.effective_message, "Sadece anlıyorum off/del/warn/ban/kick/mute/tban/tmute!")
			return
		if conn:
			text = "Kara liste çıkartma modu değişti, kullanıcılar olacak `{}` at *{}*!".format(settypeblacklist, chat_name)
		else:
			text = "Kara liste çıkartma modu değişti, kullanıcılar olacak `{}`!".format(settypeblacklist)
		send_message(update.effective_message, text, parse_mode="markdown")
		return "<b>{}:</b>\n" \
				"<b>Admin:</b> {}\n" \
				"Etiket kara listesi modunu değiştirdi. kullanıcılar olacak {}.".format(html.escape(chat.title),
																			mention_html(user.id, user.first_name), settypeblacklist)
	else:
		getmode, getvalue = sql.get_blacklist_setting(chat.id)
		if getmode == 0:
			settypeblacklist = "not active"
		elif getmode == 1:
			settypeblacklist = "hapus"
		elif getmode == 2:
			settypeblacklist = "warn"
		elif getmode == 3:
			settypeblacklist = "mute"
		elif getmode == 4:
			settypeblacklist = "kick"
		elif getmode == 5:
			settypeblacklist = "ban"
		elif getmode == 6:
			settypeblacklist = "geçici olarak yasaklandı {}".format(getvalue)
		elif getmode == 7:
			settypeblacklist = "geçici olarak susturuldu {}".format(getvalue)
		if conn:
			text = "Kara liste çıkartma modu şu anda olarak ayarlanmış *{}* in *{}*.".format(settypeblacklist, chat_name)
		else:
			text = "Kara liste çıkartma modu şu anda olarak ayarlanmış *{}*.".format(settypeblacklist)
		send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
	return ""

@run_async
@user_not_admin
def del_blackliststicker(bot: Bot, update: Update):
	chat = update.effective_chat  # type: Optional[Chat]
	message = update.effective_message  # type: Optional[Message]
	user = update.effective_user
	to_match = message.sticker
	if not to_match:
		return

	getmode, value = sql.get_blacklist_setting(chat.id)

	chat_filters = sql.get_chat_stickers(chat.id)
	for trigger in chat_filters:
		if to_match.set_name.lower() == trigger.lower():
			try:
				if getmode == 0:
					return
				elif getmode == 1:
					message.delete()
				elif getmode == 2:
					message.delete()
					warn(update.effective_user, chat, "Çıkartma kullanma '{}' hangi kara liste çıkartmaları".format(trigger), message, update.effective_user, conn=False)
					return
				elif getmode == 3:
					message.delete()
					bot.restrict_chat_member(chat.id, update.effective_user.id, can_send_messages=False)
					bot.sendMessage(chat.id, "{} sesi kapalı çünkü kullanıyor '{}' hangi kara liste çıkartmaları".format(mention_markdown(user.id, user.first_name), trigger), parse_mode="markdown")
					return
				elif getmode == 4:
					message.delete()
					res = chat.unban_member(update.effective_user.id)
					if res:
						bot.sendMessage(chat.id, "{} çünkü tekmeledi '{}' hangi kara liste çıkartmaları".format(mention_markdown(user.id, user.first_name), trigger), parse_mode="markdown")
					return
				elif getmode == 5:
					message.delete()
					chat.kick_member(user.id)
					bot.sendMessage(chat.id, "{} kullanıldığından yasaklandı '{}' hangi kara liste çıkartmaları".format(mention_markdown(user.id, user.first_name), trigger), parse_mode="markdown")
					return
				elif getmode == 6:
					message.delete()
					bantime = extract_time(message, value)
					chat.kick_member(user.id, until_date=bantime)
					bot.sendMessage(chat.id, "{} için yasaklandı {} çünkü kullanmak '{}' hangi kara liste çıkartmaları".format(mention_markdown(user.id, user.first_name), value, trigger), parse_mode="markdown")
					return
				elif getmode == 7:
					message.delete()
					mutetime = extract_time(message, value)
					bot.restrict_chat_member(chat.id, user.id, until_date=mutetime, can_send_messages=False)
					bot.sendMessage(chat.id, "{} sesi kapatıldı {} çünkü kullanmak '{}' hangi kara liste çıkartmaları".format(mention_markdown(user.id, user.first_name), value, trigger), parse_mode="markdown")
					return
			except BadRequest as excp:
				if excp.message == "Silinecek mesaj bulunamadı":
					pass
				else:
					LOGGER.exception("Kara liste mesajı silinirken hata oluştu.")
				break


def __import_data__(chat_id, data):
	# set chat blacklist
	blacklist = data.get('sticker_blacklist', {})
	for trigger in blacklist:
		sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
	sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
	blacklisted = sql.num_stickers_chat_filters(chat_id)
	return "Var `{} `kara listeye alınan çıkartmalar.".format(blacklisted)

def __stats__():
	return "{} kara liste çıkartmalar, karşısında {} sohbetler.".format(sql.num_stickers_filters(), sql.num_stickers_filter_chats())

__help__ = """
Kara liste etiketi, belirli etiketleri durdurmak için kullanılır. Bir çıkartma gönderildiğinde, mesaj hemen silinecek.
*NOTE:* Kara liste etiketleri grup yöneticisini etkilemez.
 • `/blsticker`*:* Geçerli kara listeye alınmış etikete bakın.
*Only admin:*
 • `/addblsticker <sticker link>`*:* Etiket tetikleyicisini kara listeye ekleyin. Cevap etiketi ile eklenebilir.
 • `/unblsticker <sticker link>`*:* Tetikleyicileri kara listeden kaldır. Aynı yeni satır mantığı burada geçerlidir, böylece aynı anda birden fazla tetikleyiciyi silebilirsiniz.
 • `/rmblsticker <sticker link>`*:* Yukarıdaki ile aynı.
 • `/blstickermode <ban/tban/mute/tmute>`*:* kullanıcılar kara listeye alınmış etiketler kullanıyorsa ne yapılacağı konusunda varsayılan bir işlem ayarlar. (`tmute şu anda kırık görünüyor`)
Note:
 • `<sticker link>` can be `https://t.me/addstickers/<sticker>` or just `<sticker>` or reply to the sticker message.
"""

__mod_name__ = "Sticker Blacklist"

BLACKLIST_STICKER_HANDLER = DisableAbleCommandHandler("blsticker", blackliststicker, pass_args=True, admin_ok=True)
ADDBLACKLIST_STICKER_HANDLER = DisableAbleCommandHandler("addblsticker", add_blackliststicker)
UNBLACKLIST_STICKER_HANDLER = CommandHandler(["unblsticker", "rmblsticker"], unblackliststicker)
BLACKLISTMODE_HANDLER = CommandHandler("blstickermode", blacklist_mode, pass_args=True)
BLACKLIST_STICKER_DEL_HANDLER = MessageHandler(Filters.sticker & Filters.group, del_blackliststicker)

dispatcher.add_handler(BLACKLIST_STICKER_HANDLER)
dispatcher.add_handler(ADDBLACKLIST_STICKER_HANDLER)
dispatcher.add_handler(UNBLACKLIST_STICKER_HANDLER)
dispatcher.add_handler(BLACKLISTMODE_HANDLER)
dispatcher.add_handler(BLACKLIST_STICKER_DEL_HANDLER)
