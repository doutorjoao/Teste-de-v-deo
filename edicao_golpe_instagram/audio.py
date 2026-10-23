"""Builds mix.wav: dialogue (with echo opening), original synthesized score, SFX."""
import os, sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit import EDL, START, TOTAL, T  # noqa: E402

S = os.path.dirname(os.path.abspath(__file__))
SR = 48000
N = int(TOTAL * SR) + SR
rng = np.random.default_rng(3)


def bp(x, lo=None, hi=None, order=4):
    if lo:
        x = sosfilt(butter(order, lo, "hp", fs=SR, output="sos"), x)
    if hi:
        x = sosfilt(butter(order, hi, "lp", fs=SR, output="sos"), x)
    return x


def fades(x, fi=0.012, fo=0.012):
    x = x.copy()
    a, b = int(fi * SR), int(fo * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def at(buf, t, x, g=1.0):
    i = int(round(t * SR))
    j = min(len(buf), i + len(x))
    buf[i:j] += g * x[: j - i]


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)) + 1e-12)


# ------------------------------------------------------------------ dialogue
voice = np.zeros(N)
for k, (clip, a, b, tail) in enumerate(EDL):
    x, sr = sf.read(f"{S}/aud/n{clip}.wav")
    assert sr == SR
    seg = x[int(a * SR):int(b * SR)]
    if k == 0:
        # distant voice: narrower band, small room + short echo, then a short tail
        dry = bp(seg, 200, 5200)
        pad = np.concatenate([dry, np.zeros(int(1.2 * SR))])
        n_ir = int(0.9 * SR)
        tt = np.arange(n_ir) / SR
        ir = rng.normal(0, 1, n_ir) * np.exp(-tt / 0.16)
        ir = bp(ir, 300, 4200, 2)
        ir[: int(0.012 * SR)] = 0
        wet = fftconvolve(pad, ir)[: len(pad)]
        wet *= 0.42 * rms(dry) / rms(wet)
        room = pad * 0.82 + wet
        out = room.copy()
        for d, g in ((0.21, 0.30), (0.42, 0.13)):
            sh = int(d * SR)
            out[sh:] += g * bp(room[:-sh], 350, 3800, 2)
        out = out[: len(seg) + int(tail * SR)]
        out = fades(out, 0.03, 0.09)   # echo tail closes just before the hard cut
        at(voice, START[k], out)
    else:
        at(voice, START[k], fades(seg, 0.010, 0.014))

# ------------------------------------------------------------------ score
t = np.arange(N) / SR
BEAT = 60 / 72
mus_on = START[1]


def sine(f, ph=0.0):
    return np.sin(2 * np.pi * f * t + ph)


drone = (0.55 * sine(55) + 0.35 * sine(110.3) + 0.22 * sine(82.41) + 0.12 * sine(164.6)
         + 0.08 * sine(220.6)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * t))
drone = bp(drone, 35, 900, 2)

# pad: Am - F - Dm - E, two bars each
chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (146.83, 174.61, 220.0), (164.81, 207.65, 246.94)]
pad = np.zeros(N)
bar = BEAT * 4 * 2
for i in range(int(TOTAL / bar) + 2):
    c = chords[i % 4]
    s0, s1 = int((mus_on + i * bar) * SR), int((mus_on + (i + 1) * bar) * SR)
    if s0 >= N:
        break
    s1 = min(s1, N)
    tt = np.arange(s1 - s0) / SR
    env = np.minimum(1, tt / 1.2) * np.minimum(1, (tt[-1] - tt + 1e-3) / 1.0)
    tone = sum(np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt + 0.3) for f in c)
    pad[s0:s1] += tone * env
pad = bp(pad, 120, 1800, 2)

pulse = np.zeros(N)
tick = np.zeros(N)
n_th = int(0.35 * SR)
tt = np.arange(n_th) / SR
thump = np.sin(2 * np.pi * (38 * tt + 22 * 0.06 * (1 - np.exp(-tt / 0.06)))) * np.exp(-tt / 0.11)
n_tk = int(0.03 * SR)
tk = bp(rng.normal(0, 1, n_tk), 2500, 6500, 2) * np.exp(-np.arange(n_tk) / SR / 0.006)
b = 0
while mus_on + b * BEAT < TOTAL:
    tb = mus_on + b * BEAT
    at(pulse, tb, thump, 1.0 if b % 2 == 0 else 0.6)
    at(tick, tb + BEAT / 2, tk, 1.0)
    b += 1


def env_curve(points):
    """piecewise-linear gain over the timeline: [(time, gain), ...]"""
    xs, ys = zip(*points)
    return np.interp(t, xs, ys)


t_gone = T(4, 4.95)           # "foi embora": music stops (pausa sonora)
full = [(0, 0), (mus_on - 0.01, 0), (mus_on + 0.4, 1), (t_gone, 1), (t_gone + 0.12, 0),
        (START[5] - 0.01, 0), (START[5] + 0.6, 0.55), (START[6] - 0.3, 0.55), (START[6] + 0.4, 0.95),
        (START[7], 0.95), (START[7] + 0.6, 0.45), (TOTAL - 2.0, 0.40), (TOTAL - 0.1, 0), (TOTAL + 1, 0)]
rhythm = [(0, 0), (mus_on - 0.01, 0), (mus_on + 0.4, 1), (t_gone, 1), (t_gone + 0.1, 0),
          (START[6] - 0.01, 0), (START[6] + 0.8, 0.9), (START[7], 0.9), (START[7] + 0.5, 0), (TOTAL + 1, 0)]
g_full, g_rh = env_curve(full), env_curve(rhythm)
score = (drone * 1.0 + pad * 0.16) * g_full + (pulse * 0.55 + tick * 0.10) * g_full * g_rh

# duck under the voice (envelope follower)
ve = np.abs(voice)
win = int(0.08 * SR)
ve = np.convolve(ve, np.ones(win) / win, mode="same")
duck = 1 - 0.45 * np.clip(ve / (np.percentile(ve[ve > 1e-4], 70) + 1e-9), 0, 1)
score *= duck

speech_rms = rms(voice[voice != 0])
mus_rms = rms(score[int(mus_on * SR):int(t_gone * SR)])
score *= (speech_rms * 10 ** (-17 / 20)) / mus_rms     # bed ~17 dB under the voice

# ------------------------------------------------------------------ SFX
sfx = np.zeros(N)
# 1) discreet impact on the cut from the white opening to the camera
n_im = int(0.6 * SR)
ti = np.arange(n_im) / SR
f_inst = 40 + 80 * np.exp(-ti / 0.07)
impact = np.sin(2 * np.pi * np.cumsum(f_inst) / SR) * np.exp(-ti / 0.16)
impact += bp(rng.normal(0, 1, n_im), 80, 1200, 2) * np.exp(-ti / 0.03) * 0.5
at(sfx, START[1], impact / np.max(np.abs(impact)) * 0.30)


def ping(f1, f2, amp):
    n = int(0.42 * SR)
    tt = np.arange(n) / SR
    s = np.zeros(n)
    for f, d, a in ((f1, 0.0, 1.0), (f2, 0.085, 1.0)):
        k = tt - d
        m = k >= 0
        s[m] += a * (np.sin(2 * np.pi * f * k[m]) + 0.18 * np.sin(2 * np.pi * 2 * f * k[m])) * np.exp(-k[m] / 0.09)
    return s / np.max(np.abs(s)) * amp


p_soft = ping(1318.5, 1760.0, 0.13)
at(sfx, T(2, 7.74), p_soft)                 # "Eu consigo resolver agora."
at(sfx, T(3, 1.10), p_soft)                 # Pagamento pelo serviço
p_ins = ping(1396.9, 1864.7, 0.15)
at(sfx, T(3, 3.40), p_ins)                  # Taxa de desbloqueio — a bit more insistent
at(sfx, T(3, 3.40) + 0.20, p_ins * 0.85)

mix = voice + score + sfx
mix = mix[: int(TOTAL * SR)]
mix = np.stack([mix, mix], 1)
sf.write(f"{S}/mix_raw.wav", mix.astype(np.float32), SR, subtype="FLOAT")
print("speech rms", speech_rms, "peak", np.max(np.abs(mix)), "dur", len(mix) / SR)
