import os, sqlite3, threading
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from flask import Flask
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackQueryHandler
from telegram.request import HTTPXRequest

TOKEN = "8962498308:AAFzBUN4uChTXnXdPXmIKszLlMRvVkpn2Kg"
DB_PATH = "colaboradores.db"
CHAPA, NOME, SOBRENOME, TELEFONE, BA, DATA_INI, SEL_HORA_INI_H, SEL_HORA_INI_M, PERG_VIRADA, SEL_HORA_FIM_H, SEL_HORA_FIM_M = range(11)
ADM_CHAPA = "062289"

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Bot HE_TIME_BHO online 24h"
def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

def init_db():
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS colaboradores (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, chapa TEXT, nome TEXT, telefone TEXT, ba TEXT, data TEXT, data_fim TEXT, hora_inicio TEXT, hora_fim TEXT, total_min INTEGER, criado_em TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS cadastro (telegram_id INTEGER PRIMARY KEY, chapa TEXT UNIQUE, nome TEXT, telefone TEXT)""")
    conn.commit(); conn.close()

def calcular(di, hi, df, hf):
    fmt="%d/%m/%Y %H:%M"; d1=datetime.strptime(f"{di} {hi}", fmt); d2=datetime.strptime(f"{df} {hf}", fmt)
    if d2 <= d1: d2 += timedelta(days=1)
    m=int((d2-d1).total_seconds()//60); return f"{m//60}h {m%60:02d}min", m

def gerar_mascara(chapa, nome, tel, ba, di, df, hi, hf, total):
    W,H=800,600; img=Image.new("RGB",(W,H),"white"); draw=ImageDraw.Draw(img)
    try: bold=ImageFont.truetype("arial.ttf",34); regular=ImageFont.truetype("arial.ttf",26); small=ImageFont.truetype("arial.ttf",20)
    except: bold=ImageFont.load_default(); regular=bold; small=bold
    draw.rectangle([(10,10),(W-10,H-10)],outline="#2e7d32",width=3); draw.rectangle([(10,10),(W-10,70)],fill="#2e7d32")
    draw.text((20,18),"HE_TIME_BHO",fill="white",font=bold); y=90
    draw.text((25,y),f"CHAPA: {chapa}",fill="black",font=bold); y+=50
    draw.text((25,y),f"NOME: {nome.upper()}",fill="black",font=regular); y+=45
    draw.text((25,y),f"BA: {ba}",fill="black",font=bold); y+=55
    draw.line([(25,y),(W-25,y)],fill="#ddd",width=2); y+=20
    draw.text((25,y),f"INICIO: {di}  {hi}",fill="black",font=regular); y+=40
    draw.text((25,y),f"FIM:    {df}  {hf}",fill="black",font=regular); y+=60
    draw.rectangle([(25,y),(W-25,y+65)],fill="#e8f5e9"); draw.text((35,y+14),f"TOTAL: {total}",fill="#2e7d32",font=bold)
    draw.text((25,H-35),f"{tel} | {datetime.now().strftime('%d/%m/%Y %H:%M')}",fill="#999",font=small)
    out=f"mascara_{chapa}_{ba}.jpg"; img.save(out,quality=95); return out

def kb_datas():
    hoje=datetime.now(); botoes=[]
    for i in range(7):
        d=hoje - timedelta(days=i); label=d.strftime("%d/%m - %a").replace("Mon","Seg").replace("Tue","Ter").replace("Wed","Qua").replace("Thu","Qui").replace("Fri","Sex").replace("Sat","Sab").replace("Sun","Dom")
        botoes.append([InlineKeyboardButton(f"📅 {label}", callback_data=f"data_{d.strftime('%d/%m/%Y')}")])
    return InlineKeyboardMarkup(botoes)

def relogio_horas():
    kb=[]
    for i in range(0,24,4): kb.append([InlineKeyboardButton(f"{h:02d}:00", callback_data=f"hora_h_{h:02d}") for h in range(i, min(i+4,24))])
    return InlineKeyboardMarkup(kb)

def relogio_minutos():
    mins=["00","10","20","30","40","50"]; kb=[[InlineKeyboardButton(f":{m}", callback_data=f"hora_m_{m}") for m in mins]]
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="hora_voltar")]); return InlineKeyboardMarkup(kb)

async def reset_cmd(u,c):
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    cur.execute("SELECT chapa FROM cadastro WHERE telegram_id=?", (u.effective_user.id,))
    row=cur.fetchone()
    if not row or row[0]!=ADM_CHAPA:
        cur.execute("SELECT COUNT(*) FROM cadastro")
        result = cur.fetchone()
        count = result[0] if result else 0
        if count>0:
            await u.message.reply_text("❌ Só ADM 062289"); conn.close(); return
    conn.close()
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("✅ SIM, APAGAR TUDO", callback_data="reset_sim")],[InlineKeyboardButton("❌ NÃO", callback_data="reset_nao")]])
    await u.message.reply_text(f"⚠️ ADM {ADM_CHAPA}\nAPAGAR TUDO?", reply_markup=kb)

async def reset_confirm(u,c):
    q=u.callback_query; await q.answer(); conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    if q.data=="reset_sim": cur.execute("DELETE FROM colaboradores"); cur.execute("DELETE FROM cadastro"); conn.commit(); await q.edit_message_text(f"✅ BASE RESETADA! ADM {ADM_CHAPA}\n/start")
    else: await q.edit_message_text("❌ Cancelado")
    conn.close()

async def start(u,c):
    c.user_data['telegram_id']=u.effective_user.id; conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    cur.execute("SELECT chapa, nome, telefone FROM cadastro WHERE telegram_id=?", (c.user_data['telegram_id'],)); row=cur.fetchone(); conn.close()
    if row: c.user_data['chapa'],c.user_data['nome'],c.user_data['telefone']=row; await u.message.reply_text(f"👷 {row[1]} CHAPA {row[0]}\n\nBA (7 dígitos):", reply_markup=ReplyKeyboardRemove()); return BA
    await u.message.reply_text("👷 Primeiro acesso\nCHAPA 6 dígitos (ex: 062289):", reply_markup=ReplyKeyboardRemove()); return CHAPA

async def r_chapa(u,c):
    chapa=u.message.text.strip()
    if not chapa.isdigit() or len(chapa)!=6: await u.message.reply_text("❌ CHAPA 6 dígitos!"); return CHAPA
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor(); cur.execute("SELECT telegram_id FROM cadastro WHERE chapa=?", (chapa,)); existe=cur.fetchone(); conn.close()
    if existe: await u.message.reply_text(f"❌ CHAPA {chapa} já usada."); return CHAPA
    c.user_data['chapa']=chapa; await u.message.reply_text(f"✅ CHAPA {chapa} OK!\nNome:"); return NOME

async def r_nome(u,c): c.user_data['nome']=u.message.text.strip(); await u.message.reply_text("Sobrenome:"); return SOBRENOME
async def r_sobrenome(u,c):
    c.user_data['sobrenome']=u.message.text.strip(); kb=[[KeyboardButton("📱 Compartilhar número", request_contact=True)]]
    await u.message.reply_text("Compartilhe contato:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)); return TELEFONE
async def r_tel(u,c):
    tel=u.message.contact.phone_number if u.message.contact else u.message.text.strip(); nome_full=f"{c.user_data['nome']} {c.user_data['sobrenome']}".strip()
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor(); cur.execute("INSERT OR REPLACE INTO cadastro (telegram_id, chapa, nome, telefone) VALUES (?,?,?,?)",(c.user_data['telegram_id'], c.user_data['chapa'], nome_full, tel)); conn.commit(); conn.close()
    c.user_data['nome']=nome_full; c.user_data['telefone']=tel; await u.message.reply_text(f"✅ {nome_full}\n\nBA (7 dígitos):", reply_markup=ReplyKeyboardRemove()); return BA
async def r_ba(u,c):
    ba=u.message.text.strip()
    if len(ba)!=7 or not ba.isdigit(): await u.message.reply_text("❌ BA 7 dígitos!"); return BA
    c.user_data['ba']=ba; await u.message.reply_text("📅 ESCOLHA A DATA INICIAL:", reply_markup=kb_datas()); return DATA_INI
async def r_data_ini(u,c):
    q=u.callback_query; await q.answer()
    if q.data.startswith("data_"): c.user_data['data_ini']=q.data.replace("data_",""); await q.edit_message_text(f"📅 Data: {c.user_data['data_ini']}\n\n🕐 Hora inicial:"); await q.message.reply_text("Hora inicial:", reply_markup=relogio_horas()); return SEL_HORA_INI_H
    return DATA_INI
async def sel_hora_ini_h(u,c):
    q=u.callback_query; await q.answer()
    if q.data.startswith("hora_h_"): c.user_data['hora_ini_h']=q.data.split("_")[-1]; await q.edit_message_text(f"Hora ini: {c.user_data['hora_ini_h']}:??", reply_markup=relogio_minutos()); return SEL_HORA_INI_M
    return SEL_HORA_INI_H
async def sel_hora_ini_m(u,c):
    q=u.callback_query; await q.answer()
    if q.data=="hora_voltar": await q.edit_message_text("Hora inicial:", reply_markup=relogio_horas()); return SEL_HORA_INI_H
    if q.data.startswith("hora_m_"): c.user_data['hora_ini']=f"{c.user_data['hora_ini_h']}:{q.data.split('_')[-1]}"; kb=InlineKeyboardMarkup([[InlineKeyboardButton("🌙 SIM, VIRADA (fim = amanhã)", callback_data="virada_sim")],[InlineKeyboardButton("☀️ NÃO, mesmo dia", callback_data="virada_nao")]]); await q.edit_message_text(f"✅ {c.user_data['data_ini']} {c.user_data['hora_ini']}\nFoi virada?", reply_markup=kb); return PERG_VIRADA
    return SEL_HORA_INI_M
async def perg_virada(u,c):
    q=u.callback_query; await q.answer(); d=c.user_data; di_obj=datetime.strptime(d['data_ini'], "%d/%m/%Y")
    if q.data=="virada_sim": d['data_fim']=(di_obj + timedelta(days=1)).strftime("%d/%m/%Y"); d['is_virada']=True
    else: d['data_fim']=d['data_ini']; d['is_virada']=False
    await q.edit_message_text(f"Inicio: {d['data_ini']} {d['hora_ini']}\nFim: {d['data_fim']}\nHora final:"); await q.message.reply_text("Hora final:", reply_markup=relogio_horas()); return SEL_HORA_FIM_H
async def sel_hora_fim_h(u,c):
    q=u.callback_query; await q.answer()
    if q.data.startswith("hora_h_"): c.user_data['hora_fim_h']=q.data.split("_")[-1]; await q.edit_message_text(f"Hora fim: {c.user_data['hora_fim_h']}:??", reply_markup=relogio_minutos()); return SEL_HORA_FIM_M
    return SEL_HORA_FIM_H
async def sel_hora_fim_m(u,c):
    q=u.callback_query; await q.answer()
    if q.data=="hora_voltar": await q.edit_message_text("Hora final:", reply_markup=relogio_horas()); return SEL_HORA_FIM_H
    if q.data.startswith("hora_m_"):
        d=c.user_data; d['hora_fim']=f"{d['hora_fim_h']}:{q.data.split('_')[-1]}"; total_txt,total_min=calcular(d['data_ini'],d['hora_ini'],d['data_fim'],d['hora_fim'])
        if total_min>1620: await q.edit_message_text(f"❌ PASSOU DE 27H! {total_txt}"); await q.message.reply_text("Hora final:", reply_markup=relogio_horas()); return SEL_HORA_FIM_H
        if total_min<=0: await q.edit_message_text("❌ Hora final depois da inicial!"); await q.message.reply_text("Hora final:", reply_markup=relogio_horas()); return SEL_HORA_FIM_H
        is_virada=" (VIRADA)" if d['is_virada'] else ""; conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
        cur.execute("INSERT INTO colaboradores (telegram_id,chapa,nome,telefone,ba,data,data_fim,hora_inicio,hora_fim,total_min,criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(d['telegram_id'],d['chapa'],d['nome'],d['telefone'],d['ba'],d['data_ini'],d['data_fim'],d['hora_ini'],d['hora_fim'],total_min,datetime.now().strftime("%d/%m/%Y %H:%M"))); conn.commit(); conn.close()
        path=gerar_mascara(d['chapa'],d['nome'],d['telefone'],d['ba'],d['data_ini'],d['data_fim'],d['hora_ini'],d['hora_fim'],total_txt)
        await q.edit_message_text(f"✅ REGISTRADO{is_virada}!\n{d['chapa']} {d['nome']}\nBA {d['ba']}\n{d['data_ini']} {d['hora_ini']} -> {d['data_fim']} {d['hora_fim']}\nTOTAL {total_txt}"); await q.message.reply_photo(photo=open(path,'rb'), caption=f"{d['chapa']} - {total_txt}{is_virada}"); return ConversationHandler.END
    return SEL_HORA_FIM_M
async def cancel(u,c): await u.message.reply_text("Cancelado", reply_markup=ReplyKeyboardRemove()); return ConversationHandler.END

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    init_db(); request=HTTPXRequest(connect_timeout=30, read_timeout=30, pool_timeout=30)
    app=ApplicationBuilder().token(TOKEN).request(request).build()
    app.add_handler(CommandHandler("reset", reset_cmd)); app.add_handler(CallbackQueryHandler(reset_confirm, pattern="^reset_"))
    conv=ConversationHandler(entry_points=[CommandHandler("start",start)], states={CHAPA:[MessageHandler(filters.TEXT & ~filters.COMMAND,r_chapa)],NOME:[MessageHandler(filters.TEXT & ~filters.COMMAND,r_nome)],SOBRENOME:[MessageHandler(filters.TEXT & ~filters.COMMAND,r_sobrenome)],TELEFONE:[MessageHandler(filters.TEXT | filters.CONTACT, r_tel)],BA:[MessageHandler(filters.TEXT & ~filters.COMMAND,r_ba)],DATA_INI:[CallbackQueryHandler(r_data_ini)],SEL_HORA_INI_H:[CallbackQueryHandler(sel_hora_ini_h)],SEL_HORA_INI_M:[CallbackQueryHandler(sel_hora_ini_m)],PERG_VIRADA:[CallbackQueryHandler(perg_virada)],SEL_HORA_FIM_H:[CallbackQueryHandler(sel_hora_fim_h)],SEL_HORA_FIM_M:[CallbackQueryHandler(sel_hora_fim_m)],}, fallbacks=[CommandHandler("cancel",cancel)])
    app.add_handler(conv); print(f"Bot 24h WEB rodando... ADM {ADM_CHAPA}"); app.run_polling()

if __name__=="__main__": main()
