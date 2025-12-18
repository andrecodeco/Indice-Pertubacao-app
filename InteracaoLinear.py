"""
Análise de Interação Linear - Teoria do Domínio Sonoro
Integra três dimensões: Eventos (Ev), Pitch (Pi) e Dynamics (Dy)

Baseado na visualização de Syrinx de Debussy
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from collections import defaultdict
from pathlib import Path
import mido


class InteracaoLinear:
    """
    Analisador de Interação Linear para arquivos MIDI.
    Teoria do Domínio Sonoro - Integração Ev/Pi/Dy
    """

    def __init__(self, nome_arquivo=""):
        self.nome_arquivo = nome_arquivo
        self.ticks_per_beat = 480
        self.tempo_bpm = 120.0
        self.tempo_uspb = 500000
        self.time_signature = (4, 4)
        self.notas = []
        self.compassos = defaultdict(list)

        # Dados para perturbação
        self.indices_perturbacao_duracao = []
        self.indices_perturbacao_pitch = []

    def carregar_midi(self, caminho_arquivo: str):
        """Carrega e processa arquivo MIDI extraindo notas com todas as informações."""
        try:
            print(f"\n📂 Carregando arquivo: {caminho_arquivo}")
            if not os.path.exists(caminho_arquivo):
                print(f"❌ Arquivo '{caminho_arquivo}' não encontrado!")
                return None

            mid = mido.MidiFile(caminho_arquivo)
            self.nome_arquivo = self.nome_arquivo or Path(caminho_arquivo).name
            self.ticks_per_beat = mid.ticks_per_beat

            # Processar todas as tracks
            for track in mid.tracks:
                abs_ticks = 0
                notas_ativas = {}

                for msg in track:
                    abs_ticks += msg.time

                    if msg.type == 'set_tempo':
                        self.tempo_uspb = msg.tempo
                        self.tempo_bpm = mido.tempo2bpm(msg.tempo)
                    elif msg.type == 'time_signature':
                        self.time_signature = (msg.numerator, msg.denominator)
                    elif msg.type == 'note_on' and msg.velocity > 0:
                        ch = getattr(msg, 'channel', 0)
                        notas_ativas[(ch, msg.note)] = (abs_ticks, msg.velocity)
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        ch = getattr(msg, 'channel', 0)
                        key = (ch, msg.note)
                        if key in notas_ativas:
                            inicio_ticks, velocity = notas_ativas.pop(key)
                            fim_ticks = abs_ticks

                            # Converter para beats
                            inicio_beats = inicio_ticks / self.ticks_per_beat
                            duracao_beats = (fim_ticks - inicio_ticks) / self.ticks_per_beat

                            self.notas.append({
                                'inicio_beats': inicio_beats,
                                'duracao_beats': max(duracao_beats, 0.001),
                                'pitch': msg.note,
                                'velocity': velocity,
                                'inicio_ticks': inicio_ticks,
                                'duracao_ticks': fim_ticks - inicio_ticks
                            })

            # Ordenar por tempo de início
            self.notas.sort(key=lambda x: x['inicio_beats'])

            if not self.notas:
                print("⚠️ Nenhuma nota encontrada!")
                return None

            # Organizar por compassos
            n, d = self.time_signature
            beats_por_compasso = n * (4 / d)

            for nota in self.notas:
                num_compasso = int(nota['inicio_beats'] // beats_por_compasso)
                self.compassos[num_compasso].append(nota)

            print("✅ Arquivo carregado com sucesso!")
            print(f"🎵 Notas: {len(self.notas)}")
            print(f"📊 Compassos: {len(self.compassos)}")
            print(f"⏱️ BPM: {self.tempo_bpm:.1f}")
            print(f"🎼 Fórmula de compasso: {self.time_signature[0]}/{self.time_signature[1]}")

            return self.notas

        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calcular_perturbacao_duracao(self, tolerancia=0.1):
        """Calcula índices de perturbação baseados na variação de duração."""
        self.indices_perturbacao_duracao = []

        for i in range(1, len(self.notas)):
            dur_ant = self.notas[i-1]['duracao_beats']
            dur_atual = self.notas[i]['duracao_beats']

            if dur_ant > 0:
                variacao = abs(dur_atual - dur_ant) / dur_ant
                if variacao > tolerancia:
                    self.indices_perturbacao_duracao.append({
                        'indice': i,
                        'tempo_beats': self.notas[i]['inicio_beats'],
                        'variacao': variacao,
                        'tipo': 'duracao'
                    })

        print(f"🎯 Perturbações de duração: {len(self.indices_perturbacao_duracao)}")
        return self.indices_perturbacao_duracao

    def calcular_perturbacao_pitch(self, tolerancia_semitons=2):
        """Calcula índices de perturbação baseados em saltos de altura."""
        self.indices_perturbacao_pitch = []

        for i in range(1, len(self.notas)):
            pitch_ant = self.notas[i-1]['pitch']
            pitch_atual = self.notas[i]['pitch']

            intervalo = abs(pitch_atual - pitch_ant)
            if intervalo > tolerancia_semitons:
                self.indices_perturbacao_pitch.append({
                    'indice': i,
                    'tempo_beats': self.notas[i]['inicio_beats'],
                    'intervalo': intervalo,
                    'tipo': 'pitch'
                })

        print(f"🎯 Perturbações de pitch: {len(self.indices_perturbacao_pitch)}")
        return self.indices_perturbacao_pitch

    def plotar_interacao_linear(self, compasso_inicio=1, compasso_fim=None,
                                 mostrar_perturbacoes=True, normalizar_pitch=True):
        """
        Plota gráfico de Interação Linear com três dimensões:
        - Ev (Eventos): linha preta - progressão dos eventos
        - Pi (Pitch): círculos vermelhos - alturas das notas
        - Dy (Dynamics): linha azul - dinâmica/velocidade
        """
        if not self.notas:
            print("⚠️ Sem dados para plotar")
            return None, None

        # Configurar intervalo de compassos
        n, d = self.time_signature
        beats_por_compasso = n * (4 / d)

        if compasso_fim is None:
            compasso_fim = max(self.compassos.keys()) + 1

        # Filtrar notas no intervalo
        inicio_beats = (compasso_inicio - 1) * beats_por_compasso
        fim_beats = compasso_fim * beats_por_compasso

        notas_filtradas = [
            nota for nota in self.notas
            if inicio_beats <= nota['inicio_beats'] < fim_beats
        ]

        if not notas_filtradas:
            print("⚠️ Nenhuma nota no intervalo selecionado")
            return None, None

        # Preparar dados
        tempos = [nota['inicio_beats'] for nota in notas_filtradas]
        pitches = [nota['pitch'] for nota in notas_filtradas]
        velocities = [nota['velocity'] for nota in notas_filtradas]
        duracoes = [nota['duracao_beats'] for nota in notas_filtradas]

        # Normalizar pitch para visualização (relativo ao pitch mínimo)
        pitch_min = min(pitches)
        pitch_max = max(pitches)

        if normalizar_pitch:
            # Escalar pitches para faixa de eventos
            pitches_norm = [(p - pitch_min) for p in pitches]
        else:
            pitches_norm = pitches

        # Normalizar velocidade para valores negativos (abaixo do eixo)
        vel_max = max(velocities) if velocities else 127
        dynamics_norm = [-(v / vel_max) * 4 for v in velocities]  # Escala de 0 a -4

        # Criar figura
        fig, ax = plt.subplots(figsize=(16, 10))

        # Calcular eventos por compasso (como no original)
        eventos_y = []
        evento_atual = 0
        compasso_anterior = -1

        for nota in notas_filtradas:
            compasso_nota = int(nota['inicio_beats'] // beats_por_compasso)
            if compasso_nota != compasso_anterior:
                evento_atual = 0
                compasso_anterior = compasso_nota
            eventos_y.append(evento_atual)
            evento_atual += 1

        # ===== PLOTAR EVENTOS (Ev) - Linha preta =====
        for i in range(len(notas_filtradas)):
            x = tempos[i]
            y = eventos_y[i]

            # Ponto do evento
            ax.plot(x, y, 'ko', markersize=6, zorder=5)

            # Linha conectando ao próximo evento (se houver)
            if i < len(notas_filtradas) - 1:
                x_next = tempos[i + 1]
                y_next = eventos_y[i + 1]
                # Linha diagonal para próximo evento
                ax.plot([x, x + duracoes[i]], [y, y + 1], 'k-', linewidth=1.5, zorder=4)

        # ===== PLOTAR PITCH (Pi) - Círculos vermelhos =====
        for i in range(len(notas_filtradas)):
            x_start = tempos[i]
            x_end = x_start + duracoes[i]
            y_pitch = pitches_norm[i]

            # Círculo vermelho vazio no início
            ax.plot(x_start, y_pitch, 'ro', markersize=8, markerfacecolor='white',
                   markeredgewidth=1.5, zorder=6)

            # Linha horizontal vermelha (duração da nota)
            ax.plot([x_start, x_end], [y_pitch, y_pitch], 'r-', linewidth=2, zorder=3)

            # Círculo vermelho vazio no fim
            ax.plot(x_end, y_pitch, 'ro', markersize=6, markerfacecolor='white',
                   markeredgewidth=1, zorder=6)

            # Linha vertical tracejada conectando Ev a Pi
            ax.plot([x_start, x_start], [eventos_y[i], y_pitch],
                   color='gray', linestyle=':', linewidth=0.8, alpha=0.6, zorder=2)

        # ===== PLOTAR DYNAMICS (Dy) - Linha azul =====
        ax.plot(tempos, dynamics_norm, 'b-', linewidth=1.5, zorder=4, alpha=0.8)
        ax.plot(tempos, dynamics_norm, 'bo', markersize=5, zorder=5)

        # ===== MARCAR PERTURBAÇÕES =====
        if mostrar_perturbacoes:
            # Perturbações de duração (marcador especial)
            for ip in self.indices_perturbacao_duracao:
                idx_global = ip['indice']
                # Encontrar no array filtrado
                for i, nota in enumerate(notas_filtradas):
                    if self.notas.index(nota) == idx_global:
                        ax.annotate(f'Ip_d', (tempos[i], eventos_y[i] + 0.3),
                                   fontsize=8, color='darkred',
                                   bbox=dict(boxstyle='round,pad=0.2',
                                           facecolor='yellow', alpha=0.7))
                        break

            # Perturbações de pitch
            for ip in self.indices_perturbacao_pitch:
                idx_global = ip['indice']
                for i, nota in enumerate(notas_filtradas):
                    if self.notas.index(nota) == idx_global:
                        pitch_y = pitches_norm[i]
                        ax.annotate(f'Ip_p', (tempos[i] + 0.1, pitch_y + 0.3),
                                   fontsize=8, color='darkblue',
                                   bbox=dict(boxstyle='round,pad=0.2',
                                           facecolor='lightblue', alpha=0.7))
                        break

        # ===== LINHAS DE COMPASSO =====
        max_tempo = max(tempos) + max(duracoes) if duracoes else max(tempos) + 1
        total_compassos = int(np.ceil(max_tempo / beats_por_compasso)) + 1

        for m in range(total_compassos + 1):
            x_bar = m * beats_por_compasso
            if inicio_beats <= x_bar <= fim_beats:
                ax.axvline(x=x_bar, color='gray', linestyle='--',
                          linewidth=0.8, alpha=0.4, zorder=1)

        # ===== CONFIGURAR EIXOS =====
        ax.axhline(y=0, color='black', linewidth=0.5, zorder=1)

        ax.set_xlabel('beats', fontsize=12)
        ax.set_ylabel('Ev, Pi, Dy', fontsize=12, color='black')

        # Título
        nome_sem_ext = Path(self.nome_arquivo).stem if self.nome_arquivo else "MIDI"
        ax.set_title(f'{nome_sem_ext} — Interação Linear (c.{compasso_inicio}-{compasso_fim})',
                    fontsize=14, fontweight='bold')

        # Limites
        y_max = max(max(eventos_y), max(pitches_norm)) + 2
        y_min = min(dynamics_norm) - 1
        ax.set_xlim(inicio_beats - 0.5, fim_beats + 0.5)
        ax.set_ylim(y_min, y_max)

        # Ticks do eixo X (beats)
        beat_ticks = np.arange(int(inicio_beats), int(fim_beats) + 1, 1)
        ax.set_xticks(beat_ticks)
        ax.set_xticklabels([str(int(b)) for b in beat_ticks])

        # Ticks do eixo Y (inteiros)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        # Grid
        ax.grid(True, alpha=0.2, linestyle=':', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Legenda
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='black', marker='o', linestyle='-',
                   markersize=6, label='Ev (Eventos)'),
            Line2D([0], [0], color='red', marker='o', linestyle='-',
                   markerfacecolor='white', markersize=8, label='Pi (Pitch)'),
            Line2D([0], [0], color='blue', marker='o', linestyle='-',
                   markersize=5, label='Dy (Dynamics)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

        plt.tight_layout()
        return fig, ax

    def gerar_relatorio(self):
        """Gera relatório completo da análise."""
        print("\n" + "=" * 70)
        print(f"RELATÓRIO - INTERAÇÃO LINEAR")
        print(f"Arquivo: {self.nome_arquivo}")
        print("=" * 70)
        print(f"🎵 Total de notas: {len(self.notas)}")
        print(f"📊 Compassos: {len(self.compassos)}")
        print(f"⏱️ BPM: {self.tempo_bpm:.1f}")
        print(f"🎼 Fórmula: {self.time_signature[0]}/{self.time_signature[1]}")

        if self.notas:
            pitches = [n['pitch'] for n in self.notas]
            print(f"\n📈 Pitch: {min(pitches)} - {max(pitches)} (MIDI)")

            duracoes = [n['duracao_beats'] for n in self.notas]
            print(f"⏳ Duração: {min(duracoes):.3f} - {max(duracoes):.3f} beats")

            velocities = [n['velocity'] for n in self.notas]
            print(f"🔊 Velocity: {min(velocities)} - {max(velocities)}")

        print(f"\n🎯 Perturbações de duração: {len(self.indices_perturbacao_duracao)}")
        print(f"🎯 Perturbações de pitch: {len(self.indices_perturbacao_pitch)}")
        print("=" * 70)


def analisar_interacao_linear(caminho_arquivo: str, compasso_inicio=1,
                               compasso_fim=None, tolerancia_duracao=0.1,
                               tolerancia_pitch=2):
    """Função helper para análise rápida."""
    print("\n" + "=" * 70)
    print("🎵 ANÁLISE DE INTERAÇÃO LINEAR - TEORIA DO DOMÍNIO SONORO")
    print("=" * 70)

    analisador = InteracaoLinear()
    notas = analisador.carregar_midi(caminho_arquivo)

    if notas:
        analisador.calcular_perturbacao_duracao(tolerancia_duracao)
        analisador.calcular_perturbacao_pitch(tolerancia_pitch)
        analisador.gerar_relatorio()

        fig, ax = analisador.plotar_interacao_linear(
            compasso_inicio=compasso_inicio,
            compasso_fim=compasso_fim
        )

        if fig:
            plt.show()

        return analisador

    return None


if __name__ == "__main__":
    # Configuração
    ARQUIVO_MIDI = "base.midi"  # ou "teste.midi"
    COMPASSO_INICIO = 1
    COMPASSO_FIM = 8  # None = todos

    if os.path.exists(ARQUIVO_MIDI):
        analisar_interacao_linear(
            ARQUIVO_MIDI,
            compasso_inicio=COMPASSO_INICIO,
            compasso_fim=COMPASSO_FIM
        )
    else:
        print(f"\n❌ Arquivo '{ARQUIVO_MIDI}' não encontrado!")
        print(f"📍 Pasta: {os.getcwd()}")

        import glob
        midis = glob.glob("*.mid") + glob.glob("*.midi")
        if midis:
            print(f"\n📁 Arquivos MIDI disponíveis:")
            for m in midis:
                print(f"   • {m}")
