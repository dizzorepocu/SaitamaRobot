import html
from io import BytesIO
from typing import Optional, List
import random
import uuid
import re
import json
import time
import csv
import os
from time import sleep

from future.utils import string_types
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram import ParseMode, Update, Bot, Chat, User, MessageEntity, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from SaitamaRobot import dispatcher, OWNER_ID, SUDO_USERS, WHITELIST_USERS, TIGER_USERS, GBAN_LOGS, LOGGER
from SaitamaRobot.modules.helper_funcs.handlers import CMD_STARTERS
from SaitamaRobot.modules.helper_funcs.misc import is_module_loaded, send_to_list
from SaitamaRobot.modules.helper_funcs.chat_status import is_user_admin
from SaitamaRobot.modules.helper_funcs.extraction import extract_user, extract_unt_fedban, extract_user_fban
from SaitamaRobot.modules.helper_funcs.string_handling import markdown_parser
from SaitamaRobot.modules.disable import DisableAbleCommandHandler

import SaitamaRobot.modules.sql.feds_sql as sql

from SaitamaRobot.modules.connection import connected
from SaitamaRobot.modules.helper_funcs.alternate import send_message
# Hello bot owner, I spended for feds many hours of my life, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
# Total spended for making this features is 68+ hours
# LOGGER.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram.")

FBAN_ERRORS = {
	"Kullanıcı sohbetin yöneticisidir",
	"Sohbet bulunamadı",
	"Sohbet üyelerini kısıtlamak /unrestric için yeterli hak yok",
	"Kullanıcı_katılımcı_değil",
	"Eş_kimliği_geçersiz",
	"Grup sohbeti devre dışı bırakıldı",
	"Temel bir gruptan tekme atmak için kullanıcının davetli olması gerekir",
	"sohbet_yöneticisi_gerekli",
	"Yalnızca temel bir grubun yaratıcısı grup yöneticilerini tekmeleyebilir",
	"Kanal_Gizli",
	"Sohbette değil",
	"Mesaj gönderme hakkınız yok"
}

UNFBAN_ERRORS = {
	"Kullanıcı sohbetin yöneticisidir",
	"Sohbet bulunamadı",
	"Sohbet üyelerini kısıtlamak /unrestrict için yeterli hak yok",
	"Kullanıcı_değil_katılımcı",
	"Yöntem yalnızca üst grup ve kanal sohbetleri için kullanılabilir",
	"Sohbette değil",
	"Özel_kanal",
	"Sohbet_yöneticisi_gerekli",
	"Mesaj gönderme hakkınız yok"
}

@run_async
def new_fed(bot: Bot, update: Update):
	chat = update.effective_chat  
	user = update.effective_user  
	message = update.effective_message
	if chat.type != "private":
		update.effective_message.reply_text("Federasyonlar yalnızca bana özel mesaj göndererek oluşturulabilir.")
		return
	if len(message.text) == 1:
		send_message(update.effective_message, "Lütfen federasyonun adını yazın!")
		return
	fednam = message.text.split(None, 1)[1]
	if not fednam == '':
		fed_id = str(uuid.uuid4())
		fed_name = fednam
		LOGGER.info(fed_id)

		# Currently only for creator
		#if fednam == 'Team Nusantara Disciplinary Circle':
			 #fed_id = "TeamNusantaraDevs"

		x = sql.new_fed(user.id, fed_name, fed_id)
		if not x:
			update.effective_message.reply_text("Federasyon olamaz! Sorun devam ederse lütfen @AphroditeSupport ile iletişime geçin.")
			return

		update.effective_message.reply_text("*Yeni bir federasyon oluşturmayı başardınız!*"\
											"\nİsmi: `{}`"\
											"\nID: `{}`"
											"\n\nFederasyona katılmak için aşağıdaki komutu kullanın:"
											"\n`/joinfed {}`".format(fed_name, fed_id, fed_id), parse_mode=ParseMode.MARKDOWN)
		try:
			bot.send_message(GBAN_LOGS,
				"Yeni Federasyon: <b>{}</b>\nID: <pre>{}</pre>".format(fed_name, fed_id), parse_mode=ParseMode.HTML)
		except:
			LOGGER.warning("Adresine mesaj gönderilemiyor GBAN_LOGS")
	else:
		update.effective_message.reply_text("Lütfen federasyonun adını yazın")

@run_async
def del_fed(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  
	if chat.type != "private":
		update.effective_message.reply_text("Federasyonlar yalnızca bana özel mesaj göndererek silinebilir.")
		return
	if args:
		is_fed_id = args[0]
		getinfo = sql.get_fed_info(is_fed_id)
		if getinfo == False:
			update.effective_message.reply_text("Bu federasyon mevcut değil.")
			return
		if int(getinfo['owner']) == int(user.id) or int(user.id) == OWNER_ID:
			fed_id = is_fed_id
		else:
			update.effective_message.reply_text("Bunu sadece federasyon sahipleri yapabilir!!")
			return
	else:
		update.effective_message.reply_text("Ne silmeliyim?")
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		update.effective_message.reply_text("Bunu yalnızca federasyon sahipleri yapabilir!")
		return

	update.effective_message.reply_text("Federasyonunuzu silmek istediğinizden emin misiniz? Bu geri alınamaz, tüm yasak listenizi kaybedersiniz, ve '{}' kalıcı olarak kaybolacak.".format(getinfo['fname']),
			reply_markup=InlineKeyboardMarkup(
						[[InlineKeyboardButton(text="⚠️Federasyonu Sil ⚠️", callback_data="rmfed_{}".format(fed_id))],
						[InlineKeyboardButton(text="İptal Et", callback_data="rmfed_cancel")]]))

@run_async
def fed_chat(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  
	fed_id = sql.get_fed_id(chat.id)

	user_id = update.effective_message.from_user.id
	if not is_user_admin(update.effective_chat, user_id):
		update.effective_message.reply_text("Bu komutu yürütmek için yönetici olmalısınız")
		return

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonda değil!")
		return

	user = update.effective_user  
	chat = update.effective_chat  
	info = sql.get_fed_info(fed_id)

	text = "Bu grup aşağıdaki federasyonun bir parçası:"
	text += "\n{} (ID: <code>{}</code>)".format(info['fname'], fed_id)

	update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

@run_async
def join_fed(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	message = update.effective_message
	administrators = chat.get_administrators()
	fed_id = sql.get_fed_id(chat.id)

	if user.id in SUDO_USERS:
		pass
	else:
		for admin in administrators:
			status = admin.status
			if status == "creator":
				if str(admin.user.id) == str(user.id):
					pass
				else:
					update.effective_message.reply_text("Bu grubu yalnızca grup oluşturucuları kullanabilir!")
					return
	if fed_id:
		message.reply_text("Bir sohbetten iki federasyona katılamazsınız ")
		return

	if len(args) >= 1:
		getfed = sql.search_fed_by_id(args[0])
		if getfed == False:
			message.reply_text("Lütfen geçerli bir federasyon kimliği girin")
			return

		x = sql.chat_join_fed(args[0], chat.title, chat.id)
		if not x:
			message.reply_text("Federasyona katılamadı! Bu sorun devam ederse lütfen @AphroditSupport ile iletişime geçin!")
			return

		get_fedlog = sql.get_fed_log(args[0])
		if get_fedlog:
			if eval(get_fedlog):
				bot.send_message(get_fedlog, "Sohbet * {} * federasyona katıldı *{}*".format(chat.title, getfed['fname']), parse_mode="markdown")

		message.reply_text("Bu grup federasyona katıldı: {}!".format(getfed['fname']))

@run_async
def leave_fed(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut PM'ye değil, gruba özgüdür!")
		return

	fed_id = sql.get_fed_id(chat.id)
	fed_info = sql.get_fed_info(fed_id)

	# administrators = chat.get_administrators().status
	getuser = bot.get_chat_member(chat.id, user.id).status
	if getuser in 'creator' or user.id in SUDO_USERS:
		if sql.chat_leave_fed(chat.id) == True:
			get_fedlog = sql.get_fed_log(fed_id)
			if get_fedlog:
				if eval(get_fedlog):
					bot.send_message(get_fedlog, "Sohbet * {} * federasyondan ayrıldı*{}*".format(chat.title, fed_info['fname']), parse_mode="markdown")
			send_message(update.effective_message, "Bu grup federasyondan ayrıldı {}!".format(fed_info['fname']))
		else:
			update.effective_message.reply_text("Hiç katılmadığınız bir federasyondan nasıl ayrılabilirsiniz?!")
	else:
		update.effective_message.reply_text("Bu grubu yalnızca grup oluşturucuları kullanabilir!")

@run_async
def user_join_fed(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)

	if is_user_fed_owner(fed_id, user.id) or user.id in SUDO_USERS:
		user_id = extract_user(msg, args)
		if user_id:
			user = bot.get_chat(user_id)
		elif not msg.reply_to_message and not args:
			user = msg.from_user
		elif not msg.reply_to_message and (not args or (
			len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
			[MessageEntity.TEXT_MENTION]))):
			msg.reply_text("Kullanıcıyı bu iletiden çıkaramıyorum")
			return
		else:
			LOGGER.warning('error')
		getuser = sql.search_user_in_fed(fed_id, user_id)
		fed_id = sql.get_fed_id(chat.id)
		info = sql.get_fed_info(fed_id)
		get_owner = eval(info['fusers'])['owner']
		get_owner = bot.get_chat(get_owner).id
		if user_id == get_owner:
			update.effective_message.reply_text("Kullanıcının federasyon sahibi olduğunu biliyorsunuz, değil mi? SAĞ?")
			return
		if getuser:
			update.effective_message.reply_text("Zaten federasyon yöneticisi olan kullanıcıları tanıtamam! İsterseniz bunları kaldırabilir!")
			return
		if user_id == bot.id:
			update.effective_message.reply_text("Ben zaten tüm federasyonlarda federasyon yöneticisiyim!")
			return
		res = sql.user_join_fed(fed_id, user_id)
		if res:
			update.effective_message.reply_text("Başarıyla Terfi Edildi!")
		else:
			update.effective_message.reply_text("Tanıtım yapılamadı!")
	else:
		update.effective_message.reply_text("Bunu yalnızca federasyon sahipleri yapabilirs!")


@run_async
def user_demote_fed(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)

	if is_user_fed_owner(fed_id, user.id):
		msg = update.effective_message  
		user_id = extract_user(msg, args)
		if user_id:
			user = bot.get_chat(user_id)

		elif not msg.reply_to_message and not args:
			user = msg.from_user

		elif not msg.reply_to_message and (not args or (
			len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
			[MessageEntity.TEXT_MENTION]))):
			msg.reply_text("Kullanıcıyı bu iletiden çıkaramıyorum")
			return
		else:
			LOGGER.warning('error')

		if user_id == bot.id:
			update.effective_message.reply_text("Beni indirmeye çalıştığın şey bensiz çalışamayacak! Sadece söylüyorum.")
			return

		if sql.search_user_in_fed(fed_id, user_id) == False:
			update.effective_message.reply_text("Federasyon yöneticisi olmayan insanları indiremem!")
			return

		res = sql.user_demote_fed(fed_id, user_id)
		if res == True:
			update.effective_message.reply_text("Fed Yöneticisinden indirgendi!")
		else:
			update.effective_message.reply_text("Düşürme başarısız oldu!")
	else:
		update.effective_message.reply_text("Bunu yalnızca federasyon sahipleri yapabilir!")
		return

@run_async
def fed_info(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  
	if args:
		fed_id = args[0]
		info = sql.get_fed_info(fed_id)
	else:
		fed_id = sql.get_fed_id(chat.id)
		if not fed_id:
			send_message(update.effective_message, "Bu grup herhangi bir federasyonda değil!")
			return
		info = sql.get_fed_info(fed_id)

	if is_user_fed_admin(fed_id, user.id) == False:
		update.effective_message.reply_text("Bunu sadece bir federasyon yöneticisi yapabilir!")
		return

	owner = bot.get_chat(info['owner'])
	try:
		owner_name = owner.first_name + " " + owner.last_name
	except:
		owner_name = owner.first_name
	FEDADMIN = sql.all_fed_users(fed_id)
	FEDADMIN.append(int(owner.id))
	TotalAdminFed = len(FEDADMIN)

	user = update.effective_user  
	chat = update.effective_chat  
	info = sql.get_fed_info(fed_id)

	text = "<b>ℹ️ Federasyon Bilgileri:</b>"
	text += "\nFedID: <code>{}</code>".format(fed_id)
	text += "\nİsim: {}".format(info['fname'])
	text += "\nOluşturucu: {}".format(mention_html(owner.id, owner_name))
	text += "\nAll Adminler: <code>{}</code>".format(TotalAdminFed)
	getfban = sql.get_all_fban_users(fed_id)
	text += "\nToplam yasaklanmış kullanıcı: <code>{}</code>".format(len(getfban))
	getfchat = sql.all_fed_chats(fed_id)
	text += "\nBu federasyondaki grup sayısı: <code>{}</code>".format(len(getfchat))

	update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

@run_async
def fed_admin(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonda değil!")
		return

	if is_user_fed_admin(fed_id, user.id) == False:
		update.effective_message.reply_text("Bunu yalnızca federasyon yöneticileri yapabilir!")
		return

	user = update.effective_user  
	chat = update.effective_chat  
	info = sql.get_fed_info(fed_id)

	text = "<b>Federasyon Admin {}:</b>\n\n".format(info['fname'])
	text += "👑 Kurucu:\n"
	owner = bot.get_chat(info['owner'])
	try:
		owner_name = owner.first_name + " " + owner.last_name
	except:
		owner_name = owner.first_name
	text += " • {}\n".format(mention_html(owner.id, owner_name))

	members = sql.all_fed_members(fed_id)
	if len(members) == 0:
		text += "\n🔱 Bu federasyonda yönetici yok"
	else:
		text += "\n🔱 Admin:\n"
		for x in members:
			user = bot.get_chat(x)
			text += " • {}\n".format(mention_html(user.id, user.first_name))

	update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def fed_ban(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonun parçası değil!")
		return

	info = sql.get_fed_info(fed_id)
	getfednotif = sql.user_feds_report(info['owner'])

	if is_user_fed_admin(fed_id, user.id) == False:
		update.effective_message.reply_text("Bunu yalnızca federasyon yöneticileri yapabilir!")
		return

	message = update.effective_message  

	user_id, reason = extract_unt_fedban(message, args)

	fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

	if not user_id:
		message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz")
		return

	if user_id == bot.id:
		message.reply_text("Grup yaratıcısını tekmelemekten daha komik olan nedir? Özveri.")
		return

	if is_user_fed_owner(fed_id, user_id) == True:
		message.reply_text("Federasyon FBA'yı neden denediniz?")
		return

	if is_user_fed_admin(fed_id, user_id) == True:
		message.reply_text("O bir federasyon yöneticisi, onu fban edemem.")
		return

	if user_id == OWNER_ID:
		message.reply_text("Diaster seviyesi Tanrı yasaklı beslenemez!")
		return

	if int(user_id) in SUDO_USERS:
		message.reply_text("Ejderhalar yasaklanamaz!")
		return

	if int(user_id) in TIGER_USERS:
		message.reply_text("Kaplanlar yasaklanamaz!")
		return

	if int(user_id) in WHITELIST_USERS:
		message.reply_text("Kurtlar yasaklanamaz!")
		return

	try:
		user_chat = bot.get_chat(user_id)
		isvalid = True
		fban_user_id = user_chat.id
		fban_user_name = user_chat.first_name
		fban_user_lname = user_chat.last_name
		fban_user_uname = user_chat.username
	except BadRequest as excp:
		if not str(user_id).isdigit():
			send_message(update.effective_message, excp.message)
			return
		elif not len(str(user_id)) == 9:
			send_message(update.effective_message, "Bu bir kullanıcı değil!")
			return
		isvalid = False
		fban_user_id = int(user_id)
		fban_user_name = "user({})".format(user_id)
		fban_user_lname = None
		fban_user_uname = None


	if isvalid and user_chat.type != 'private':
		send_message(update.effective_message, "Bu bir kullanıcı değil!")
		return

	if isvalid:
		user_target = mention_html(fban_user_id, fban_user_name)
	else:
		user_target = fban_user_name

	if fban:
		fed_name = info['fname']
		#https://t.me/OnePunchSupport/41606 // https://t.me/OnePunchSupport/41619
		#starting = "The reason fban is replaced for {} in the Federation <b>{}</b>.".format(user_target, fed_name)
		#send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

		if reason == "":
			reason = "Sebep yok."

		temp = sql.un_fban_user(fed_id, fban_user_id)
		if not temp:
			message.reply_text("Fedban nedeni güncellenemedi!")
			return
		x = sql.fban_user(fed_id, fban_user_id, fban_user_name, fban_user_lname, fban_user_uname, reason, int(time.time()))
		if not x:
			message.reply_text("Federasyon yasaklanamadı! Bu sorun devam ederse @AphroditeSupport ile iletişim kurun.")
			return

		fed_chats = sql.all_fed_chats(fed_id)
		# Will send to current chat
		bot.send_message(chat.id, "<b>FedBan nedeni güncellendi</b>" \
							 "\n<b>Federasyon:</b> {}" \
							 "\n<b>Federasyon Admin:</b> {}" \
							 "\n<b>Kullanıcı:</b> {}" \
							 "\n<b>Kullanıcı ID:</b> <code>{}</code>" \
							 "\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
		# Send message to owner if fednotif is enabled
		if getfednotif:
			bot.send_message(info['owner'], "<b>FedBan nedeni güncellendi</b>" \
							 "\n<b>Federasyon:</b> {}" \
							 "\n<b>Federasyon Admin:</b> {}" \
							 "\n<b>Kullanıcı:</b> {}" \
							 "\n<b>Kullanıcı ID:</b> <code>{}</code>" \
							 "\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
		# If fedlog is set, then send message, except fedlog is current chat
		get_fedlog = sql.get_fed_log(fed_id)
		if get_fedlog:
			if int(get_fedlog) != int(chat.id):
				bot.send_message(get_fedlog, "<b>FedBan nedeni güncellendi</b>" \
							 "\n<b>Federasyon:</b> {}" \
							 "\n<b>Federasyon Admin:</b> {}" \
							 "\n<b>Kulllanıcı:</b> {}" \
							 "\n<b>Kullanıcı ID:</b> <code>{}</code>" \
							 "\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
		for fedschat in fed_chats:
			try:
				# Do not spam all fed chats
				"""
				bot.send_message(chat, "<b>FedBan nedeni güncellendi</b>" \
							 "\n<b>Federasyon:</b> {}" \
							 "\n<b>Federasyon Admin:</b> {}" \
							 "\n<b>Kullanıcı:</b> {}" \
							 "\n<b>Kullanıcı ID:</b> <code>{}</code>" \
							 "\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
				"""
				bot.kick_chat_member(fedschat, fban_user_id)
			except BadRequest as excp:
				if excp.message in FBAN_ERRORS:
					try:
						dispatcher.bot.getChat(fedschat)
					except Unauthorized:
						sql.chat_leave_fed(fedschat)
						LOGGER.info("Sohbet {} tekmelendiğim için gitti {}".format(fedschat, info['fname']))
						continue
				elif excp.message == "User_id_invalid":
					break
				else:
					LOGGER.warning("{} Üzerinde fban bulunamadı çünkü: {}".format(chat, excp.message))
			except TelegramError:
				pass
		# Also do not spam all fed admins
		"""
		send_to_list(bot, FEDADMIN,
				 "<b>FedBan sebebi güncellendi</b>" \
							 "\n<b>Federasyon:</b> {}" \
							 "\n<b>Federasyon Admin:</b> {}" \
							 "\n<b>Kullanıcı:</b> {}" \
							 "\n<b>Kullanıcı ID:</b> <code>{}</code>" \
							 "\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), 
							html=True)
		"""

		# Fban for fed subscriber
		subscriber = list(sql.get_subscriber(fed_id))
		if len(subscriber) != 0:
			for fedsid in subscriber:
				all_fedschat = sql.all_fed_chats(fedsid)
				for fedschat in all_fedschat:
					try:
						bot.kick_chat_member(fedschat, fban_user_id)
					except BadRequest as excp:
						if excp.message in FBAN_ERRORS:
							try:
								dispatcher.bot.getChat(fedschat)
							except Unauthorized:
								targetfed_id = sql.get_fed_id(fedschat)
								sql.unsubs_fed(fed_id, targetfed_id)
								LOGGER.info("{} Sohbeti tekmelendiğim için {} aboneliği iptal edildi".format(fedschat, info['fname']))
								continue
						elif excp.message == "User_id_invalid":
							break
						else:
							LOGGER.warning("{} Üzerinde yayınlanamıyor çünkü: {}".format(fedschat, excp.message))
					except TelegramError:
						pass
		#send_message(update.effective_message, "Fedban Reason has been updated.")
		return

	fed_name = info['fname']

	starting = "Federasyonda {} için federasyon yasağı başlatma<b>{}</b>.".format(user_target, fed_name)
	update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

	if reason == "":
		reason = "Sebep yok."

	x = sql.fban_user(fed_id, fban_user_id, fban_user_name, fban_user_lname, fban_user_uname, reason, int(time.time()))
	if not x:
		message.reply_text("Federasyon yasaklanamadı! Bu sorun devam ederse, iletişim kurun @AphroditeSupport.")
		return

	fed_chats = sql.all_fed_chats(fed_id)
	# Will send to current chat
	bot.send_message(chat.id, "<b>FedBan nedeni güncellendi</b>" \
							"\n<b>Federasyon:</b> {}" \
							"\n<b>Federasyon Admin:</b> {}" \
							"\n<b>Kullanıcı:</b> {}" \
							"\n<b>Kullanıcı ID:</b> <code>{}</code>" \
							"\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
	# Send message to owner if fednotif is enabled
	if getfednotif:
		bot.send_message(info['owner'], "<b>FedBan nedeni güncellendi</b>" \
							"\n<b>Federasyon:</b> {}" \
							"\n<b>Federasyon Admin:</b> {}" \
							"\n<b>Kullanıcı:</b> {}" \
							"\n<b>Kulllanıcı ID:</b> <code>{}</code>" \
							"\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
	# If fedlog is set, then send message, except fedlog is current chat
	get_fedlog = sql.get_fed_log(fed_id)
	if get_fedlog:
		if int(get_fedlog) != int(chat.id):
			bot.send_message(get_fedlog, "<b>FedBan nedeni güncellendi</b>" \
							"\n<b>Federasyon:</b> {}" \
							"\n<b>Federasyon Admin:</b> {}" \
							"\n<b>Kullanıcı:</b> {}" \
							"\n<b>Kullanıcı ID:</b> <code>{}</code>" \
							"\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
	chats_in_fed = 0
	for fedschat in fed_chats:
		chats_in_fed += 1
		try:
			# Do not spamming all fed chats
			"""
			bot.send_message(chat, "<b>FedBan nedeni güncellendi</b>" \
							"\n<b>Federasyon:</b> {}" \
							"\n<b>Federasyon Admin:</b> {}" \
							"\n<b>Kullanıcı:</b> {}" \
							"\n<bKullanıcı ID:</b> <code>{}</code>" \
							"\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
			"""
			bot.kick_chat_member(fedschat, fban_user_id)
		except BadRequest as excp:
			if excp.message in FBAN_ERRORS:
				pass
			elif excp.message == "User_id_invalid":
				break
			else:
				LOGGER.warning("{} Üzerinde fban bulunamadı çünkü: {}".format(chat, excp.message))
		except TelegramError:
			pass

	# Also do not spamming all fed admins
		"""
		send_to_list(bot, FEDADMIN,
				 "<b>FedBan nedeni güncellendi</b>" \
							 "\n<b>Federasyon:</b> {}" \
							 "\n<b>Federasyon Admin:</b> {}" \
							 "\n<b>Kullanıcı:</b> {}" \
							 "\n<b>Kullanıcı ID:</b> <code>{}</code>" \
							 "\n<b>Sebep:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), 
							html=True)
		"""

		# Fban for fed subscriber
		subscriber = list(sql.get_subscriber(fed_id))
		if len(subscriber) != 0:
			for fedsid in subscriber:
				all_fedschat = sql.all_fed_chats(fedsid)
				for fedschat in all_fedschat:
					try:
						bot.kick_chat_member(fedschat, fban_user_id)
					except BadRequest as excp:
						if excp.message in FBAN_ERRORS:
							try:
								dispatcher.bot.getChat(fedschat)
							except Unauthorized:
								targetfed_id = sql.get_fed_id(fedschat)
								sql.unsubs_fed(fed_id, targetfed_id)
								LOGGER.info("{} Sohbeti tekmelendiğim için {} aboneliği iptal edildi".format(fedschat, info['fname']))
								continue
						elif excp.message == "User_id_invalid":
							break
						else:
							LOGGER.warning("{} Üzerinde yayınlanamıyor çünkü: {}".format(fedschat, excp.message))
					except TelegramError:
						pass
	if chats_in_fed == 0:
		send_message(update.effective_message, "Fedban 0 sohbeti etkiledi. ")
	elif chats_in_fed > 0:
		send_message(update.effective_message, "Fedban {} sohbetlerini etkiledi. ".format(chats_in_fed))


@run_async
def unfban(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  
	message = update.effective_message  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonun parçası değil!")
		return

	info = sql.get_fed_info(fed_id)
	getfednotif = sql.user_feds_report(info['owner'])

	if is_user_fed_admin(fed_id, user.id) == False:
		update.effective_message.reply_text("Bunu yalnızca federasyon yöneticileri yapabilir!")
		return

	user_id = extract_user_fban(message, args)
	if not user_id:
		message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz.")
		return

	try:
		user_chat = bot.get_chat(user_id)
		isvalid = True
		fban_user_id = user_chat.id
		fban_user_name = user_chat.first_name
		fban_user_lname = user_chat.last_name
		fban_user_uname = user_chat.username
	except BadRequest as excp:
		if not str(user_id).isdigit():
			send_message(update.effective_message, excp.message)
			return
		elif not len(str(user_id)) == 9:
			send_message(update.effective_message, "Bu bir kullanıcı değil!")
			return
		isvalid = False
		fban_user_id = int(user_id)
		fban_user_name = "user({})".format(user_id)
		fban_user_lname = None
		fban_user_uname = None

	if isvalid and user_chat.type != 'private':
		message.reply_text("Bu bir kullanıcı değil!")
		return

	if isvalid:
		user_target = mention_html(fban_user_id, fban_user_name)
	else:
		user_target = fban_user_name

	fban, fbanreason, fbantime = sql.get_fban_user(fed_id, fban_user_id)
	if fban == False:
		message.reply_text("Bu kullanıcı yasaklanmış değil!")
		return

	banner = update.effective_user  

	message.reply_text("Bu federasyona {} bir şans daha vereceğim".format(user_chat.first_name))

	chat_list = sql.all_fed_chats(fed_id)
	# Will send to current chat
	bot.send_message(chat.id, "<b>Kaldır-FedBan</b>" \
						 "\n<b>Federasyon:</b> {}" \
						 "\n<b>Federasyon Admin:</b> {}" \
						 "\n<b>Kulllanıcı:</b> {}" \
						 "\n<b>Kullanıcı ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
	# Send message to owner if fednotif is enabled
	if getfednotif:
		bot.send_message(info['owner'], "<b>Kaldır-FedBan</b>" \
						 "\n<b>Federasyon:</b> {}" \
						 "\n<b>Federasyon Admin:</b> {}" \
						 "\n<b>Kullanıcı:</b> {}" \
						 "\n<b>Kullanıcı ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
	# If fedlog is set, then send message, except fedlog is current chat
	get_fedlog = sql.get_fed_log(fed_id)
	if get_fedlog:
		if int(get_fedlog) != int(chat.id):
			bot.send_message(get_fedlog, "<b>Kaldır-FedBan</b>" \
						 "\n<b>Federasyon:</b> {}" \
						 "\n<b>Federasyon Admin:</b> {}" \
						 "\n<b>Kullanıcı:</b> {}" \
						 "\n<b>Kullanıcı ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
	unfbanned_in_chats = 0
	for fedchats in chat_list:
		unfbanned_in_chats += 1
		try:
			member = bot.get_chat_member(fedchats, user_id)
			if member.status == 'kicked':
				bot.unban_chat_member(fedchats, user_id)
			# Do not spamming all fed chats
			"""
			bot.send_message(chat, "<b>Kaldır-FedBan</b>" \
						 "\n<b>Federasyon:</b> {}" \
						 "\n<b>Federasyon Admin:</b> {}" \
						 "\n<b>Kullanıcı:</b> {}" \
						 "\n<b>Kullanıcı ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
			"""
		except BadRequest as excp:
			if excp.message in UNFBAN_ERRORS:
				pass
			elif excp.message == "User_id_invalid":
				break
			else:
				LOGGER.warning("{} Üzerinde fban bulunamadı çünkü: {}".format(chat, excp.message))
		except TelegramError:
			pass

	try:
		x = sql.un_fban_user(fed_id, user_id)
		if not x:
			send_message(update.effective_message, "Yasaklanma başarısız oldu, bu kullanıcının zaten yasaklanmamış olması!")
			return
	except:
		pass

	# UnFban for fed subscriber
	subscriber = list(sql.get_subscriber(fed_id))
	if len(subscriber) != 0:
		for fedsid in subscriber:
			all_fedschat = sql.all_fed_chats(fedsid)
			for fedschat in all_fedschat:
				try:
					bot.unban_chat_member(fedchats, user_id)
				except BadRequest as excp:
					if excp.message in FBAN_ERRORS:
						try:
							dispatcher.bot.getChat(fedschat)
						except Unauthorized:
							targetfed_id = sql.get_fed_id(fedschat)
							sql.unsubs_fed(fed_id, targetfed_id)
							LOGGER.info("{} Sohbeti tekmelendiğim için {} aboneliği iptal edildi".format(fedschat, info['fname']))
							continue
					elif excp.message == "User_id_invalid":
						break
					else:
						LOGGER.warning("{} Üzerinde yayınlanamıyor çünkü: {}".format(fedschat, excp.message))
				except TelegramError:
					pass

	if unfbanned_in_chats == 0:
		send_message(update.effective_message,"Bu kişinin 0 sohbeti yasaklandı.")
	if unfbanned_in_chats > 0:
		send_message(update.effective_message,"Bu kişinin {} sohbeti yasaklandı.".format(unfbanned_in_chats))
	# Also do not spamming all fed admins
	"""
	FEDADMIN = sql.all_fed_users(fed_id)
	for x in FEDADMIN:
		getreport = sql.user_feds_report(x)
		if getreport == False:
			FEDADMIN.remove(x)
	send_to_list(bot, FEDADMIN,
			 "<b>Kaldır-FedBan</b>" \
			 "\n<b>Federasyon:</b> {}" \
			 "\n<b>Federasyon Admin:</b> {}" \
			 "\n<b>Kullanıcı:</b> {}" \
			 "\n<b>Kullanıcı ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name),
												 mention_html(user_chat.id, user_chat.first_name),
															  user_chat.id),
			html=True)
	"""


@run_async
def set_frules(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonda değil!")
		return

	if is_user_fed_admin(fed_id, user.id) == False:
		update.effective_message.reply_text("Bunu yalnızca beslenen yöneticiler yapabilir!")
		return

	if len(args) >= 1:
		msg = update.effective_message  
		raw_text = msg.text
		args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
		if len(args) == 2:
			txt = args[1]
			offset = len(txt) - len(raw_text)  # set correct offset relative to command
			markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
		x = sql.set_frules(fed_id, markdown_rules)
		if not x:
			update.effective_message.reply_text("Oha! Federasyon kuralları ayarlanırken bir hata oluştu! Nedenini merak ettiyseniz lütfen sorun @AphroditSupport !")
			return

		rules = sql.get_fed_info(fed_id)['frules']
		getfed = sql.get_fed_info(fed_id)
		get_fedlog = sql.get_fed_log(fed_id)
		if get_fedlog:
			if eval(get_fedlog):
				bot.send_message(get_fedlog, "*{}* fed için federasyon kurallarını güncelledi *{}*".format(user.first_name, getfed['fname']), parse_mode="markdown")
		update.effective_message.reply_text(f"Kurallar olarak değiştirildi :\n{rules}!")
	else:
		update.effective_message.reply_text("Bunu ayarlamak için lütfen kurallar yazın!")


@run_async
def get_frules(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)
	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonda değil!")
		return

	rules = sql.get_frules(fed_id)
	text = "*Bu fed içindeki kurallar:*\n"
	text += rules
	update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@run_async
def fed_broadcast(bot: Bot, update: Update, args: List[str]):
	msg = update.effective_message  
	user = update.effective_user  
	chat = update.effective_chat  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	if args:
		chat = update.effective_chat  
		fed_id = sql.get_fed_id(chat.id)
		fedinfo = sql.get_fed_info(fed_id)
		if is_user_fed_owner(fed_id, user.id) == False:
			update.effective_message.reply_text("Bunu yalnızca federasyon sahipleri yapabilir!")
			return  
		# Parsing md
		raw_text = msg.text
		args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
		txt = args[1]
		offset = len(txt) - len(raw_text)  # set correct offset relative to command
		text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
		text = text_parser
		try:
			broadcaster = user.first_name
		except:
			broadcaster = user.first_name + " " + user.last_name
		text += "\n\n- {}".format(mention_markdown(user.id, broadcaster))
		chat_list = sql.all_fed_chats(fed_id)
		failed = 0
		for chat in chat_list:
			title = "*Fed'den yeni yayın {}*\n".format(fedinfo['fname'])
			try:
				bot.sendMessage(chat, title + text, parse_mode="markdown")
			except TelegramError:
				try:
					dispatcher.bot.getChat(chat)
				except Unauthorized:
					failed += 1
					sql.chat_leave_fed(chat)
					LOGGER.info("{} Sohbeti delinmiş olduğum için {} kicklendi. ".format(chat, fedinfo['fname']))
					continue
				failed += 1
				LOGGER.warning("Adresine yayın gönderilemedi {}".format(str(chat)))

		send_text = "Federasyon yayını tamamlandı"
		if failed >= 1:
			send_text += "{} büyük olasılıkla Federasyon'dan ayrıldığı için grup mesajı alamadı.".format(failed)
		update.effective_message.reply_text(send_text)

@run_async
def fed_ban_list(bot: Bot, update: Update, args: List[str], chat_data):
	chat = update.effective_chat  
	user = update.effective_user  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)
	info = sql.get_fed_info(fed_id)

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonun parçası değil!")
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		update.effective_message.reply_text("Bunu sadece Federasyon sahipleri yapabilir!")
		return

	user = update.effective_user  
	chat = update.effective_chat  
	getfban = sql.get_all_fban_users(fed_id)
	if len(getfban) == 0:
		update.effective_message.reply_text("{} Federasyon yasak listesi boş".format(info['fname']), parse_mode=ParseMode.HTML)
		return

	if args:
		if args[0] == 'json':
			jam = time.time()
			new_jam = jam + 1800
			cek = get_chat(chat.id, chat_data)
			if cek.get('status'):
				if jam <= int(cek.get('value')):
					waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
					update.effective_message.reply_text("Verilerinizi 30 dakikada bir yedekleyebilirsiniz!\nVerileri şu adreste tekrar yedekleyebilirsiniz: `{}`".format(waktu), parse_mode=ParseMode.MARKDOWN)
					return
				else:
					if user.id not in SUDO_USERS:
						put_chat(chat.id, new_jam, chat_data)
			else:
				if user.id not in SUDO_USERS:
					put_chat(chat.id, new_jam, chat_data)
			backups = ""
			for users in getfban:
				getuserinfo = sql.get_all_fban_users_target(fed_id, users)
				json_parser = {"user_id": users, "first_name": getuserinfo['first_name'], "last_name": getuserinfo['last_name'], "user_name": getuserinfo['user_name'], "reason": getuserinfo['reason']}
				backups += json.dumps(json_parser)
				backups += "\n"
			with BytesIO(str.encode(backups)) as output:
				output.name = "saitama_fbanned_users.json"
				update.effective_message.reply_document(document=output, filename="saitama_fbanned_users.json",
													caption="Toplam {} Kullanıcı Federasyon tarafından engellendi {}.".format(len(getfban), info['fname']))
			return
		elif args[0] == 'csv':
			jam = time.time()
			new_jam = jam + 1800
			cek = get_chat(chat.id, chat_data)
			if cek.get('status'):
				if jam <= int(cek.get('value')):
					waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
					update.effective_message.reply_text("Verileri 30 dakikada bir yedekleyebilirsiniz!\nVerileri şu adreste tekrar yedekleyebilirsiniz: `{}`".format(waktu), parse_mode=ParseMode.MARKDOWN)
					return
				else:
					if user.id not in SUDO_USERS:
						put_chat(chat.id, new_jam, chat_data)
			else:
				if user.id not in SUDO_USERS:
					put_chat(chat.id, new_jam, chat_data)
			backups = "id,firstname,lastname,username,reason\n"
			for users in getfban:
				getuserinfo = sql.get_all_fban_users_target(fed_id, users)
				backups += "{user_id},{first_name},{last_name},{user_name},{reason}".format(user_id=users, first_name=getuserinfo['first_name'], last_name=getuserinfo['last_name'], user_name=getuserinfo['user_name'], reason=getuserinfo['reason'])
				backups += "\n"
			with BytesIO(str.encode(backups)) as output:
				output.name = "saitama_fbanned_users.csv"
				update.effective_message.reply_document(document=output, filename="saitama_fbanned_users.csv",
													caption="Toplam {} Kullanıcı Federasyon tarafından engellendi {}.".format(len(getfban), info['fname']))
			return

	text = "<b>{}kullanıcıların federasyondan men edilmesi yasaklandı {}:</b>\n".format(len(getfban), info['fname'])
	for users in getfban:
		getuserinfo = sql.get_all_fban_users_target(fed_id, users)
		if getuserinfo == False:
			text = "Federasyondan yasaklanmış kullanıcı yok {}".format(info['fname'])
			break
		user_name = getuserinfo['first_name']
		if getuserinfo['last_name']:
			user_name += " " + getuserinfo['last_name']
		text += " • {} (<code>{}</code>)\n".format(mention_html(users, user_name), users)

	try:
		update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
	except:
		jam = time.time()
		new_jam = jam + 1800
		cek = get_chat(chat.id, chat_data)
		if cek.get('status'):
			if jam <= int(cek.get('value')):
				waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
				update.effective_message.reply_text("Verileri 30 dakikada bir yedekleyebilirsiniz!\nVerileri şu adreste tekrar yedekleyebilirsiniz: `{}`".format(waktu), parse_mode=ParseMode.MARKDOWN)
				return
			else:
				if user.id not in SUDO_USERS:
					put_chat(chat.id, new_jam, chat_data)
		else:
			if user.id not in SUDO_USERS:
				put_chat(chat.id, new_jam, chat_data)
		cleanr = re.compile('<.*?>')
		cleantext = re.sub(cleanr, '', text)
		with BytesIO(str.encode(cleantext)) as output:
			output.name = "fbanlist.txt"
			update.effective_message.reply_document(document=output, filename="fbanlist.txt",
													caption="Aşağıda, Federasyonda şu anda yasaklanmış olan kullanıcıların bir listesi bulunmaktadır {}.".format(info['fname']))

@run_async
def fed_notif(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  
	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonun parçası değil!")
		return

	if args:
		if args[0] in ("yes", "on"):
			sql.set_feds_setting(user.id, True)
			msg.reply_text("Raporlama Federasyonu yedeklendi! Fban /unfban olan her kullanıcı PM aracılığıyla bilgilendirilir..")
		elif args[0] in ("no", "off"):
			sql.set_feds_setting(user.id, False)
			msg.reply_text("Raporlama Federasyonu durdu! Fban /unfban olan her kullanıcı PM aracılığıyla bilgilendirilmez..")
		else:
			msg.reply_text("Lütfen Girin `on`/`off`", parse_mode="markdown")
	else:
		getreport = sql.user_feds_report(user.id)
		msg.reply_text("Mevcut Federasyon raporu tercihleriniz: `{}`".format(getreport), parse_mode="markdown")

@run_async
def fed_chats(bot: Bot, update: Update, args: List[str]):
	chat = update.effective_chat  
	user = update.effective_user  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)
	info = sql.get_fed_info(fed_id)

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonun parçası değil!")
		return

	if is_user_fed_admin(fed_id, user.id) == False:
		update.effective_message.reply_text("Bunu yalnızca federasyon yöneticileri yapabilir!")
		return

	getlist = sql.all_fed_chats(fed_id)
	if len(getlist) == 0:
		update.effective_message.reply_text("Hiçbir kullanıcı federasyondan uzak değil {}".format(info['fname']), parse_mode=ParseMode.HTML)
		return

	text = "<b>New chat joined the federation {}:</b>\n".format(info['fname'])
	for chats in getlist:
		try:
			chat_name = dispatcher.bot.getChat(chats).title
		except Unauthorized:
			sql.chat_leave_fed(chats)
			LOGGER.info("Sohbet {} tekmelendiğim için beslendi {}".format(chats, info['fname']))
			continue
		text += " • {} (<code>{}</code>)\n".format(chat_name, chats)

	try:
		update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
	except:
		cleanr = re.compile('<.*?>')
		cleantext = re.sub(cleanr, '', text)
		with BytesIO(str.encode(cleantext)) as output:
			output.name = "fedchats.txt"
			update.effective_message.reply_document(document=output, filename="fedchats.txt",
													caption="İşte federasyona katılan tüm sohbetlerin bir listesi {}.".format(info['fname']))

@run_async
def fed_import_bans(bot: Bot, update: Update, chat_data):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)
	info = sql.get_fed_info(fed_id)
	getfed = sql.get_fed_info(fed_id)

	if not fed_id:
		update.effective_message.reply_text("Bu grup herhangi bir federasyonun parçası değil!")
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		update.effective_message.reply_text("!")
		return

	if msg.reply_to_message and msg.reply_to_message.document:
		jam = time.time()
		new_jam = jam + 1800
		cek = get_chat(chat.id, chat_data)
		if cek.get('status'):
			if jam <= int(cek.get('value')):
				waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
				update.effective_message.reply_text("Verilerinizi 30 dakikada bir alabilirsiniz!\nVerileri şu adresten tekrar alabilirsiniz:`{}`".format(waktu), parse_mode=ParseMode.MARKDOWN)
				return
			else:
				if user.id not in SUDO_USERS:
					put_chat(chat.id, new_jam, chat_data)
		else:
			if user.id not in SUDO_USERS:
				put_chat(chat.id, new_jam, chat_data)
		#if int(int(msg.reply_to_message.document.file_size)/1024) >= 200:
		#	msg.reply_text("This file is too big!")
		#	return
		success = 0
		failed = 0
		try:
			file_info = bot.get_file(msg.reply_to_message.document.file_id)
		except BadRequest:
			msg.reply_text("Dosyayı indirip yeniden yüklemeyi deneyin, bu bozuk görünüyor!")
			return
		fileformat = msg.reply_to_message.document.file_name.split('.')[-1]
		if fileformat == 'json':
			multi_fed_id = []
			multi_import_userid = []
			multi_import_firstname = []
			multi_import_lastname = []
			multi_import_username = []
			multi_import_reason = []
			with BytesIO() as file:
				file_info.download(out=file)
				file.seek(0)
				reading = file.read().decode('UTF-8')
				splitting = reading.split('\n')
				for x in splitting:
					if x == '':
						continue
					try:
						data = json.loads(x)
					except json.decoder.JSONDecodeError as err:
						failed += 1
						continue
					try:
						import_userid = int(data['user_id']) # Make sure it int
						import_firstname = str(data['first_name'])
						import_lastname = str(data['last_name'])
						import_username = str(data['user_name'])
						import_reason = str(data['reason'])
					except ValueError:
						failed += 1
						continue
					# Checking user
					if int(import_userid) == bot.id:
						failed += 1
						continue
					if is_user_fed_owner(fed_id, import_userid) == True:
						failed += 1
						continue
					if is_user_fed_admin(fed_id, import_userid) == True:
						failed += 1
						continue
					if str(import_userid) == str(OWNER_ID):
						failed += 1
						continue
					if int(import_userid) in SUDO_USERS:
						failed += 1
						continue
					if int(import_userid) in TIGER_USERS:
						failed += 1
						continue  
					if int(import_userid) in WHITELIST_USERS:
						failed += 1
						continue
					multi_fed_id.append(fed_id)
					multi_import_userid.append(str(import_userid))
					multi_import_firstname.append(import_firstname)
					multi_import_lastname.append(import_lastname)
					multi_import_username.append(import_username)
					multi_import_reason.append(import_reason)
					success += 1
				sql.multi_fban_user(multi_fed_id, multi_import_userid, multi_import_firstname, multi_import_lastname, multi_import_username, multi_import_reason)
			text = "Bloklar başarıyla içe aktarıldı. {} kişi engellendi.".format(success)
			if failed >= 1:
				text += " {} Failed to import.".format(failed)
			get_fedlog = sql.get_fed_log(fed_id)
			if get_fedlog:
				if eval(get_fedlog):
					teks = "Fed * {} * verileri başarıyla içe aktardı. {} banned.".format(getfed['fname'], success)
					if failed >= 1:
						teks += " {} Failed to import.".format(failed)
					bot.send_message(get_fedlog, teks, parse_mode="markdown")
		elif fileformat == 'csv':
			multi_fed_id = []
			multi_import_userid = []
			multi_import_firstname = []
			multi_import_lastname = []
			multi_import_username = []
			multi_import_reason = []
			file_info.download("fban_{}.csv".format(msg.reply_to_message.document.file_id))
			with open("fban_{}.csv".format(msg.reply_to_message.document.file_id), 'r', encoding="utf8") as csvFile:
				reader = csv.reader(csvFile)
				for data in reader:
					try:
						import_userid = int(data[0]) # Make sure it int
						import_firstname = str(data[1])
						import_lastname = str(data[2])
						import_username = str(data[3])
						import_reason = str(data[4])
					except ValueError:
						failed += 1
						continue
					# Checking user
					if int(import_userid) == bot.id:
						failed += 1
						continue
					if is_user_fed_owner(fed_id, import_userid) == True:
						failed += 1
						continue
					if is_user_fed_admin(fed_id, import_userid) == True:
						failed += 1
						continue
					if str(import_userid) == str(OWNER_ID):
						failed += 1
						continue
					if int(import_userid) in SUDO_USERS:
						failed += 1
						continue
					if int(import_userid) in TIGER_USERS:
						failed += 1
						continue  
					if int(import_userid) in WHITELIST_USERS:
						failed += 1
						continue
					multi_fed_id.append(fed_id)
					multi_import_userid.append(str(import_userid))
					multi_import_firstname.append(import_firstname)
					multi_import_lastname.append(import_lastname)
					multi_import_username.append(import_username)
					multi_import_reason.append(import_reason)
					success += 1
					# t = ThreadWithReturnValue(target=sql.fban_user, args=(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason,))
					# t.start()
				sql.multi_fban_user(multi_fed_id, multi_import_userid, multi_import_firstname, multi_import_lastname, multi_import_username, multi_import_reason)
			csvFile.close()
			os.remove("fban_{}.csv".format(msg.reply_to_message.document.file_id))
			text = "Dosyalar başarıyla içe aktarıldı. {} insanlar yasaklandı.".format(success)
			if failed >= 1:
				text += " {} Failed to import.".format(failed)
			get_fedlog = sql.get_fed_log(fed_id)
			if get_fedlog:
				if eval(get_fedlog):
					teks = "Fed * {} * verileri başarıyla içe aktardı. {} banned.".format(getfed['fname'], success)
					if failed >= 1:
						teks += " {} İçe aktarılamadı.".format(failed)
					bot.send_message(get_fedlog, teks, parse_mode="markdown")
		else:
			send_message(update.effective_message, "Bu dosya desteklenmiyor.")
			return
		send_message(update.effective_message, text)

@run_async
def del_fed_button(bot, update):
	query = update.callback_query
	userid = query.message.chat.id
	fed_id = query.data.split("_")[1]

	if fed_id == 'cancel':
		query.message.edit_text("Federasyon silme işlemi iptal edildi")
		return

	getfed = sql.get_fed_info(fed_id)
	if getfed:
		delete = sql.del_fed(fed_id)
		if delete:
			query.message.edit_text("Federasyonunuzu kaldırdınız! Artık `{}` ile bağlantılı tüm Grupların bir Federasyonu yok.".format(getfed['fname']), parse_mode='markdown')

@run_async
def fed_stat_user(bot, update, args):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	if args:
		if args[0].isdigit():
			user_id = args[0]
		else:
			user_id = extract_user(msg, args)
	else:
		user_id = extract_user(msg, args)

	if user_id:
		if len(args) == 2 and args[0].isdigit():
			fed_id = args[1]
			user_name, reason, fbantime = sql.get_user_fban(fed_id, str(user_id))
			if fbantime:
				fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
			else:
				fbantime = "Unavaiable"
			if user_name == False:
				send_message(update.effective_message, "Fed {} bulunamadı!".format(fed_id), parse_mode="markdown")
				return
			if user_name == "" or user_name == None:
				user_name = "He/she"
			if not reason:
				send_message(update.effective_message, "{} bu federasyonda yasak değil!".format(user_name))
			else:
				teks = "{} bu federasyonda yasaklandı çünkü:\nTarihinde yasaklandı`{}`\n*:* `{}`".format(user_name, reason, fbantime)
				send_message(update.effective_message, teks, parse_mode="markdown")
			return
		user_name, fbanlist = sql.get_user_fbanlist(str(user_id))
		if user_name == "":
			try:
				user_name = bot.get_chat(user_id).first_name
			except BadRequest:
				user_name = "He/she"
			if user_name == "" or user_name == None:
				user_name = "He/she"
		if len(fbanlist) == 0:
			send_message(update.effective_message, "{} herhangi bir federasyonda yasaklanmadı!".format(user_name))
			return
		else:
			teks = "{} bu federasyonda yasaklandı:\n".format(user_name)
			for x in fbanlist:
				teks += "- `{}`: {}\n".format(x[0], x[1][:20])
			teks += "\nÖzellikle Fedban'ın nedenleri hakkında daha fazla bilgi edinmek istiyorsanız /fbanstat kullanın <FedID>"
			send_message(update.effective_message, teks, parse_mode="markdown")

	elif not msg.reply_to_message and not args:
		user_id = msg.from_user.id
		user_name, fbanlist = sql.get_user_fbanlist(user_id)
		if user_name == "":
			user_name = msg.from_user.first_name
		if len(fbanlist) == 0:
			send_message(update.effective_message, "{} hiçbir federasyonda yasaklanmadı!".format(user_name))
		else:
			teks = "{} has been banned in this federation:\n".format(user_name)
			for x in fbanlist:
				teks += "- `{}`: {}\n".format(x[0], x[1][:20])
			teks += "\nÖzellikle Fedban'ın nedenleri hakkında daha fazla bilgi edinmek istiyorsanız /fbanstat kullanın <FedID>"
			send_message(update.effective_message, teks, parse_mode="markdown")

	else:
		fed_id = args[0]
		fedinfo = sql.get_fed_info(fed_id)
		if not fedinfo:
			send_message(update.effective_message, "Fed {} bulunamadı!".format(fed_id))
			return
		name, reason, fbantime = sql.get_user_fban(fed_id, msg.from_user.id)
		if fbantime:
			fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
		else:
			fbantime = "Unavaiable"
		if not name:
			name = msg.from_user.first_name
		if not reason:
			send_message(update.effective_message, "{} bu federasyonda yasaklanmadı".format(name))
			return
		send_message(update.effective_message, "{} bu federasyonda yasaklandı çünkü:\n`{}`\n*Tarihinde yasaklandı:* `{}`".format(name, reason, fbantime), parse_mode="markdown")


@run_async
def set_fed_log(bot, update, args):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	if args:
		fedinfo = sql.get_fed_info(args[0])
		if not fedinfo:
			send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!!")
			return
		isowner = is_user_fed_owner(args[0], user.id)
		if not isowner:
			send_message(update.effective_message, "Yalnızca federasyon oluşturucu federasyon günlüklerini ayarlayabilir.")
			return
		setlog = sql.set_fed_log(args[0], chat.id)
		if setlog:
			send_message(update.effective_message, "Federasyon günlüğü `{}` olarak ayarlandı {}".format(fedinfo['fname'], chat.title), parse_mode="markdown")
	else:
		send_message(update.effective_message, "Fed kimliğinizi sağlamadınız!")

@run_async
def unset_fed_log(bot, update, args):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	if args:
		fedinfo = sql.get_fed_info(args[0])
		if not fedinfo:
			send_message(update.effective_message, "Bu Federasyon mevcut değil!")
			return
		isowner = is_user_fed_owner(args[0], user.id)
		if not isowner:
			send_message(update.effective_message, "Yalnızca federasyon oluşturucu federasyon günlüklerini ayarlayabilir.")
			return
		setlog = sql.set_fed_log(args[0], None)
		if setlog:
			send_message(update.effective_message, "Federasyon günlüğü `{}` tarihinde iptal edildi {}".format(fedinfo['fname'], chat.title), parse_mode="markdown")
	else:
		send_message(update.effective_message, "Fed kimliğinizi sağlamadınız!")


@run_async
def subs_feds(bot, update, args):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)
	fedinfo = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, "Bu grup herhangi bir federasyonda değiln!")
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, "Bunu yalnızca fed sahip yapabilir!")
		return

	if args:
		getfed = sql.search_fed_by_id(args[0])
		if getfed == False:
			send_message(update.effective_message, "Lütfen geçerli bir federasyon kimliği girin.")
			return
		subfed = sql.subs_fed(args[0], fed_id)
		if subfed:
			send_message(update.effective_message, "`{}` Federasyonu `{}` federasyonuna abone oldu. Bu federasyondan bir Fedban olduğunda, bu federasyon aynı zamanda bu kullanıcıyı da yasaklayacak.".format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
			get_fedlog = sql.get_fed_log(args[0])
			if get_fedlog:
				if int(get_fedlog) != int(chat.id):
					bot.send_message(get_fedlog, "Federation `{}` has subscribe the federation `{}`".format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
		else:
			send_message(update.effective_message, "Federasyon `{}` federasyona zaten abone oldu `{}`.".format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
	else:
		send_message(update.effective_message, "Fed kimliğinizi sağlamadınız!")

@run_async
def unsubs_feds(bot, update, args):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)
	fedinfo = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, "Bu grup herhangi bir federasyonda değil!")
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, "Bunu yalnızca beslenen sahip yapabilir!")
		return

	if args:
		getfed = sql.search_fed_by_id(args[0])
		if getfed == False:
			send_message(update.effective_message, "Lütfen geçerli bir federasyon kimliği girin.")
			return
		subfed = sql.unsubs_fed(args[0], fed_id)
		if subfed:
			send_message(update.effective_message, "Federasyon `{}` şimdi aboneliği iptal et `{}`.".format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
			get_fedlog = sql.get_fed_log(args[0])
			if get_fedlog:
				if int(get_fedlog) != int(chat.id):
					bot.send_message(get_fedlog, "`{}` Federasyonu abonelikten çıkıldı `{}`.".format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
		else:
			send_message(update.effective_message, "`{}` Federasyonu abone değil `{}`.".format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
	else:
		send_message(update.effective_message, "FED kimliğinizi sağlamadınız!")

@run_async
def get_myfedsubs(bot, update, args):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	if chat.type == 'private':
		send_message(update.effective_message, "Bu komut grubumuza özeldir, pm'ye değil!")
		return

	fed_id = sql.get_fed_id(chat.id)
	fedinfo = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, "Bu grup herhangi bir federasyonda değil!")
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, "Bunu yalnızca Fed sahip yapabilir!")
		return

	try:
		getmy = sql.get_mysubs(fed_id)
	except:
		getmy = []
	 

	if len(getmy) == 0:
		send_message(update.effective_message, "`{}` Federasyonu herhangi bir federasyona abone değil.".format(fedinfo['fname']), parse_mode="markdown")
		return
	else:
		listfed = "Federation `{}` federasyona abone oluyor:\n".format(fedinfo['fname'])
		for x in getmy:
			listfed += "- `{}`\n".format(x)
		listfed += "\nBeslenen bilgi almak için `/fedinfo <fedid>`. Aboneliği iptal etmek için `/unsubfed <fedid>`."
		send_message(update.effective_message, listfed, parse_mode="markdown")

@run_async
def get_myfeds_list(bot, update):
	chat = update.effective_chat  
	user = update.effective_user  
	msg = update.effective_message  

	fedowner = sql.get_user_owner_fed_full(user.id)
	if fedowner:
		text = "*Sen fedin sahibisin:\n*"
		for f in fedowner:
			text += "- `{}`: *{}*\n".format(f['fed_id'], f['fed']['fname'])
	else:
		text = "*Hiç fedin yok!*"
	send_message(update.effective_message, text, parse_mode="markdown")


def is_user_fed_admin(fed_id, user_id):
	fed_admins = sql.all_fed_users(fed_id)
	if fed_admins == False:
		return False
	if int(user_id) in fed_admins or int(user_id) == OWNER_ID:
		return True
	else:
		return False


def is_user_fed_owner(fed_id, user_id):
	getsql = sql.get_fed_info(fed_id)
	if getsql == False:
		return False
	getfedowner = eval(getsql['fusers'])
	if getfedowner == None or getfedowner == False:
		return False
	getfedowner = getfedowner['owner']
	if str(user_id) == getfedowner or int(user_id) == OWNER_ID:
		return True
	else:
		return False


@run_async
def welcome_fed(bot, update):
	chat = update.effective_chat  
	user = update.effective_user  
	fed_id = sql.get_fed_id(chat.id)
	fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user.id)
	if fban:
		update.effective_message.reply_text("Bu kullanıcı şu anki federasyonda yasaklandı! Onu kaldıracağım.")
		bot.kick_chat_member(chat.id, user.id)
		return True
	else:
		return False


def __stats__():
	all_fbanned = sql.get_all_fban_users_global()
	all_feds = sql.get_all_feds_users_global()
	return "{} {} Federasyonunda kullanıcı yasaklandı".format(len(all_fbanned), len(all_feds))


def __user_info__(user_id, chat_id):
	fed_id = sql.get_fed_id(chat_id)
	if fed_id:
		fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)
		info = sql.get_fed_info(fed_id)
		infoname = info['fname']

		if int(info['owner']) == user_id:
			text = "Bu kullanıcı mevcut Federasyonun sahibidir: <b>{}</b>.".format(infoname)
		elif is_user_fed_admin(fed_id, user_id):
			text = "Bu kullanıcı mevcut Federasyonun yöneticisidir: <b>{}</b>.".format(infoname)

		elif fban:
			text = "Prohibited in the current Federation: <b>Yes</b>"
			text += "\n<b>Sebep:</b> {}".format(fbanreason)
		else:
			text = "Mevcut Federasyonda yasaklanmış: <b>No</b>"
	else:
		text = ""
	return text


# Temporary data
def put_chat(chat_id, value, chat_data):
	# print(chat_data)
	if value == False:
		status = False
	else:
		status = True
	chat_data[chat_id] = {'federation': {"status": status, "value": value}}

def get_chat(chat_id, chat_data):
	# print(chat_data)
	try:
		value = chat_data[chat_id]['federation']
		return value
	except KeyError:
		return {"status": False, "value": False}

@run_async
def fed_owner_help(bot: Bot, update: Update):
   update.effective_message.reply_text("""*👑 Yalnızca Fed Sahibi:*
 • `/newfed <fed_ismi>`*:* Kullanıcı başına izin verilen bir Federasyon oluşturur. Fed adını değiştirmek için de kullanılabilir. (max. 64 karakter)
 • `/delfed <fed_id>`*:* Bir Federasyonu ve bununla ilgili bilgileri silin. Engellenen kullanıcıları iptal etmeyecek.
 • `/fpromote <kullanıcı>`*:* Kullanıcıyı bir federasyon yöneticisi olarak atar. `Fed Yöneticileri 'altında kullanıcı için tüm komutları etkinleştirir.
 • `/fdemote  <kullanıcı>`*:* Kullanıcıyı Yönetici Federasyonundan normal bir kullanıcıya bırakır.
 • `/subfed <fed_id>`*:* Belirli bir beslenen kimliğe abone olursanız, bu beslenen beslemenin yasakları da beslemenizde gerçekleşir.
 • `/unsubfed <fed_id>`*:* Belirli bir beslenen kimliğe olan aboneliği iptal eder.
 • `/setfedlog <fed_id>`*:* Grubu, federasyon için bir beslemeli günlük raporu tabanı olarak ayarlar.
 • `/unsetfedlog <fed_id>`*:* Grubu, federasyon için bir beslemeli günlük raporu tabanı olarak kaldırdı.
 • `/fbroadcast <mesaj>`*:* Fedinize katılan tüm gruplara mesaj yayınlar.
 • `/fedsubs`*:* Grubunuzun abone olduğu hakları gösterir. `(kırık rn)`""", parse_mode = ParseMode.MARKDOWN)
   
@run_async
def fed_admin_help(bot: Bot, update: Update):
   update.effective_message.reply_text("""*🔱 Fed Adminleri:*
 • `/fban <kullanıcı> <sebep>`*:* Fed bir kullanıcıyı yasaklar.
 • `/unfban <kullanıcı> <sebep>`*:* Bir kullanıcıyı beslenen yasağı kaldırır.
 • `/fedinfo <fed_id>`*:* Belirtilen Federasyon hakkında bilgi.
 • `/joinfed <fed_id>`*:* Federasyon ile mevcut sohbete katılın. Bunu yalnızca sohbet sahipleri yapabilir. Her sohbet yalnızca bir Federasyonda olabilir.
 • `/leavefed <fed_id>`*:*Federasyonu ver. Bunu yalnızca sohbet sahipleri yapabilir.
 • `/setfrules <kurallar>`*:* Federasyon kurallarını düzenleyin.
 • `/fednotif <on/off>`*:* fbaned /unfbaned kullanıcılar olduğunda Federasyon ayarları PM'de değil.
 • `/frules`*:* Federasyon düzenlemelerine bakınız.
 • `/fedadmins`*:* Federasyon yöneticisini göster.
 • `/fbanlist`*:* Şu anda Federasyonda mağdur olan tüm kullanıcıları görüntüler.
 • `/fedchats`*:* Federasyona bağlı tüm sohbetleri alın.\n""", parse_mode = ParseMode.MARKDOWN)
   
@run_async
def fed_user_help(bot: Bot, update: Update):
   update.effective_message.reply_text("""*🎩 Herhangi bir kullanıcı:*
• `/fbanstat`*:* Siz / veya yanıtladığınız kullanıcının veya kullanıcı adının bir yerlerde yasaklanıp yasaklanmadığını gösterir.
• `/chatfed `*:* Mevcut sohbette Federasyon'a bakın.\n""", parse_mode = ParseMode.MARKDOWN)   

__mod_name__ = "Federations"

__help__ = """
İstenmeyen posta gönderenler grubunuza girmeye başlayana ve onu engellemeniz gerekene kadar her şey eğlencelidir. O zaman daha fazla ve daha fazla yasaklamaya başlamanız gerekiyor ve acıyor.
Ama sonra birçok grubunuz var ve bu spam göndericinin gruplarınızdan birinde olmasını istemiyorsunuz - nasıl başa çıkabilirsiniz? Tüm gruplarınızda manuel olarak engellemeniz mi gerekiyor? \ N
* Artık yok! * Federasyon ile, diğer tüm sohbetlerle tek bir sohbet örtüşmesini yasaklayabilirsiniz.\n
Federasyon yöneticilerini bile atayabilirsiniz, böylece güvenilir yöneticiniz tüm spam göndericileri korumak istediğiniz sohbetlerden yasaklayabilir.\n

*Komutlar:*\n
Fed'ler artık rahatınız için 3 bölüme ayrılmıştır. 
• `/fedownerhelp`*:* fed oluşturma ve yalnızca sahip komutları için yardım sağlar.
• `/fedadminhelp`*:* fed yönetim komutları için yardım sağlar.
• `/feduserhelp`*:* Herkesin kullanabileceği komutlar için yardım sağlar.

"""

NEW_FED_HANDLER = CommandHandler("newfed", new_fed)
DEL_FED_HANDLER = CommandHandler("delfed", del_fed, pass_args=True)
JOIN_FED_HANDLER = CommandHandler("joinfed", join_fed, pass_args=True)
LEAVE_FED_HANDLER = CommandHandler("leavefed", leave_fed, pass_args=True)
PROMOTE_FED_HANDLER = CommandHandler("fpromote", user_join_fed, pass_args=True)
DEMOTE_FED_HANDLER = CommandHandler("fdemote", user_demote_fed, pass_args=True)
INFO_FED_HANDLER = CommandHandler("fedinfo", fed_info, pass_args=True)
BAN_FED_HANDLER = DisableAbleCommandHandler(["fban", "fedban"], fed_ban, pass_args=True)
UN_BAN_FED_HANDLER = CommandHandler("unfban", unfban, pass_args=True)
FED_BROADCAST_HANDLER = CommandHandler("fbroadcast", fed_broadcast, pass_args=True)
FED_SET_RULES_HANDLER = CommandHandler("setfrules", set_frules, pass_args=True)
FED_GET_RULES_HANDLER = CommandHandler("frules", get_frules, pass_args=True)
FED_CHAT_HANDLER = CommandHandler("chatfed", fed_chat, pass_args=True)
FED_ADMIN_HANDLER = CommandHandler("fedadmins", fed_admin, pass_args=True)
FED_USERBAN_HANDLER = CommandHandler("fbanlist", fed_ban_list, pass_args=True, pass_chat_data=True)
FED_NOTIF_HANDLER = CommandHandler("fednotif", fed_notif, pass_args=True)
FED_CHATLIST_HANDLER = CommandHandler("fedchats", fed_chats, pass_args=True)
FED_IMPORTBAN_HANDLER = CommandHandler("importfbans", fed_import_bans, pass_chat_data=True)
FEDSTAT_USER = DisableAbleCommandHandler(["fedstat", "fbanstat"], fed_stat_user, pass_args=True)
SET_FED_LOG = CommandHandler("setfedlog", set_fed_log, pass_args=True)
UNSET_FED_LOG = CommandHandler("unsetfedlog", unset_fed_log, pass_args=True)
SUBS_FED = CommandHandler("subfed", subs_feds, pass_args=True)
UNSUBS_FED = CommandHandler("unsubfed", unsubs_feds, pass_args=True)
MY_SUB_FED = CommandHandler("fedsubs", get_myfedsubs, pass_args=True)
MY_FEDS_LIST = CommandHandler("myfeds", get_myfeds_list)
DELETEBTN_FED_HANDLER = CallbackQueryHandler(del_fed_button, pattern=r"rmfed_")
FED_OWNER_HELP_HANDLER = CommandHandler("fedownerhelp", fed_owner_help)
FED_ADMIN_HELP_HANDLER = CommandHandler("fedadminhelp", fed_admin_help)
FED_USER_HELP_HANDLER = CommandHandler("feduserhelp", fed_user_help)

dispatcher.add_handler(NEW_FED_HANDLER)
dispatcher.add_handler(DEL_FED_HANDLER)
dispatcher.add_handler(JOIN_FED_HANDLER)
dispatcher.add_handler(LEAVE_FED_HANDLER)
dispatcher.add_handler(PROMOTE_FED_HANDLER)
dispatcher.add_handler(DEMOTE_FED_HANDLER)
dispatcher.add_handler(INFO_FED_HANDLER)
dispatcher.add_handler(BAN_FED_HANDLER)
dispatcher.add_handler(UN_BAN_FED_HANDLER)
dispatcher.add_handler(FED_BROADCAST_HANDLER)
dispatcher.add_handler(FED_SET_RULES_HANDLER)
dispatcher.add_handler(FED_GET_RULES_HANDLER)
dispatcher.add_handler(FED_CHAT_HANDLER)
dispatcher.add_handler(FED_ADMIN_HANDLER)
dispatcher.add_handler(FED_USERBAN_HANDLER)
dispatcher.add_handler(FED_NOTIF_HANDLER)
dispatcher.add_handler(FED_CHATLIST_HANDLER)
#dispatcher.add_handler(FED_IMPORTBAN_HANDLER)
dispatcher.add_handler(FEDSTAT_USER)
dispatcher.add_handler(SET_FED_LOG)
dispatcher.add_handler(UNSET_FED_LOG)
dispatcher.add_handler(SUBS_FED)
dispatcher.add_handler(UNSUBS_FED)
dispatcher.add_handler(MY_SUB_FED)
dispatcher.add_handler(MY_FEDS_LIST)
dispatcher.add_handler(DELETEBTN_FED_HANDLER)
dispatcher.add_handler(FED_OWNER_HELP_HANDLER)
dispatcher.add_handler(FED_ADMIN_HELP_HANDLER)
dispatcher.add_handler(FED_USER_HELP_HANDLER)
