import streamlit as st
import tempfile
import io
from IndicePetubacao import IndicePerturbacaoMIDI

# Configuração da página (deve ser o primeiro comando Streamlit)
st.set_page_config(
    page_title="Índice de Perturbação",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Injeta meta tags de PWA no HTML
PWA_TAGS = """
<link rel="manifest" href="https://raw.githubusercontent.com/andrecodeco/Indice-Pertubacao-app/main/static/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="IP MIDI">
<link rel="apple-touch-icon" href="https://raw.githubusercontent.com/andrecodeco/Indice-Pertubacao-app/main/static/icon-192.png">
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
