import os
import threading

from kivy.utils import platform

if platform not in ('android', 'ios'):
    from kivy.config import Config
    Config.set('input', 'mouse', 'mouse,disable_multitouch')
    Config.set('graphics', 'width', '1024')
    Config.set('graphics', 'height', '576')
    Config.set('kivy', 'exit_on_escape', '0')

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty

import cameras as busca_cameras
import permissoes
from alertas import Alarme
from configuracoes import Configuracoes
import camera_re
import componentes
import sobreposicao
import telas

PASTA = os.path.dirname(os.path.abspath(__file__))


class RevisaoApp(App):
    title = 'RéVisão'
    icon = 'assets/icone.png'
    escala_texto = NumericProperty(1.0)
    motor_nome = StringProperty('')
    erro_detector = StringProperty('')
    cameras = ListProperty([])
    procurando_cameras = BooleanProperty(False)
    camera_atual = StringProperty('')

    def build(self):
        self.cfg = Configuracoes(self.user_data_dir)
        self.escala_texto = self.cfg['escala_texto']
        self.detector = None
        self.alarme = Alarme(os.path.join(PASTA, 'assets'))
        self.alarme.configurar(self.cfg['som'], self.cfg['volume'])
        self._historico = []
        Window.bind(on_keyboard=self._ao_teclar)
        return Builder.load_file(os.path.join(PASTA, 'interface.kv'))

    def on_start(self):
        Clock.schedule_once(self._carregar_detector, 0.2)
        self.camera_atual = self.cfg['camera']
        self.procurar_cameras()

    def procurar_cameras(self):
        if self.procurando_cameras:
            return
        self.procurando_cameras = True
        busca_cameras.procurar_em_segundo_plano(self._cameras_achadas)

    def _cameras_achadas(self, achadas):
        self.procurando_cameras = False
        self.cameras = achadas

    def nome_da_camera(self, ident, lista):
        for codigo, nome in lista:
            if codigo == ident:
                return nome
        return f'Câmera {int(ident) + 1}' if ident.isdigit() else ident

    def _carregar_detector(self, dt=None):
        def tarefa():
            try:
                from detector import Detector
                detector = Detector(confianca=self.cfg['confianca'])
            except Exception as erro:
                Logger.exception('RéVisão: o detector não carregou')
                self._detector_falhou(str(erro))
            else:
                self._detector_pronto(detector)

        if platform == 'android':
            tarefa()
        else:
            threading.Thread(target=tarefa, daemon=True).start()

    @mainthread
    def _detector_pronto(self, detector):
        self.detector = detector
        self.motor_nome = detector.motor_nome
        Logger.info('RéVisão: detector pronto (%s, entrada %dx%d)',
                    detector.motor_nome, *detector.tamanho_entrada)
        for nome in ('camera', 'calibracao'):
            self.root.get_screen(nome).detector_carregado(detector)

    @mainthread
    def _detector_falhou(self, mensagem):
        self.erro_detector = mensagem
        tela = self.root.get_screen('camera')
        if self.root.current == 'camera':
            tela.ao_erro(mensagem)

    def aplicar_configuracoes(self):
        self.escala_texto = self.cfg['escala_texto']
        self.camera_atual = self.cfg['camera']
        self.alarme.configurar(self.cfg['som'], self.cfg['volume'])
        if self.detector is not None:
            self.detector.confianca = self.cfg['confianca']

    def iniciar_camera(self, empilhar=True):
        def resposta(permitido):
            if permitido:
                self.ir('camera', empilhar)
            else:
                self.ir('ajuda', empilhar)

        permissoes.pedir_camera(resposta)

    def ir(self, nome, empilhar=True):
        gerente = self.root
        if gerente.current == nome:
            return
        if empilhar:
            self._historico.append(gerente.current)
        gerente.current = nome

    def voltar(self):
        gerente = self.root
        while self._historico:
            anterior = self._historico.pop()
            if anterior != gerente.current:
                gerente.current = anterior
                return True
        if gerente.current != 'inicio':
            gerente.current = 'inicio'
            return True
        return False

    def voltar_para(self, nome):
        self._historico.clear()
        self.root.current = nome

    def _ao_teclar(self, janela, tecla, *args):
        if tecla == 27:
            return self.voltar()
        return False

    def on_pause(self):
        tela = self.root.current_screen
        if hasattr(tela, 'pausar'):
            tela.pausar()
        self.alarme.parar()
        return True

    def on_resume(self):
        tela = self.root.current_screen
        if hasattr(tela, 'retomar'):
            tela.retomar()

    def on_stop(self):
        tela = self.root.current_screen if self.root else None
        if tela is not None and hasattr(tela, 'pausar'):
            tela.pausar()
        self.alarme.parar()
        self.cfg.salvar()


if __name__ == '__main__':
    RevisaoApp().run()
