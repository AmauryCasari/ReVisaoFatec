import math

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty
from kivy.uix.stencilview import StencilView
from kivy.utils import get_color_from_hex

from distancia import ATENCAO, LIVRE, PERIGO, Calibracao, formatar_limite

COR_ZONA = {
    LIVRE: get_color_from_hex('#3DD68C'),
    ATENCAO: get_color_from_hex('#F5B83D'),
    PERIGO: get_color_from_hex('#FF6B61'),
}
TEXTO_ESCURO = (0.07, 0.08, 0.09, 1)
BRANCO = (1, 1, 1, 1)


class _Desenho(StencilView):
    area_imagem = ListProperty([])
    espelhado = BooleanProperty(False)
    escala_texto = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._texturas = {}
        self.redesenhar_depois = Clock.create_trigger(self.redesenhar, -1)
        self.bind(pos=self.redesenhar_depois, size=self.redesenhar_depois,
                  area_imagem=self.redesenhar_depois, espelhado=self.redesenhar_depois,
                  escala_texto=self.redesenhar_depois)

    def area(self):
        a = self.area_imagem
        if len(a) == 4 and a[2] > 0 and a[3] > 0:
            return a
        return [self.x, self.y, self.width, self.height]

    def ponto(self, xn, yn):
        x, y, largura, altura = self.area()
        if self.espelhado:
            xn = 1.0 - xn
        return x + xn * largura, y + (1.0 - yn) * altura

    def y_normal(self, y_tela):
        _, y, _, altura = self.area()
        return 1.0 - (y_tela - y) / altura

    def textura(self, texto, tamanho, cor=TEXTO_ESCURO, negrito=True):
        chave = (texto, int(tamanho), tuple(cor), negrito)
        tex = self._texturas.get(chave)
        if tex is None:
            if len(self._texturas) > 150:
                self._texturas.clear()
            rotulo = CoreLabel(text=texto, font_size=tamanho, bold=negrito, color=tuple(cor))
            rotulo.refresh()
            tex = self._texturas[chave] = rotulo.texture
        return tex

    def etiqueta(self, texto, x, y, cor_fundo, cor_texto=TEXTO_ESCURO,
                 posicao='acima', a_esquerda=False, tamanho=13):
        tex = self.textura(texto, sp(tamanho) * self.escala_texto, cor_texto)
        folga = dp(6)
        largura, altura = tex.width + 2 * folga, tex.height + folga
        ax, ay, aw, ah = self.area()
        if a_esquerda:
            x -= largura
        x = max(ax + dp(2), min(x, ax + aw - largura - dp(2)))
        if posicao == 'centro':
            yy = y - altura / 2
        else:
            yy = y + dp(3)
            if yy + altura > ay + ah:
                yy = y - altura - dp(3)
        yy = max(ay + dp(2), min(yy, ay + ah - altura - dp(2)))
        Color(*cor_fundo)
        RoundedRectangle(pos=(x, yy), size=(largura, altura), radius=[dp(6)])
        Color(*BRANCO)
        Rectangle(texture=tex, pos=(x + folga, yy + folga / 2), size=tex.size)

    def redesenhar(self, *args):
        self.canvas.clear()
        with self.canvas:
            self.desenhar()

    def desenhar(self):
        pass


class Sobreposicao(_Desenho):
    objetos = ListProperty([], force_dispatch=True)
    calibracao = ObjectProperty(None, allownone=True)
    dist_perigo = NumericProperty(1.0)
    dist_atencao = NumericProperty(3.0)
    modo_calibracao = BooleanProperty(False)
    linha_1m = NumericProperty(0.82)
    linha_3m = NumericProperty(0.51)
    pessoas = ListProperty([], force_dispatch=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._arrastando = None
        self.bind(objetos=self.redesenhar_depois, calibracao=self.redesenhar_depois,
                  dist_perigo=self.redesenhar_depois, dist_atencao=self.redesenhar_depois,
                  modo_calibracao=self.redesenhar_depois, linha_1m=self.redesenhar_depois,
                  linha_3m=self.redesenhar_depois, pessoas=self.redesenhar_depois)

    def desenhar(self):
        self._desenhar_guias()
        if self.modo_calibracao:
            self._desenhar_pessoas()
        else:
            self._desenhar_objetos()

    def _desenhar_guias(self):
        if self.modo_calibracao:
            cal = Calibracao(self.linha_1m, self.linha_3m)
            marcas = [(self.linha_1m, PERIGO, '1 m'), (self.linha_3m, ATENCAO, '3 m')]
        else:
            cal = self.calibracao or Calibracao()
            marcas = [
                (cal.y_no_chao(self.dist_perigo), PERIGO,
                 f'{formatar_limite(self.dist_perigo)} m · perigo'),
                (cal.y_no_chao(self.dist_atencao), ATENCAO,
                 f'{formatar_limite(self.dist_atencao)} m · atenção'),
            ]
        horizonte = cal.horizonte

        def meia_largura(yn):
            if 1.0 - horizonte <= 1e-3:
                return 0.36
            return 0.36 * max(0.0, (yn - horizonte) / (1.0 - horizonte))

        espessura = dp(3)
        y_perigo = min(1.0, marcas[0][0])
        y_atencao = min(1.0, marcas[1][0])
        if not self.modo_calibracao:
            for lado in (-1, 1):
                for ya, yb, zona in ((1.0, y_perigo, PERIGO), (y_perigo, y_atencao, ATENCAO)):
                    if ya - yb < 1e-3:
                        continue
                    Color(*COR_ZONA[zona][:3], 0.85)
                    Line(points=[*self.ponto(0.5 + lado * meia_largura(ya), ya),
                                 *self.ponto(0.5 + lado * meia_largura(yb), yb)],
                         width=espessura, cap='round')

        for yn, zona, texto in marcas:
            if not 0.0 <= yn <= 1.0:
                continue
            if self.modo_calibracao:
                xa, xb = 0.04, 0.96
            else:
                m = meia_largura(yn)
                xa, xb = 0.5 - m, 0.5 + m
            p0, p1 = self.ponto(xa, yn), self.ponto(xb, yn)
            Color(*COR_ZONA[zona])
            if zona == ATENCAO:
                self._tracejada(p0, p1, espessura)
            else:
                Line(points=[*p0, *p1], width=espessura, cap='round')
            direita = max(p0[0], p1[0])
            if self.modo_calibracao:
                self._alca(direita, p0[1], COR_ZONA[zona])
                self.etiqueta(texto, direita - dp(26), p0[1], COR_ZONA[zona],
                              posicao='centro', a_esquerda=True, tamanho=15)
            else:
                self.etiqueta(texto, direita + dp(8), p0[1], COR_ZONA[zona], posicao='centro')

    def _tracejada(self, p0, p1, largura, traco=None, espaco=None):
        traco = traco or dp(16)
        espaco = espaco or dp(10)
        (x0, y0), (x1, y1) = p0, p1
        comprimento = math.hypot(x1 - x0, y1 - y0)
        if comprimento <= 0:
            return
        dx, dy = (x1 - x0) / comprimento, (y1 - y0) / comprimento
        s = 0.0
        while s < comprimento:
            e = min(s + traco, comprimento)
            Line(points=[x0 + dx * s, y0 + dy * s, x0 + dx * e, y0 + dy * e],
                 width=largura, cap='round')
            s = e + espaco

    def _alca(self, x, y, cor):
        raio = dp(16)
        Color(*cor)
        Ellipse(pos=(x - raio, y - raio), size=(2 * raio, 2 * raio))
        Color(*TEXTO_ESCURO)
        for dy in (-dp(4), 0, dp(4)):
            Line(points=[x - raio * 0.45, y + dy, x + raio * 0.45, y + dy], width=dp(1.2))

    def _desenhar_objetos(self):
        for obj in sorted(self.objetos, key=lambda o: -o.distancia):
            cor = COR_ZONA[obj.zona]
            c = obj.caixa
            xa, y_topo = self.ponto(c.x0, c.y0)
            xb, y_base = self.ponto(c.x1, c.y1)
            esquerda, direita = min(xa, xb), max(xa, xb)
            Color(*cor)
            Line(rectangle=(esquerda, y_base, direita - esquerda, y_topo - y_base),
                 width=dp(3) if obj.zona == PERIGO else dp(2))
            self.etiqueta(obj.rotulo_tela(), esquerda, y_topo, cor)

    def _desenhar_pessoas(self):
        for p in self.pessoas:
            xa, y_topo = self.ponto(p.x0, p.y0)
            xb, y_base = self.ponto(p.x1, p.y1)
            Color(1, 1, 1, 0.9)
            Line(rectangle=(min(xa, xb), y_base, abs(xb - xa), y_topo - y_base), width=dp(2))
            self.etiqueta('Pessoa', min(xa, xb), y_topo, (1, 1, 1, 0.9))

    def on_touch_down(self, touch):
        if self.modo_calibracao and self.collide_point(*touch.pos):
            candidatas = []
            for nome in ('linha_1m', 'linha_3m'):
                _, y_linha = self.ponto(0.5, getattr(self, nome))
                candidatas.append((abs(touch.y - y_linha), nome))
            distancia, nome = min(candidatas)
            if distancia <= dp(36):
                touch.grab(self)
                self._arrastando = nome
                return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and self._arrastando:
            yn = self.y_normal(touch.y)
            if self._arrastando == 'linha_1m':
                yn = min(0.99, max(self.linha_3m + 0.05, yn))
            else:
                yn = max(0.05, min(self.linha_1m - 0.05, yn))
            setattr(self, self._arrastando, yn)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._arrastando = None
            return True
        return super().on_touch_up(touch)
