import datetime
from typing import List

import requests
from telegram import Bot, Update, ParseMode
from telegram.ext import run_async

from SaitamaRobot import dispatcher, TIME_API_KEY
from SaitamaRobot.modules.disable import DisableAbleCommandHandler


def generate_time(to_find: str, findtype: List[str]) -> str:
    data = requests.get(f"http://api.timezonedb.com/v2.1/list-time-zone"
                        f"?key={TIME_API_KEY}"
                        f"&format=json"
                        f"&fields=countryCode,countryName,zoneName,gmtOffset,timestamp,dst").json()

    for zone in data["zones"]:
        for eachtype in findtype:
            if to_find in zone[eachtype].lower():
                country_name = zone['countryName']
                country_zone = zone['zoneName']
                country_code = zone['countryCode']

                if zone['dst'] == 1:
                    daylight_saving = "Yes"
                else:
                    daylight_saving = "No"

                date_fmt = r"%d-%m-%Y"
                time_fmt = r"%H:%M:%S"
                day_fmt = r"%A"
                gmt_offset = zone['gmtOffset']
                timestamp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=gmt_offset)
                current_date = timestamp.strftime(date_fmt)
                current_time = timestamp.strftime(time_fmt)
                current_day = timestamp.strftime(day_fmt)

                break

    try:
        result = (f"<b>Şehir :</b> <code>{country_name}</code>\n"
                  f"<b>Bölge Adı :</b> <code>{country_zone}</code>\n"
                  f"<b>Ülke Kodu :</b> <code>{country_code}</code>\n"
                  f"<b>Yaz saati uygulaması :</b> <code>{daylight_saving}</code>\n"
                  f"<b>Gün :</b> <code>{current_day}</code>\n"
                  f"<b>Şimdiki zaman :</b> <code>{current_time}</code>\n"
                  f"<b>Geçerli tarih :</b> <code>{current_date}</code>")
    except:
        result = None

    return result


@run_async
def gettime(bot: Bot, update: Update):
    message = update.effective_message

    try:
        query = message.text.strip().split(" ", 1)[1]
    except:
        message.reply_text("Bulmak için bir ülke adı /abbreviatio /timezone dilimi girin.")
        return
    send_message = message.reply_text(f"İçin saat dilimi bilgilerini bulma <b>{query}</b>", parse_mode=ParseMode.HTML)

    query_timezone = query.lower()
    if len(query_timezone) == 2:
        result = generate_time(query_timezone, ["countryCode"])
    else:
        result = generate_time(query_timezone, ["zoneName", "countryName"])

    if not result:
        send_message.edit_text(f"Saat dilimi bilgisi mevcut değil <b>{query}</b>", parse_mode=ParseMode.HTML)
        return

    send_message.edit_text(result, parse_mode=ParseMode.HTML)


__help__ = """
 • `/time <sorgu>`*:*Bir saat dilimi hakkında bilgi verir.

*Kullanılabilir sorgular:* Ülke Kodu / Ülke Adı / Saat Dilimi Adı
"""

TIME_HANDLER = DisableAbleCommandHandler("time", gettime)

dispatcher.add_handler(TIME_HANDLER)

__mod_name__ = "Time"
__command_list__ = ["time"]
__handlers__ = [TIME_HANDLER]
