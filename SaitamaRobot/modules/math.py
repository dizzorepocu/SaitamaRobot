from typing import List
import requests
from telegram import Message, Update, Bot, MessageEntity
from telegram.ext import CommandHandler, run_async
from SaitamaRobot import dispatcher
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
import pynewtonmath as newton
import math

@run_async
def simplify(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    message.reply_text(newton.simplify('{}'.format(args[0])))

@run_async
def factor(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    message.reply_text(newton.factor('{}'.format(args[0])))

@run_async
def derive(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    message.reply_text(newton.derive('{}'.format(args[0])))

@run_async
def integrate(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    message.reply_text(newton.integrate('{}'.format(args[0])))

@run_async
def zeroes(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    message.reply_text(newton.zeroes('{}'.format(args[0])))

@run_async
def tangent(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    message.reply_text(newton.tangent('{}'.format(args[0])))

@run_async
def area(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    message.reply_text(newton.area('{}'.format(args[0])))

@run_async
def cos(bot: Bot, update: Update, args):
    message = update.effective_message
    message.reply_text(math.cos(int(args[0])))

@run_async
def sin(bot: Bot, update: Update, args):
    message = update.effective_message
    message.reply_text(math.sin(int(args[0])))

@run_async
def tan(bot: Bot, update: Update, args):
    message = update.effective_message
    message.reply_text(math.tan(int(args[0])))

@run_async
def arccos(bot: Bot, update: Update, args):
    message = update.effective_message
    message.reply_text(math.acos(int(args[0])))

@run_async
def arcsin(bot: Bot, update: Update, args):
    message = update.effective_message
    message.reply_text(math.asin(int(args[0])))

@run_async
def arctan(bot: Bot, update: Update, args):
    message = update.effective_message
    message.reply_text(math.atan(int(args[0])))

@run_async
def abs(bot: Bot, update: Update, args):
    message = update.effective_message
    message.reply_text(math.fabs(int(args[0])))

@run_async
def log(bot: Bot, update: Update, args):
    message = update.effective_message
    message.reply_text(math.log(int(args[0])))

__help__ = """
Karmaşık matematik problemlerini kullanarak çözer https://newton.now.sh
 • `/math`*:* basitleştirin `/simplify 2^2+2(2)`
 • `/factor`*:* faktör `/factor x^2 + 2x`
 • `/derive`*:* Derive `/derive x^2+2x`
 • `/integrate`*:* Birleştirmek `/integrate x^2+2x`
 • `/zeroes`*:* Ara 0's `/zeroes x^2+2x`
 • `/tangent`*:* Teğet Bul`/tangent 2lx^3`
 • `/area`*:* Eğri Altındaki Alan `/area 2:4lx^3`
 • `/cos`*:* Kosinüs `/cos pi`
 • `/sin`*:* Sinüs `/sin 0`
 • `/tan`*:* Teğet `/tan 0`
 • `/arccos`*:* Ters Kosinüs `/arccos 1`
 • `/arcsin`*:* Ters Sinüs `/arcsin 0`
 • `/arctan`*:* Ters Teğet `/arctan 0`
 • `/abs`*:* Mutlak değer `/abs -1`
 • `/log`*:* logaritma `/log 2l8`

_Unutmayın_: Bir işlevin belirli bir x değerinde teğet satırını bulmak için, isteği c | f (x) olarak gönderin; burada c verilen x değeri ve f (x) işlev ifadesidir, ayırıcı dikeydir çubuğu '|'. Örnek bir istek için yukarıdaki tabloya bakın.
Bir işlevin altındaki alanı bulmak için, isteği c: d | f (x) olarak gönderin; burada c, başlangıç ​​x değeri, d bitiş x değeridir ve f (x), altında eğrinin olmasını istediğiniz işlevdir iki x değeri.
Kesirleri hesaplamak için ifadeleri pay (üst) payda olarak girin. Örneğin, 2/4 işlemek için ifadenizi 2 (üzerinden) 4 olarak göndermeniz gerekir. Sonuç ifadesi standart matematik gösteriminde olacaktır (1/2, 3/4).
"""

__mod_name__ = "Math"

SIMPLIFY_HANDLER = DisableAbleCommandHandler("math", simplify, pass_args=True)
FACTOR_HANDLER = DisableAbleCommandHandler("factor", factor, pass_args=True)
DERIVE_HANDLER = DisableAbleCommandHandler("derive", derive, pass_args=True)
INTEGRATE_HANDLER = DisableAbleCommandHandler("integrate", integrate, pass_args=True)
ZEROES_HANDLER = DisableAbleCommandHandler("zeroes", zeroes, pass_args=True)
TANGENT_HANDLER = DisableAbleCommandHandler("tangent", tangent, pass_args=True)
AREA_HANDLER = DisableAbleCommandHandler("area", area, pass_args=True)
COS_HANDLER = DisableAbleCommandHandler("cos", cos, pass_args=True)
SIN_HANDLER = DisableAbleCommandHandler("sin", sin, pass_args=True)
TAN_HANDLER = DisableAbleCommandHandler("tan", tan, pass_args=True)
ARCCOS_HANDLER = DisableAbleCommandHandler("arccos", arccos, pass_args=True)
ARCSIN_HANDLER = DisableAbleCommandHandler("arcsin", arcsin, pass_args=True)
ARCTAN_HANDLER = DisableAbleCommandHandler("arctan", arctan, pass_args=True)
ABS_HANDLER = DisableAbleCommandHandler("abs", abs, pass_args=True)
LOG_HANDLER = DisableAbleCommandHandler("log", log, pass_args=True)

dispatcher.add_handler(SIMPLIFY_HANDLER)
dispatcher.add_handler(FACTOR_HANDLER)
dispatcher.add_handler(DERIVE_HANDLER)
dispatcher.add_handler(INTEGRATE_HANDLER)
dispatcher.add_handler(ZEROES_HANDLER)
dispatcher.add_handler(TANGENT_HANDLER) 
dispatcher.add_handler(AREA_HANDLER)
dispatcher.add_handler(COS_HANDLER)
dispatcher.add_handler(SIN_HANDLER)
dispatcher.add_handler(TAN_HANDLER)
dispatcher.add_handler(ARCCOS_HANDLER)
dispatcher.add_handler(ARCSIN_HANDLER)
dispatcher.add_handler(ARCTAN_HANDLER)
dispatcher.add_handler(ABS_HANDLER)
dispatcher.add_handler(LOG_HANDLER)
