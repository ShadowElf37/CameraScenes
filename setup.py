from sys import argv
from platform import system
from getpass import getuser
import os
import PyInstaller.__main__ as pyi

# https://pyinstaller.readthedocs.io/en/stable/usage.html

"""
exclude = 'libcrypto psutil'
exclude_bin = 'libcrypto-1_1.dll'#libopenblas.PYQHXLVVQ7VESDPUVUADXEVJOBGHJPAY.gfortran-win_amd64'

pyi.run_makespec(['client.py'], pathex=[os.getcwd()], name='Proscenium', excludes=exclude.split())

with open('Proscenium.spec', 'a') as spec:
    if exclude_bin:
        spec.write("a.binaries = a.binaries - TOC([\n\t" + ',\n\t'.join(
            f"('{lib}', None, None)" for lib in exclude_bin.split()) + '])')
"""

if system() == 'Windows':
    pyi.run([
        'client.py',
        '--onefile',
        '--clean',
        '--windowed',
        '--add-data=images/favicon.png;images',
        '--add-data=images/easter_egg.png;images',
        '--icon=images/favicon.ico',
        '--name=Proscenium'
    ])

elif system() == 'Darwin':
    pyi.run([
        'client.py',
        '--clean',
        '--osx-bundle-identifier=com.keycohen.Proscenium',
        '--windowed',
        '--add-data=images/favicon.png:images',
        '--add-data=images/easter_egg.png:images',
        '--icon=images/favicon.icns',
        '--name=Proscenium'
    ])

    if getuser() == 'speedyturtle':
        import subprocess
        path = os.path.join('dist', 'Proscenium.app')
        # subprocess.Popen(['xattr', '-cr', path])
        subprocess.Popen(['codesign', '--force', '--deep', '--sign', 'Developer ID Application: Karen Coveler (K559Z5J335)',  path])

#codesign --force --deep --sign "Developer ID Application: Karen Coveler (K559Z5J335)" --entitlements /Users/speedyturtle/Desktop/entitlements.plist -o runtime /Users/speedyturtle/Desktop/CameraScenes/dist/Proscenium.app
#xcrun altool --notarize-app --primary-bundle-id "com.keycohen.proscenium" --username "coveler@icloud.com" --password "qkdq-gpht-wyxz-keuk" --file /Users/speedyturtle/Proscenium\ 0.13.1.dmg