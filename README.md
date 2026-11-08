# RéVisão: câmera de ré inteligente

Projeto do Ideathon FATEC (mobilidade urbana e sustentabilidade).

O RéVisão é um app em Python com Kivy que, ligado a uma câmera USB com ou sem fio instalada na traseira do carro, reconhece pessoas, veículos e animais e avisa o motorista com bipes e alertas na tela quando algo se aproxima. Tudo roda no aparelho, sem internet, login ou servidor, e o vídeo não é gravado.

## Equipe

| Integrante | Papel |
|---|---|
| Henrique de Sousa Costa e Lucas Grauth Dessandre | Visão computacional: detecção e distância |
| Amaury Casari Pardin Junior | Interface e acessibilidade |
| Carlos Eliel da Silva | Alertas: linhas-guia, caixas, faixa e bipes |
| Heitor Scavassa Barbosa | Testes, dados e vídeo |

## Como funciona

1. A câmera USB manda o vídeo para o app.
2. A IA (TensorFlow Lite com o modelo EfficientDet-Lite0) encontra pessoas, veículos e animais em cada quadro.
3. O app estima a distância de cada objeto e define a zona: livre, atenção (até 3 m) ou perigo (até 1 m).
4. A tela mostra as linhas-guia, as caixas e a faixa PARE, e o bipe acelera conforme o objeto se aproxima.

## Como rodar no computador

Precisa do Python 3.12 e de uma câmera USB ligada ao computador.

```
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements-desktop.txt
python main.py
```

Em Configurações, escolha a câmera na lista "Qual câmera usar". O botão Câmera, na tela da câmera, troca de câmera sem sair dela.

Para a distância ficar certa, faça a calibração uma vez em Configurações > Calibrar linhas-guia:

1. Com uma pessoa em pé a 3 m da câmera, de corpo inteiro, toque em Medir pessoa.
2. Se a câmera enxerga o chão, marque 1 m e 3 m no chão e arraste as linhas até as marcas. Assim as linhas do chão passam a ser usadas.
3. Toque em Salvar calibração.

## Telas

Principais: inicial, ajuda e câmera. Extras: configurações e calibração.

## Limitações

- A distância é uma estimativa e depende da calibração e do chão plano.
- O app não detecta muros, postes nem meio-fio.
- À noite ou contra a luz, a detecção piora.
- É uma ferramenta de apoio e não substitui a atenção do motorista.

## Bibliotecas

Kivy, Camera4Kivy, TensorFlow Lite (LiteRT) e o modelo EfficientDet-Lite0 (TensorFlow, conjunto COCO). O código da câmera e do detector foi baseado no exemplo c4k_tflite_example, da Camera4Kivy.

## Uso de IA

Usamos o Claude (Anthropic) como ferramenta de apoio no desenvolvimento do projeto. Todo o conteúdo foi revisado, ajustado e testado pela equipe, que é responsável pelas decisões e pelo resultado final.
