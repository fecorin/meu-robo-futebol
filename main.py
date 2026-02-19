import pandas as pd
import requests
import time
import os
from scipy.stats import poisson
from datetime import datetime

# --- CONFIGURAÇÕES ---
# No GitHub Actions, use Secrets. Para teste local, preencha as strings.
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TOKEN or not CHAT_ID:
    print("❌ ERRO: As senhas (Secrets) não foram encontradas pelo código!")
else:
    print("✅ SUCESSO: As senhas foram carregadas corretamente.")

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensagem}&parse_mode=Markdown"
    requests.get(url)

def calcular_poisson(media_casa, media_fora):
    """Calcula probabilidades de mercados baseados em Poisson"""
    # Probabilidade de cada time marcar de 0 a 5 gols
    prob_casa = [poisson.pmf(i, media_casa) for i in range(6)]
    prob_fora = [poisson.pmf(i, media_fora) for i in range(6)]
    
    # BTTS (Ambas Marcam): 1 - (Prob Casa 0 ou Prob Fora 0)
    prob_btts = (1 - prob_casa[0]) * (1 - prob_fora[0]) * 100
    
    # Over 1.5: 1 - (Prob 0x0 + Prob 1x0 + Prob 0x1)
    zero_zero = prob_casa[0] * prob_fora[0]
    um_zero = prob_casa[1] * prob_fora[0]
    zero_um = prob_casa[0] * prob_fora[1]
    prob_over15 = (1 - (zero_zero + um_zero + zero_um)) * 100
    
    return round(prob_btts, 2), round(prob_over15, 2)

def pipeline_inteligente(liga_id):
    headers = {'User-Agent': 'Mozilla/5.0'}
    # 1. Coletar Médias de Ataque/Defesa (Página de Estatísticas de Equipes)
    url_stats = f"https://fbref.com/pt/comps/{liga_id}/stats/Squad-Standard-Stats"
    
    try:
        time.sleep(5) # Rate Limit
        res = requests.get(url_stats, headers=headers)
        df_equipes = pd.read_html(res.text)[0]
        
        # Simplificando: Pegar as colunas de Gols por jogo (Gls / MP)
        # Nota: Ajuste os índices das colunas conforme a estrutura exata do FBref
        df_equipes = df_equipes[[('Unnamed: 0_level_0', 'Squad'), ('Per 90 Minutes', 'Gls')]]
        df_equipes.columns = ['Time', 'Media_Gols']
        
        # 2. Simular um próximo jogo (Exemplo: Líder vs Vice-Líder)
        time_a = df_equipes.iloc[0]
        time_b = df_equipes.iloc[1]
        
        btts, over15 = calcular_poisson(time_a['Media_Gols'], time_b['Media_Gols'])
        
        # 3. Lógica de Alerta: Se a probabilidade for alta, envia Telegram
        if over15 > 75 or btts > 65:
            mensagem = (
                f"🚨 *ALERTA DE VALOR detectado!*\n\n"
                f"🏟 *Jogo:* {time_a['Time']} x {time_b['Time']}\n"
                f"📈 *Prob. Over 1.5:* {over15}%\n"
                f"⚽ *Prob. BTTS:* {btts}%\n"
                f"📊 *Média Combinada:* {(time_a['Media_Gols'] + time_b['Media_Gols']):.2f} gols"
            )
            enviar_telegram(mensagem)
            print("✔ Alerta enviado para o Telegram!")
        
    except Exception as e:
        print(f"Erro no pipeline: {e}")

# Rodar para o Brasileirão (ID 24)
pipeline_inteligente("24")
