from sys import argv
from platform import system
import PyInstaller.__main__ as pyi

# pyinstaller --onedir --windowed --add-data="images/favicon.png:images" --icon="images/favicon.icns" --name="Proscenium" client.py

if system() == 'Windows':
    pyi.run([
        'client.py',
        '--onefile',
        '--windowed',
        '--add-data=images/favicon.png;images',
        '--icon=images/favicon.ico',
        '--name=Proscenium'
    ])
elif system() == 'Darwin':
    pyi.run([
        'client.py',
        '--onedir',
        '--osx-bundle-identifier=com.stuff.Proscenium',
        '--windowed',
        '--add-data=images/favicon.png:images',
        '--icon=images/favicon.icns',
        '--name=Proscenium'
    ])

    import subprocess
    subprocess.run('codesign --force --deep --sign "Developer ID Application: Karen Coveler (K559Z5J335)" dist/Proscenium.app')