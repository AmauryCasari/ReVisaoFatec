import json
import os
import sys

from distancia import Calibracao

NO_ANDROID = 'ANDROID_ARGUMENT' in os.environ or hasattr(sys, 'getandroidapilevel')

PADRAO = {
    'som': True,
    'volume': 0.8,
    'confianca': 0.5,
    'dist_perigo': 1.0,
    'dist_atencao': 3.0,
    'camera': 'back' if NO_ANDROID else '0',
    'espelhar': False,
    'escala_texto': 1.0,
    'linha_1m': 0.82,
    'linha_3m': 0.51,
    'foco': 1.0,
    'linhas_do_chao': False,
    'distancia_medida': 3.0,
    'altura_pessoa': 1.70,
}

LIMITES = {
    'volume': (0.0, 1.0),
    'confianca': (0.3, 0.9),
    'dist_perigo': (0.5, 2.5),
    'dist_atencao': (1.0, 8.0),
    'escala_texto': (0.8, 1.6),
    'linha_1m': (0.1, 1.0),
    'linha_3m': (0.05, 0.95),
    'foco': (0.3, 3.0),
    'altura_pessoa': (1.0, 2.2),
    'distancia_medida': (1.0, 5.0),
}


def _mesmo_tipo(valor, padrao):
    if isinstance(padrao, bool):
        return isinstance(valor, bool)
    if isinstance(padrao, float):
        return isinstance(valor, (int, float)) and not isinstance(valor, bool)
    return isinstance(valor, type(padrao))


class Configuracoes:
    def __init__(self, pasta):
        self.caminho = os.path.join(pasta, 'revisao_config.json')
        self.valores = dict(PADRAO)
        self.carregar()

    def __getitem__(self, chave):
        return self.valores[chave]

    def __setitem__(self, chave, valor):
        if chave not in PADRAO:
            raise KeyError(chave)
        self.valores[chave] = valor

    def carregar(self):
        try:
            with open(self.caminho, encoding='utf-8') as arquivo:
                dados = json.load(arquivo)
        except (OSError, ValueError):
            dados = {}
        if isinstance(dados, dict):
            for chave, padrao in PADRAO.items():
                if chave in dados and _mesmo_tipo(dados[chave], padrao):
                    self.valores[chave] = dados[chave]
        self.validar()

    def validar(self):
        v = self.valores
        for chave, (minimo, maximo) in LIMITES.items():
            v[chave] = float(min(maximo, max(minimo, v[chave])))
        antigas = {'traseira': PADRAO['camera'], 'frontal': 'front' if NO_ANDROID else '1'}
        v['camera'] = antigas.get(v['camera'], v['camera'])
        if NO_ANDROID and v['camera'] not in ('back', 'front'):
            v['camera'] = 'back'
        if not NO_ANDROID and not v['camera'].isdigit():
            v['camera'] = '0'
        if v['dist_atencao'] < v['dist_perigo'] + 0.5:
            v['dist_atencao'] = round(v['dist_perigo'] + 0.5, 1)
        if v['linha_3m'] > v['linha_1m'] - 0.05:
            v['linha_1m'], v['linha_3m'] = PADRAO['linha_1m'], PADRAO['linha_3m']

    def salvar(self):
        self.validar()
        try:
            os.makedirs(os.path.dirname(self.caminho) or '.', exist_ok=True)
            temporario = self.caminho + '.tmp'
            with open(temporario, 'w', encoding='utf-8') as arquivo:
                json.dump(self.valores, arquivo, ensure_ascii=False, indent=2)
            os.replace(temporario, self.caminho)
            return True
        except OSError:
            return False

    def restaurar(self, manter_calibracao=True):
        calibracao = {k: self.valores[k] for k in ('linha_1m', 'linha_3m', 'foco', 'linhas_do_chao')}
        self.valores = dict(PADRAO)
        if manter_calibracao:
            self.valores.update(calibracao)

    def calibracao(self):
        v = self.valores
        return Calibracao(v['linha_1m'], v['linha_3m'], v['foco'], v['linhas_do_chao'])
