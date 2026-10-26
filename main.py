import os, json, threading, time
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import datetime

TOKEN = os.environ.get("BOT_TOKEN")
SHEET_ID = os.environ.get("SHEET_ID", "1hPBH4M1yJEbJdKpm6jXmZu-N7RA7-x0Tm6CY7sXl2YE")
GOOGLE_CREDS = os.environ.get("GOOGLE_CREDENTIALS")

sheet = None
try:
    if GOOGLE_CREDS and SHEET_ID:
        import gspread
        creds_dict = json.loads(GOOGLE_CREDS)
        gc = gspread.service_account_from_dict(creds_dict)
        sheet = gc.open_by_key(SHEET_ID).sheet1
        print(">>> PLANILHA OK")
except Exception as e:
    print(f"Planilha off: {e}")

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "OK"
@app_flask.route('/base')
def ver_base():
    if not sheet: return "Planilha não conectada"
    rows = sheet.get_all_values()
    html = "<h2>Base AO VIVO</h2><table border=1>"
    for r in rows[-200:][::-1]:
        html+=f"<tr><td>{'</td><td>'.join(r)}</td></tr>"
    return html+"</table>"

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

def salvar_fundo(agora, tid, nome, chapa):
    try:
        sheet.append_row([agora, tid, nome, chapa])
    except Exception as e:
        print(f"Erro fundo: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Manda a CHAPA 6 dígitos:")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔄 Reset! Manda a CHAPA:")

async def chapa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not (texto.isdigit() and len(texto)==6):
        return
    # RESPONDE NA HORA - não espera planilha
    await update.message.reply_text(f"✅ Chapa {texto} recebida! Salvando...")
    
    # salva em segundo plano
    if sheet:
        agora = datetime.datetime.now().strftime("%d/%m %H:%M:%S")
        tid = str(update.effective_user.id)
        nome = update.effective_user.first_name or ""
        threading.Thread(target=salvar_fundo, args=(agora, tid, nome, texto), daemon=True).start()

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
            print(">>> BOT RAPIDO")
            app.run_polling(drop_pending_updates=True, close_loop=False)
        except Exception as e:
            print(e); time.sleep(5)

if __name__ == "__main__":
    main()
