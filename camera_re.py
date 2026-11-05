from kivy.clock import mainthread
from kivy.logger import Logger
from kivy.properties import BooleanProperty
from camera4kivy import Preview


class CameraAnalise(Preview):
    espelhar = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.detector = None
        self.ao_detectar = None
        self.ao_erro = None
        self._erro_avisado = False

    def usar_detector(self, detector, ao_detectar, ao_erro=None):
        self.detector = detector
        self.ao_detectar = ao_detectar
        self.ao_erro = ao_erro
        self._erro_avisado = False
        if detector is not None:
            self.auto_analyze_resolution = list(detector.tamanho_analise(16 / 9))

    def analyze_pixels_callback(self, pixels, image_size, image_pos, image_scale, mirror):
        detector = self.detector
        if detector is None:
            return
        if isinstance(image_scale, (list, tuple)):
            escala_x, escala_y = image_scale
        else:
            escala_x = escala_y = image_scale
        area = [image_pos[0], image_pos[1],
                image_size[0] * escala_x, image_size[1] * escala_y]
        if area[2] > 0 and area[3] > 0:
            ideal = list(detector.tamanho_analise(area[2] / area[3]))
            if ideal != list(self.auto_analyze_resolution):
                self.auto_analyze_resolution = ideal
        try:
            deteccoes = detector.detectar_rgba(pixels, image_size[0], image_size[1])
        except Exception as erro:
            if not self._erro_avisado:
                self._erro_avisado = True
                Logger.exception('RéVisão: falha no detector')
                self._avisar_erro(str(erro))
            return
        self._entregar(deteccoes, area, bool(mirror))

    @mainthread
    def _entregar(self, deteccoes, area, espelhado):
        if self.camera_connected and self.ao_detectar:
            self.ao_detectar(deteccoes, area, espelhado)

    @mainthread
    def _avisar_erro(self, mensagem):
        if self.ao_erro:
            self.ao_erro(mensagem)
