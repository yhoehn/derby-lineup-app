[app]

# App-Name (wie er auf dem Gerät erscheint)
title = Derby Lineup Manager

# Package-Name (eindeutig, reverse domain style)
package.name = derbylineup

# Package Domain (deine Domain oder github)
package.domain = org.derbyapp

# Quellcode-Verzeichnis
source.dir = .

# Haupt-Python-Datei
source.include_exts = py,png,jpg,kv,atlas,json

# Version (erhöhe bei Updates)
version = 1.0.0

# Python-Requirements (alle dependencies)
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow

# Android-Permissions
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Android API Level (mindestens 21 für moderne Features)
android.api = 31
android.minapi = 21

# Android NDK Version
android.ndk = 25b

# Android SDK Version
android.sdk = 33

# Orientierung (landscape = quer, portrait = hoch, all = beide)
orientation = landscape

# Fullscreen (für Tablets empfohlen)
fullscreen = 1

# App-Icon (optional, falls du eins hast)
# icon.filename = %(source.dir)s/icon.png

# Presplash (Ladebildschirm, optional)
# presplash.filename = %(source.dir)s/presplash.png

# Android Theme (für Material Design)
android.gradle_dependencies = com.google.android.material:material:1.4.0

# Unterstützte Architekturen (für Tablets wichtig)
android.archs = arm64-v8a,armeabi-v7a

# Release-Modus (0 = Debug, 1 = Release)
# Für Tests erst mal Debug
# p4a.bootstrap = sdl2

[buildozer]

# Log-Level (für Debugging)
log_level = 2

# Warnungen
warn_on_root = 1