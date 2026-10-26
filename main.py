import os, threading, time, csv, datetime, calendar
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
ARQ_CAD = "cadastros.csv"
ARQ_HE = "base.csv"

for arq, header in [
    (ARQ_CAD, ["chapa","nome","sobrenome","telefone","id_telegram"]),
    (ARQ_HE, ["data_registro","chapa","nome","sobrenome","ba","data_inicio","data_fim","hora_inicio","hora_fim","total_horas","telefone"])
]:
    if not os.path.exists(arq):
        with open(arq, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)

CHAPA, NOME, SOBRENOME, TELEFONE, BA, DATA_INI, HORA_INI, MIN_INI, VIRADA, HORA_FIM, MIN_FIM = range(11)

def buscar_cadastro(chapa):
    try:
        with open(ARQ_CAD, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["chapa"] == chapa: return r
    except: pass
    return None

def salvar_cadastro(chapa, nome, sobrenome, telefone, tid):
    nome = nome.strip().upper()
    sobrenome = sobrenome.strip().upper()
    rows=[]
    try:
        with open(ARQ_CAD, encoding="utf-8") as f:
            rows=list(csv.DictReader(f))
    except: pass
    rows=[r for r in rows if r["chapa"]!=chapa]
    rows.append({"chapa":chapa,"nome":nome,"sobrenome":sobrenome,"telefone":telefone,"id_telegram":tid})
    with open(ARQ_CAD, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["chapa","nome","sobrenome","telefone","id_telegram"])
        w.writeheader(); w.writerows(rows)

def montar_calendario(ano, mes):
    hoje=datetime.date.today()
    limite_futuro=hoje+datetime.timedelta(days=1)
    limite_passado=hoje-datetime.timedelta(days=7)
    cal=calendar.monthcalendar(ano, mes)
    botoes=[]
    botoes.append([InlineKeyboardButton(f"📅 {calendar.month_name[mes]} {ano}", callback_data="IGNORE")])
    botoes.append([InlineKeyboardButton(d, callback_data="IGNORE") for d in ["S","T","Q","Q","S","S"]])
    for semana in cal:
        linha=[]
        for dia in semana:
            if dia==0:
                linha.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
            else:
                data_dia=datetime.date(ano, mes, dia)
                if data_dia>limite_futuro or data_dia<limite_passado:
                    linha.append(InlineKeyboardButton("🔒", callback_data="IGNORE"))
                else:
                    linha.append(InlineKeyboardButton(f"{dia}", callback_data=f"DAY_{ano:04d}-{mes:02d}-{dia:02d}"))
        botoes.append(linha)
    mes_ant=mes-1 if mes>1 else 12; ano_ant=ano if mes>1 else ano-1
    mes_prox=mes+1 if mes<12 else 1; ano_prox=ano if mes<12 else ano+1
    nav=[]
    nav.append(InlineKeyboardButton("◀️", callback_data=f"NAV_{ano_ant:04d}-{mes_ant:02d}"))
    nav.append(InlineKeyboardButton("Hoje", callback_data=f"NAV_{hoje.year:04d}-{hoje.month:02d}"))
    if datetime.date(ano_prox, mes_prox, 1)<=limite_futuro.replace(day=1):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"NAV_{ano_prox:04d}-{mes_prox:02d}"))
    else: nav.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
    botoes.append(nav)
    return InlineKeyboardMarkup(botoes)

app_flask=Flask(__name__)
@app_flask.route('/')
def home(): return "BOT ON"
@app_flask.route('/base')
def ver_base():
    inicio=request.args.get('inicio',''); fim=request.args.get('fim',''); chapa_f=request.args.get('chapa','')
    html=f"""<style>body{{font-family:Arial;padding:15px}} table{{border-collapse:collapse;width:100%;font-size:13px}} th{{background:#111;color:white;padding:8px}} td{{padding:6px;border:1px solid #ccc}}</style>
    <h2>BASE HE - NOMES EM MAIÚSCULO</h2><form method="get">Data Inicial: <input type="date" name="inicio" value="{inicio}"> Data Final: <input type="date" name="fim" value="{fim}"> CHAPA: <input type="text" name="chapa" value="{chapa_f}"><button>Filtrar</button> <a href="/base">Limpar</a></form><br>"""
    total_h=0; total_reg=0; linhas=[]
    try:
        with open(ARQ_HE, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if not r.get("data_inicio"): continue
                if chapa_f and chapa_f not in r.get("chapa",""): continue
                try:
                    d=datetime.datetime.strptime(r["data_inicio"], "%d/%m/%Y").date()
                    if inicio and d < datetime.datetime.strptime(inicio, "%Y-%m-%d").date(): continue
                    if fim and d > datetime.datetime.strptime(fim, "%Y-%m-%d").date(): continue
                except: pass
                linhas.append(r); total_reg+=1
                try: total_h+=float(str(r.get("total_horas","0")).replace(",","."))
                except: pass
    except Exception as e: html+=f"Erro: {e}<br>"
    html+=f"<b>Total: {total_reg} | Horas: {total_h:.2f}h</b><br><br><table><tr><th>Data Reg</th><th>Chapa</th><th>Nome Completo</th><th>BA</th><th>Data Início</th><th>Data Fim</th><th>Hora Início</th><th>Hora Fim</th><th>Total</th></tr>"
    for r in reversed(linhas[-500:]):
        nome = r.get('nome','').upper()
        sobre = r.get('sobrenome','').upper()
        html+=f"<tr><td>{r.get('data_registro','')}</td><td>{r.get('chapa','')}</td><td>{nome} {sobre}</td><td>{r.get('ba','')}</td><td>{r.get('data_inicio','')}</td><td>{r.get('data_fim','')}</td><td>{r.get('hora_inicio','')}</td><td>{r.get('hora_fim','')}</td><td>{r.get('total_horas','')}</td></tr>"
    html+="</table>"; return html

def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Envie sua CHAPA (6 dígitos)"); return CHAPA

async def chapa_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chapa=update.message.text.strip()
    if not (chapa.isdigit() and len(chapa)==6): await update.message.reply_text("CHAPA inválida. 6 dígitos:"); return CHAPA
    context.user_data["chapa"]=chapa
    cad=buscar_cadastro(chapa)
    if cad: 
        context.user_data.update(cad)
        context.user_data["nome"]=cad["nome"].upper()
        context.user_data["sobrenome"]=cad["sobrenome"].upper()
        await update.message.reply_text(f"Bem vinda {cad['nome'].upper()}! Envie BA 7 dígitos:"); return BA
    await update.message.reply_text("Seu NOME:"); return NOME

async def nome_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nome"]=update.message.text.strip().upper()
    await update.message.reply_text("Sobrenome:"); return SOBRENOME

async def sobrenome_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sobrenome"]=update.message.text.strip().upper()
    kb=[[KeyboardButton("📱 Compartilhar telefone", request_contact=True)]]
    await update.message.reply_text("Compartilhe telefone:", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)); return TELEFONE

async def telefone_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tel=update.message.contact.phone_number if update.message.contact else update.message.text.strip()
    context.user_data["telefone"]=tel
    salvar_cadastro(context.user_data["chapa"], context.user_data["nome"], context.user_data["sobrenome"], tel, str(update.effective_user.id))
    await update.message.reply_text(f"✅ Salvo! {context.user_data['nome']} {context.user_data['sobrenome']}\nAgora BA 7 dígitos:", reply_markup={"remove_keyboard": True}); return BA

async def ba_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ba=update.message.text.strip()
    if not (ba.isdigit() and len(ba)==7): await update.message.reply_text("BA inválido! 7 dígitos:"); return BA
    context.user_data["ba"]=ba; hoje=datetime.date.today()
    await update.message.reply_text(f"BA {ba} ok! Data Inicial (últimos 7 dias até amanhã):", reply_markup=montar_calendario(hoje.year, hoje.month)); return DATA_INI

async def calendario_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer()
    data=query.data
    if data.startswith("NAV_"): ano,mes=map(int,data.replace("NAV_","").split("-")); await query.edit_message_text("Data Inicial:", reply_markup=montar_calendario(ano, mes)); return DATA_INI
    if data.startswith("DAY_"): d=data.replace("DAY_",""); dt=datetime.datetime.strptime(d, "%Y-%m-%d"); context.user_data["data_inicio"]=dt.strftime("%d/%m/%Y"); kb=[]; [kb.append([InlineKeyboardButton(f"{h:02d}:00", callback_data=f"HINI_{h:02d}")]) for h in range(6,23)]; await query.edit_message_text(f"Data Inicial: {context.user_data['data_inicio']}\nHora INICIAL:", reply_markup=InlineKeyboardMarkup(kb)); return HORA_INI
    return DATA_INI

async def hora_ini_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); context.user_data["hora_ini"]=query.data.replace("HINI_","")
    kb=[[InlineKeyboardButton(f"{m:02d} min", callback_data=f"MINI_{m:02d}") for m in [0,10,20,30,40,50]]]
    await query.edit_message_text(f"Hora: {context.user_data['hora_ini']}h\nMinutos (10 em 10):", reply_markup=InlineKeyboardMarkup(kb)); return MIN_INI

async def min_ini_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); context.user_data["min_ini"]=query.data.replace("MINI_","")
    kb=[[InlineKeyboardButton("SIM - é virada", callback_data="VIRADA_SIM"), InlineKeyboardButton("NÃO - mesmo dia", callback_data="VIRADA_NAO")]]
    await query.edit_message_text(f"Início: {context.user_data['data_inicio']} {context.user_data['hora_ini']}:{context.user_data['min_ini']}\nÉ VIRADA?", reply_markup=InlineKeyboardMarkup(kb)); return VIRADA

async def virada_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); is_virada=query.data=="VIRADA_SIM"
    if is_virada: d_ini=datetime.datetime.strptime(context.user_data["data_inicio"], "%d/%m/%Y"); context.user_data["data_fim"]=(d_ini+datetime.timedelta(days=1)).strftime("%d/%m/%Y")
    else: context.user_data["data_fim"]=context.user_data["data_inicio"]
    kb=[]; [kb.append([InlineKeyboardButton(f"{h:02d}:00", callback_data=f"HFIM_{h:02d}")]) for h in range(0,24)]
    await query.edit_message_text(f"Data Fim: {context.user_data['data_fim']}\nHora FINAL:", reply_markup=InlineKeyboardMarkup(kb[:18])); return HORA_FIM

async def hora_fim_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); context.user_data["hora_fim"]=query.data.replace("HFIM_","")
    kb=[[InlineKeyboardButton(f"{m:02d} min", callback_data=f"MINF_{m:02d}") for m in [0,10,20,30,40,50]]]
    await query.edit_message_text("Minutos FINAL (10 em 10):", reply_markup=InlineKeyboardMarkup(kb)); return MIN_FIM

async def min_fim_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); context.user_data["min_fim"]=query.data.replace("MINF_","")
    try:
        di=datetime.datetime.strptime(f"{context.user_data['data_inicio']} {context.user_data['hora_ini']}:{context.user_data['min_ini']}", "%d/%m/%Y %H:%M")
        df=datetime.datetime.strptime(f"{context.user_data['data_fim']} {context.user_data['hora_fim']}:{context.user_data['min_fim']}", "%d/%m/%Y %H:%M")
        total=(df-di).total_seconds()/3600; 
        if total<=0: total+=24
    except: total=0
    context.user_data["total"]=f"{total:.2f}"
    nome=context.user_data.get("nome","").upper()
    sobrenome=context.user_data.get("sobrenome","").upper()
    mascara=f"✅ REGISTRO CONFIRMADO\n\n👤 {nome} {sobrenome}\n🪪 Chapa: {context.user_data['chapa']}\n📋 BA: {context.user_data['ba']}\n📅 Data Início: {context.user_data['data_inicio']}\n📅 Data Fim: {context.user_data['data_fim']}\n⏰ Hora Inicial: {context.user_data['hora_ini']}:{context.user_data['min_ini']}\n⏰ Hora Final: {context.user_data['hora_fim']}:{context.user_data['min_fim']}\n⏱️ Total: {context.user_data['total']}h\n"
    with open(ARQ_HE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), context.user_data["chapa"], nome, sobrenome, context.user_data["ba"], context.user_data["data_inicio"], context.user_data["data_fim"], f"{context.user_data['hora_ini']}:{context.user_data['min_ini']}", f"{context.user_data['hora_fim']}:{context.user_data['min_fim']}", context.user_data["total"], context.user_data.get("telefone","")])
    kb_final=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Cadastrar nova HE", callback_data="NOVA_HE")]])
    await query.edit_message_text(mascara, reply_markup=kb_final); return BA

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Seu ID é: {update.effective_user.id}")

async def reset_base_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id)
    if ADMIN_ID and uid!=ADMIN_ID: await update.message.reply_text("⛔ Você não é ADM!"); return
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ SIM, APAGAR BASE TODA", callback_data="RESET_CONFIRM")],[InlineKeyboardButton("❌ Cancelar", callback_data="RESET_CANCEL")]])
    await update.message.reply_text("⚠️ ADM: Apagar TODA a base HE?", reply_markup=kb)

async def reset_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer()
    uid=str(query.from_user.id)
    if ADMIN_ID and uid!=ADMIN_ID: await query.edit_message_text("⛔ Sem permissão"); return
    if query.data=="RESET_CONFIRM":
        with open(ARQ_HE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["data_registro","chapa","nome","sobrenome","ba","data_inicio","data_fim","hora_inicio","hora_fim","total_horas","telefone"])
        await query.edit_message_text("✅ BASE APAGADA!")
    else: await query.edit_message_text("❌ Cancelado")

async def nova_he_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); await query.message.reply_text("Envie o BA 7 dígitos:"); return BA

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado. /start"); return ConversationHandler.END

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            app=ApplicationBuilder().token(TOKEN).build()
            conv=ConversationHandler(
                entry_points=[CommandHandler("start", start)],
                states={
                    CHAPA: [MessageHandler(filters.TEXT & ~filters.COMMAND, chapa_step)],
                    NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nome_step)],
                    SOBRENOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sobrenome_step)],
                    TELEFONE: [MessageHandler(filters.ALL, telefone_step)],
                    BA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ba_step)],
                    DATA_INI: [CallbackQueryHandler(calendario_cb, pattern="^(NAV_|DAY_|IGNORE)")],
                    HORA_INI: [CallbackQueryHandler(hora_ini_cb, pattern="^HINI_")],
                    MIN_INI: [CallbackQueryHandler(min_ini_cb, pattern="^MINI_")],
                    VIRADA: [CallbackQueryHandler(virada_cb, pattern="^VIRADA_")],
                    HORA_FIM: [CallbackQueryHandler(hora_fim_cb, pattern="^HFIM_")],
                    MIN_FIM: [CallbackQueryHandler(min_fim_cb, pattern="^MINF_")],
                },
                fallbacks=[CommandHandler("cancel", cancel)],
            )
            app.add_handler(conv)
            app.add_handler(CommandHandler("id", id_cmd))
            app.add_handler(CommandHandler("reset_base", reset_base_cmd))
            app.add_handler(CallbackQueryHandler(reset_cb, pattern="^RESET_"))
            app.add_handler(CallbackQueryHandler(nova_he_cb, pattern="^NOVA_HE$"))
            print(">>> BOT FINAL MAIUSCULO")
            app.run_polling(drop_pending_updates=True)
        except Exception as e: print(f"CRASH: {e}"); time.sleep(5)

if __name__=="__main__": main()
