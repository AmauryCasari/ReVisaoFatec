import json

from configuracoes import PADRAO, Configuracoes


def test_sem_arquivo_usa_o_padrao(tmp_path):
    cfg = Configuracoes(str(tmp_path))
    assert cfg.valores == PADRAO


def test_salva_e_carrega(tmp_path):
    cfg = Configuracoes(str(tmp_path))
    cfg['volume'] = 0.3
    cfg['camera'] = '1'
    cfg['som'] = False
    assert cfg.salvar()
    outra = Configuracoes(str(tmp_path))
    assert outra['volume'] == 0.3
    assert outra['camera'] == '1'
    assert outra['som'] is False


def test_arquivo_estragado_nao_trava(tmp_path):
    (tmp_path / 'revisao_config.json').write_text('{isso não é json', encoding='utf-8')
    assert Configuracoes(str(tmp_path)).valores == PADRAO


def test_valores_fora_do_lugar_sao_corrigidos(tmp_path):
    ruim = {'volume': 7, 'confianca': 'alta', 'som': 'sim', 'camera': 'lateral',
            'dist_perigo': 2.0, 'dist_atencao': 1.0, 'linha_1m': 0.3, 'linha_3m': 0.6}
    (tmp_path / 'revisao_config.json').write_text(json.dumps(ruim), encoding='utf-8')
    cfg = Configuracoes(str(tmp_path))
    assert cfg['volume'] == 1.0
    assert cfg['confianca'] == PADRAO['confianca']
    assert cfg['som'] is True
    assert cfg['camera'] == '0'
    assert cfg['dist_atencao'] >= cfg['dist_perigo'] + 0.5
    assert cfg['linha_1m'] > cfg['linha_3m']


def test_restaurar_mantem_a_calibracao(tmp_path):
    cfg = Configuracoes(str(tmp_path))
    cfg['linha_1m'] = 0.9
    cfg['volume'] = 0.1
    cfg.restaurar()
    assert cfg['linha_1m'] == 0.9
    assert cfg['volume'] == PADRAO['volume']
