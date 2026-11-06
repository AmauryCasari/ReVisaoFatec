import os

import pytest

from detector import _separar_saidas, rgba_para_rgb

PASTA_IMAGENS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'imagens')


@pytest.fixture(scope='module')
def detector():
    pytest.importorskip('PIL')
    from detector import Detector
    try:
        return Detector(confianca=0.4)
    except RuntimeError as erro:
        pytest.skip(str(erro))


def abrir(nome):
    from PIL import Image
    return Image.open(os.path.join(PASTA_IMAGENS, nome)).convert('RGB')


def test_rgba_para_rgb():
    assert rgba_para_rgb(bytes([1, 2, 3, 255, 4, 5, 6, 0])) == bytes([1, 2, 3, 4, 5, 6])


def test_separa_saidas_mesmo_com_a_ordem_trocada():
    caixas = [0.1, 0.2, 0.5, 0.6] + [0.0] * 4
    classes = [17.0, 0.0]
    pontuacoes = [0.83, 0.41]
    quantidade = [2.0]
    for ordem in ([caixas, classes, pontuacoes, quantidade],
                  [caixas, pontuacoes, classes, quantidade]):
        c, cl, p, n = _separar_saidas(ordem)
        assert (c, cl, p, n) == (caixas, classes, pontuacoes, 2)


def test_encontra_a_pessoa(detector):
    achados = detector.detectar_imagem(abrir('astronauta.jpg'))
    assert 'person' in [d.rotulo for d in achados]


def test_encontra_o_gato(detector):
    achados = detector.detectar_imagem(abrir('gata.jpg'))
    assert 'cat' in [d.rotulo for d in achados]


def test_imagem_deitada_volta_no_lugar_certo(detector):
    from PIL import Image
    cena = Image.new('RGB', (1024, 576), (70, 70, 70))
    cena.paste(abrir('gata.jpg').resize((420, 280)), (580, 280))
    gatos = [d for d in detector.detectar_imagem(cena) if d.rotulo == 'cat']
    assert gatos, 'a gata deveria ser encontrada'
    g = gatos[0]
    assert 0.0 <= g.x0 < g.x1 <= 1.0 and 0.0 <= g.y0 < g.y1 <= 1.0
    assert g.x0 > 0.45 and g.y0 > 0.35
    assert g.x1 == pytest.approx(1000 / 1024, abs=0.06)


def test_imagem_em_pe_tambem_funciona(detector):
    from PIL import Image
    cena = Image.new('RGB', (576, 1024), (70, 70, 70))
    cena.paste(abrir('astronauta.jpg').resize((560, 560)), (8, 440))
    pessoas = [d for d in detector.detectar_imagem(cena) if d.rotulo == 'person']
    assert pessoas, 'a pessoa deveria ser encontrada'
    p = pessoas[0]
    assert 0.0 <= p.x0 < p.x1 <= 1.0
    assert p.y0 > 0.35


def test_quadro_da_camera_em_rgba(detector):
    imagem = abrir('astronauta.jpg')
    largura, altura = detector.tamanho_analise(imagem.width / imagem.height)
    pixels = imagem.convert('RGBA').resize((largura, altura)).tobytes()
    assert 'person' in [d.rotulo for d in detector.detectar_rgba(pixels, largura, altura)]


def test_quadro_de_tamanho_errado_e_ignorado(detector):
    assert detector.detectar_rgba(bytes(4 * 10 * 10), 10, 10) == []
