import math
import os
import struct
import wave

PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
TAXA = 44100
FREQUENCIA = 1800
VOLUME = 0.7


def salvar_wav(caminho, amostras):
    with wave.open(caminho, 'wb') as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA)
        arquivo.writeframes(b''.join(struct.pack('<h', int(a * 32767)) for a in amostras))


def bipe(duracao=0.09, rampa=0.006):
    n = int(TAXA * duracao)
    m = int(TAXA * rampa)
    amostras = []
    for i in range(n):
        envelope = min(1.0, i / m, (n - 1 - i) / m)
        amostras.append(VOLUME * envelope * math.sin(2 * math.pi * FREQUENCIA * i / TAXA))
    return amostras


def tom_continuo(duracao=1.0):
    n = int(TAXA * duracao)
    return [VOLUME * 0.9 * math.sin(2 * math.pi * FREQUENCIA * i / TAXA) for i in range(n)]


def icone(caminho, tamanho=512):
    from PIL import Image, ImageDraw
    escala = 4
    t = tamanho * escala
    img = Image.new('RGBA', (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, t - 1, t - 1], radius=int(t * 0.22), fill=(16, 20, 24, 255))

    def p(x, y):
        return (x * t, y * t)

    verde, ambar, vermelho = (61, 214, 140, 255), (245, 184, 61, 255), (255, 107, 97, 255)
    branco = (242, 244, 247, 255)
    w = int(t * 0.04)

    def lado(y):
        return 0.34 * (y - 0.30) / (0.90 - 0.30)

    trechos = ((0.90, 0.76, vermelho), (0.76, 0.60, ambar), (0.60, 0.48, verde))
    for y0, y1, c in trechos:
        for s in (-1, 1):
            d.line([p(0.5 + s * lado(y0), y0), p(0.5 + s * lado(y1), y1)], fill=c, width=w)
        d.line([p(0.5 - lado(y1), y1), p(0.5 + lado(y1), y1)], fill=c, width=w)
    d.rounded_rectangle([p(0.33, 0.12), p(0.67, 0.34)], radius=int(t * 0.04), fill=branco)
    d.rounded_rectangle([p(0.38, 0.09), p(0.48, 0.14)], radius=int(t * 0.015), fill=branco)
    d.ellipse([p(0.43, 0.16), p(0.57, 0.30)], fill=(16, 20, 24, 255))
    d.ellipse([p(0.465, 0.195), p(0.535, 0.265)], fill=ambar)
    img.resize((tamanho, tamanho), Image.LANCZOS).save(caminho)


if __name__ == '__main__':
    os.makedirs(PASTA, exist_ok=True)
    salvar_wav(os.path.join(PASTA, 'bipe.wav'), bipe())
    salvar_wav(os.path.join(PASTA, 'bipe_continuo.wav'), tom_continuo())
    icone(os.path.join(PASTA, 'icone.png'))
    print('Pronto: sons e ícone em', PASTA)
