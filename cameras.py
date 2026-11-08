import glob
import os
import sys
import threading

from kivy.clock import mainthread
from kivy.utils import platform

MAXIMO = 6


def _nomes_windows():
    try:
        from pygrabber.dshow_graph import FilterGraph
        return FilterGraph().get_input_devices()
    except Exception:
        return []


def _nome_linux(indice):
    try:
        with open(f'/sys/class/video4linux/video{indice}/name', encoding='utf-8') as arquivo:
            return arquivo.read().strip()
    except OSError:
        return ''


def _abre(cv2, indice):
    backend = cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_ANY
    captura = cv2.VideoCapture(indice, backend)
    try:
        return captura.isOpened() and captura.read()[0]
    finally:
        captura.release()


def procurar():
    if platform == 'android':
        return [('back', 'Câmera traseira do celular'), ('front', 'Câmera frontal do celular')]
    try:
        import cv2
    except ImportError:
        return [('0', 'Câmera 1')]
    nomes = _nomes_windows() if sys.platform == 'win32' else []
    if sys.platform.startswith('linux'):
        indices = sorted(int(os.path.basename(c)[5:]) for c in glob.glob('/dev/video*')
                         if os.path.basename(c)[5:].isdigit())[:MAXIMO]
    else:
        indices = range(MAXIMO)
    achadas = []
    for i in indices:
        if not _abre(cv2, i):
            continue
        nome = nomes[i] if i < len(nomes) else _nome_linux(i)
        rotulo = f'Câmera {len(achadas) + 1}'
        achadas.append((str(i), f'{rotulo}: {nome}' if nome else rotulo))
    return achadas


def procurar_em_segundo_plano(ao_terminar):
    def tarefa():
        try:
            achadas = procurar()
        except Exception:
            achadas = []
        _entregar(ao_terminar, achadas)
    threading.Thread(target=tarefa, daemon=True).start()


@mainthread
def _entregar(ao_terminar, achadas):
    ao_terminar(achadas)
