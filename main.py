import os, threading, time
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "HE_TIME_BHO - 24h"

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot 24h ON! Sem conflito.\n\nManda a CHAPA 6 dígitos (ex: 062289):")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔄 Reset feito! Apagado.\n\nManda de novo a CHAPA 6 dígitos:")

async def post_init(app):
    await app.bot.delete_webhook(drop_pending_updates=True)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("reset", reset))
            print(">>> BOT COM /reset ATIVO")
            app.run_polling(drop_pending_updates=True, close_loop=False)
        except Exception as e:
            print(f"Erro {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
