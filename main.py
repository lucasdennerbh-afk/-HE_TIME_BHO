import os, threading, time, csv, datetime
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
ARQ = "base.csv"

if not os.path.exists(ARQ):
    with open(ARQ, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["data_hora", "id", "nome", "chapa", "horas"])

app_flask = Flask(__name__)

@app_flask.route('/')
def home(): return "BOT ON"

@app_flask.route('/base')
def ver_base():
    inicio = request.args.get('inicio', '') # formato 2026-05-12
    fim = request.args.get('fim', '')
    chapa_filtro = request.args.get('chapa', '')

    html = """
    <h2>BASE HE - PAINEL COM FILTROS</h2>
    <form method="get">
      Data Inicial: <input type="date" name="inicio" value="{inicio}">
      Data Final: <input type="date" name="fim" value="{fim}">
      CHAPA: <input type="text" name="chapa" placeholder="062289" value="{chapa_filtro}">
      <button type="submit">Filtrar</button> <a href="/base">Limpar</a>
    </form><br>
    """.format(inicio=inicio, fim=fim, chapa_filtro=chapa_filtro)

    total_reg = 0
    total_horas = 0
    linhas_filtradas = []

    try:
        with open(ARQ, encoding="utf-8") as f:
            reader = list(csv.reader(f))
            for r in reader[1:]:
                if len(r) < 4: continue
                data_str, id_, nome, chapa = r[0], r[1], r[2], r[3]
                horas = float(r[4]) if len(r)>4 and r[4] else 1 # cada registro = 1h, muda aqui se quiser
                
                # Filtro CHAPA
                if chapa_filtro and chapa_filtro not in chapa:
                    continue
                
                # Filtro DATA - converte dd/mm para comparar
                try:
                    data_obj = datetime.datetime.strptime(data_str.split()[0], "%d/%m/%Y" if "/" in data_str.split()[0] else "%d/%m")
                except:
                    try:
                        data_obj = datetime.datetime.strptime(data_str[:10], "%Y-%m-%d")
                    except:
                        data_obj = None
                
                if inicio and data_obj:
                    if data_obj.date() < datetime.datetime.strptime(inicio, "%Y-%m-%d").date():
                        continue
                if fim and data_obj:
                    if data_obj.date() > datetime.datetime.strptime(fim, "%Y-%m-%d").date():
                        continue

                linhas_filtradas.append(r)
                total_reg += 1
                total_horas += horas
    except Exception as e:
        html+=f"Erro ler base: {e}<br>"

    html+=f"<b>Total filtrado: {total_reg} registros | Total Horas Executadas: {total_horas:.2f}h</b><br><br>"
    html+="<table border=1 cellpadding=5><tr><th>Data</th><th>ID</th><th>Nome</th><th>Chapa</th><th>Horas</th></tr>"
    for r in reversed(linhas_filtradas[-300:]):
        html+=f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4] if len(r)>4 else 1}</td></tr>"
    html+="</table>"
    return html

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Manda a CHAPA 6 dígitos:")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔄 Reset!")

async def chapa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    # Aceita formato: 062289 ou 062289 2.5 (chapa + horas)
    partes = texto.split()
    chapa_num = partes[0]
    horas = partes[1] if len(partes)>1 else "1"
    if not (chapa_num.isdigit() and len(chapa_num)==6):
        await update.message.reply_text("❌ Ex: 062289 ou 062289 2.5")
        return
    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(ARQ, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([agora, update.effective_user.id, update.effective_user.first_name, chapa_num, horas])
    await update.message.reply_text(f"✅ Chapa {chapa_num} | {horas}h salva!")

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
            app.run_polling(drop_pending_updates=True, close_loop=False)
        except Exception as e:
            print(e); time.sleep(5)

if __name__ == "__main__":
    main()
