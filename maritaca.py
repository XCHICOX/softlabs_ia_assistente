from flask import Flask, request, jsonify, render_template, session
import openai
import json
import os

app = Flask(__name__)
app.secret_key = "sua_chave_secreta"  # necessário para session

DATA_FILE = "solicitacoes.json"

# Cliente da Maritaca
client = openai.OpenAI(
    api_key="Seu token aqui",
    base_url="https://chat.maritaca.ai/api",
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/perguntar', methods=['POST'])
def perguntar():
    pergunta = request.json.get("pergunta")
    if not pergunta:
        return jsonify({"erro": "Pergunta não fornecida"}), 400

    historico = session.get('historico', [])

    try:
        # Chamada ao modelo
        response = client.chat.completions.create(
            model="sabia-3",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é a SoftlabsIA, atendente virtual da Softlabs.\n"
                        "Fluxo obrigatório passo a passo:\n"
                        "1. Primeiro peça o nome.\n"
                        "2. Depois peça o telefone.\n"
                        "3. Depois peça o email.\n"
                        "4. Depois peça o tipo de sistema ou site.\n"
                        "5. Quando os 4 dados estiverem completos, responda SOMENTE com JSON válido.\n"
                        "Não volte ao passo 1 se já tiver coletado o dado."
                    )
                },
                *historico,
                {"role": "user", "content": pergunta}
            ],
            max_tokens=400
        )

        answer = getattr(response.choices[0].message, "content", "").strip()
        if not answer:
            return jsonify({"erro": "A IA não retornou resposta"}), 500

        # Atualiza histórico
        historico.append({"role": "user", "content": pergunta})
        historico.append({"role": "assistant", "content": answer})
        session['historico'] = historico

        # Tenta interpretar como JSON
        try:
            data = json.loads(answer)

            # Salva no arquivo JSON
            if not os.path.exists(DATA_FILE):
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4, ensure_ascii=False)

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                try:
                    solicitacoes = json.load(f)
                except json.JSONDecodeError:
                    solicitacoes = []

            solicitacoes.append(data)

            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(solicitacoes, f, indent=4, ensure_ascii=False)

            # Limpa histórico para liberar a session
            session.pop('historico', None)

            # Retorna mensagem final apenas
            return jsonify({
                "resposta": f"Perfeito, {data.get('nome', '')}! Seus dados foram registrados com sucesso. "
                            "Em breve, um de nossos atendentes entrará em contato. Obrigado."
            })

        except json.JSONDecodeError:
            # Ainda coletando dados passo a passo
            return jsonify({"resposta": answer})

    except Exception as e:
        return jsonify({"erro": f"Erro inesperado: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=False)
