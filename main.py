import os, threading, time
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "HE_TIME_BHO - 24h ON - Sem Conflito"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

# --- COMANDOS DO BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot 24h ON! Sem conflito.\n\nPrimeiro acesso\nCHAPA 6 dígitos (ex: 062289):")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Limpa qualquer dado salvo do usuário
    context.user_data.clear()
    await update.message.reply_text("🔄 Reset feito! Dados apagados.\n\nManda de novo:\nCHAPA 6 dígitos (ex: 062289):")

async def post_init(app):
    await app.bot.delete_webhook(drop_pending_updates=True)
    print(">>> BOT PRONTO SEM CONFLITO")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            print(">>> Iniciando bot...")
            app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
            
            # Registra os 2 comandos
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("reset", reset))
            
            # Pega todas as mensagens que são chapa 6 dígitos também
            # (seu bot antigo fazia isso)
            
            app.run_polling(drop_pending_updates=True, close_loop=False)
        except Exception as e:
            print(f"Erro: {e} - reiniciando em 10s")
            time.sleep(10)

if __name__ == "__main__":
    main()
