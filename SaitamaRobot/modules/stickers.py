import hashlib
import math
import os
import urllib.request as urllib
from typing import List

from PIL import Image
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import TelegramError
from telegram import Update, Bot
from telegram.ext import run_async
from telegram.utils.helpers import escape_markdown

from SaitamaRobot import dispatcher
from SaitamaRobot.modules.disable import DisableAbleCommandHandler


@run_async
def stickerid(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        update.effective_message.reply_text("Sticker ID:\n```" +
                                            escape_markdown(msg.reply_to_message.sticker.file_id) + "```",
                                            parse_mode=ParseMode.MARKDOWN)
    else:
        update.effective_message.reply_text("Kimliğini almak için lütfen bir çıkartmayı yanıtlayın.")


@run_async
def getsticker(bot: Bot, update: Update):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        file_id = msg.reply_to_message.sticker.file_id
        new_file = bot.get_file(file_id)
        new_file.download('sticker.png')
        bot.send_document(chat_id, document=open('sticker.png', 'rb'))
        os.remove("sticker.png")
    else:
        update.effective_message.reply_text("Lütfen PNG'sini yüklemem için bir çıkartmaya yanıt verin.")


@run_async
def kang(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    user = update.effective_user
    _hash = hashlib.sha1(bytearray(user.id)).hexdigest()
    packname = "a" + _hash[:20] + "_by_" + bot.username
    kangsticker = "kangsticker.png"
    if msg.reply_to_message:
        if msg.reply_to_message.sticker:
            file_id = msg.reply_to_message.sticker.file_id
        elif msg.reply_to_message.photo:
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.document:
            file_id = msg.reply_to_message.document.file_id
        kang_file = bot.get_file(file_id)
        kang_file.download('kangsticker.png')
        if args:
            sticker_emoji = str(args[0])
        elif msg.reply_to_message.sticker and msg.reply_to_message.sticker.emoji:
            sticker_emoji = msg.reply_to_message.sticker.emoji
        else:
            sticker_emoji = "🤔"
        try:
            im = Image.open(kangsticker)
            maxsize = (512, 512)
            if (im.width and im.height) < 512:
                size1 = im.width
                size2 = im.height
                if im.width > im.height:
                    scale = 512 / size1
                    size1new = 512
                    size2new = size2 * scale
                else:
                    scale = 512 / size2
                    size1new = size1 * scale
                    size2new = 512
                size1new = math.floor(size1new)
                size2new = math.floor(size2new)
                sizenew = (size1new, size2new)
                im = im.resize(sizenew)
            else:
                im.thumbnail(maxsize)
            if not msg.reply_to_message.sticker:
                im.save(kangsticker, "PNG")
            with open('kangsticker.png', 'rb') as sticker:
                bot.add_sticker_to_set(user_id=user.id, name=packname,
                                       png_sticker=sticker, emojis=sticker_emoji)
            msg.reply_text(f"Etiket başarıyla eklendi [pack](t.me/addstickers/{packname})\n"
                           f"Emoji is:" + " " + sticker_emoji,
                           parse_mode=ParseMode.MARKDOWN)
        except OSError as e:
            msg.reply_text("Ben sadece kang görüntüleri m8.")
            print(e)
            return
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                with open('kangsticker.png', 'rb') as sticker:
                    makepack_internal(msg, user, sticker, sticker_emoji, bot)
            elif e.message == "Sticker_png_dimensions":
                im.save(kangsticker, "PNG")
                with open('kangsticker.png', 'rb') as sticker:
                    bot.add_sticker_to_set(user_id=user.id, name=packname,
                                           png_sticker=sticker, emojis=sticker_emoji)
                msg.reply_text(f"Etiket başarıyla eklendi [pack](t.me/addstickers/{packname})\n"
                               f"Emoji is: {sticker_emoji}",
                               parse_mode=ParseMode.MARKDOWN)
            elif e.message == "Geçersiz etiket emojileri":
                msg.reply_text("Geçersiz emoji(s).")
            elif e.message == "Stickers_too_much":
                msg.reply_text("Maksimum paket boyutuna ulaşıldı. İlgili ödemeyi yapmak için F tuşuna basın.")
            print(e)
    elif args:
        try:
            try:
                urlemoji = msg.text.split(" ")
                png_sticker = urlemoji[1]
                sticker_emoji = urlemoji[2]
            except IndexError:
                sticker_emoji = "🤔"
            urllib.urlretrieve(png_sticker, kangsticker)
            im = Image.open(kangsticker)
            maxsize = (512, 512)
            if (im.width and im.height) < 512:
                size1 = im.width
                size2 = im.height
                if im.width > im.height:
                    scale = 512 / size1
                    size1new = 512
                    size2new = size2 * scale
                else:
                    scale = 512 / size2
                    size1new = size1 * scale
                    size2new = 512
                size1new = math.floor(size1new)
                size2new = math.floor(size2new)
                sizenew = (size1new, size2new)
                im = im.resize(sizenew)
            else:
                im.thumbnail(maxsize)
            im.save(kangsticker, "PNG")
            with open('kangsticker.png', 'rb') as sticker:
                msg.reply_photo(photo=sticker)
            with open('kangsticker.png', 'rb') as sticker:
                bot.add_sticker_to_set(user_id=user.id, name=packname,
                                       png_sticker=sticker, emojis=sticker_emoji)
            msg.reply_text(
                f"Etiket başarıyla eklendi [pack](t.me/addstickers/{packname})\n"
                f"Emoji is: {sticker_emoji}",
                parse_mode=ParseMode.MARKDOWN)
        except OSError as e:
            msg.reply_text("Ben sadece kang görüntüleri m8.")
            print(e)
            return
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                with open('kangsticker.png', 'rb') as sticker:
                    makepack_internal(msg, user, sticker, sticker_emoji, bot)
            elif e.message == "Sticker_png_dimensions":
                msg.reply_text("Görüntü doğru boyutlara göre yeniden boyutlandırılamadı.")
            elif e.message == "Geçersiz etiket emojileri":
                msg.reply_text("Geçersiz emoji(s).")
            print(e)
    else:
        msg.reply_text(
            f"Lütfen bir çıkartmaya veya kang için resme cevap verin!\n"
            f"Oh, bu arada. Paketiniz bulunabilir [here](t.me/addstickers/{packname})",
            parse_mode=ParseMode.MARKDOWN)
    if os.path.isfile("kangsticker.png"):
        im.close()
        os.remove("kangsticker.png")


def makepack_internal(msg, user, png_sticker, emoji, bot):
    name = user.first_name
    name = name[:50]
    hash = hashlib.sha1(bytearray(user.id)).hexdigest()
    packname = f"a{hash[:20]}_by_{bot.username}"
    try:
        success = bot.create_new_sticker_set(user.id, packname, name + "'s kang pack",
                                             png_sticker=png_sticker,
                                             emojis=emoji)
    except TelegramError as e:
        print(e)
        if e.message == "Etiket kümesi adı zaten dolu":
            msg.reply_text(f"Paketiniz bulunabilir [here](t.me/addstickers/{packname})",
                           parse_mode=ParseMode.MARKDOWN)
        elif e.message == "Peer_id_invalid":
            msg.reply_text("Önce PM'de bana ulaşın.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                text="Start", url=f"t.me/{bot.username}")]]))
        return

    if success:
        msg.reply_text(f"Çıkartma paketi başarıyla oluşturuldu. Anla [here](t.me/addstickers/{packname})",
                       parse_mode=ParseMode.MARKDOWN)
    else:
        msg.reply_text("Çıkartma paketi oluşturulamadı. Muhtemelen blek mejik nedeniyle.")


__help__ = """
• `/stickerid`*:* bana dosya kimliğini söylemek için bir çıkartmaya cevap ver.
• `/getsticker`*:* ham PNG dosyasını yüklemek için bana bir çıkartmayı yanıtla.
• `/kang`*:* paketinize eklemek için bir etikete cevap verin.
"""

__mod_name__ = "Stickers"
STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)
KANG_HANDLER = DisableAbleCommandHandler("kang", kang, pass_args=True, admin_ok=True)

dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
dispatcher.add_handler(KANG_HANDLER)
