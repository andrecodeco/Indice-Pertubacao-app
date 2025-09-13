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

    def __init__(self):
        self.duracao_acumulada_ticks = [0]
        self.ticks_dados = []
        self.eventos_dados = []
        self.indices_perturbacao = []
        self.nome_arquivo = ""
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
            self.nome_arquivo = os.path.basename(caminho_arquivo)
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
                            todos_eventos.append({'inicio': inicio_ticks,
                                                 'duracao_ticks': duracao_ticks,
                                                 'nota': msg.note,
                                                 'track': i})
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

    def processar_eventos(self, eventos):
        print(f"\n🔄 Processando {len(eventos)} eventos...")
        self.ticks_dados = []
        self.duracao_acumulada_ticks = [0]
        tempo_acumulado = 0
        for ev in eventos:
            dur_ticks = ev['duracao_ticks']
            self.ticks_dados.append(dur_ticks)
            tempo_acumulado += dur_ticks
            self.duracao_acumulada_ticks.append(tempo_acumulado)
        self.eventos_dados = list(range(len(self.duracao_acumulada_ticks)))
        tempo_beats = tempo_acumulado / self.ticks_per_beat
        print("✅ Processamento completo!")
        print(f" • Eventos: {len(eventos)}")
        print(f" • Duração total: {tempo_beats:.2f} beats")
        segundos = mido.tick2second(tempo_acumulado, self.ticks_per_beat, mido.bpm2tempo(self.tempo_bpm))
        print(f" • Duração total: {segundos:.2f} segundos ({segundos/60:.2f} minutos)")

    def calcular_indices_perturbacao(self, tolerancia_relativa=0.1):
        if len(self.ticks_dados) < 2:
            print("⚠️ Dados insuficientes")
            return []
        self.indices_perturbacao = []
        for i in range(1, len(self.ticks_dados)):
            d_ant = self.ticks_dados[i - 1]
            d_atual = self.ticks_dados[i]
            if d_ant == 0:
                variacao = np.inf
            else:
                variacao = abs(d_atual - d_ant) / d_ant
            if variacao > tolerancia_relativa:
                tempo_ticks = self.duracao_acumulada_ticks[i]
                tempo_beats = tempo_ticks / self.ticks_per_beat
                self.indices_perturbacao.append({
                    'posicao': i,
                    'tempo_beats': tempo_beats,
                    'evento': self.eventos_dados[i],
                    'variacao': variacao,
                })
        print(f"\n🎯 Índices de perturbação detectados: {len(self.indices_perturbacao)}")
        return self.indices_perturbacao

    def gerar_relatorio_completo(self):
        print("\n" + "=" * 70)
        print(f"RELATÓRIO COMPLETO - {self.nome_arquivo}")
        print("=" * 70)
        print(f"📊 Total de eventos: {len(self.eventos_dados)}")
        dur_ticks = self.duracao_acumulada_ticks[-1] if self.duracao_acumulada_ticks else 0
        dur_beats = dur_ticks / self.ticks_per_beat if self.ticks_per_beat > 0 else 0
        dur_sec = mido.tick2second(dur_ticks, self.ticks_per_beat, mido.bpm2tempo(self.tempo_bpm))
        print(f"⏱️ Duração total: {dur_beats:.2f} beats")
        print(f"⏱️ Duração total: {dur_sec:.2f} segundos ({dur_sec/60:.2f} minutos)")
        print(f"🎵 Tempo: {self.tempo_bpm:.1f} BPM")
        print(f"🎯 Índices de perturbação (Ips): {len(self.indices_perturbacao)}\n")
        if self.indices_perturbacao:
            print("DETALHAMENTO DOS ÍNDICES DE PERTURBAÇÃO:")
            print("-" * 50)
            for i, ip in enumerate(self.indices_perturbacao[:20], 1):
                print(f"{i:3d}. Ip{ip['posicao']}:")
                print(f" • Tempo: {ip['tempo_beats']:.2f} beats")
                print(f" • Variação: {ip['variacao']:.1%}")
            if len(self.indices_perturbacao) > 20:
                print(f"\n... e mais {len(self.indices_perturbacao) - 20} perturbações")
        print("=" * 70)

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
        # Apenas “Índice de Perturbação – nome do arquivo analisado”
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.set_title(f"Índice de Perturbação - {self.nome_arquivo}", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        return fig, ax
