import math

import pytest

from distancia import (ATENCAO, LIVRE, OBJETOS, PERIGO, Calibracao, Deteccao, Rastreador,
                       Situacao, escolher_pessoa, formatar_limite, formatar_metros,
                       intervalo_bipe, iou, medir_foco, texto_pare, texto_status,
                       zona_da_distancia)


def caixa_no_chao(cal, rotulo, distancia, centro=0.5, proporcao=0.4, confianca=0.9):
    altura = OBJETOS[rotulo][2] * cal.foco / distancia
    base = cal.y_no_chao(distancia)
    largura = altura * proporcao
    return Deteccao(rotulo, confianca, centro - largura / 2, base - altura,
                    centro + largura / 2, base)


def test_calibracao_bate_nas_marcas_de_1m_e_3m():
    cal = Calibracao()
    assert cal.distancia_pelo_chao(cal.linha_1m) == pytest.approx(1.0)
    assert cal.distancia_pelo_chao(cal.linha_3m) == pytest.approx(3.0)


def test_quanto_mais_baixo_na_imagem_mais_perto():
    cal = Calibracao()
    distancias = [cal.distancia_pelo_chao(y) for y in (0.55, 0.65, 0.75, 0.85, 0.95)]
    assert distancias == sorted(distancias, reverse=True)


def test_acima_do_horizonte_e_longe():
    cal = Calibracao()
    assert math.isinf(cal.distancia_pelo_chao(cal.horizonte - 0.05))


def test_y_no_chao_e_o_inverso_da_distancia():
    cal = Calibracao(0.8, 0.5, 0.9)
    for d in (0.8, 1.0, 2.0, 3.0, 6.0):
        assert cal.distancia_pelo_chao(cal.y_no_chao(d)) == pytest.approx(d)


def test_distancia_pelo_tamanho():
    cal = Calibracao(foco=0.9)
    assert cal.distancia_pelo_tamanho(1.7 * 0.9 / 2.0, 1.7) == pytest.approx(2.0)


def test_estimar_objeto_inteiro_na_imagem():
    cal = Calibracao()
    for d in (1.5, 2.0, 4.0):
        assert cal.estimar(caixa_no_chao(cal, 'person', d)) == pytest.approx(d)


def test_crianca_nao_parece_mais_longe():
    cal = Calibracao()
    altura = 1.10 * cal.foco / 2.0
    base = cal.y_no_chao(2.0)
    crianca = Deteccao('person', 0.9, 0.45, base - altura, 0.55, base)
    assert cal.estimar(crianca) == pytest.approx(2.0)


def test_objeto_cortado_na_borda_de_baixo_fica_em_perigo():
    cal = Calibracao()
    cortado = Deteccao('person', 0.9, 0.3, 0.1, 0.7, 1.0)
    assert cal.estimar(cortado) <= 1.0


def test_medir_foco_com_uma_pessoa_a_3m():
    cal = Calibracao(foco=0.95)
    pessoa = caixa_no_chao(cal, 'person', 3.0)
    assert medir_foco(pessoa, 3.0, 1.70) == pytest.approx(0.95)


def test_escolher_pessoa_pega_a_mais_confiavel():
    a = Deteccao('person', 0.6, 0, 0, 0.1, 0.5)
    b = Deteccao('person', 0.8, 0.5, 0, 0.6, 0.5)
    c = Deteccao('dog', 0.99, 0.2, 0.5, 0.3, 0.6)
    assert escolher_pessoa([a, b, c]) is b
    assert escolher_pessoa([c]) is None


def test_zonas_com_margem_para_nao_piscar():
    assert zona_da_distancia(0.8, 1.0, 3.0) == PERIGO
    assert zona_da_distancia(2.0, 1.0, 3.0) == ATENCAO
    assert zona_da_distancia(4.0, 1.0, 3.0) == LIVRE
    assert zona_da_distancia(1.1, 1.0, 3.0, PERIGO) == PERIGO
    assert zona_da_distancia(1.2, 1.0, 3.0, PERIGO) == ATENCAO
    assert zona_da_distancia(3.1, 1.0, 3.0, ATENCAO) == ATENCAO
    assert zona_da_distancia(3.2, 1.0, 3.0, ATENCAO) == LIVRE


def test_formatos_em_portugues():
    assert formatar_metros(0.83) == '0,8'
    assert formatar_metros(2.0) == '2'
    assert formatar_metros(2.04) == '2'
    assert formatar_metros(4.6) == '5'
    assert formatar_metros(math.inf) == 'longe'
    assert formatar_limite(1.5) == '1,5'
    assert formatar_limite(3.0) == '3'


def test_textos_da_tela():
    r = Rastreador()
    perto = r.atualizar([caixa_no_chao(r.calibracao, 'person', 0.8)], 0.0)
    assert texto_status(perto, 3.0) == 'PARE: pessoa a ~0,8 m'
    assert texto_pare(perto) == 'pessoa a ~0,8 m atrás do carro'
    assert perto.objetos[0].rotulo_tela() == 'Pessoa · ~0,8 m · perigo'
    assert texto_status(Situacao(), 3.0) == 'Livre: nada a menos de 3 m'


def test_intervalo_do_bipe_acelera_quando_aproxima():
    intervalos = [intervalo_bipe(d, 1.0, 3.0) for d in (3.0, 2.5, 2.0, 1.5, 1.0)]
    assert intervalos == sorted(intervalos, reverse=True)
    assert intervalo_bipe(0.5, 1.0, 3.0) == pytest.approx(0.15)
    assert intervalo_bipe(9.0, 1.0, 3.0) == pytest.approx(0.8)


def test_iou():
    a = Deteccao('car', 1, 0, 0, 0.5, 0.5)
    assert iou(a, a) == pytest.approx(1.0)
    assert iou(a, Deteccao('car', 1, 0.5, 0.5, 1, 1)) == 0.0
    assert iou(a, Deteccao('car', 1, 0.25, 0, 0.75, 0.5)) == pytest.approx(1 / 3)


def test_objeto_novo_precisa_aparecer_em_dois_quadros():
    r = Rastreador()
    d = Deteccao('dog', 0.6, 0.4, 0.5, 0.6, 0.9)
    assert r.atualizar([d], 0.0).objetos == []
    assert len(r.atualizar([d], 0.1).objetos) == 1


def test_confianca_alta_conta_na_hora():
    r = Rastreador()
    d = Deteccao('person', 0.9, 0.4, 0.3, 0.6, 0.9)
    assert len(r.atualizar([d], 0.0).objetos) == 1


def test_memoria_segura_o_alerta_quando_o_detector_pisca():
    r = Rastreador(memoria=0.5)
    d = caixa_no_chao(r.calibracao, 'person', 0.8)
    assert r.atualizar([d], 0.0).nivel == PERIGO
    assert r.atualizar([], 0.3).nivel == PERIGO
    assert r.atualizar([], 0.9).nivel == LIVRE


def test_suavizacao_rapida_ao_aproximar_e_lenta_ao_afastar():
    cal = Calibracao()
    r = Rastreador(cal)
    r.atualizar([caixa_no_chao(cal, 'person', 3.0)], 0.0)
    aproximando = r.atualizar([caixa_no_chao(cal, 'person', 2.0)], 0.1).objetos[0].distancia
    r2 = Rastreador(cal)
    r2.atualizar([caixa_no_chao(cal, 'person', 2.0)], 0.0)
    afastando = r2.atualizar([caixa_no_chao(cal, 'person', 3.0)], 0.1).objetos[0].distancia
    assert aproximando == pytest.approx(3.0 + 0.7 * (2.0 - 3.0))
    assert afastando == pytest.approx(2.0 + 0.35 * (3.0 - 2.0))


def test_nivel_e_o_do_objeto_mais_perigoso():
    cal = Calibracao()
    r = Rastreador(cal)
    pessoa = caixa_no_chao(cal, 'person', 4.0, centro=0.2)
    cachorro = caixa_no_chao(cal, 'dog', 2.0, centro=0.7, proporcao=1.2)
    situacao = r.atualizar([pessoa, cachorro], 0.0)
    assert situacao.nivel == ATENCAO
    assert [o.rotulo for o in situacao.objetos] == ['dog', 'person']


def test_grupos_diferentes_nao_se_misturam():
    r = Rastreador()
    pessoa = Deteccao('person', 0.9, 0.40, 0.30, 0.60, 0.90)
    cachorro = Deteccao('dog', 0.9, 0.42, 0.32, 0.62, 0.90)
    r.atualizar([pessoa, cachorro], 0.0)
    situacao = r.atualizar([pessoa, cachorro], 0.1)
    assert sorted(o.rotulo for o in situacao.objetos) == ['dog', 'person']


def test_carro_que_vira_caminhao_continua_o_mesmo_objeto():
    r = Rastreador()
    r.atualizar([Deteccao('car', 0.9, 0.4, 0.4, 0.6, 0.6)], 0.0)
    situacao = r.atualizar([Deteccao('truck', 0.9, 0.41, 0.4, 0.61, 0.6)], 0.1)
    assert len(situacao.objetos) == 1
    assert situacao.objetos[0].acertos == 2


def test_ignora_o_que_nao_e_pessoa_veiculo_ou_animal():
    r = Rastreador()
    assert r.atualizar([Deteccao('chair', 0.99, 0.4, 0.4, 0.6, 0.99)], 0.0).objetos == []
