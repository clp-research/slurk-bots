import json
from pathlib import Path

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters


class TGramClient:
    def __init__(self, token):
        self.app = ApplicationBuilder().token(token).build()

    async def login(self, update, context):
        await update.message.reply_text(f'Hello {update.effective_user.first_name}')

    
    async def echo(self, update, context):
        print(update)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

    def run(self):
        self.app.add_handler(CommandHandler("login", self.login))
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.echo))
        self.app.run_polling()


if __name__ == "__main__":
    tokens = json.loads(Path("TOKENS.json").read_text())
    bot = TGramClient(tokens["test"])
    bot.run()
