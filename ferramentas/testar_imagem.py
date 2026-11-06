import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

from detector import Detector
from distancia import (NOME_ZONA, OBJETOS, Calibracao, formatar_metros,
                       zona_da_distancia)

CORES = {0: (61, 214, 140), 1: (245, 184, 61), 2: (255, 107, 97)}


def main():
    p = argparse.ArgumentParser(description='Testa o RéVisão numa foto.')
    p.add_argument('imagem')
    p.add_argument('--confianca', type=float, default=0.5)
    p.add_argument('--linha-1m', type=float, default=0.82)
    p.add_argument('--linha-3m', type=float, default=0.51)
    p.add_argument('--foco', type=float, default=0.87)
    p.add_argument('--perigo', type=float, default=1.0)
    p.add_argument('--atencao', type=float, default=3.0)
    a = p.parse_args()

    imagem = Image.open(a.imagem).convert('RGB')
    detector = Detector(confianca=a.confianca)
    cal = Calibracao(a.linha_1m, a.linha_3m, a.foco)
    achados = detector.detectar_imagem(imagem)
    print(f'Motor: {detector.motor_nome} | {len(achados)} objeto(s) encontrado(s)')

    desenho = ImageDraw.Draw(imagem)
    largura, altura = imagem.size
    espessura = max(2, largura // 300)
    for y, cor in ((a.linha_1m, CORES[2]), (a.linha_3m, CORES[1])):
        desenho.line([(0, y * altura), (largura, y * altura)], fill=cor, width=espessura)
    for d in achados:
        distancia = cal.estimar(d)
        zona = zona_da_distancia(distancia, a.perigo, a.atencao)
        texto = (f'{OBJETOS[d.rotulo][0]} ~{formatar_metros(distancia)} m '
                 f'({NOME_ZONA[zona]}) {d.confianca:.0%}')
        print(f' - {texto} | base y = {d.y1:.3f} | altura = {d.altura:.3f}')
        caixa = [d.x0 * largura, d.y0 * altura, d.x1 * largura, d.y1 * altura]
        desenho.rectangle(caixa, outline=CORES[zona], width=espessura)
        desenho.text((caixa[0] + 4, caixa[1] + 4), texto, fill=CORES[zona])

    saida = os.path.splitext(a.imagem)[0] + '_revisao.png'
    imagem.save(saida)
    print('Imagem salva em', saida)


if __name__ == '__main__':
    main()
