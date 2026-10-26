import os, threading, time, csv, datetime, calendar
from flask import Flask, request, send_file
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
ARQ_CAD = "cadastros.csv"
ARQ_HE = "base.csv"
ARQ_FUNC = "funcionarios.csv"

for arq, header in [
    (ARQ_CAD, ["chapa","nome","sobrenome","telefone","id_telegram"]),
    (ARQ_HE, ["data_registro","chapa","nome","sobrenome","ba","data_inicio","data_fim","hora_inicio","hora_fim","total_horas","status_intervalo","data_confirmacao","telefone"]),
]:
    if not os.path.exists(arq):
        with open(arq, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)

CHAPA, NOME, SOBRENOME, TELEFONE, BA, DATA_INI, HORA_INI, MIN_INI, VIRADA, HORA_FIM, MIN_FIM = range(11)

def buscar_nome_na_base_mestra(chapa):
    try:
        chapa_6 = str(chapa).strip().zfill(6)
        chapa_sem_zero = str(int(chapa)) if str(chapa).strip().isdigit() else str(chapa).strip()
        with open(ARQ_FUNC, encoding="utf-8-sig") as f:
            primeira_linha = f.readline()
            f.seek(0)
            delim = ";" if ";" in primeira_linha else ","
            reader = csv.DictReader(f, delimiter=delim)
            if reader.fieldnames:
                reader.fieldnames = [c.strip().lower().replace(" ", "_").replace("\ufeff","") for c in reader.fieldnames]
            chapa_col = "chapa" if "chapa" in reader.fieldnames else reader.fieldnames[0]
            nome_col = "nome_completo" if "nome_completo" in reader.fieldnames else ("funcionario" if "funcionario" in reader.fieldnames else reader.fieldnames[1])
            for r in reader:
                val_chapa = str(r.get(chapa_col,"")).strip()
                if not val_chapa or val_chapa.lower() == "none": continue
                c = val_chapa.zfill(6)
                if c == chapa_6 or val_chapa == str(chapa).strip() or val_chapa == chapa_sem_zero:
                    nome_full = str(r.get(nome_col,"")).strip().upper()
                    if not nome_full or nome_full == "NONE": continue
                    partes = nome_full.split()
                    primeiro = partes[0] if partes else nome_full
                    resto = " ".join(partes[1:]) if len(partes)>1 else ""
                    return primeiro, resto, nome_full
    except Exception as e:
        print(f"Erro base mestra: {e}")
    return None

def buscar_cadastro(chapa):
    try:
        with open(ARQ_CAD, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["chapa"] == chapa: return r
    except: pass
    return None

def salvar_cadastro(chapa, nome, sobrenome, telefone, tid):
    nome = nome.strip().upper(); sobrenome = sobrenome.strip().upper()
    rows=[]
    try:
        with open(ARQ_CAD, encoding="utf-8") as f: rows=list(csv.DictReader(f))
    except: pass
    rows=[r for r in rows if r["chapa"]!=chapa]
    rows.append({"chapa":chapa,"nome":nome,"sobrenome":sobrenome,"telefone":telefone,"id_telegram":tid})
    with open(ARQ_CAD, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["chapa","nome","sobrenome","telefone","id_telegram"]); w.writeheader(); w.writerows(rows)

def atualizar_confirmacao_na_base(chapa):
    try:
        with open(ARQ_HE, encoding="utf-8") as f:
            rows=list(csv.DictReader(f))
        agora=datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for i in range(len(rows)-1, -1, -1):
            if rows[i]["chapa"]==chapa and rows[i].get("status_intervalo")=="PENDENTE":
                rows[i]["status_intervalo"]="CONFIRMADO"
                rows[i]["data_confirmacao"]=agora
                break
        with open(ARQ_HE, "w", newline="", encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["data_registro","chapa","nome","sobrenome","ba","data_inicio","data_fim","hora_inicio","hora_fim","total_horas","status_intervalo","data_confirmacao","telefone"])
            w.writeheader(); w.writerows(rows)
        return True
    except: return False

def apagar_chapa_da_base(chapa_alvo):
    try:
        chapa_alvo = str(chapa_alvo).strip().zfill(6)
        with open(ARQ_HE, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        antes = len(rows)
        rows_filtradas = [r for r in rows if str(r.get("chapa","")).strip().zfill(6) != chapa_alvo]
        depois = len(rows_filtradas)
        with open(ARQ_HE, "w", newline="", encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["data_registro","chapa","nome","sobrenome","ba","data_inicio","data_fim","hora_inicio","hora_fim","total_horas","status_intervalo","data_confirmacao","telefone"])
            w.writeheader(); w.writerows(rows_filtradas)
        return antes - depois
    except Exception as e:
        print(f"Erro apagar chapa: {e}")
        return -1

def montar_calendario(ano, mes):
    calendar.setfirstweekday(calendar.SUNDAY)
    hoje=datetime.date.today(); limite_futuro=hoje+datetime.timedelta(days=1); limite_passado=hoje-datetime.timedelta(days=7)
    cal=calendar.monthcalendar(ano, mes); botoes=[]
    botoes.append([InlineKeyboardButton(f"📅 {calendar.month_name[mes]} {ano}", callback_data="IGNORE")])
    botoes.append([InlineKeyboardButton(d, callback_data="IGNORE") for d in ["D","S","T","Q","Q","S","S"]])
    for semana in cal:
        linha=[]
        for dia in semana:
            if dia==0: linha.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
            else:
                data_dia=datetime.date(ano, mes, dia)
                if data_dia>limite_futuro or data_dia<limite_passado: linha.append(InlineKeyboardButton("🔒", callback_data="IGNORE"))
                else: linha.append(InlineKeyboardButton(f"{dia}", callback_data=f"DAY_{ano:04d}-{mes:02d}-{dia:02d}"))
        botoes.append(linha)
    mes_ant=mes-1 if mes>1 else 12; ano_ant=ano if mes>1 else ano-1
    mes_prox=mes+1 if mes<12 else 1; ano_prox=ano if mes<12 else ano+1
    nav=[InlineKeyboardButton("◀️", callback_data=f"NAV_{ano_ant:04d}-{mes_ant:02d}"), InlineKeyboardButton("Hoje", callback_data=f"NAV_{hoje.year:04d}-{hoje.month:02d}")]
    if datetime.date(ano_prox, mes_prox, 1)<=limite_futuro.replace(day=1): nav.append(InlineKeyboardButton("▶️", callback_data=f"NAV_{ano_prox:04d}-{mes_prox:02d}"))
    else: nav.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
    botoes.append(nav); return InlineKeyboardMarkup(botoes)

app_flask=Flask(__name__)
@app_flask.route('/')
def home(): return "BOT ON - 8578 FUNC - FINAL"

@app_flask.route('/base')
def ver_base():
    inicio=request.args.get('inicio',''); fim=request.args.get('fim',''); chapa_f=request.args.get('chapa',''); status_f=request.args.get('status','')
    html=f"""
    <style>body{{font-family:Arial;padding:15px}} table{{border-collapse:collapse;width:100%;font-size:12px}} th{{background:#111;color:white;padding:8px}} td{{padding:6px;border:1px solid #ccc;text-transform:uppercase}} .btn{{padding:8px 15px;text-decoration:none;border-radius:5px;margin-right:8px;color:white;display:inline-block;font-size:13px}} .btn-green{{background:#28a745}} .btn-red{{background:#dc3545}} .btn-blue{{background:#007bff}} .btn-orange{{background:#fd7e14}} .pendente{{background:#f8d7da}} .confirmado{{background:#d4edda}} .nao{{background:#e2e3e5}} .trash{{background:#ff4444;color:white;padding:4px 8px;border-radius:4px;text-decoration:none;font-size:11px}}</style>
    <h2>base horas extra bho</h2>
    <form method="get" style="margin-bottom:15px">
      Data Inicial: <input type="date" name="inicio" value="{inicio}"> Data Final: <input type="date" name="fim" value="{fim}"> 
      CHAPA: <input type="text" name="chapa" value="{chapa_f}" size=8>
      Status: <select name="status"><option value="">TODOS</option><option value="PENDENTE" {'selected' if status_f=='PENDENTE' else ''}>PENDENTE</option><option value="CONFIRMADO" {'selected' if status_f=='CONFIRMADO' else ''}>CONFIRMADO</option></select>
      <button class="btn btn-blue" type="submit">Filtrar</button> <a href="/base">Limpar</a>
    </form>
    <div style="margin-bottom:15px"><a href="/exportar" class="btn btn-green">📥 Extrair Base</a> <a href="/base?limpar=1" class="btn btn-red" onclick="return confirm('Limpar TODA a base?')">🗑️ Limpar Base TODA</a> <a href="/base?status=PENDENTE" class="btn btn-orange">⚠️ Ver só PENDENTES</a> <a href="/funcionarios" class="btn btn-blue">👥 Ver Base Mestra</a></div>
    """
    if request.args.get('limpar')=='1':
        with open(ARQ_HE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["data_registro","chapa","nome","sobrenome","ba","data_inicio","data_fim","hora_inicio","hora_fim","total_horas","status_intervalo","data_confirmacao","telefone"])
        html+="<div style='background:#d4edda;padding:10px;border:1px solid green;margin-bottom:15px'>✅ Base toda limpa!</div>"
    if request.args.get('apagar_chapa'):
        chapa_del = request.args.get('apagar_chapa')
        qtd = apagar_chapa_da_base(chapa_del)
        html+=f"<div style='background:#f8d7da;padding:10px;border:1px solid red;margin-bottom:15px'>✅ Chapa {chapa_del} apagada! {qtd} registros removidos.</div>"
    total_min=0; total_reg=0; pendentes=0; linhas=[]
    try:
        with open(ARQ_HE, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if not r.get("data_inicio"): continue
                if chapa_f and chapa_f not in r.get("chapa",""): continue
                if status_f and status_f != r.get("status_intervalo",""): continue
                try:
                    d=datetime.datetime.strptime(r["data_inicio"], "%d/%m/%Y").date()
                    if inicio and d < datetime.datetime.strptime(inicio, "%Y-%m-%d").date(): continue
                    if fim and d > datetime.datetime.strptime(fim, "%Y-%m-%d").date(): continue
                except: pass
                linhas.append(r); total_reg+=1
                if r.get("status_intervalo")=="PENDENTE": pendentes+=1
                try:
                    if ":" in r.get("total_horas","00:00"):
                        h,m=map(int,r.get("total_horas").split(":"))
                        total_min+=h*60+m
                except: pass
    except Exception as e: html+=f"Erro: {e}<br>"
    th=int(total_min//60); tm=int(total_min%60)
    html+=f"<b>Total: {total_reg} | Pendentes: {pendentes} | Horas: {th:02d}:{tm:02d}</b><br><br>"
    html+="<table><tr><th>Data Reg</th><th>Chapa</th><th>Nome</th><th>BA</th><th>Total</th><th>Status</th><th>Confirmação</th><th>AÇÃO</th></tr>"
    for r in reversed(linhas[-500:]):
        nome_site = f"{r.get('nome','')} {r.get('sobrenome','')}".upper()
        st=r.get('status_intervalo',''); classe='pendente' if st=='PENDENTE' else 'confirmado' if st=='CONFIRMADO' else 'nao'
        ch = r.get('chapa','')
        html+=f"<tr class='{classe}'><td>{r.get('data_registro','')}</td><td>{ch}</td><td>{nome_site}</td><td>{r.get('ba','')}</td><td>{r.get('total_horas','')}</td><td><b>{st}</b></td><td>{r.get('data_confirmacao','')}</td><td><a class='trash' href='/base?apagar_chapa={ch}' onclick=\"return confirm('Apagar TODOS os registros da chapa {ch}?')\">🗑️ Apagar</a></td></tr>"
    html+="</table>"; return html

@app_flask.route('/funcionarios')
def ver_func(): 
    try:
        with open(ARQ_FUNC, encoding="utf-8-sig") as f:
            primeira = f.readline(); f.seek(0)
            delim = ";" if ";" in primeira else ","
            reader = csv.DictReader(f, delimiter=delim)
            if reader.fieldnames:
                reader.fieldnames = [c.strip().lower().replace(" ", "_").replace("\ufeff","") for c in reader.fieldnames]
            chapa_col = "chapa" if "chapa" in reader.fieldnames else reader.fieldnames[0]
            nome_col = "nome_completo" if "nome_completo" in reader.fieldnames else ("funcionario" if "funcionario" in reader.fieldnames else reader.fieldnames[1])
            rows = list(reader)
        html = f"<h2>Base Mestra - {len(rows)} funcionários</h2><table><tr><th>CHAPA</th><th>NOME COMPLETO</th></tr>"
        for r in rows[:1000]:
            ch = r.get(chapa_col, ""); nm = r.get(nome_col, "")
            if ch.lower() != "none" and nm.lower() != "none":
                html+=f"<tr><td>{ch}</td><td>{nm}</td></tr>"
        return html+"</table>"
    except Exception as e: return f"Erro: {e}"

@app_flask.route('/exportar')
def exportar(): return send_file(ARQ_HE, as_attachment=True, download_name="base_horas_extra_bho.csv")
def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Olá! Envie sua CHAPA (6 dígitos)"); return CHAPA

async def chapa_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chapa_raw=update.message.text.strip()
        if not chapa_raw.isdigit(): await update.message.reply_text("CHAPA inválida. Só números, 6 dígitos:"); return CHAPA
        chapa=chapa_raw.zfill(6)
        context.user_data["chapa"]=chapa
        achou=None
        try: achou=buscar_nome_na_base_mestra(chapa)
        except: achou=None
        if achou:
            nome,sobrenome,completo=achou
            context.user_data["nome"]=nome; context.user_data["sobrenome"]=sobrenome; context.user_data["telefone"]="BASE_MESTRA"
            try: salvar_cadastro(chapa,nome,sobrenome,"BASE_MESTRA",str(update.effective_user.id))
            except: pass
            await update.message.reply_text(f"✅ CHAPA ENCONTRADA:\n👤 {completo}\nChapa {chapa}\n\nAgora envie o BA (7 dígitos):")
            return BA
        cad=buscar_cadastro(chapa)
        if cad: 
            context.user_data.update(cad)
            await update.message.reply_text(f"Bem vindo {cad['nome']}! Envie BA 7 dígitos:"); return BA
        await update.message.reply_text(f"Chapa {chapa} não encontrada na base mestra.\nDigite seu NOME:"); return NOME
    except Exception as e:
        await update.message.reply_text(f"Chapa {update.message.text} não encontrada. Digite seu NOME:"); return NOME

async def nome_step(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data["nome"]=update.message.text.strip().upper(); await update.message.reply_text("Sobrenome:"); return SOBRENOME
async def sobrenome_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sobrenome"]=update.message.text.strip().upper(); kb=[[KeyboardButton("📱 Compartilhar telefone", request_contact=True)]]
    await update.message.reply_text("Compartilhe telefone:", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)); return TELEFONE
async def telefone_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tel=update.message.contact.phone_number if update.message.contact else update.message.text.strip(); context.user_data["telefone"]=tel
    salvar_cadastro(context.user_data["chapa"], context.user_data["nome"], context.user_data["sobrenome"], tel, str(update.effective_user.id))
    await update.message.reply_text(f"✅ Salvo! {context.user_data['nome']} {context.user_data['sobrenome']}\nAgora BA 7 dígitos:", reply_markup={"remove_keyboard": True}); return BA
async def ba_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ba=update.message.text.strip()
    if not (ba.isdigit() and len(ba)==7): await update.message.reply_text("BA inválido! 7 dígitos:"); return BA
    context.user_data["ba"]=ba; hoje=datetime.date.today(); await update.message.reply_text(f"BA {ba} ok! Data Inicial:", reply_markup=montar_calendario(hoje.year, hoje.month)); return DATA_INI
async def calendario_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); data=query.data
    if data.startswith("NAV_"): ano,mes=map(int,data.replace("NAV_","").split("-")); await query.edit_message_text("Data Inicial:", reply_markup=montar_calendario(ano, mes)); return DATA_INI
    if data.startswith("DAY_"): d=data.replace("DAY_",""); dt=datetime.datetime.strptime(d, "%Y-%m-%d"); context.user_data["data_inicio"]=dt.strftime("%d/%m/%Y"); kb=[]; [kb.append([InlineKeyboardButton(f"{h:02d}:00", callback_data=f"HINI_{h:02d}")]) for h in range(6,23)]; await query.edit_message_text(f"Data Inicial: {context.user_data['data_inicio']}\nHora INICIAL:", reply_markup=InlineKeyboardMarkup(kb)); return HORA_INI
    return DATA_INI
async def hora_ini_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); context.user_data["hora_ini"]=query.data.replace("HINI_","")
    kb=[[InlineKeyboardButton(f"{m:02d} min", callback_data=f"MINI_{m:02d}") for m in [0,10,20,30,40,50]]]
    await query.edit_message_text(f"Hora: {context.user_data['hora_ini']}h\nMinutos:", reply_markup=InlineKeyboardMarkup(kb)); return MIN_INI
async def min_ini_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); context.user_data["min_ini"]=query.data.replace("MINI_","")
    kb=[[InlineKeyboardButton("SIM - é virada", callback_data="VIRADA_SIM"), InlineKeyboardButton("NÃO - mesmo dia", callback_data="VIRADA_NAO")]]
    await query.edit_message_text(f"Início: {context.user_data['data_inicio']} {context.user_data['hora_ini']}:{context.user_data['min_ini']}\nÉ VIRADA?", reply_markup=InlineKeyboardMarkup(kb)); return VIRADA
async def virada_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); is_virada = query.data=="VIRADA_SIM"
    d_ini = datetime.datetime.strptime(context.user_data["data_inicio"], "%d/%m/%Y")
    context.user_data["data_fim"]=(d_ini+datetime.timedelta(days=1)).strftime("%d/%m/%Y") if is_virada else context.user_data["data_inicio"]
    botoes=[]; linha=[]
    for h in range(24):
        linha.append(InlineKeyboardButton(f"{h:02d}:00", callback_data=f"HFIM_{h:02d}"))
        if len(linha)==4: botoes.append(linha); linha=[]
    if linha: botoes.append(linha)
    await query.edit_message_text(f"Data Fim: {context.user_data['data_fim']}\nHora FINAL:", reply_markup=InlineKeyboardMarkup(botoes)); return HORA_FIM
async def hora_fim_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); context.user_data["hora_fim"]=query.data.replace("HFIM_","")
    kb=[[InlineKeyboardButton(f"{m:02d} min", callback_data=f"MINF_{m:02d}") for m in [0,10,20,30,40,50]]]
    await query.edit_message_text(f"Hora final: {context.user_data['hora_fim']}h\nMinutos:", reply_markup=InlineKeyboardMarkup(kb)); return MIN_FIM

async def min_fim_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); context.user_data["min_fim"]=query.data.replace("MINF_","")
    try:
        di=datetime.datetime.strptime(f"{context.user_data['data_inicio']} {context.user_data['hora_ini']}:{context.user_data['min_ini']}", "%d/%m/%Y %H:%M")
        df=datetime.datetime.strptime(f"{context.user_data['data_fim']} {context.user_data['hora_fim']}:{context.user_data['min_fim']}", "%d/%m/%Y %H:%M")
        diff_seg = (df - di).total_seconds()
        if diff_seg <= 0: diff_seg += 24*3600
        horas = int(diff_seg // 3600); minutos = int((diff_seg % 3600) // 60)
        total_hhmm = f"{horas:02d}:{minutos:02d}"; total_minutos = horas * 60 + minutos
    except: total_hhmm = "00:00"; total_minutos = 0
    nome = context.user_data.get("nome","").upper(); sobrenome = context.user_data.get("sobrenome","").upper()
    chapa = context.user_data.get("chapa",""); ba = context.user_data.get("ba","")
    data_ini = context.user_data.get("data_inicio",""); data_fim = context.user_data.get("data_fim","")
    hora_ini = context.user_data.get("hora_ini",""); min_ini = context.user_data.get("min_ini","")
    hora_fim = context.user_data.get("hora_fim",""); min_fim = context.user_data.get("min_fim","")
    status_intervalo = "PENDENTE" if total_minutos > 360 else "NÃO NECESSÁRIO"
    data_confirmacao = ""
    mascara=f"✅ REGISTRO CONFIRMADO\n\n👤 {nome} {sobrenome}\n🪪 Chapa: {chapa}\n📋 BA: {ba}\n📅 Data Início: {data_ini}\n📅 Data Fim: {data_fim}\n⏰ Hora Inicial: {hora_ini}:{min_ini}\n⏰ Hora Final: {hora_fim}:{min_fim}\n⏱️ Total: {total_hhmm}\n"
    with open(ARQ_HE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), chapa, nome, sobrenome, ba, data_ini, data_fim, f"{hora_ini}:{min_ini}", f"{hora_fim}:{min_fim}", total_hhmm, status_intervalo, data_confirmacao, context.user_data.get("telefone","")])
    
    # === BOTÕES CHAMATIVOS NOVOS ===
    kb_final=InlineKeyboardMarkup([
        [InlineKeyboardButton("↗️ Encaminhar no Telegram", switch_inline_query=mascara)],
        [InlineKeyboardButton(" ", callback_data="IGNORE")],
        [InlineKeyboardButton("🟩🟩🟩 ➕ CADASTRAR NOVA HE ➕ 🟩🟩🟩", callback_data="NOVA_HE")],
        [InlineKeyboardButton("🔥👉 CLIQUE AQUI PARA LANÇAR OUTRA 👈🔥", callback_data="NOVA_HE")]
    ])
    
    await query.edit_message_text(mascara, reply_markup=kb_final)
    if total_minutos > 360:
        alerta = f"🚨🚨🚨 ATENÇÃO {nome} 🚨🚨🚨\n\n⚠️ Não esqueça da inclusão do INTERVALO REFEIÇÃO no RH."
        kb_alerta = InlineKeyboardMarkup([[InlineKeyboardButton("✅ ESTOU CIENTE - INCLUÍ O INTERVALO", callback_data=f"CONFIRMA_INTERVALO_{chapa}")]])
        await query.message.reply_text(alerta, reply_markup=kb_alerta)
    return BA

async def confirma_intervalo_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer()
    chapa = query.data.replace("CONFIRMA_INTERVALO_","").replace("CONFIRMA_INTERVALO","")
    if not chapa: chapa = context.user_data.get("chapa","")
    atualizar_confirmacao_na_base(chapa)
    await query.edit_message_text(f"✅ Confirmado!\nChapa {chapa} confirmou inclusão do INTERVALO. Registrado como CONFIRMADO na base!")

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(f"Seu ID é: {update.effective_user.id}")
async def reset_base_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id)
    if ADMIN_ID and uid!=ADMIN_ID: await update.message.reply_text("⛔ Você não é ADM!"); return
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ SIM, APAGAR BASE TODA", callback_data="RESET_CONFIRM")],[InlineKeyboardButton("❌ Cancelar", callback_data="RESET_CANCEL")]])
    await update.message.reply_text("⚠️ ADM: Apagar TODA a base HE?", reply_markup=kb)
async def reset_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); uid=str(query.from_user.id)
    if ADMIN_ID and uid!=ADMIN_ID: await query.edit_message_text("⛔ Sem permissão"); return
    if query.data=="RESET_CONFIRM":
        with open(ARQ_HE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["data_registro","chapa","nome","sobrenome","ba","data_inicio","data_fim","hora_inicio","hora_fim","total_horas","status_intervalo","data_confirmacao","telefone"])
        await query.edit_message_text("✅ BASE TODA APAGADA!")
    else: await query.edit_message_text("❌ Cancelado")
async def reset_chapa_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id)
    if ADMIN_ID and uid!=ADMIN_ID: await update.message.reply_text("⛔ Você não é ADM!"); return
    if not context.args:
        await update.message.reply_text("Use assim:\n/reset_chapa 062289")
        return
    chapa=context.args[0].strip().zfill(6)
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"🗑️ SIM, APAGAR CHAPA {chapa}", callback_data=f"RESET_CHAPA_{chapa}")],[InlineKeyboardButton("❌ Cancelar", callback_data="RESET_CHAPA_CANCEL")]])
    await update.message.reply_text(f"⚠️ ADM: Apagar TODOS os registros da chapa {chapa}?", reply_markup=kb)
async def reset_chapa_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); uid=str(query.from_user.id)
    if ADMIN_ID and uid!=ADMIN_ID: await query.edit_message_text("⛔ Sem permissão"); return
    if query.data=="RESET_CHAPA_CANCEL": await query.edit_message_text("❌ Cancelado"); return
    if query.data.startswith("RESET_CHAPA_"):
        chapa=query.data.replace("RESET_CHAPA_","")
        qtd=apagar_chapa_da_base(chapa)
        if qtd>=0: await query.edit_message_text(f"✅ CHAPA {chapa} APAGADA! {qtd} registros removidos.")
        else: await query.edit_message_text(f"❌ Erro ao apagar chapa {chapa}")
async def nova_he_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query=update.callback_query; await query.answer(); await query.message.reply_text("Envie o BA 7 dígitos:"); return BA
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Cancelado. /start"); return ConversationHandler.END

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            app=ApplicationBuilder().token(TOKEN).build()
            conv=ConversationHandler(
                entry_points=[CommandHandler("start", start)],
                states={
                    CHAPA: [MessageHandler(filters.TEXT & ~filters.COMMAND, chapa_step)], NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nome_step)],
                    SOBRENOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sobrenome_step)], TELEFONE: [MessageHandler(filters.ALL, telefone_step)],
                    BA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ba_step)], DATA_INI: [CallbackQueryHandler(calendario_cb, pattern="^(NAV_|DAY_|IGNORE)")],
                    HORA_INI: [CallbackQueryHandler(hora_ini_cb, pattern="^HINI_")], MIN_INI: [CallbackQueryHandler(min_ini_cb, pattern="^MINI_")],
                    VIRADA: [CallbackQueryHandler(virada_cb, pattern="^VIRADA_")], HORA_FIM: [CallbackQueryHandler(hora_fim_cb, pattern="^HFIM_")],
                    MIN_FIM: [CallbackQueryHandler(min_fim_cb, pattern="^MINF_")],
                }, fallbacks=[CommandHandler("cancel", cancel)],
            )
            app.add_handler(conv)
            app.add_handler(CommandHandler("id", id_cmd))
            app.add_handler(CommandHandler("reset_base", reset_base_cmd))
            app.add_handler(CommandHandler("reset_chapa", reset_chapa_cmd))
            app.add_handler(CallbackQueryHandler(reset_cb, pattern="^RESET_"))
            app.add_handler(CallbackQueryHandler(reset_chapa_cb, pattern="^RESET_CHAPA_"))
            app.add_handler(CallbackQueryHandler(nova_he_cb, pattern="^NOVA_HE$"))
            app.add_handler(CallbackQueryHandler(confirma_intervalo_cb, pattern="^CONFIRMA_INTERVALO"))
            print(">>> BOT FINAL - TUDO OK"); app.run_polling(drop_pending_updates=True)
        except Exception as e: print(f"CRASH: {e}"); time.sleep(5)

if __name__=="__main__": main()
