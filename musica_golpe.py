"""Trilha sintetizada para o vídeo do golpe: clima de "investigação" em lá menor, 110 BPM.

Tudo é gerado aqui (sem samples), então não tem problema de direitos autorais.
A estrutura segue a montagem do vídeo:
    intro (suspense: pad, arpejo abrindo, batida de coração) -> virada antes do painel ->
    batida cheia -> respiro com impacto antes da foto -> batida cheia -> final só com pad.
"""
import numpy as np
from scipy import signal

SR = 48000
BPM = 110
TEMPO = 60 / BPM            # um tempo (semínima)
COMPASSO = 4 * TEMPO
# Am - F - Dm - E (menor harmônica, dá a tensão no E)
ACORDES = [(57, 60, 64), (53, 57, 60), (50, 53, 57), (52, 56, 59)]
BAIXOS = [33, 29, 38, 40]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def serra(f, t, fase=0.0):
    x = (f * t + fase) % 1.0
    return 2 * x - 1


def passa_baixa(x, fc, ordem=2):
    b, a = signal.butter(ordem, min(fc, SR / 2 - 100) / (SR / 2))
    return signal.lfilter(b, a, x)


def passa_alta(x, fc, ordem=2):
    b, a = signal.butter(ordem, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def passa_banda(x, f0, f1):
    b, a = signal.butter(2, [f0 / (SR / 2), f1 / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def passa_baixa_variavel(x, cortes, bloco=512):
    """Passa-baixa com corte variando no tempo (um valor por amostra), em blocos."""
    y = np.zeros_like(x)
    zi = None
    for i in range(0, len(x), bloco):
        b, a = signal.butter(2, min(cortes[i], SR / 2 - 100) / (SR / 2))
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        y[i:i + bloco], zi = signal.lfilter(b, a, x[i:i + bloco], zi=zi)
    return y


class Trilha:
    def __init__(self, duracao, inicio_grade):
        self.n = int(duracao * SR)
        self.esq = np.zeros(self.n)
        self.dir = np.zeros(self.n)
        self.t0 = inicio_grade  # onde cai o primeiro compasso
        self.rng = np.random.default_rng(11)

    def compasso(self, k):
        return self.t0 + k * COMPASSO

    def somar(self, som, inicio, ganho=1.0, pan=0.0):
        i = int(round(inicio * SR))
        if i >= self.n:
            return
        if i < 0:
            som, i = som[-i:], 0
        j = min(self.n, i + len(som))
        self.esq[i:j] += som[:j - i] * ganho * np.sqrt(0.5 * (1 - pan))
        self.dir[i:j] += som[:j - i] * ganho * np.sqrt(0.5 * (1 + pan))

    # ------------------------------------------------------------------ instrumentos

    def kick(self, dur=0.45):
        t = np.arange(int(dur * SR)) / SR
        f = 48 + 110 * np.exp(-t * 28)
        fase = 2 * np.pi * np.cumsum(f) / SR
        corpo = np.sin(fase) * np.exp(-t * 6.5)
        clique = self.rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.3
        return np.tanh(1.6 * (corpo + clique))

    def clap(self):
        t = np.arange(int(0.3 * SR)) / SR
        r = passa_banda(self.rng.standard_normal(len(t)), 900, 3500)
        env = np.zeros(len(t))
        for d in (0.0, 0.011, 0.022):
            env += (t >= d) * np.exp(-np.clip(t - d, 0, None) * (90 if d < 0.02 else 14))
        return r * env / 2.2

    def chimbal(self, aberto=False):
        dur = 0.22 if aberto else 0.05
        t = np.arange(int(dur * SR)) / SR
        r = passa_alta(self.rng.standard_normal(len(t)), 7500)
        return r * np.exp(-t * (14 if aberto else 85))

    def pluck(self, f, dur=0.32, brilho=3500):
        t = np.arange(int(dur * SR)) / SR
        x = serra(f, t) * 0.6 + serra(f * 1.004, t, 0.3) * 0.4
        cortes = 300 + brilho * np.exp(-t * 18)
        x = passa_baixa_variavel(x, cortes, 256)
        return x * np.exp(-t * 9) * np.minimum(1, t * 400)

    def baixo(self, midi, dur):
        t = np.arange(int(dur * SR)) / SR
        f = hz(midi)
        x = np.sin(2 * np.pi * f * t) + 0.35 * passa_baixa(serra(f, t), 380)
        env = np.minimum(1, t * 300) * np.exp(-t * 2.5) * np.minimum(1, (dur - t) * 60)
        return np.tanh(1.4 * x) * env

    def pad(self, notas, dur, corte):
        t = np.arange(int(dur * SR)) / SR
        x = np.zeros(len(t))
        for m in notas:
            f = hz(m)
            for det, fase in ((-0.004, 0.0), (0.004, 0.37), (0.0, 0.71)):
                x += serra(f * (1 + det), t, fase)
        x = passa_baixa(x / (3 * len(notas)), corte)
        env = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.3)
        return x * env

    def riser(self, dur):
        m = int(dur * SR)
        t = np.arange(m) / SR
        r = self.rng.standard_normal(m)
        cortes = 400 * (9000 / 400) ** (t / dur)
        x = passa_baixa_variavel(r, cortes)
        return x * (t / dur) ** 2

    def impacto(self):
        t = np.arange(int(1.6 * SR)) / SR
        sub = np.sin(2 * np.pi * (38 + 70 * np.exp(-t * 16)) * t) * np.exp(-t * 2.4)
        ruido = passa_baixa(self.rng.standard_normal(len(t)), 2500) * np.exp(-t * 5) * 0.35
        return np.tanh(1.5 * (sub + ruido))

    # ------------------------------------------------------------------ arranjo

    def tocar(self, secoes, fim_batida, pausa, impacto_em, final):
        """secoes: lista de (compasso_ini, compasso_fim, nome)."""
        kick, clap = self.kick(), self.clap()
        hat_f, hat_a = self.chimbal(), self.chimbal(True)
        total = int(np.ceil((self.n / SR - self.t0) / COMPASSO)) + 1
        for k in range(-1, total):
            c0 = self.compasso(k)
            acorde, raiz = ACORDES[k % 4], BAIXOS[k % 4]
            secao = next((s[2] for s in secoes if s[0] <= k < s[1]), "final")
            # pad abre aos poucos na intro
            corte = {"intro": 600 + 300 * max(k, 0), "cheia": 2200, "final": 1400}[secao]
            self.somar(self.pad(acorde, COMPASSO + 0.3, corte), c0, 0.7, 0)
            for s in range(16):  # semicolcheias
                ts = c0 + s * TEMPO / 4
                em_pausa = pausa[0] <= ts < pausa[1]
                # arpejo
                padrao = [0, 1, 2, 3, 2, 1, 3, 1]
                notas = list(acorde) + [acorde[0] + 12]
                nota = notas[padrao[s % 8]] + 12
                ganho_arp = {"intro": 0.14 + 0.05 * max(k, 0), "cheia": 0.34, "final": 0.26}[secao]
                if not (secao == "intro" and s % 2):
                    pl = self.pluck(hz(nota), brilho=2500 if secao == "intro" else 4200)
                    self.somar(pl, ts, ganho_arp, -0.35 if s % 4 < 2 else 0.35)
                    self.somar(pl, ts + 3 * TEMPO / 4, ganho_arp * 0.35, 0.6 if s % 4 < 2 else -0.6)
                if ts >= fim_batida or em_pausa:
                    continue
                if secao == "cheia":
                    if s in (0, 8, 10):
                        self.somar(kick, ts, 0.65)
                    if s in (4, 12):
                        self.somar(clap, ts, 0.55)
                    self.somar(hat_a if s % 4 == 2 else hat_f, ts, 0.16 if s % 2 else 0.24,
                               0.25)
                    if s % 2 == 0:
                        self.somar(self.baixo(raiz, TEMPO / 2 - 0.02), ts, 0.38)
                elif secao == "intro":
                    # batida de coração: tum-tum no 1 e no 3
                    if s in (0, 8):
                        self.somar(passa_baixa(kick, 400), ts, 0.45)
                        self.somar(passa_baixa(kick, 400), ts + 0.17, 0.3)
                    if k >= 2 and s % 4 == 2:
                        self.somar(hat_f, ts, 0.1, 0.3)
            if secao == "final" and c0 >= final:
                self.somar(self.baixo(raiz, COMPASSO), c0, 0.3)
        # virada de caixa e riser antes da entrada da batida
        entrada = self.compasso(secoes[1][0])
        self.somar(self.riser(COMPASSO), entrada - COMPASSO, 0.25, 0)
        for i in range(12):
            ts = entrada - TEMPO * 2 + i * TEMPO / 6
            self.somar(clap, ts, 0.12 + 0.03 * i)
        self.somar(self.impacto(), entrada, 0.7)
        # respiro: riser curto e impacto na revelação
        self.somar(self.riser(pausa[1] - pausa[0]), pausa[0], 0.22)
        self.somar(self.impacto(), impacto_em, 0.7)

    def estereo(self, fade_fim=2.5):
        x = np.stack([self.esq, self.dir], axis=1)
        t = np.arange(self.n) / SR
        x *= np.clip((self.n / SR - t) / fade_fim, 0, 1)[:, None]
        return x / (np.abs(x).max() + 1e-9)


def compor(duracao, entrada_batida, revelacao, inicio_dicas):
    """Gera a trilha (estéreo, pico 1.0) com a batida entrando no compasso de `entrada_batida`."""
    k_entrada = 4
    t0 = entrada_batida - k_entrada * COMPASSO
    tr = Trilha(duracao, t0)
    # compasso em que a revelação acontece: a batida para meio compasso antes
    k_rev = int(np.floor((revelacao - t0) / COMPASSO))
    meio = tr.compasso(k_rev) + 2 * TEMPO
    pausa = (meio - COMPASSO / 2, meio) if meio > revelacao - 0.4 else (meio, meio + COMPASSO / 2)
    k_final = int(np.ceil((inicio_dicas - t0) / COMPASSO))
    secoes = [(-1, k_entrada, "intro"), (k_entrada, k_final, "cheia")]
    tr.tocar(secoes, fim_batida=tr.compasso(k_final), pausa=pausa, impacto_em=pausa[1],
             final=tr.compasso(k_final))
    return tr.estereo()
