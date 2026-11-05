import os

from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.logger import Logger

from distancia import ATENCAO, LIVRE, PERIGO, intervalo_bipe


class Alarme:
    def __init__(self, pasta_sons):
        self.bipe = self._carregar(os.path.join(pasta_sons, 'bipe.wav'))
        self.continuo = self._carregar(os.path.join(pasta_sons, 'bipe_continuo.wav'))
        if self.continuo:
            self.continuo.loop = True
        self.ligado = True
        self.volume = 0.8
        self.nivel = LIVRE
        self.intervalo = 0.8
        self._evento = None

    @staticmethod
    def _carregar(caminho):
        try:
            som = SoundLoader.load(caminho)
        except Exception:
            Logger.exception('RéVisão: erro ao carregar %s', caminho)
            som = None
        if som is None:
            Logger.warning('RéVisão: sem som (%s); os alertas ficam só na tela', caminho)
        return som

    def configurar(self, ligado, volume):
        self.ligado = bool(ligado)
        self.volume = max(0.0, min(1.0, float(volume)))
        for som in (self.bipe, self.continuo):
            if som:
                som.volume = self.volume
        if not self.ligado:
            self.parar()

    def atualizar(self, nivel, distancia, perigo, atencao):
        if not self.ligado:
            nivel = LIVRE
        self.nivel = nivel
        if nivel == PERIGO:
            self._cancelar_bipes()
            if self.continuo and self.continuo.state != 'play':
                self.continuo.volume = self.volume
                self.continuo.play()
            return
        self._parar_continuo()
        if nivel == ATENCAO:
            self.intervalo = intervalo_bipe(distancia, perigo, atencao)
            if self._evento is None:
                self._tocar_bipe(0)
        else:
            self._cancelar_bipes()

    def testar(self, volume=None):
        if self.bipe:
            if self.bipe.state == 'play':
                self.bipe.stop()
            self.bipe.volume = self.volume if volume is None else volume
            self.bipe.play()

    def parar(self):
        self.nivel = LIVRE
        self._cancelar_bipes()
        self._parar_continuo()
        if self.bipe and self.bipe.state == 'play':
            self.bipe.stop()

    def _tocar_bipe(self, dt):
        self._evento = None
        if self.nivel != ATENCAO or not self.ligado:
            return
        if self.bipe:
            if self.bipe.state == 'play':
                self.bipe.stop()
            self.bipe.volume = self.volume
            self.bipe.play()
        self._evento = Clock.schedule_once(self._tocar_bipe, self.intervalo)

    def _cancelar_bipes(self):
        if self._evento is not None:
            self._evento.cancel()
            self._evento = None

    def _parar_continuo(self):
        if self.continuo and self.continuo.state == 'play':
            self.continuo.stop()
