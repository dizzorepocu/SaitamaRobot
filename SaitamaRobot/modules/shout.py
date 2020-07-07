from typing import List

from telegram import Update, Bot
from telegram.ext import run_async

from SaitamaRobot import dispatcher
from SaitamaRobot.modules.disable import DisableAbleCommandHandler


@run_async
def shout(bot: Bot, update: Update, args: List[str]):
    text = " ".join(args)
    result = []
    result.append(' '.join([s for s in text]))
    for pos, symbol in enumerate(text[1:]):
        result.append(symbol + ' ' + '  ' * pos + symbol)
    result = list("\n".join(result))
    result[0] = text[0]
    result = "".join(result)
    msg = "```\n" + result + "```"
    return update.effective_message.reply_text(msg, parse_mode="MARKDOWN")


__help__ = """
 Eğlenceli bir parça küçük ifade! Sohbet odasında yüksek sesle bağır.
 
 i.e `/shout HELP`, bot kare içinde büyük kodlu * YARDIM * harfleri ile cevaplar. 
 
 • `/shout <klavye>`*:* yüksek sesle vermek istediğiniz her şeyi yazın.
    ```
    t e s t
    e e
    s   s
    t     t
    ```
"""

SHOUT_HANDLER = DisableAbleCommandHandler("shout", shout, pass_args=True)

dispatcher.add_handler(SHOUT_HANDLER)

__mod_name__ = "Shout"
__command_list__ = ["shout"]
__handlers__ = [SHOUT_HANDLER]
