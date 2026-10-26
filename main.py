import os, threading, time, csv, datetime, json
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
ARQ_CAD = "cadastros.csv"
ARQ_HE = "base.csv"

for arq, header in [(ARQ_CAD, ["chapa","nome","sobrenome","telefone","id_telegram"]), (ARQ_HE, ["data_registro","chapa","nome","sobrenome","ba","data_inicio","data_fim","hora_inicio","hora_fim","total_horas","telefone"])]:
    if not os.path.exists(arq):
        with open(arq, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)

# ESTADOS
CHAPA, NOME, SOBRENOME, TELEFONE, BA, DATA_INI, HORA_INI, MIN_INI, VIRADA, HORA_FIM, MIN_FIM = range(11)

def buscar_cadastro(chapa):
    try:
        with open(ARQ_CAD, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["chapa"] == chapa:
                    return r
    except: pass
    return None

def salvar_cadastro(chapa, nome, sobrenome, telefone, tid):
    # remove se ja existe
    rows = []
    try:
        with open(ARQ_CAD, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except: pass
    rows = [r for r in rows if r["chapa"] != chapa]
    rows.append({"chapa":chapa,"nome":nome,"sobrenome":sobrenome,"telefone":telefone,"id_telegram":tid})
    with open(ARQ_CAD, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["chapa","nome","sobrenome","telefone","id_telegram"])
        w.writeheader(); w.writerows(rows)

# FLASK COM FILTROS
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "BOT ON"
@app_flask.route('/base')
def ver_base():
    inicio = request.args.get('inicio','')
    fim = request.args.get('fim','')
    chapa_f = request.args.get('chapa','')
    html = f"""
    <h2>BASE HE - COM FILTROS</h2>
    <form method="get">
      Data Inicial: <input type="date" name="inicio" value="{inicio}">
      Data Final: <input type="date" name="fim" value="{fim}">
      CHAPA: <input type="text" name="chapa" value="{chapa_f}">
      <button>Filtrar</button> <a href="/base">Limpar</a>
    </form><br>
    """
    total_h = 0; total_reg=0; linhas=[]
    try:
        with open(ARQ_HE, encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            for r in reader:
                if chapa_f and chapa_f not in r["chapa"]: continue
                # filtro data
                try:
                    d = datetime.datetime.strptime(r["data_inicio"], "%d/%m/%Y").date()
                    if inicio and d < datetime.datetime.strptime(inicio, "%Y-%m-%d").date(): continue
                    if fim and d > datetime.datetime.strptime(fim, "%Y-%m-%d").date(): continue
                except: pass
                linhas.append(r)
                total_reg+=1
                try: total_h+=float(r["total_horas"])
                except: pass
    except Exception as e:
        html+=f"Erro: {e}"
    
    html+=f"<b>Total: {total_reg} | Total Horas: {total_h:.2f}h</b><br><br>"
    html+="<table border=1 cellpadding=5><tr><th>DataReg</th><th>Chapa</th><th>Nome</th><th>BA</th><th>Dt Ini</th><th>Dt Fim</th><th>Hr Ini</th><th>Hr Fim</th><th>Total</th></tr>"
    for r in reversed(linhas[-300:]):
        html+=f"<tr><td>{r['data_registro']}</td><td>{r['chapa']}</td><td>{r['nome']} {r['sobrenome']}</td><td>{r['ba']}</td><td>{r['data_inicio']}</td><td>{r['data_fim']}</td><td>{r['hora_inicio']}</td><td>{r['hora_fim']}</td><td>{r['total_horas']}</td></tr>"
    html+="</table>"
    return html

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# BOT FLUXO
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Primeiro acesso: me envie sua CHAPA (6 dígitos)")
    return CHAPA

async def chapa_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chapa = update.message.text.strip()
    if not (chapa.isdigit() and len(chapa)==6):
        await update.message.reply_text("CHAPA inválida. Envie 6 dígitos:")
        return CHAPA
    context.user_data["chapa"]=chapa
    cad = buscar_cadastro(chapa)
    if cad:
        context.user_data.update(cad)
        await update.message.reply_text(f"Bem vinda de volta {cad['nome']}! \nEnvie o BA com 7 dígitos (apenas números):")
        return BA
    await update.message.reply_text("Agora me diga seu NOME:")
    return NOME

async def nome_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nome"]=update.message.text.strip()
    await update.message.reply_text("Sobrenome:")
    return SOBRENOME

async def sobrenome_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sobrenome"]=update.message.text.strip()
    kb = [[KeyboardButton("Compartilhar telefone", request_contact=True)]]
    await update.message.reply_text("Compartilhe seu número:", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return TELEFONE

async def telefone_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tel = update.message.contact.phone_number if update.message.contact else update.message.text
    context.user_data["telefone"]=tel
    salvar_cadastro(context.user_data["chapa"], context.user_data["nome"], context.user_data["sobrenome"], tel, str(update.effective_user.id))
    await update.message.reply_text(f"Cadastro salvo! {context.user_data['nome']} {context.user_data['sobrenome']}\n\nAgora envie o BA (7 dígitos):", reply_markup={"remove_keyboard": True})
    return BA

async def ba_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ba = update.message.text.strip()
    if not (ba.isdigit() and len(ba)==7):
        await update.message.reply_text("BA inválido! Tem que ter 7 dígitos apenas números:")
        return BA
    context.user_data["ba"]=ba
    # calendario simples - botoes de datas
    hoje = datetime.date.today()
    botoes=[]
    for i in range(7):
        d = hoje + datetime.timedelta(days=i)
        botoes.append([InlineKeyboardButton(d.strftime("%d/%m/%Y"), callback_data=f"DATA_{d.strftime('%d/%m/%Y')}")])
    await update.message.reply_text("Escolha a DATA INICIAL (calendário):", reply_markup=InlineKeyboardMarkup(botoes))
    return DATA_INI

async def data_ini_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data.replace("DATA_","")
    context.user_data["data_inicio"]=data
    # hora inicial - de 10 em 10 min vai depois
    botoes = [[InlineKeyboardButton(f"{h:02d}h", callback_data=f"HINI_{h:02d}") for h in range(0,24,4)] for _ in range(1)]
    # simplificado: botoes horas
    kb=[]
    for h in range(6,23):
        kb.append([InlineKeyboardButton(f"{h:02d}:00", callback_data=f"HINI_{h:02d}")])
    await query.edit_message_text(f"Data Inicial: {data}\nEscolha HORA INICIAL:", reply_markup=InlineKeyboardMarkup(kb))
    return HORA_INI

async def hora_ini_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    h = query.data.replace("HINI_","")
    context.user_data["hora_ini"]=h
    # minutos 10 em 10
    kb = [[InlineKeyboardButton(f"{m:02d} min", callback_data=f"MINI_{m:02d}") for m in [0,10,20,30,40,50]]]
    await query.edit_message_text(f"Hora inicial: {h}h\nEscolha MINUTOS (10 em 10):", reply_markup=InlineKeyboardMarkup(kb))
    return MIN_INI

async def min_ini_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    m = query.data.replace("MINI_","")
    context.user_data["min_ini"]=m
    kb = [[InlineKeyboardButton("SIM - é virada", callback_data="VIRADA_SIM"), InlineKeyboardButton("NÃO - mesmo dia", callback_data="VIRADA_NAO")]]
    await query.edit_message_text(f"Início: {context.user_data['data_inicio']} {context.user_data['hora_ini']}:{m}\n\nÉ VIRADA? (passa da meia-noite?)", reply_markup=InlineKeyboardMarkup(kb))
    return VIRADA

async def virada_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    is_virada = query.data=="VIRADA_SIM"
    context.user_data["virada"]=is_virada
    if is_virada:
        d_ini = datetime.datetime.strptime(context.user_data["data_inicio"], "%d/%m/%Y")
        d_fim = d_ini + datetime.timedelta(days=1)
        context.user_data["data_fim"]=d_fim.strftime("%d/%m/%Y")
    else:
        context.user_data["data_fim"]=context.user_data["data_inicio"]
    
    kb=[]
    for h in range(0,24):
        kb.append([InlineKeyboardButton(f"{h:02d}:00", callback_data=f"HFIM_{h:02d}")])
    await query.edit_message_text(f"Data Fim automática: {context.user_data['data_fim']}\n\nEscolha HORA FINAL:", reply_markup=InlineKeyboardMarkup(kb[:12]))
    return HORA_FIM

async def hora_fim_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    context.user_data["hora_fim"]=query.data.replace("HFIM_","")
    kb = [[InlineKeyboardButton(f"{m:02d} min", callback_data=f"MINF_{m:02d}") for m in [0,10,20,30,40,50]]]
    await query.edit_message_text("Escolha MINUTOS FINAL (10 em 10):", reply_markup=InlineKeyboardMarkup(kb))
    return MIN_FIM

async def min_fim_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    context.user_data["min_fim"]=query.data.replace("MINF_","")
    
    # calcula total
    try:
        di = datetime.datetime.strptime(f"{context.user_data['data_inicio']} {context.user_data['hora_ini']}:{context.user_data['min_ini']}", "%d/%m/%Y %H:%M")
        df = datetime.datetime.strptime(f"{context.user_data['data_fim']} {context.user_data['hora_fim']}:{context.user_data['min_fim']}", "%d/%m/%Y %H:%M")
        total = (df - di).total_seconds()/3600
        if total <0: total+=24
    except:
        total=0
    context.user_data["total"]=f"{total:.2f}"

    # MASCARA FINAL
    nome = context.user_data.get("nome",""); sobrenome=context.user_data.get("sobrenome","")
    mascara = f"""
✅ **REGISTRO CONFIRMADO**

👤 {nome} {sobrenome}
🪪 Chapa: {context.user_data['chapa']}
📞 {context.user_data.get('telefone','')}

📋 BA: {context.user_data['ba']}
📅 Início: {context.user_data['data_inicio']} às {context.user_data['hora_ini']}:{context.user_data['min_ini']}
📅 Fim: {context.user_data['data_fim']} às {context.user_data['hora_fim']}:{context.user_data['min_fim']}
⏱️ Total: {context.user_data['total']} horas
"""
    # salva
    with open(ARQ_HE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            context.user_data["chapa"], nome, sobrenome,
            context.user_data["ba"],
            context.user_data["data_inicio"], context.user_data["data_fim"],
            f"{context.user_data['hora_ini']}:{context.user_data['min_ini']}",
            f"{context.user_data['hora_fim']}:{context.user_data['min_fim']}",
            context.user_data["total"],
            context.user_data.get("telefone","")
        ])
    
    await query.edit_message_text(mascara)
    await query.message.reply_text("Para lançar outra HE, envie o BA com 7 dígitos")
    return BA

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado. /start para recomeçar")
    return ConversationHandler.END

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            app = ApplicationBuilder().token(TOKEN).build()
            conv = ConversationHandler(
                entry_points=[CommandHandler("start", start)],
                states={
                    CHAPA: [MessageHandler(filters.TEXT & ~filters.COMMAND, chapa_step)],
                    NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nome_step)],
                    SOBRENOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sobrenome_step)],
                    TELEFONE: [MessageHandler(filters.ALL, telefone_step)],
                    BA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ba_step)],
                    DATA_INI: [CallbackQueryHandler(data_ini_cb, pattern="^DATA_")],
                    HORA_INI: [CallbackQueryHandler(hora_ini_cb, pattern="^HINI_")],
                    MIN_INI: [CallbackQueryHandler(min_ini_cb, pattern="^MINI_")],
                    VIRADA: [CallbackQueryHandler(virada_cb, pattern="^VIRADA_")],
                    HORA_FIM: [CallbackQueryHandler(hora_fim_cb, pattern="^HFIM_")],
                    MIN_FIM: [CallbackQueryHandler(min_fim_cb, pattern="^MINF_")],
                },
                fallbacks=[CommandHandler("cancel", cancel)],
                per_message=False
            )
            app.add_handler(conv)
            print(">>> BOT FLUXO COMPLETO")
            app.run_polling(drop_pending_updates=True, close_loop=False)
        except Exception as e:
            print(f"CRASH: {e}"); time.sleep(5)

if __name__=="__main__":
    main()
