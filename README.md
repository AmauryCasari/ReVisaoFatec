<h1 align="center">RéVisão: câmera de ré inteligente</h1>

<p align="center">
  Projeto do <strong>Ideathon FATEC</strong> (mobilidade urbana e sustentabilidade).
</p>

## O que é

O RéVisão é um app em Python com Kivy que, ligado a uma câmera USB com ou sem fio instalada na traseira do carro, reconhece **pessoas, veículos e animais** e avisa o motorista com **bipes e alertas na tela** quando algo se aproxima.

Tudo roda no aparelho, **sem internet, login ou servidor**, e o vídeo **não é gravado**.

**Por que importa:** manobras de ré têm pontos cegos que podem causar atropelamentos e acidentes, principalmente com pedestres, crianças e animais. O RéVisão leva esse aviso para carros que não têm o recurso usando uma câmera USB comum, inclusive webcams e câmeras que já estavam paradas e seriam descartadas. Em vez de comprar um kit novo, a pessoa reaproveita o equipamento que já tem, o que adia o descarte de lixo eletrônico, e a calibração das linhas-guia permite que câmeras de modelos diferentes funcionem bem. Tudo roda localmente, sem servidor nem internet.

## Como funciona

1. A câmera USB manda o vídeo para o app.
2. A IA (TensorFlow Lite com o modelo EfficientDet-Lite0) encontra pessoas, veículos e animais em cada quadro.
3. O app estima a distância de cada objeto e define a zona:
   - 🟢 **Livre**
   - 🟡 **Atenção**: até 3 m
   - 🔴 **Perigo**: até 1 m
4. A tela mostra as linhas-guia, as caixas e a faixa **PARE**, e o bipe acelera conforme o objeto se aproxima.

**Telas do app:** inicial, ajuda e câmera (principais); configurações e calibração (extras).

## Como rodar no computador

Precisa do **Python 3.12** e de uma **câmera USB** ligada ao computador.

Se ainda não tem o Python 3.12, instale pelo terminal (Windows):

```bash
winget install -e --id Python.Python.3.12
```

Feche e abra o terminal de novo depois da instalação. Em seguida, dentro da pasta do projeto:

```bash
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements-desktop.txt
python main.py
```

Em **Configurações**, escolha a câmera USB e faça a calibração das linhas-guia uma vez, marcando no chão **1 m** e **3 m** a partir da câmera.

## Limitações

- A distância é uma estimativa e depende da calibração e do chão plano.
- O app não detecta muros, postes nem meio-fio.
- À noite ou contra a luz, a detecção piora.
- É uma ferramenta de apoio e **não substitui a atenção do motorista**.

## Equipe

| Integrante | Papel |
|---|---|
| Henrique de Sousa Costa e Lucas Grauth Dessandre | Visão computacional: detecção e distância |
| Amaury Casari Pardin Junior | Interface e acessibilidade |
| Carlos Eliel da Silva | Alertas: linhas-guia, caixas, faixa e bipes |
| Heitor Scavassa Barbosa | Testes, dados e vídeo |

## Bibliotecas e atribuição

Kivy, [Camera4Kivy](https://github.com/Android-for-Python/Camera4Kivy), TensorFlow Lite (LiteRT) e o modelo EfficientDet-Lite0 (TensorFlow, conjunto COCO).

O código da câmera e do detector foi baseado no exemplo `c4k_tflite_example`, da Camera4Kivy.

## Uso de IA

Usamos o Claude (Anthropic) como ferramenta de apoio no desenvolvimento do projeto. Todo o conteúdo foi revisado, ajustado e testado pela equipe, que é responsável pelas decisões e pelo resultado final.
