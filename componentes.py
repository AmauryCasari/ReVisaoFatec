from kivy.properties import BooleanProperty, ColorProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label


class Botao(ButtonBehavior, Label):
    cor = ColorProperty('#2C2C2E')


class BotaoOpcao(Botao):
    ativo = BooleanProperty(False)


class Chip(Label):
    fundo = ColorProperty([0, 0, 0, 0.62])
