import streamlit as st
import os
from docxtpl import DocxTemplate, RichText
from io import BytesIO
from datetime import datetime

# -------------------------
# LOGIN
# -------------------------
usuarios = {
    "admin": "1234",
    "analista": "abcd"
}

def tela_login():
    st.title("Login do Sistema")

    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user in usuarios and usuarios[user] == senha:
            st.session_state["logado"] = True
            st.session_state["usuario"] = user
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    tela_login()
    st.stop()

st.sidebar.write(f"👤 {st.session_state['usuario']}")
if st.sidebar.button("Sair"):
    st.session_state["logado"] = False
    st.rerun()

# -------------------------
# CARREGAR PERGUNTAS (TXT)
# -------------------------
def carregar_perguntas_txt(caminho):
    if not os.path.exists(caminho):
        st.error("Arquivo perguntas.txt não encontrado")
        st.stop()

    perguntas = []
    bloco = {}

    with open(caminho, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    for linha in linhas:
        linha = linha.strip()

        if not linha:
            if bloco:
                perguntas.append(bloco)
                bloco = {}
            continue

        if linha.startswith("GRUPO:"):
            bloco["grupo"] = linha.replace("GRUPO:", "").strip()

        elif linha.startswith("ID:"):
            bloco["id"] = linha.replace("ID:", "").strip()

        elif linha.startswith("PERGUNTA:"):
            bloco["pergunta"] = linha.replace("PERGUNTA:", "").strip()

        elif linha.startswith("OPCOES:"):
            bloco["opcoes"] = linha.replace("OPCOES:", "").strip().split(";")

        elif linha.startswith("REGRA_"):
            chave, valor = linha.split(":", 1)
            resposta = chave.replace("REGRA_", "").strip()

            bloco.setdefault("regras", {})[resposta] = {
                "texto": valor.strip()
            }

    if bloco:
        perguntas.append(bloco)

    return perguntas


perguntas = carregar_perguntas_txt("perguntas.txt")

# -------------------------
# FUNÇÕES
# -------------------------
def definir_conclusao(respostas):
    for p in perguntas:
        if respostas[p["id"]] in p.get("regras", {}):
            return "DESFAVORÁVEL"
    return "FAVORÁVEL"


def gerar_docx(dados, respostas, observacoes, conclusao, analista, matricula, setor):

    if not os.path.exists("modelo_parecer.docx"):
        st.error("Template modelo_parecer.docx não encontrado")
        st.stop()

    doc = DocxTemplate("modelo_parecer.docx")

    grupos = {}

    for p in perguntas:
        resp = respostas[p["id"]]

        if resp in p.get("regras", {}):
            grupo = p["grupo"]
            regra = p["regras"][resp]
            obs = observacoes[p["id"]]

            texto = regra["texto"]

            if obs.strip():
                texto += f"\nObservação: {obs}"

            grupos.setdefault(grupo, []).append(texto)

rt = RichText()
contador = 1

if grupos:
    for grupo, itens in grupos.items():
        # TÍTULO EM NEGRITO
        rt.add(grupo.upper(), bold=True)
        rt.add("\n\n")

        for item in itens:
            rt.add(f"{contador}. {item}")
            rt.add("\n\n")
            contador += 1
else:
    rt.add("Não foram identificadas inconformidades.")

inconformidades_texto = rt

context = {
    "protocolo": dados["protocolo"],
    "tipo": dados["tipo"],
    "interessado": dados["interessado"],
    "n_lotes": dados["n_lotes"],
    "inconformidades": inconformidades_texto,
    "conclusao": conclusao,
    "data": f"Data: {datetime.now().strftime('%d/%m/%Y')}",
    "analista": f"Analista: {analista}",
    "matricula": matricula,
    "setor": setor
    }

    doc.render(context)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return buffer

# -------------------------
# INTERFACE
# -------------------------
st.title("Sistema de Parecer Urbanístico")

st.header("Dados do Empreendimento")
protocolo = st.text_input("N° Protocolo")
tipo = st.selectbox("Tipo do Empreendimento", ["Loteamento", "Condomínio fechado de lotes"])
interessado = st.text_input("Requerente")
n_lotes = st.number_input("Número de Lotes", min_value=1)

st.header("Dados do Analista")
analista = st.text_input("Nome do Analista")
matricula = st.text_input("Matrícula")
setor = st.text_input("Setor")

st.header("Análise")

respostas = {}
observacoes = {}

# ORGANIZAÇÃO POR GRUPO
grupos_ui = {}
for p in perguntas:
    grupos_ui.setdefault(p["grupo"], []).append(p)

for grupo, lista in grupos_ui.items():
    st.subheader(grupo)

    for p in lista:
        respostas[p["id"]] = st.selectbox(
            p["pergunta"],
            p["opcoes"],
            key=p["id"]
        )

        observacoes[p["id"]] = st.text_area(
            "Observação do analista",
            key=f"obs_{p['id']}"
        )

# -------------------------
# GERAR DOCUMENTO
# -------------------------
if st.button("Gerar Parecer"):

    dados = {
        "protocolo": protocolo,
        "tipo": tipo,
        "interessado": interessado,
        "n_lotes": n_lotes
    }

    conclusao = definir_conclusao(respostas)

    arquivo = gerar_docx(
        dados,
        respostas,
        observacoes,
        conclusao,
        analista,
        matricula,
        setor
    )

    st.download_button(
        label="📄 Baixar Parecer (.docx)",
        data=arquivo,
        file_name="parecer_urbanistico.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
