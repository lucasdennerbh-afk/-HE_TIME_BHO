import os
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# SEU TOKEN - pega nas Environment Variables do Render ou cola aqui direto
TOKEN = os.environ.get("BOT_TOKEN") or "COLOQUE_SEU_TOKEN_AQUI"

# --- FLASK PARA O RENDER NÃO DORMIR ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot 24h WEB rodando... ADM 062289 - LIVE"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    # Render precisa disso
    app_flask.run(host='0.0.0.0', port=port)

# --- SEU BOT ---
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ON 24h no Render! Pronto pra trabalhar.")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot rodando 100%. Me mande qualquer coisa.")

# COLE SEUS OUTROS COMANDOS AQUI EM CIMA DO main()

def main():
    # Inicia o Flask em segundo plano
    threading.Thread(target=run_flask, daemon=True).start()

    print("Iniciando bot...")
    
    # Cria o bot já derrubando qualquer outra sessão antiga (resolve o Conflict)
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", ajuda))
    
    # Se você tinha outros handlers, mantenha eles
    # Exemplo: app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, sua_funcao))

    # ESSA LINHA CORRIGE O ERRO QUE VOCÊ MANDOU NO PRINT
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
