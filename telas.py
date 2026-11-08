import time

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.utils import platform

import permissoes
from configuracoes import PADRAO
from distancia import (LIVRE, PERIGO, Rastreador, Situacao, escolher_pessoa, formatar_limite,
                       medir_foco, texto_pare, texto_status)


def app():
    return App.get_running_app()


def conectar(camera, cfg):
    camera.espelhar = cfg['espelhar']
    camera.connect_camera(camera_id=cfg['camera'], mirrored=False,
                          enable_analyze_pixels=True, enable_video=False)


def desconectar(camera):
    if camera.camera_connected:
        camera.disconnect_camera()


class TelaInicio(Screen):
    pass


class TelaAjuda(Screen):
    no_android = BooleanProperty(platform == 'android')

    def abrir_configuracoes(self):
        permissoes.abrir_configuracoes_do_app()

    def tentar_de_novo(self):
        app().iniciar_camera(empilhar=False)


class TelaCamera(Screen):
    status_texto = StringProperty('')
    nivel = NumericProperty(LIVRE)
    analisando = BooleanProperty(False)
    pare_detalhe = StringProperty('')
    aviso = StringProperty('')
    som_ligado = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rastreador = Rastreador()
        self._eventos = []
        self._ultimo_quadro = 0.0
        self._sem_imagem = False

    def on_enter(self):
        self._comecar()

    def on_pre_leave(self):
        self._encerrar()

    def pausar(self):
        self._encerrar()

    def retomar(self):
        self._comecar()

    def _comecar(self):
        a = app()
        cfg = a.cfg
        self.som_ligado = cfg['som']
        calibracao = cfg.calibracao()
        self.rastreador = Rastreador(calibracao, cfg['dist_perigo'], cfg['dist_atencao'])
        sobre = self.ids.sobre
        sobre.calibracao = calibracao
        sobre.dist_perigo = cfg['dist_perigo']
        sobre.dist_atencao = cfg['dist_atencao']
        sobre.mostrar_guias = True
        sobre.area_imagem = []
        sobre.espelhado = False
        self.aviso = ''
        self._sem_imagem = False
        self.analisando = False
        self._ultimo_quadro = time.monotonic()
        self._mostrar(Situacao())

        if not permissoes.tem_camera():
            self.status_texto = 'Câmera bloqueada'
            self.aviso = 'O RéVisão não tem permissão para usar a câmera.'
            return
        camera = self.ids.camera
        if a.detector is not None:
            camera.usar_detector(a.detector, self.ao_detectar, self.ao_erro)
            self.status_texto = 'Iniciando a câmera...'
        elif a.erro_detector:
            self.ao_erro(a.erro_detector)
        else:
            self.status_texto = 'Carregando o detector...'
        conectar(camera, cfg)
        self._eventos.append(Clock.schedule_interval(self._vigiar, 0.5))

    def _encerrar(self):
        for evento in self._eventos:
            evento.cancel()
        self._eventos = []
        desconectar(self.ids.camera)
        if app() is not None:
            app().alarme.parar()
        self.rastreador.limpar()
        self.ids.sobre.objetos = []
        self.nivel = LIVRE
        self.analisando = False
        self.pare_detalhe = ''

    def detector_carregado(self, detector):
        if (self.manager and self.manager.current == self.name
                and permissoes.tem_camera()):
            self.ids.camera.usar_detector(detector, self.ao_detectar, self.ao_erro)
            self.status_texto = 'Iniciando a câmera...'

    def ao_erro(self, mensagem):
        self.aviso = ('O detector de objetos não funcionou neste aparelho.\n'
                      'Detalhe: ' + mensagem[:180])
        self.status_texto = 'Detector com problema'
        self.analisando = False
        app().alarme.parar()

    def ao_detectar(self, deteccoes, area, espelhado):
        self._ultimo_quadro = time.monotonic()
        self.analisando = True
        if self._sem_imagem:
            self._sem_imagem = False
            self.aviso = ''
        if len(area) == 4 and area[3] > 0:
            self.rastreador.calibracao.aspecto = area[2] / area[3]
        situacao = self.rastreador.atualizar(deteccoes, self._ultimo_quadro)
        sobre = self.ids.sobre
        sobre.area_imagem = area
        sobre.espelhado = espelhado != self.ids.camera.espelhar
        self._mostrar(situacao)

    def _mostrar(self, situacao):
        a = app()
        cfg = a.cfg
        self.ids.sobre.objetos = situacao.objetos
        self.nivel = situacao.nivel
        self.status_texto = texto_status(situacao, cfg['dist_atencao'])
        self.pare_detalhe = texto_pare(situacao) if situacao.nivel == PERIGO else ''
        if self.analisando:
            a.alarme.atualizar(situacao.nivel, situacao.distancia,
                               cfg['dist_perigo'], cfg['dist_atencao'])

    def _vigiar(self, dt):
        parado = time.monotonic() - self._ultimo_quadro
        if self.analisando and parado > 1.5:
            self.analisando = False
            self.rastreador.limpar()
            self.ids.sobre.objetos = []
            self.nivel = LIVRE
            self.pare_detalhe = ''
            self.status_texto = 'Sem análise da imagem agora'
            app().alarme.parar()
        elif not self.analisando and not self.aviso and app().detector is not None and parado > 6:
            self._sem_imagem = True
            self.status_texto = 'Sem imagem da câmera'
            self.aviso = ('A câmera não mandou imagem. Feche outros apps que usam a câmera '
                          'e tente de novo.')


    def alternar_som(self):
        a = app()
        self.som_ligado = not self.som_ligado
        a.cfg['som'] = self.som_ligado
        a.cfg.salvar()
        a.alarme.configurar(self.som_ligado, a.cfg['volume'])

    def abrir_ajustes(self):
        app().ir('ajustes')

    def trocar_camera(self):
        a = app()
        ids = [ident for ident, _ in a.cameras]
        if len(ids) < 2:
            self.status_texto = 'Só uma câmera encontrada'
            return
        atual = a.cfg['camera']
        proxima = ids[(ids.index(atual) + 1) % len(ids)] if atual in ids else ids[0]
        a.cfg['camera'] = proxima
        a.cfg.salvar()
        a.aplicar_configuracoes()
        self._encerrar()
        self.status_texto = 'Trocando de câmera...'
        Clock.schedule_once(lambda dt: self._comecar(), 0.5)

    def parar(self):
        app().voltar_para('inicio')


class TelaCalibracao(Screen):
    linha_1m = NumericProperty(PADRAO['linha_1m'])
    linha_3m = NumericProperty(PADRAO['linha_3m'])
    foco = NumericProperty(PADRAO['foco'])
    usar_chao = BooleanProperty(False)
    distancia_medida = NumericProperty(3.0)
    mensagem = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pessoas = []
        self._carregando = False
        self._aspecto = 16 / 9


    def on_enter(self):
        self._comecar()

    def on_pre_leave(self):
        self._encerrar()

    def pausar(self):
        self._encerrar()

    def retomar(self):
        self._comecar(recarregar=False)

    def _comecar(self, recarregar=True):
        a = app()
        cfg = a.cfg
        if recarregar:
            self._carregando = True
            self.linha_1m = cfg['linha_1m']
            self.linha_3m = cfg['linha_3m']
            self.foco = cfg['foco']
            self.usar_chao = cfg['linhas_do_chao']
            self.distancia_medida = cfg['distancia_medida']
            self._carregando = False
            self.mensagem = ''
        self._pessoas = []
        self.ids.sobre.pessoas = []
        self.ids.sobre.area_imagem = []
        if not permissoes.tem_camera():
            self.mensagem = 'Sem permissão da câmera: dá para mover as linhas, mas sem ver a imagem.'
            return
        if a.detector is not None:
            self.ids.camera.usar_detector(a.detector, self.ao_detectar)
        conectar(self.ids.camera, cfg)

    def _encerrar(self):
        desconectar(self.ids.camera)
        self._pessoas = []
        self.ids.sobre.pessoas = []

    def detector_carregado(self, detector):
        if self.manager and self.manager.current == self.name and permissoes.tem_camera():
            self.ids.camera.usar_detector(detector, self.ao_detectar)

    def ao_detectar(self, deteccoes, area, espelhado):
        self._pessoas = [d for d in deteccoes if d.rotulo == 'person']
        if len(area) == 4 and area[3] > 0:
            self._aspecto = area[2] / area[3]
        sobre = self.ids.sobre
        sobre.area_imagem = area
        sobre.espelhado = espelhado != self.ids.camera.espelhar
        sobre.pessoas = self._pessoas

    def medir_pessoa(self):
        a = app()
        if a.detector is None:
            self.mensagem = 'O detector ainda não está pronto. Espere alguns segundos.'
            return
        pessoa = escolher_pessoa(self._pessoas)
        d = formatar_limite(self.distancia_medida)
        if pessoa is None:
            self.mensagem = f'Não encontrei ninguém. Peça para a pessoa ficar de frente, a {d} m da câmera.'
            return
        if pessoa.x0 < 0.01 or pessoa.x1 > 0.99:
            self.mensagem = 'A pessoa está cortada dos lados. Ela precisa ficar no meio da imagem.'
            return
        aspecto = self._aspecto
        self.foco = medir_foco(pessoa, self.distancia_medida, a.cfg['altura_pessoa'], aspecto)
        self.mensagem = f'Pessoa medida a {d} m. Toque em Salvar calibração.'

    def mudar_distancia_medida(self):
        opcoes = [1.0, 1.5, 2.0, 3.0]
        atual = self.distancia_medida
        self.distancia_medida = opcoes[(opcoes.index(atual) + 1) % len(opcoes)] if atual in opcoes else 2.0

    def salvar(self):
        a = app()
        a.cfg['linha_1m'] = self.linha_1m
        a.cfg['linha_3m'] = self.linha_3m
        a.cfg['foco'] = self.foco
        a.cfg['linhas_do_chao'] = self.usar_chao
        a.cfg['distancia_medida'] = self.distancia_medida
        a.cfg.salvar()
        a.voltar()

    def cancelar(self):
        app().voltar()

    def restaurar(self):
        self._carregando = True
        self.linha_1m = PADRAO['linha_1m']
        self.linha_3m = PADRAO['linha_3m']
        self.foco = PADRAO['foco']
        self.usar_chao = False
        self._carregando = False
        self.mensagem = 'Valores padrão. Toque em Salvar calibração para manter.'

    def alternar_chao(self):
        self.usar_chao = not self.usar_chao


CHAVES_AJUSTES = ('som', 'volume', 'confianca', 'dist_perigo', 'dist_atencao',
                  'camera', 'espelhar', 'escala_texto')


class TelaAjustes(Screen):
    som = BooleanProperty(True)
    volume = NumericProperty(0.8)
    confianca = NumericProperty(0.5)
    dist_perigo = NumericProperty(1.0)
    dist_atencao = NumericProperty(3.0)
    camera = StringProperty(PADRAO['camera'])
    espelhar = BooleanProperty(False)
    escala_texto = NumericProperty(1.0)

    def on_pre_enter(self):
        cfg = app().cfg
        for chave in CHAVES_AJUSTES:
            setattr(self, chave, cfg[chave])

    def on_leave(self):
        a = app()
        a.escala_texto = a.cfg['escala_texto']

    def mudar_perigo(self, passo):
        self.dist_perigo = round(min(2.5, max(0.5, self.dist_perigo + passo)), 1)
        if self.dist_atencao < self.dist_perigo + 0.5:
            self.dist_atencao = round(self.dist_perigo + 0.5, 1)

    def mudar_atencao(self, passo):
        self.dist_atencao = round(min(8.0, max(self.dist_perigo + 0.5, self.dist_atencao + passo)), 1)

    def mudar_texto(self, passo):
        self.escala_texto = round(min(1.6, max(0.8, self.escala_texto + passo)), 2)
        app().escala_texto = self.escala_texto

    def testar_som(self):
        app().alarme.testar(self.volume)

    def escolher_camera(self, nome):
        for ident, rotulo in app().cameras:
            if rotulo == nome:
                self.camera = ident
                return

    def procurar_cameras(self):
        app().procurar_cameras()

    def _aplicar(self):
        a = app()
        for chave in CHAVES_AJUSTES:
            a.cfg[chave] = getattr(self, chave)
        a.cfg.salvar()
        a.aplicar_configuracoes()

    def salvar_e_voltar(self):
        self._aplicar()
        app().voltar()

    def calibrar(self):
        self._aplicar()
        app().ir('calibracao')

    def restaurar(self):
        for chave in CHAVES_AJUSTES:
            setattr(self, chave, PADRAO[chave])
        app().escala_texto = self.escala_texto
