import os, threading, time, csv, datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
ARQ = "base.csv"

# Cria base se não existe
if not os.path.exists(ARQ):
    with open(ARQ, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["data", "id", "nome", "chapa"])

app_flask = Flask(__name__)

@app_flask.route('/')
def home(): return "BOT ON"

@app_flask.route('/base')
def ver_base():
    html = "<h2>BASE HE - AO VIVO</h2><table border=1><tr><th>Data</th><th>ID</th><th>Nome</th><th>Chapa</th></tr>"
    try:
        with open(ARQ, encoding="utf-8") as f:
            linhas = list(csv.reader(f))[1:]
            for r in reversed(linhas[-200:]):
                if len(r)>=4:
                    html+=f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"
    except:
        html+="<tr><td colspan=4>Vazia ainda</td></tr>"
    return html+"</table><br><a href='/base'>Atualizar</a>"

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ON!\nManda a CHAPA 6 dígitos:")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔄 Reset! Manda a chapa:")

async def chapa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not (texto.isdigit() and len(texto)==6):
        await update.message.reply_text("❌ Manda 6 números ex: 062289")
        return
    agora = datetime.datetime.now().strftime("%d/%m %H:%M:%S")
    tid = update.effective_user.id
    nome = update.effective_user.first_name or ""
    with open(ARQ, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([agora, tid, nome, texto])
    await update.message.reply_text(f"✅ Chapa {texto} salva!\nVeja em: https://he-time-bho.onrender.com/base")

async def post_init(app):
    await app.bot.delete_webhook(drop_pending_updates=True)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("reset", reset))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chapa))
            print(">>> BOT BASE LOCAL")
            app.run_polling(drop_pending_updates=True, close_loop=False)
        except Exception as e:
            print(e); time.sleep(5)

if __name__ == "__main__":
    main()
