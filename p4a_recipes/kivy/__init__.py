from os.path import dirname

import pythonforandroid.recipes.kivy as original
from pythonforandroid.recipes.kivy import KivyRecipe


class KivyRevisao(KivyRecipe):
    python_depends = ['certifi', 'chardet', 'idna', 'urllib3', 'filetype']

    def get_recipe_dir(self):
        return dirname(original.__file__)


recipe = KivyRevisao()
