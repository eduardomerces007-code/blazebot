from flask import Flask, render_template_string
import requests
from collections import deque, Counter
import time
import threading
import os

app = Flask(__name__)

# 🔑 Configurações do Telegram
TOKEN = "8205989336:AAGYq9omnk8IygqJ0i8ezpM0q4nlB9vIohg"  # Seu token
CHAT_ID = 190791381  # Seu chat_id

# Blaze API
API_URL = "https://blaze.com/api/roulette_games/recent"
historico = deque(maxlen=500)
ultimo_id = None
mensagens = deque(maxlen=20)  # últimas 20 mensagens exibidas no navegador


def cor_texto(cor):
    return {0: "Branco", 1: "Vermelho", 2: "Preto"}[cor]


def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.get(url, params={"chat_id": CHAT_ID, "text": msg})
        resultado = r.json()
        print("📨 Envio Telegram:", resultado)  # log no Render
    except Exception as e:
        print("❌ Erro no envio Telegram:", e)


def coletar_dados():
    global ultimo_id
    while True:
        try:
            r = requests.get(API_URL).json()
            ultimo = r[0]

            game_id = ultimo["id"]
            numero = ultimo["roll"]
            cor = ultimo["color"]
            horario = ultimo["created_at"]

            if game_id != ultimo_id:
                ultimo_id = game_id
                historico.append(cor)

                msg = f"🎲 {horario} → {cor_texto(cor)} ({numero})"

                # Detectar sequências de 3 seguidos
                if len(historico) >= 4:
                    ultimos3 = list(historico)[-4:-1]
                    if len(set(ultimos3)) == 1 and ultimos3[0] in [1, 2]:
                        cor_seq = ultimos3[0]

                        ocorrencias = []
                        hist_list = list(historico)
                        for i in range(len(hist_list) - 3):
                            if hist_list[i] == hist_list[i + 1] == hist_list[i + 2] == cor_seq:
                                if i + 3 < len(hist_list):
                                    ocorrencias.append(hist_list[i + 3])

                        if ocorrencias:
                            contagem = Counter(ocorrencias)
                            total = sum(contagem.values())
                            prob_vermelho = contagem.get(1, 0) / total * 100
                            prob_preto = contagem.get(2, 0) / total * 100
                            prob_branco = contagem.get(0, 0) / total * 100

                            sugestao = "Vermelho" if prob_vermelho > prob_preto else "Preto"

                            msg += (
                                f"\n\n📊 Após 3 {cor_texto(cor_seq)} seguidos:"
                                f"\n➡️ Vermelho: {prob_vermelho:.1f}%"
                                f"\n➡️ Preto: {prob_preto:.1f}%"
                                f"\n➡️ Branco: {prob_branco:.1f}%"
                                f"\n🎯 Entrada sugerida: {sugestao}"
                                f"\n⚠️ Proteção: Branco"
                            )

                mensagens.appendleft(msg.replace("\n", "<br>"))
                enviar_telegram(msg)

            time.sleep(10)

        except Exception as e:
            mensagens.appendleft(f"Erro: {e}")
            print("❌ Erro no coletor:", e)
            time.sleep(20)


# Thread para rodar em paralelo
threading.Thread(target=coletar_dados, daemon=True).start()


@app.route("/")
def index():
    template = """
<html>
    <head>
        <title>Blaze Bot - Sinais</title>
        <meta http-equiv="refresh" content="10">
    </head>
    <body style="font-family: Arial; background:#111; color:#eee;">
        <h2>🔥 Blaze Double - Sinais em tempo real</h2>
        <ul>
        {% for m in mensagens %}
            <li>{{ m|safe }}</li>
        {% endfor %}
        </ul>
    </body>
</html>
"""
    return render_template_string(template, mensagens=mensagens)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
