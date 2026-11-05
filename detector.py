import importlib
import os
import sys
import threading
import zipfile

from distancia import OBJETOS, Deteccao

PASTA = os.path.dirname(os.path.abspath(__file__))
CAMINHO_MODELO = os.path.join(PASTA, 'modelos', 'efficientdet_lite0.tflite')


def no_android():
    return 'ANDROID_ARGUMENT' in os.environ or hasattr(sys, 'getandroidapilevel')


def ler_rotulos(caminho):
    try:
        with zipfile.ZipFile(caminho) as pacote:
            nome = pacote.namelist()[0]
            return [linha.strip() for linha in pacote.read(nome).decode('utf-8').splitlines()]
    except (zipfile.BadZipFile, IndexError):
        raise ValueError('O modelo não tem a lista de rótulos embutida. Use um modelo '
                         'EfficientDet-Lite do TensorFlow Hub ou do Model Maker.')


def rgba_para_rgb(pixels):
    rgba = bytes(pixels)
    rgb = bytearray(len(rgba) // 4 * 3)
    rgb[0::3] = rgba[0::4]
    rgb[1::3] = rgba[1::4]
    rgb[2::3] = rgba[2::4]
    return bytes(rgb)


def _normalizar_float(rgb):
    try:
        import numpy as np
        valores = (np.frombuffer(rgb, dtype=np.uint8).astype(np.float32) - 127.5) / 127.5
        return valores.tobytes()
    except ImportError:
        from array import array
        return array('f', ((v - 127.5) / 127.5 for v in rgb)).tobytes()


def _separar_saidas(saidas):
    quantidade = next(s for s in saidas if len(s) == 1)
    resto = [s for s in saidas if s is not quantidade]
    n = min(len(s) for s in resto)
    caixas = next(s for s in resto if len(s) == 4 * n)
    classes, pontuacoes = [s for s in resto if s is not caixas]
    total = max(0, min(int(quantidade[0]), n))

    def inteiros(valores):
        return all(float(v).is_integer() for v in valores[:total])

    if total and inteiros(pontuacoes) and not inteiros(classes):
        classes, pontuacoes = pontuacoes, classes
    return caixas, classes, pontuacoes, total


class _MotorPython:
    def __init__(self, Interpreter, caminho, threads, nome):
        import numpy as np
        self.np = np
        self.nome = nome
        try:
            self.it = Interpreter(model_path=caminho, num_threads=threads)
        except TypeError:
            self.it = Interpreter(model_path=caminho)
        self.it.allocate_tensors()
        entrada = self.it.get_input_details()[0]
        self.indice_entrada = entrada['index']
        _, self.altura, self.largura, _ = (int(v) for v in entrada['shape'])
        self.quantizado = entrada['dtype'] == np.uint8
        self.saidas = sorted(s['index'] for s in self.it.get_output_details())

    def inferir(self, rgb):
        np = self.np
        if self.quantizado:
            x = np.frombuffer(rgb, dtype=np.uint8)
        else:
            x = np.frombuffer(_normalizar_float(rgb), dtype=np.float32)
        self.it.set_tensor(self.indice_entrada, x.reshape(1, self.altura, self.largura, 3))
        self.it.invoke()
        return [self.it.get_tensor(i).reshape(-1).tolist() for i in self.saidas]


class _MotorJava:
    def __init__(self, caminho, threads):
        from jnius import autoclass
        File = autoclass('java.io.File')
        Interpreter = autoclass('org.tensorflow.lite.Interpreter')
        Opcoes = autoclass('org.tensorflow.lite.Interpreter$Options')
        ByteBuffer = autoclass('java.nio.ByteBuffer')
        ByteOrder = autoclass('java.nio.ByteOrder')
        HashMap = autoclass('java.util.HashMap')
        Integer = autoclass('java.lang.Integer')

        self.nome = 'TensorFlow Lite (Java)'
        opcoes = Opcoes()
        opcoes.setNumThreads(threads)
        self.it = Interpreter(File(caminho), opcoes)

        entrada = self.it.getInputTensor(0)
        _, self.altura, self.largura, _ = list(entrada.shape())
        self.quantizado = entrada.dataType().name() == 'UINT8'
        ordem = ByteOrder.nativeOrder()
        self.buffer_entrada = ByteBuffer.allocateDirect(entrada.numBytes())
        self.buffer_entrada.order(ordem)
        self.entradas = [self.buffer_entrada]

        saidas = []
        for posicao in range(self.it.getOutputTensorCount()):
            tensor = self.it.getOutputTensor(posicao)
            try:
                indice = tensor.index()
            except Exception:
                indice = posicao
            buffer = ByteBuffer.allocateDirect(tensor.numBytes())
            buffer.order(ordem)
            saidas.append((indice, posicao, tensor.numElements(), buffer))
        saidas.sort(key=lambda s: s[0])

        self.mapa_saidas = HashMap()
        for _, posicao, _, buffer in saidas:
            self.mapa_saidas.put(Integer.valueOf(posicao), buffer)
        self.saidas = [(elementos, buffer) for _, _, elementos, buffer in saidas]
        self.saidas[0][1].asFloatBuffer()

    def inferir(self, rgb):
        dados = rgb if self.quantizado else _normalizar_float(rgb)
        entrada = self.buffer_entrada
        entrada.rewind()
        entrada.put(dados)
        entrada.rewind()
        for _, buffer in self.saidas:
            buffer.rewind()
        self.it.runForMultipleInputsOutputs(self.entradas, self.mapa_saidas)
        resultado = []
        for elementos, buffer in self.saidas:
            buffer.rewind()
            numeros = buffer.asFloatBuffer()
            resultado.append([numeros.get(i) for i in range(elementos)])
        return resultado


def criar_motor(caminho, threads=4):
    problemas = []
    for modulo, nome in (('tflite_runtime.interpreter', 'tflite-runtime'),
                         ('ai_edge_litert.interpreter', 'LiteRT (ai-edge-litert)')):
        try:
            Interpreter = importlib.import_module(modulo).Interpreter
        except Exception as erro:
            problemas.append(f'{nome}: {erro}')
            continue
        return _MotorPython(Interpreter, caminho, threads, nome)
    if no_android():
        return _MotorJava(caminho, threads)
    try:
        import tensorflow as tf
        return _MotorPython(tf.lite.Interpreter, caminho, threads, 'TensorFlow (tf.lite)')
    except Exception as erro:
        problemas.append(f'tensorflow: {erro}')
    raise RuntimeError('Não encontrei o TensorFlow Lite. No computador, rode: '
                       'pip install ai-edge-litert  (detalhes: ' + '; '.join(problemas) + ')')


class Detector:
    def __init__(self, caminho=CAMINHO_MODELO, confianca=0.5, threads=4, motor=None):
        self.rotulos = ler_rotulos(caminho)
        self.confianca = confianca
        self._motor = motor or criar_motor(caminho, threads)
        self._trava = threading.Lock()

    @property
    def tamanho_entrada(self):
        return (self._motor.largura, self._motor.altura)

    @property
    def motor_nome(self):
        return self._motor.nome

    def tamanho_analise(self, aspecto):
        largura, altura = self.tamanho_entrada
        if aspecto >= largura / altura:
            return (largura, max(1, round(largura / aspecto)))
        return (max(1, round(altura * aspecto)), altura)

    def detectar_rgba(self, pixels, largura, altura):
        return self.detectar_quadro(rgba_para_rgb(pixels), largura, altura)

    def detectar_quadro(self, rgb, largura, altura):
        L, A = self.tamanho_entrada
        if largura > L or altura > A or (largura != L and altura != A):
            return []
        if largura < L:
            linha, extra = largura * 3, bytes((L - largura) * 3)
            rgb = b''.join(rgb[i * linha:(i + 1) * linha] + extra for i in range(altura))
        if altura < A:
            rgb = bytes(rgb) + bytes((A - altura) * L * 3)
        fx, fy = L / largura, A / altura
        resultado = []
        for d in self.detectar_rgb(rgb):
            x0, y0 = d.x0 * fx, d.y0 * fy
            if x0 >= 1.0 or y0 >= 1.0:
                continue
            d.x0, d.y0 = x0, y0
            d.x1, d.y1 = min(1.0, d.x1 * fx), min(1.0, d.y1 * fy)
            resultado.append(d)
        return resultado

    def detectar_rgb(self, rgb):
        with self._trava:
            saidas = self._motor.inferir(rgb)
        caixas, classes, pontuacoes, total = _separar_saidas(saidas)
        resultado = []
        for i in range(total):
            confianca = float(pontuacoes[i])
            if confianca < self.confianca:
                continue
            classe = int(classes[i])
            rotulo = self.rotulos[classe] if 0 <= classe < len(self.rotulos) else ''
            if rotulo not in OBJETOS:
                continue
            y0, x0, y1, x1 = (min(1.0, max(0.0, float(v))) for v in caixas[4 * i:4 * i + 4])
            if x1 - x0 < 0.005 or y1 - y0 < 0.005:
                continue
            resultado.append(Deteccao(rotulo, confianca, x0, y0, x1, y1))
        return resultado

    def detectar_imagem(self, imagem):
        tamanho = self.tamanho_analise(imagem.width / imagem.height)
        rgb = imagem.convert('RGB').resize(tamanho)
        return self.detectar_quadro(rgb.tobytes(), *tamanho)
