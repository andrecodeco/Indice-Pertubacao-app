import os
import numpy as np
import matplotlib
import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import mido

class IndicePerturbacaoMIDI:
    """
    Analisador de Índice de Perturbação para arquivos MIDI.
    Teoria do Domínio Sonoro - Tempo em BEATS
    """
    def __init__(self, nome_arquivo=""):
        self.duracao_acumulada_ticks = [0]
        self.ticks_dados = []
        self.eventos_dados = []
        self.indices_perturbacao = []
        self.nome_arquivo = nome_arquivo
        self.tempo_bpm = 120.0
        self.ticks_per_beat = 480
        self.figura_unidade_tempo = "Semínima"

    def carregar_midi(self, caminho_arquivo: str, max_eventos: int | None = None, eventos_inicio: int = 0):
        try:
            print(f"\n📂 Carregando arquivo: {caminho_arquivo}")
            if not os.path.exists(caminho_arquivo):
                print(f"❌ Arquivo '{caminho_arquivo}' não encontrado!")
                print(f"📍 Pasta atual: {os.getcwd()}")
                return None
            mid = mido.MidiFile(caminho_arquivo)
            # NÃO sobreescrever o nome do arquivo!
            self.ticks_per_beat = mid.ticks_per_beat
            tempo_uspb = None
            for msg in mid:
                if msg.type == "set_tempo":
                    tempo_uspb = msg.tempo
                    break
            self.tempo_bpm = mido.tempo2bpm(tempo_uspb) if tempo_uspb is not None else 120.0
            print("✅ Arquivo carregado com sucesso!")
            print(f"📊 Tracks: {len(mid.tracks)}")
            print(f"🎵 Ticks per beat: {self.ticks_per_beat}, BPM: {self.tempo_bpm:.2f}")

            todos_eventos = []
            for i, track in enumerate(mid.tracks):
                tempo_acumulado = 0
                notas_ativas = {}
                for msg in track:
                    tempo_acumulado += msg.time
                    if msg.type == "note_on" and msg.velocity > 0:
                        notas_ativas[msg.note] = tempo_acumulado
                    elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                        if msg.note in notas_ativas:
                            inicio_ticks = notas_ativas[msg.note]
                            duracao_ticks = tempo_acumulado - inicio_ticks
                            todos_eventos.append({
                                'inicio': inicio_ticks,
                                'duracao_ticks': duracao_ticks,
                                'nota': msg.note,
                                'track': i
                            })
                            del notas_ativas[msg.note]

            print(f"📝 Total eventos: {len(todos_eventos)}")
            if not todos_eventos:
                print("⚠️ Nenhuma nota encontrada!")
                return None

            todos_eventos.sort(key=lambda e: e['inicio'])
            eventos_selecionados = todos_eventos[eventos_inicio:]
            if max_eventos is not None:
                eventos_selecionados = eventos_selecionados[:max_eventos]

            print(f"🎯 Processando {len(eventos_selecionados)} eventos (início: {eventos_inicio})")
            self.processar_eventos(eventos_selecionados)
            return eventos_selecionados

        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ... (os demais métodos permanecem iguais) ...

    def plotar_grafico(self, max_labels=20, mostrar_apenas_principais=True):
        if not self.duracao_acumulada_ticks:
            print("⚠️ Sem dados para plotar")
            return None, None
        tempos_beats = [ticks / self.ticks_per_beat for ticks in self.duracao_acumulada_ticks]
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.plot(tempos_beats, self.eventos_dados, "ko", markersize=3, alpha=0.8, label="Eventos")
        ax.plot(tempos_beats, self.eventos_dados, "b-", linewidth=1, alpha=0.3)
        pontos_ip = self.indices_perturbacao
        if pontos_ip:
            for ip in pontos_ip:
                ax.plot(ip["tempo_beats"], ip["evento"], "ro", markersize=7, alpha=0.9)
            if mostrar_apenas_principais and len(pontos_ip) > max_labels:
                perturbacoes_com_label = sorted(
                    pontos_ip, key=lambda x: x["variacao"], reverse=True
                )[:max_labels]
            else:
                perturbacoes_com_label = pontos_ip[:max_labels]
            for idx, ip in enumerate(perturbacoes_com_label, start=1):
                ax.text(
                    ip["tempo_beats"],
                    ip["evento"] + 0.5,
                    f"Ip{idx}",
                    fontsize=9,
                    color="red",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8),
                )
        ax.set_xlabel("Tempo (beats)", fontsize=12)
        ax.set_ylabel("Eventos", fontsize=12)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        # Título só com o nome do arquivo original
        ax.set_title(f"Índice de Perturbação - {self.nome_arquivo}", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        return fig, ax
