import streamlit as st
import tempfile
import io
import base64
import requests
from IndicePetubacao import IndicePerturbacaoMIDI

# Configuração da página
st.set_page_config(
    page_title="Índice de Perturbação",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Carrega ícone do GitHub e converte para base64 (cache para não baixar toda vez)
@st.cache_data
def carregar_icone_base64(url):
    try:
        r = requests.get(url, timeout=5)
        return base64.b64encode(r.content).decode('utf-8')
    except:
        return ""

ICON_192 = carregar_icone_base64("https://raw.githubusercontent.com/andrecodeco/Indice-Pertubacao-app/main/static/icon-192.png")
ICON_512 = carregar_icone_base64("https://raw.githubusercontent.com/andrecodeco/Indice-Pertubacao-app/main/static/icon-512.png")

# Manifest embutido como data URI (funciona em iPhone)
manifest_json = f'''{{
  "name": "Índice de Perturbação",
  "short_name": "IP MIDI",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0e1117",
  "theme_color": "#1e2327",
  "icons": [
    {{"src": "data:image/png;base64,{ICON_192}", "sizes": "192x192", "type": "image/png"}},
    {{"src": "data:image/png;base64,{ICON_512}", "sizes": "512x512", "type": "image/png"}}
  ]
}}'''
manifest_b64 = base64.b64encode(manifest_json.encode()).decode()

PWA_TAGS = f"""
<link rel="manifest" href="data:application/manifest+json;base64,{manifest_b64}">
<link rel="apple-touch-icon" href="data:image/png;base64,{ICON_192}">
<link rel="apple-touch-icon" sizes="192x192" href="data:image/png;base64,{ICON_192}">
<link rel="apple-touch-icon" sizes="512x512" href="data:image/png;base64,{ICON_512}">
<link rel="icon" type="image/png" href="data:image/png;base64,{ICON_192}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="IP MIDI">
<meta name="theme-color" content="#1e2327">
<meta name="mobile-web-app-capable" content="yes">
"""
st.markdown(PWA_TAGS, unsafe_allow_html=True)

st.title("Análise de Índices de Perturbação MIDI")

uploaded_file = st.file_uploader("Selecione um arquivo MIDI (.mid ou .midi)", type=["mid", "midi"])
max_events = st.number_input("Número máximo de eventos a analisar (0 = todos)", min_value=0, value=0, step=1)

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
        tmp.write(uploaded_file.getvalue())
        caminho_midi = tmp.name

    analisador = IndicePerturbacaoMIDI(nome_arquivo=uploaded_file.name)
    max_ev = None if max_events == 0 else max_events
    eventos = analisador.carregar_midi(caminho_midi, max_eventos=max_ev)

    if eventos:
        analisador.calcular_indices_perturbacao()
        analisador.gerar_relatorio_completo()
        fig, _ = analisador.plotar_grafico()
        if fig:
            st.pyplot(fig)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300)
            buf.seek(0)
            st.download_button(
                label="Download do gráfico (PNG 300 dpi)",
                data=buf,
                file_name="indice_perturbacao.png",
                mime="image/png"
            )
        else:
            st.write("Erro ao gerar o gráfico.")
    else:
        st.write("Erro ao processar o arquivo MIDI.")
else:
    st.write("Por favor, faça upload de um arquivo MIDI para análise.")
