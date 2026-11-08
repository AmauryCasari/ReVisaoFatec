[app]

title = RéVisão

package.name = revisao
package.domain = br.edu.fatec.ideathon

source.dir = .
source.include_exts = py,kv,png,wav,tflite
source.exclude_dirs = tests, ferramentas, camerax_provider, p4a_recipes, bin, .buildozer, .git, venv, .venv, __pycache__

version = 0.1.0

requirements = python3,kivy,camera4kivy,gestures4kivy

icon.filename = %(source.dir)s/assets/icone.png
presplash.filename = %(source.dir)s/assets/icone.png

orientation = landscape, landscape-reverse
fullscreen = 1

android.permissions = CAMERA

android.api = 33
android.minapi = 24

android.archs = arm64-v8a

android.gradle_dependencies = org.tensorflow:tensorflow-lite:2.16.1
android.enable_androidx = True

android.wakelock = True

android.presplash_color = #141414
android.accept_sdk_license = True

p4a.hook = camerax_provider/gradle_options.py

p4a.local_recipes = ./p4a_recipes

p4a.branch = v2026.05.09

[buildozer]

log_level = 2
warn_on_root = 1
