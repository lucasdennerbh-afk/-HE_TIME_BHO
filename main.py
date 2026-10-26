import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Bot LIVE - HE_TIME_BHO"

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot 24h ON! Sem conflito.")

async def post_init(app):
    # ISSO AQUI MATA O OUTRO BOT E RESOLVE O CONFLICT
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deletado, conflito resolvido")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    
    print("Rodando polling com drop_pending_updates...")
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
