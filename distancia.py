import math
from dataclasses import dataclass, field

LIVRE = 0
ATENCAO = 1
PERIGO = 2
NOME_ZONA = {LIVRE: 'livre', ATENCAO: 'atenção', PERIGO: 'perigo'}

OBJETOS = {
    'person': ('Pessoa', 'pessoa', 1.70),
    'bicycle': ('Bicicleta', 'veículo', 1.05),
    'car': ('Carro', 'veículo', 1.50),
    'motorcycle': ('Moto', 'veículo', 1.15),
    'bus': ('Ônibus', 'veículo', 3.00),
    'truck': ('Caminhão', 'veículo', 3.00),
    'bird': ('Pássaro', 'animal', 0.25),
    'cat': ('Gato', 'animal', 0.30),
    'dog': ('Cachorro', 'animal', 0.55),
    'horse': ('Cavalo', 'animal', 1.60),
    'sheep': ('Ovelha', 'animal', 0.90),
    'cow': ('Vaca', 'animal', 1.40),
}

LARGURAS = {
    'person': 0.55,
    'car': 1.75,
    'motorcycle': 0.80,
    'bus': 2.50,
    'truck': 2.40,
}

BORDA = 0.03


@dataclass
class Deteccao:
    rotulo: str
    confianca: float
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def largura(self):
        return self.x1 - self.x0

    @property
    def altura(self):
        return self.y1 - self.y0

    @property
    def area(self):
        return max(0.0, self.largura) * max(0.0, self.altura)


def iou(a, b):
    largura = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    altura = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    intersecao = largura * altura
    uniao = a.area + b.area - intersecao
    return intersecao / uniao if uniao > 0 else 0.0


@dataclass
class Calibracao:
    linha_1m: float = 0.82
    linha_3m: float = 0.51
    foco: float = 1.0
    usar_chao: bool = False
    aspecto: float = 16 / 9

    def _chao(self):
        k = 1.5 * (self.linha_1m - self.linha_3m)
        return k, self.linha_1m - k

    @property
    def horizonte(self):
        return self._chao()[1]

    def distancia_pelo_chao(self, y_base):
        k, horizonte = self._chao()
        if k <= 0 or y_base <= horizonte + 1e-6:
            return math.inf
        return k / (y_base - horizonte)

    def y_no_chao(self, distancia):
        k, horizonte = self._chao()
        return horizonte + k / max(distancia, 0.01)

    def distancia_pelo_tamanho(self, altura_caixa, altura_real):
        if altura_caixa <= 1e-6:
            return math.inf
        return altura_real * self.foco / altura_caixa

    def distancia_pela_largura(self, largura_caixa, largura_real):
        if largura_caixa <= 1e-6:
            return math.inf
        return largura_real * self.foco / (largura_caixa * self.aspecto)

    def estimar(self, deteccao):
        d = deteccao
        altura_real = OBJETOS.get(d.rotulo, ('', '', 1.0))[2]
        largura_real = LARGURAS.get(d.rotulo)
        corte_baixo = d.y1 >= 1.0 - BORDA
        corte_cima = d.y0 <= BORDA
        corte_lado = d.x0 <= BORDA or d.x1 >= 1.0 - BORDA

        if self.usar_chao and not corte_baixo:
            chao = self.distancia_pelo_chao(d.y1)
            if not math.isinf(chao):
                return chao

        if not corte_baixo and not corte_cima:
            estimativa = self.distancia_pelo_tamanho(d.altura, altura_real)
        elif largura_real and not corte_lado:
            estimativa = self.distancia_pela_largura(d.largura, largura_real)
        else:
            estimativa = self.distancia_pelo_tamanho(d.altura, altura_real)
            if d.altura >= 1.0 - 2 * BORDA:
                estimativa = min(estimativa, 0.5)
        return estimativa


def zona_da_distancia(distancia, perigo, atencao, zona_anterior=LIVRE, margem=0.15):
    if distancia <= perigo or (zona_anterior == PERIGO and distancia <= perigo + margem):
        return PERIGO
    if distancia <= atencao or (zona_anterior >= ATENCAO and distancia <= atencao + margem):
        return ATENCAO
    return LIVRE


def formatar_metros(distancia):
    if math.isinf(distancia):
        return 'longe'
    if distancia >= 3.0:
        return str(int(distancia + 0.5))
    texto = f'{distancia:.1f}'.replace('.', ',')
    return texto[:-2] if texto.endswith(',0') else texto


def formatar_limite(valor):
    texto = f'{valor:.1f}'.replace('.', ',')
    return texto[:-2] if texto.endswith(',0') else texto


@dataclass
class Objeto:
    id: int
    rotulo: str
    caixa: Deteccao
    distancia: float
    zona: int = LIVRE
    acertos: int = 1
    visto_em: float = 0.0
    confianca: float = 0.0

    @property
    def nome(self):
        return OBJETOS.get(self.rotulo, (self.rotulo.capitalize(), '', 1.0))[0]

    @property
    def grupo(self):
        return OBJETOS.get(self.rotulo, ('', 'outro', 1.0))[1]

    def rotulo_tela(self):
        if math.isinf(self.distancia):
            return f'{self.nome} · longe · {NOME_ZONA[self.zona]}'
        return f'{self.nome} · ~{formatar_metros(self.distancia)} m · {NOME_ZONA[self.zona]}'


@dataclass
class Situacao:
    nivel: int = LIVRE
    objetos: list = field(default_factory=list)

    @property
    def mais_proximo(self):
        return self.objetos[0] if self.objetos else None

    @property
    def distancia(self):
        return self.objetos[0].distancia if self.objetos else math.inf


class Rastreador:
    def __init__(self, calibracao=None, perigo=1.0, atencao=3.0, memoria=0.7,
                 iou_minimo=0.25, suavizacao_aproximando=0.7,
                 suavizacao_afastando=0.35, confianca_imediata=0.7):
        self.calibracao = calibracao or Calibracao()
        self.perigo = perigo
        self.atencao = atencao
        self.memoria = memoria
        self.iou_minimo = iou_minimo
        self.alfa_perto = suavizacao_aproximando
        self.alfa_longe = suavizacao_afastando
        self.confianca_imediata = confianca_imediata
        self.objetos = []
        self._proximo_id = 1

    def limpar(self):
        self.objetos = []

    def atualizar(self, deteccoes, agora):
        sem_par = list(self.objetos)
        for det in sorted(deteccoes, key=lambda d: -d.confianca):
            if det.rotulo not in OBJETOS:
                continue
            distancia = self.calibracao.estimar(det)
            grupo = OBJETOS[det.rotulo][1]
            melhor, melhor_iou = None, self.iou_minimo
            for obj in sem_par:
                if obj.grupo != grupo:
                    continue
                sobreposicao = iou(obj.caixa, det)
                if sobreposicao >= melhor_iou:
                    melhor, melhor_iou = obj, sobreposicao
            if melhor is None:
                novo = Objeto(id=self._proximo_id, rotulo=det.rotulo, caixa=det,
                              distancia=distancia, visto_em=agora, confianca=det.confianca)
                novo.zona = zona_da_distancia(distancia, self.perigo, self.atencao)
                self._proximo_id += 1
                self.objetos.append(novo)
            else:
                sem_par.remove(melhor)
                melhor.distancia = self._suavizar(melhor.distancia, distancia)
                melhor.caixa = det
                melhor.rotulo = det.rotulo
                melhor.confianca = det.confianca
                melhor.acertos += 1
                melhor.visto_em = agora
                melhor.zona = zona_da_distancia(melhor.distancia, self.perigo,
                                                self.atencao, melhor.zona)

        self.objetos = [o for o in self.objetos if agora - o.visto_em <= self.memoria]

        confirmados = [o for o in self.objetos
                       if o.acertos >= 2 or o.confianca >= self.confianca_imediata]
        confirmados.sort(key=lambda o: o.distancia)
        nivel = max((o.zona for o in confirmados), default=LIVRE)
        return Situacao(nivel=nivel, objetos=confirmados)

    def _suavizar(self, anterior, nova):
        if math.isinf(anterior) or math.isinf(nova):
            return nova
        alfa = self.alfa_perto if nova < anterior else self.alfa_longe
        return anterior + alfa * (nova - anterior)


def intervalo_bipe(distancia, perigo, atencao, rapido=0.15, lento=0.8):
    if atencao <= perigo:
        return rapido
    fracao = (distancia - perigo) / (atencao - perigo)
    fracao = min(1.0, max(0.0, fracao))
    return rapido + fracao * (lento - rapido)


def texto_status(situacao, atencao):
    obj = situacao.mais_proximo
    if situacao.nivel == LIVRE or obj is None:
        return f'Livre: nada a menos de {formatar_limite(atencao)} m'
    distancia = formatar_metros(obj.distancia)
    if situacao.nivel == ATENCAO:
        return f'Atenção: {obj.nome.lower()} a ~{distancia} m'
    return f'PARE: {obj.nome.lower()} a ~{distancia} m'


def texto_pare(situacao):
    obj = situacao.mais_proximo
    if obj is None:
        return ''
    return f'{obj.nome.lower()} a ~{formatar_metros(obj.distancia)} m atrás do carro'


def escolher_pessoa(deteccoes):
    pessoas = [d for d in deteccoes if d.rotulo == 'person']
    return max(pessoas, key=lambda d: d.confianca) if pessoas else None


def medir_foco(pessoa, distancia=3.0, altura_real=1.70, aspecto=16 / 9):
    inteira = pessoa.y0 > BORDA and pessoa.y1 < 1.0 - BORDA
    if inteira:
        return pessoa.altura * distancia / altura_real
    return pessoa.largura * aspecto * distancia / LARGURAS['person']
