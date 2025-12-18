"""
================================================================================
TEORIA DO DOMÍNIO SONORO - Análise Integrada
================================================================================
Integra análise de:
- Índice de Perturbação de Duração (Ip_d)
- Índice de Perturbação de Pitch/Altura (Ip_p)
- Visualização de Interação Linear (Ev, Pi, Dy)

Autor: André Codeço
================================================================================
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from collections import defaultdict
from pathlib import Path

try:
    import mido
except ImportError:
    print("❌ Biblioteca 'mido' não encontrada!")
    print("   Instale com: pip install mido")
    exit(1)


# ==============================================================================
# CLASSE PRINCIPAL - DOMÍNIO SONORO
# ==============================================================================

class DominioSonoro:
    """
    Analisador completo para a Teoria do Domínio Sonoro.
    Integra análise de Eventos (Ev), Pitch (Pi) e Dynamics (Dy).
    """

    def __init__(self, nome_arquivo=""):
        # Metadados do arquivo
        self.nome_arquivo = nome_arquivo
        self.ticks_per_beat = 480
        self.tempo_bpm = 120.0
        self.tempo_uspb = 500000  # microsegundos por beat
        self.time_signature = (4, 4)

        # Dados das notas
        self.notas = []
        self.compassos = defaultdict(list)

        # Índices de perturbação
        self.indices_perturbacao_duracao = []
        self.indices_perturbacao_pitch = []

        # Dados processados para plotagem
        self.duracao_acumulada_beats = [0]
        self.eventos_dados = []

    # ==========================================================================
    # CARREGAMENTO E PROCESSAMENTO MIDI
    # ==========================================================================

    def carregar_midi(self, caminho_arquivo: str):
        """
        Carrega e processa arquivo MIDI extraindo todas as informações das notas.

        Args:
            caminho_arquivo: Caminho para o arquivo .mid ou .midi

        Returns:
            Lista de notas ou None se houver erro
        """
        try:
            print(f"\n{'='*70}")
            print(f"📂 CARREGANDO ARQUIVO MIDI")
            print(f"{'='*70}")
            print(f"Arquivo: {caminho_arquivo}")

            if not os.path.exists(caminho_arquivo):
                print(f"❌ Arquivo não encontrado!")
                print(f"📍 Pasta atual: {os.getcwd()}")
                return None

            # Carregar arquivo MIDI
            mid = mido.MidiFile(caminho_arquivo)
            self.nome_arquivo = self.nome_arquivo or Path(caminho_arquivo).name
            self.ticks_per_beat = mid.ticks_per_beat

            # Processar todas as tracks
            for track in mid.tracks:
                abs_ticks = 0
                notas_ativas = {}

                for msg in track:
                    abs_ticks += msg.time

                    # Capturar tempo (BPM)
                    if msg.type == 'set_tempo':
                        self.tempo_uspb = msg.tempo
                        self.tempo_bpm = mido.tempo2bpm(msg.tempo)

                    # Capturar fórmula de compasso
                    elif msg.type == 'time_signature':
                        self.time_signature = (msg.numerator, msg.denominator)

                    # Note ON
                    elif msg.type == 'note_on' and msg.velocity > 0:
                        ch = getattr(msg, 'channel', 0)
                        notas_ativas[(ch, msg.note)] = (abs_ticks, msg.velocity)

                    # Note OFF
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        ch = getattr(msg, 'channel', 0)
                        key = (ch, msg.note)

                        if key in notas_ativas:
                            inicio_ticks, velocity = notas_ativas.pop(key)
                            fim_ticks = abs_ticks

                            # Converter para beats
                            inicio_beats = inicio_ticks / self.ticks_per_beat
                            duracao_ticks = fim_ticks - inicio_ticks
                            duracao_beats = duracao_ticks / self.ticks_per_beat

                            # Armazenar nota
                            self.notas.append({
                                'inicio_beats': inicio_beats,
                                'duracao_beats': max(duracao_beats, 0.001),
                                'pitch': msg.note,
                                'velocity': velocity,
                                'inicio_ticks': inicio_ticks,
                                'duracao_ticks': duracao_ticks
                            })

            # Ordenar por tempo de início
            self.notas.sort(key=lambda x: x['inicio_beats'])

            if not self.notas:
                print("⚠️ Nenhuma nota encontrada no arquivo!")
                return None

            # Organizar por compassos
            n, d = self.time_signature
            beats_por_compasso = n * (4 / d)

            for nota in self.notas:
                num_compasso = int(nota['inicio_beats'] // beats_por_compasso)
                self.compassos[num_compasso].append(nota)

            # Calcular duração acumulada
            self._calcular_duracao_acumulada()

            # Exibir informações
            print(f"\n✅ Arquivo carregado com sucesso!")
            print(f"{'─'*40}")
            print(f"🎵 Total de notas: {len(self.notas)}")
            print(f"📊 Compassos: {len(self.compassos)}")
            print(f"⏱️  BPM: {self.tempo_bpm:.1f}")
            print(f"🎼 Fórmula de compasso: {self.time_signature[0]}/{self.time_signature[1]}")
            print(f"🎹 Ticks per beat: {self.ticks_per_beat}")

            # Estatísticas das notas
            if self.notas:
                pitches = [n['pitch'] for n in self.notas]
                duracoes = [n['duracao_beats'] for n in self.notas]
                velocities = [n['velocity'] for n in self.notas]

                print(f"\n📈 Estatísticas:")
                print(f"   Pitch: {min(pitches)} - {max(pitches)} (MIDI)")
                print(f"   Duração: {min(duracoes):.3f} - {max(duracoes):.3f} beats")
                print(f"   Velocity: {min(velocities)} - {max(velocities)}")

                # Duração total
                duracao_total_beats = self.duracao_acumulada_beats[-1]
                duracao_total_segundos = mido.tick2second(
                    int(duracao_total_beats * self.ticks_per_beat),
                    self.ticks_per_beat,
                    self.tempo_uspb
                )
                print(f"   Duração total: {duracao_total_beats:.2f} beats ({duracao_total_segundos:.1f}s)")

            return self.notas

        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calcular_duracao_acumulada(self):
        """Calcula a duração acumulada para o gráfico de perturbação."""
        self.duracao_acumulada_beats = [0]
        tempo_acumulado = 0

        for nota in self.notas:
            tempo_acumulado += nota['duracao_beats']
            self.duracao_acumulada_beats.append(tempo_acumulado)

        self.eventos_dados = list(range(len(self.duracao_acumulada_beats)))

    # ==========================================================================
    # CÁLCULO DE ÍNDICES DE PERTURBAÇÃO
    # ==========================================================================

    def calcular_perturbacao_duracao(self, tolerancia=0.1):
        """
        Calcula índices de perturbação baseados na variação de duração.

        Args:
            tolerancia: Variação relativa mínima para considerar perturbação (0.1 = 10%)

        Returns:
            Lista de índices de perturbação de duração
        """
        self.indices_perturbacao_duracao = []

        for i in range(1, len(self.notas)):
            dur_ant = self.notas[i - 1]['duracao_beats']
            dur_atual = self.notas[i]['duracao_beats']

            if dur_ant > 0:
                variacao = abs(dur_atual - dur_ant) / dur_ant

                if variacao > tolerancia:
                    self.indices_perturbacao_duracao.append({
                        'indice': i,
                        'posicao': i,
                        'tempo_beats': self.notas[i]['inicio_beats'],
                        'evento': i,
                        'variacao': variacao,
                        'duracao_anterior': dur_ant,
                        'duracao_atual': dur_atual,
                        'tipo': 'duracao'
                    })

        print(f"\n🎯 Perturbações de DURAÇÃO detectadas: {len(self.indices_perturbacao_duracao)}")
        return self.indices_perturbacao_duracao

    def calcular_perturbacao_pitch(self, tolerancia_semitons=2):
        """
        Calcula índices de perturbação baseados em saltos de altura (pitch).

        Args:
            tolerancia_semitons: Intervalo mínimo em semitons para considerar perturbação

        Returns:
            Lista de índices de perturbação de pitch
        """
        self.indices_perturbacao_pitch = []

        for i in range(1, len(self.notas)):
            pitch_ant = self.notas[i - 1]['pitch']
            pitch_atual = self.notas[i]['pitch']

            intervalo = abs(pitch_atual - pitch_ant)

            if intervalo > tolerancia_semitons:
                self.indices_perturbacao_pitch.append({
                    'indice': i,
                    'posicao': i,
                    'tempo_beats': self.notas[i]['inicio_beats'],
                    'evento': i,
                    'intervalo': intervalo,
                    'pitch_anterior': pitch_ant,
                    'pitch_atual': pitch_atual,
                    'tipo': 'pitch'
                })

        print(f"🎯 Perturbações de PITCH detectadas: {len(self.indices_perturbacao_pitch)}")
        return self.indices_perturbacao_pitch

    def calcular_todas_perturbacoes(self, tol_duracao=0.1, tol_pitch=2):
        """
        Calcula todos os tipos de perturbação de uma vez.

        Args:
            tol_duracao: Tolerância para perturbação de duração
            tol_pitch: Tolerância em semitons para perturbação de pitch
        """
        self.calcular_perturbacao_duracao(tol_duracao)
        self.calcular_perturbacao_pitch(tol_pitch)

    # ==========================================================================
    # PLOTAGEM - ÍNDICE DE PERTURBAÇÃO (ORIGINAL)
    # ==========================================================================

    def plotar_indice_perturbacao(self, max_labels=20, mostrar_principais=True):
        """
        Plota o gráfico original de Índice de Perturbação (Eventos x Tempo).

        Args:
            max_labels: Número máximo de labels Ip a mostrar
            mostrar_principais: Se True, mostra apenas as maiores perturbações

        Returns:
            Tupla (fig, ax) do matplotlib
        """
        if not self.duracao_acumulada_beats:
            print("⚠️ Sem dados para plotar. Carregue um arquivo MIDI primeiro.")
            return None, None

        fig, ax = plt.subplots(figsize=(14, 8))

        # Plotar eventos
        ax.plot(self.duracao_acumulada_beats, self.eventos_dados,
                'ko', markersize=3, alpha=0.8, label='Eventos')
        ax.plot(self.duracao_acumulada_beats, self.eventos_dados,
                'b-', linewidth=1, alpha=0.3)

        # Plotar perturbações de duração
        if self.indices_perturbacao_duracao:
            for ip in self.indices_perturbacao_duracao:
                idx = ip['indice']
                if idx < len(self.duracao_acumulada_beats):
                    ax.plot(self.duracao_acumulada_beats[idx], idx,
                            'ro', markersize=7, alpha=0.9)

            # Adicionar labels
            if mostrar_principais and len(self.indices_perturbacao_duracao) > max_labels:
                ips_com_label = sorted(
                    self.indices_perturbacao_duracao,
                    key=lambda x: x['variacao'],
                    reverse=True
                )[:max_labels]
            else:
                ips_com_label = self.indices_perturbacao_duracao[:max_labels]

            for idx_label, ip in enumerate(ips_com_label, start=1):
                i = ip['indice']
                if i < len(self.duracao_acumulada_beats):
                    ax.text(
                        self.duracao_acumulada_beats[i],
                        i + 0.5,
                        f'Ip{idx_label}',
                        fontsize=9,
                        color='red',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8)
                    )

        # Configurar eixos
        ax.set_xlabel('Tempo (beats)', fontsize=12)
        ax.set_ylabel('Eventos', fontsize=12)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        nome_sem_ext = Path(self.nome_arquivo).stem if self.nome_arquivo else "MIDI"
        ax.set_title(f'Índice de Perturbação — {nome_sem_ext}', fontsize=14, fontweight='bold')

        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        return fig, ax

    # ==========================================================================
    # PLOTAGEM - INTERAÇÃO LINEAR (Ev, Pi, Dy)
    # ==========================================================================

    def plotar_interacao_linear(self, compasso_inicio=1, compasso_fim=None,
                                 mostrar_perturbacoes=True, normalizar_pitch=True):
        """
        Plota gráfico de Interação Linear com três dimensões:
        - Ev (Eventos): linha preta - progressão dos eventos
        - Pi (Pitch): círculos vermelhos - alturas das notas
        - Dy (Dynamics): linha azul - dinâmica/velocidade

        Args:
            compasso_inicio: Primeiro compasso a exibir (1-indexed)
            compasso_fim: Último compasso a exibir (None = todos)
            mostrar_perturbacoes: Se True, mostra marcadores de perturbação
            normalizar_pitch: Se True, normaliza pitch relativo ao mínimo

        Returns:
            Tupla (fig, ax) do matplotlib
        """
        if not self.notas:
            print("⚠️ Sem dados para plotar. Carregue um arquivo MIDI primeiro.")
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
            print(f"⚠️ Nenhuma nota no intervalo de compassos {compasso_inicio}-{compasso_fim}")
            return None, None

        # Preparar dados
        tempos = [nota['inicio_beats'] for nota in notas_filtradas]
        pitches = [nota['pitch'] for nota in notas_filtradas]
        velocities = [nota['velocity'] for nota in notas_filtradas]
        duracoes = [nota['duracao_beats'] for nota in notas_filtradas]

        # Normalizar pitch
        pitch_min = min(pitches)
        if normalizar_pitch:
            pitches_norm = [(p - pitch_min) for p in pitches]
        else:
            pitches_norm = pitches

        # Normalizar velocidade para valores negativos (abaixo do eixo)
        vel_max = max(velocities) if velocities else 127
        dynamics_norm = [-(v / vel_max) * 4 for v in velocities]

        # Criar figura
        fig, ax = plt.subplots(figsize=(16, 10))

        # Calcular eventos Y por compasso
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

            # Linha diagonal para próximo evento
            if i < len(notas_filtradas) - 1:
                ax.plot([x, x + duracoes[i]], [y, y + 1], 'k-', linewidth=1.5, zorder=4)

        # ===== PLOTAR PITCH (Pi) - Círculos vermelhos =====
        for i in range(len(notas_filtradas)):
            x_start = tempos[i]
            x_end = x_start + duracoes[i]
            y_pitch = pitches_norm[i]

            # Círculo vermelho vazio no início
            ax.plot(x_start, y_pitch, 'ro', markersize=8,
                    markerfacecolor='white', markeredgewidth=1.5, zorder=6)

            # Linha horizontal vermelha (duração da nota)
            ax.plot([x_start, x_end], [y_pitch, y_pitch], 'r-', linewidth=2, zorder=3)

            # Círculo vermelho vazio no fim
            ax.plot(x_end, y_pitch, 'ro', markersize=6,
                    markerfacecolor='white', markeredgewidth=1, zorder=6)

            # Linha vertical tracejada conectando Ev a Pi
            ax.plot([x_start, x_start], [eventos_y[i], y_pitch],
                    color='gray', linestyle=':', linewidth=0.8, alpha=0.6, zorder=2)

        # ===== PLOTAR DYNAMICS (Dy) - Linha azul =====
        ax.plot(tempos, dynamics_norm, 'b-', linewidth=1.5, zorder=4, alpha=0.8)
        ax.plot(tempos, dynamics_norm, 'bo', markersize=5, zorder=5)

        # ===== MARCAR PERTURBAÇÕES =====
        if mostrar_perturbacoes:
            # Perturbações de duração
            for ip in self.indices_perturbacao_duracao:
                idx_global = ip['indice']
                for i, nota in enumerate(notas_filtradas):
                    if self.notas.index(nota) == idx_global:
                        ax.annotate('Ip_d', (tempos[i], eventos_y[i] + 0.3),
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
                        ax.annotate('Ip_p', (tempos[i] + 0.1, pitch_y + 0.3),
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
        ax.set_ylabel('Ev, Pi, Dy', fontsize=12)

        nome_sem_ext = Path(self.nome_arquivo).stem if self.nome_arquivo else "MIDI"
        ax.set_title(f'{nome_sem_ext} — Interação Linear (c.{compasso_inicio}-{compasso_fim})',
                     fontsize=14, fontweight='bold')

        # Limites
        y_max = max(max(eventos_y), max(pitches_norm)) + 2
        y_min = min(dynamics_norm) - 1
        ax.set_xlim(inicio_beats - 0.5, fim_beats + 0.5)
        ax.set_ylim(y_min, y_max)

        # Ticks
        beat_ticks = np.arange(int(inicio_beats), int(fim_beats) + 1, 1)
        ax.set_xticks(beat_ticks)
        ax.set_xticklabels([str(int(b)) for b in beat_ticks])
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        # Grid e spines
        ax.grid(True, alpha=0.2, linestyle=':', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Legenda
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

    # ==========================================================================
    # RELATÓRIO
    # ==========================================================================

    def gerar_relatorio(self):
        """Gera relatório completo da análise no console."""
        print("\n" + "=" * 70)
        print("RELATÓRIO COMPLETO - TEORIA DO DOMÍNIO SONORO")
        print("=" * 70)
        print(f"📁 Arquivo: {self.nome_arquivo}")
        print(f"{'─' * 70}")

        print(f"\n📊 DADOS GERAIS:")
        print(f"   • Total de notas: {len(self.notas)}")
        print(f"   • Compassos: {len(self.compassos)}")
        print(f"   • BPM: {self.tempo_bpm:.1f}")
        print(f"   • Fórmula de compasso: {self.time_signature[0]}/{self.time_signature[1]}")

        if self.notas:
            pitches = [n['pitch'] for n in self.notas]
            duracoes = [n['duracao_beats'] for n in self.notas]
            velocities = [n['velocity'] for n in self.notas]

            print(f"\n📈 ESTATÍSTICAS DAS NOTAS:")
            print(f"   • Pitch: {min(pitches)} - {max(pitches)} (MIDI)")
            print(f"   • Duração: {min(duracoes):.3f} - {max(duracoes):.3f} beats")
            print(f"   • Velocity: {min(velocities)} - {max(velocities)}")

            duracao_total = self.duracao_acumulada_beats[-1] if self.duracao_acumulada_beats else 0
            print(f"   • Duração total: {duracao_total:.2f} beats")

        print(f"\n🎯 ÍNDICES DE PERTURBAÇÃO:")
        print(f"   • Perturbações de DURAÇÃO (Ip_d): {len(self.indices_perturbacao_duracao)}")
        print(f"   • Perturbações de PITCH (Ip_p): {len(self.indices_perturbacao_pitch)}")

        # Detalhar perturbações de duração
        if self.indices_perturbacao_duracao:
            print(f"\n{'─' * 70}")
            print("DETALHAMENTO - PERTURBAÇÕES DE DURAÇÃO:")
            print(f"{'─' * 70}")
            for i, ip in enumerate(self.indices_perturbacao_duracao[:15], 1):
                print(f"   {i:2d}. Ip_d no beat {ip['tempo_beats']:.2f}")
                print(f"       Variação: {ip['variacao']:.1%}")
                print(f"       Duração: {ip['duracao_anterior']:.3f} → {ip['duracao_atual']:.3f} beats")
            if len(self.indices_perturbacao_duracao) > 15:
                print(f"\n   ... e mais {len(self.indices_perturbacao_duracao) - 15} perturbações")

        # Detalhar perturbações de pitch
        if self.indices_perturbacao_pitch:
            print(f"\n{'─' * 70}")
            print("DETALHAMENTO - PERTURBAÇÕES DE PITCH:")
            print(f"{'─' * 70}")
            for i, ip in enumerate(self.indices_perturbacao_pitch[:15], 1):
                print(f"   {i:2d}. Ip_p no beat {ip['tempo_beats']:.2f}")
                print(f"       Intervalo: {ip['intervalo']} semitons")
                print(f"       Pitch: {ip['pitch_anterior']} → {ip['pitch_atual']} (MIDI)")
            if len(self.indices_perturbacao_pitch) > 15:
                print(f"\n   ... e mais {len(self.indices_perturbacao_pitch) - 15} perturbações")

        print("\n" + "=" * 70)


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def analisar_midi(caminho_arquivo: str,
                  tipo_grafico='interacao',
                  compasso_inicio=1,
                  compasso_fim=None,
                  tol_duracao=0.1,
                  tol_pitch=2,
                  mostrar_grafico=True):
    """
    Função auxiliar para análise rápida de arquivo MIDI.

    Args:
        caminho_arquivo: Caminho para o arquivo MIDI
        tipo_grafico: 'interacao' para Interação Linear, 'perturbacao' para Índice de Perturbação
        compasso_inicio: Primeiro compasso (para interação linear)
        compasso_fim: Último compasso (None = todos)
        tol_duracao: Tolerância para perturbação de duração
        tol_pitch: Tolerância em semitons para perturbação de pitch
        mostrar_grafico: Se True, exibe o gráfico automaticamente

    Returns:
        Instância de DominioSonoro com a análise completa
    """
    print("\n" + "=" * 70)
    print("🎵 TEORIA DO DOMÍNIO SONORO - ANÁLISE INTEGRADA")
    print("=" * 70)

    analisador = DominioSonoro()
    notas = analisador.carregar_midi(caminho_arquivo)

    if notas:
        # Calcular perturbações
        analisador.calcular_todas_perturbacoes(tol_duracao, tol_pitch)

        # Gerar relatório
        analisador.gerar_relatorio()

        # Plotar gráfico
        if tipo_grafico == 'interacao':
            fig, ax = analisador.plotar_interacao_linear(
                compasso_inicio=compasso_inicio,
                compasso_fim=compasso_fim
            )
        else:
            fig, ax = analisador.plotar_indice_perturbacao()

        if fig and mostrar_grafico:
            plt.show()

        return analisador

    return None


def listar_arquivos_midi():
    """Lista arquivos MIDI na pasta atual."""
    import glob
    midis = glob.glob("*.mid") + glob.glob("*.midi")
    midis += glob.glob("*.MID") + glob.glob("*.MIDI")
    return list(set(midis))


# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    # ╔══════════════════════════════════════════════════════════════════════╗
    # ║                        CONFIGURAÇÕES                                  ║
    # ╚══════════════════════════════════════════════════════════════════════╝

    # Arquivo MIDI para análise
    ARQUIVO_MIDI = "teste.midi"  # Altere para o nome do seu arquivo

    # Tipo de gráfico: 'interacao' ou 'perturbacao'
    TIPO_GRAFICO = 'interacao'

    # Intervalo de compassos (apenas para gráfico de interação)
    COMPASSO_INICIO = 1
    COMPASSO_FIM = 8  # None = todos os compassos

    # Tolerâncias para detecção de perturbação
    TOLERANCIA_DURACAO = 0.1   # 10% de variação
    TOLERANCIA_PITCH = 2       # 2 semitons

    # ╔══════════════════════════════════════════════════════════════════════╗
    # ║                        EXECUÇÃO                                       ║
    # ╚══════════════════════════════════════════════════════════════════════╝

    print("\n" + "█" * 70)
    print("█  TEORIA DO DOMÍNIO SONORO - Análise Integrada")
    print("█  Ev (Eventos) | Pi (Pitch) | Dy (Dynamics)")
    print("█" * 70)

    # Verificar se o arquivo existe
    if os.path.exists(ARQUIVO_MIDI):
        analisador = analisar_midi(
            ARQUIVO_MIDI,
            tipo_grafico=TIPO_GRAFICO,
            compasso_inicio=COMPASSO_INICIO,
            compasso_fim=COMPASSO_FIM,
            tol_duracao=TOLERANCIA_DURACAO,
            tol_pitch=TOLERANCIA_PITCH
        )

        if analisador:
            print("\n✅ Análise concluída com sucesso!")
            print("📊 O gráfico deve estar em uma janela separada.")

            # Exemplo de como gerar ambos os gráficos:
            # print("\n📈 Gerando gráfico de Índice de Perturbação...")
            # fig2, ax2 = analisador.plotar_indice_perturbacao()
            # plt.show()

    else:
        print(f"\n❌ Arquivo '{ARQUIVO_MIDI}' não encontrado!")
        print(f"📍 Pasta atual: {os.getcwd()}")

        # Listar arquivos MIDI disponíveis
        midis = listar_arquivos_midi()
        if midis:
            print(f"\n📁 Arquivos MIDI encontrados nesta pasta:")
            for m in midis:
                print(f"   • {m}")
            print(f"\n💡 Dica: Altere ARQUIVO_MIDI = \"{midis[0]}\"")
        else:
            print("\n⚠️ Nenhum arquivo MIDI encontrado na pasta atual.")
            print("💡 Coloque um arquivo .mid ou .midi na mesma pasta deste script.")
