from telegram.ext.dispatcher import run_async
from SaitamaRobot.modules.helper_funcs.chat_status import dev_plus
from telegram.ext import CommandHandler
from telegram import Bot, Update, ParseMode
from SaitamaRobot import dispatcher, LOGGER
import subprocess


@dev_plus
@run_async
def shell(bot: Bot, update: Update):
   message = update.effective_message
   cmd = message.text.split(' ', 1)
   if len(cmd) == 1:
     message.reply_text('Yürütme komutu verilmedi.')
     return
   cmd = cmd[1]
   process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
   stdout, stderr = process.communicate()
   reply = ''
   stderr = stderr.decode()
   stdout = stdout.decode()
   if stdout: 
      reply += f"*Stdout*\n`{stdout}`\n"
      LOGGER.info(f"Shell - {cmd} - {stdout}")
   if stderr: 
      reply +=  f"*Stderr*\n`{stderr}`\n"
      LOGGER.error(f"Shell - {cmd} - {stderr}")
   if len(reply) > 3000:
     with open('shell_output.txt', 'w') as file:
        file.write(reply)
     with open('shell_output.txt', 'rb') as doc:
        bot.send_document(
        document = doc,
        filename = f.name,
        reply_to_message_id = message.message_id,
        chat_id = message.chat_id
        )
   else:
     message.reply_text(reply, parse_mode = ParseMode.MARKDOWN)



SHELL_HANDLER = CommandHandler(['sh','shell', 'term', 'terminal'], shell)
dispatcher.add_handler(SHELL_HANDLER)
__mod_name__ = "Shell"
__command_list__ = ['sh','shell', 'term', 'terminal']
__handlers__ = [SHELL_HANDLER]
