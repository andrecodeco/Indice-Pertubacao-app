"""
App Streamlit para Análise de Interação Linear
Teoria do Domínio Sonoro - Integração Ev/Pi/Dy
"""

import streamlit as st
import tempfile
import io
from InteracaoLinear import InteracaoLinear

st.set_page_config(page_title="Interação Linear - Domínio Sonoro", layout="wide")

st.title("Análise de Interação Linear")
st.markdown("**Teoria do Domínio Sonoro** — Integração Ev (Eventos), Pi (Pitch), Dy (Dynamics)")

# Sidebar com configurações
st.sidebar.header("Configurações")

uploaded_file = st.sidebar.file_uploader(
    "Selecione um arquivo MIDI",
    type=["mid", "midi"]
)

st.sidebar.subheader("Intervalo de Compassos")
col1, col2 = st.sidebar.columns(2)
compasso_inicio = col1.number_input("Início", min_value=1, value=1, step=1)
compasso_fim = col2.number_input("Fim (0=todos)", min_value=0, value=8, step=1)

st.sidebar.subheader("Tolerâncias de Perturbação")
tol_duracao = st.sidebar.slider(
    "Duração (variação relativa)",
    min_value=0.0, max_value=1.0, value=0.1, step=0.05
)
tol_pitch = st.sidebar.slider(
    "Pitch (semitons)",
    min_value=1, max_value=12, value=2, step=1
)

normalizar_pitch = st.sidebar.checkbox("Normalizar Pitch", value=True)
mostrar_perturbacoes = st.sidebar.checkbox("Mostrar Perturbações", value=True)

if uploaded_file is not None:
    # Salvar arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
        tmp.write(uploaded_file.getvalue())
        caminho_midi = tmp.name

    # Criar analisador
    analisador = InteracaoLinear(nome_arquivo=uploaded_file.name)

    # Carregar MIDI
    notas = analisador.carregar_midi(caminho_midi)

    if notas:
        # Calcular perturbações
        analisador.calcular_perturbacao_duracao(tol_duracao)
        analisador.calcular_perturbacao_pitch(tol_pitch)

        # Configurar intervalo
        fim = compasso_fim if compasso_fim > 0 else None

        # Gerar gráfico
        fig, ax = analisador.plotar_interacao_linear(
            compasso_inicio=compasso_inicio,
            compasso_fim=fim,
            mostrar_perturbacoes=mostrar_perturbacoes,
            normalizar_pitch=normalizar_pitch
        )

        if fig:
            st.pyplot(fig)

            # Botão de download
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
            buf.seek(0)

            st.download_button(
                label="Download do gráfico (PNG 300 dpi)",
                data=buf,
                file_name=f"interacao_linear_{uploaded_file.name.rsplit('.', 1)[0]}.png",
                mime="image/png"
            )

        # Mostrar estatísticas
        st.subheader("Estatísticas")
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Notas", len(analisador.notas))
        col2.metric("Compassos", len(analisador.compassos))
        col3.metric("Ip Duração", len(analisador.indices_perturbacao_duracao))
        col4.metric("Ip Pitch", len(analisador.indices_perturbacao_pitch))

        # Expandir detalhes
        with st.expander("Ver detalhes das perturbações"):
            if analisador.indices_perturbacao_duracao:
                st.markdown("**Perturbações de Duração:**")
                for i, ip in enumerate(analisador.indices_perturbacao_duracao[:10], 1):
                    st.write(f"{i}. Beat {ip['tempo_beats']:.2f} — Variação: {ip['variacao']:.1%}")

            if analisador.indices_perturbacao_pitch:
                st.markdown("**Perturbações de Pitch:**")
                for i, ip in enumerate(analisador.indices_perturbacao_pitch[:10], 1):
                    st.write(f"{i}. Beat {ip['tempo_beats']:.2f} — Intervalo: {ip['intervalo']} semitons")

    else:
        st.error("Erro ao processar o arquivo MIDI.")

else:
    st.info("👆 Faça upload de um arquivo MIDI na barra lateral para começar a análise.")

    st.markdown("""
    ### Sobre esta análise

    O gráfico de **Interação Linear** visualiza três dimensões musicais simultaneamente:

    - **Ev (Eventos)** — Linha preta: progressão temporal dos eventos musicais
    - **Pi (Pitch)** — Círculos vermelhos: alturas das notas com suas durações
    - **Dy (Dynamics)** — Linha azul: dinâmica/intensidade (velocity MIDI)

    As linhas verticais tracejadas conectam cada evento à sua altura correspondente,
    permitindo visualizar a relação entre progressão temporal e movimento melódico.

    **Índices de Perturbação:**
    - `Ip_d`: Perturbação de duração (variação significativa entre durações consecutivas)
    - `Ip_p`: Perturbação de pitch (saltos melódicos significativos)
    """)
