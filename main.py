import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

app = FastAPI(title="HE_TIME_BHO - Bot HE")

# ===============================
# BASE MESTRA - 8578 FUNCIONÁRIOS
# ===============================
def carregar_base_mestra():
    try:
        # tenta ler funcionarios.csv
        if not os.path.exists("funcionarios.csv"):
            print("❌ funcionarios.csv não encontrado")
            return {}
        
        df = pd.read_csv("funcionarios.csv", dtype=str, encoding="utf-8")
        # normaliza colunas
        df.columns = [c.strip().lower() for c in df.columns]
        
        base = {}
        for _, row in df.iterrows():
            try:
                # pega chapa e nome (aceita maiusculo/minusculo)
                chapa_raw = str(row.get('chapa', '')).strip()
                nome_raw = str(row.get('nome_completo', '')).strip()
                
                if not chapa_raw or chapa_raw.lower() == 'nan':
                    continue
                
                # normaliza: 6 dígitos com zero à esquerda
                chapa = chapa_raw.zfill(6)
                nome = nome_raw.upper()
                
                base[chapa] = nome
                # também salva sem zero pra busca flexível
                base[chapa_raw] = nome
                base[chapa.lstrip('0') or '0'] = nome
                
            except Exception:
                continue
        
        print(f"✅ Base carregada: {len(base)} chaves | {len(set(base.values()))} funcionários únicos")
        return base
    except Exception as e:
        print(f"❌ Erro ao carregar base: {e}")
        return {}

BASE_MESTRA = carregar_base_mestra()

def buscar_nome_na_base_mestra(chapa_digitada: str):
    """Busca nome automático pela chapa"""
    if not chapa_digitada:
        return None
    
    chapa = str(chapa_digitada).strip()
    # tenta de várias formas
    tentativas = [
        chapa,
        chapa.zfill(6),
        chapa.lstrip('0'),
        chapa.zfill(6).lstrip('0')
    ]
    
    for t in tentativas:
        if t in BASE_MESTRA:
            return BASE_MESTRA[t]
    
    # busca com 6 dígitos
    return BASE_MESTRA.get(chapa.zfill(6))

# ===============================
# ENDPOINTS
# ===============================
@app.get("/")
def home():
    return {
        "status": "online",
        "bot": "HE_TIME_BHO",
        "base_funcionarios": len(set(BASE_MESTRA.values())),
        "endpoints": ["/funcionarios", "/buscar/{chapa}", "/health"]
    }

@app.get("/health")
def health():
    return {"status": "ok", "base": len(BASE_MESTRA) > 0}

@app.get("/funcionarios")
def listar_funcionarios():
    """Retorna total da base - pra você testar no Render"""
    unicos = {}
    for chapa, nome in BASE_MESTRA.items():
        # só chapas de 6 dígitos
        if len(chapa) == 6 and chapa.isdigit():
            unicos[chapa] = nome
    
    return {
        "total": len(unicos),
        "exemplo": dict(list(unicos.items())[:5])
    }

@app.get("/buscar/{chapa}")
def buscar_funcionario(chapa: str):
    """Busca 1 funcionário - TESTE: /buscar/126549"""
    nome = buscar_nome_na_base_mestra(chapa)
    if nome:
        return {"chapa": str(chapa).zfill(6), "nome_completo": nome, "encontrado": True}
    else:
        return JSONResponse(
            status_code=404,
            content={"chapa": chapa, "encontrado": False, "msg": "Chapa não encontrada na base"}
        )

# ===============================
# FUNÇÃO PARA USAR NO SEU BOT
# ===============================
# No seu código do Telegram/WhatsApp, onde você pede a chapa, use assim:
#
# chapa_digitada = mensagem_do_usuario
# nome_automatico = buscar_nome_na_base_mestra(chapa_digitada)
#
# if nome_automatico:
#     await responder(f"✅ Encontrado: {nome_automatico}\nChapa {chapa_digitada.zfill(6)} confirmada!")
#     # já preenche o nome e pula a pergunta do nome
# else:
#     await responder("Chapa não encontrada, digite o nome completo:")
#

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
