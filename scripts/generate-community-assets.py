#!/usr/bin/env python3
"""Generate original MIT community artwork; legacy names preserve UI compatibility."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import re
from PySide6.QtGui import QImage, QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
NAMES = [
    'Audio16x16.png', 'Settings16x16.png', 'Music30x30.png', 'Movie30x30.png',
    'Communication30x30.png', 'Gaming30x30.png', 'Speakers30x30.png',
    'EqualiserNormal24x24.png', 'LogoNahimicSteelSeries.png',
    'MuteNormalCheckedCheckBox24x24.png', 'MuteNormalUncheckedCheckBox24x24.png',
    'DesactivatedFXCheckBox45x50.png', 'NormalCheckedFXCheckbox45x50.png',
    'NormalUncheckedFXCheckBox45x50.png', 'OverUncheckedFXCheckBox45x50.png',
    'SoundSurroundOn255x255.png', 'SoundSurroundOff255x255.png',
    'VolumeStabiliserOn80x60.png', 'VolumeStabilizerOff80x60.png',
]

def generate(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in sorted(set(NAMES)):
        dimensions = re.search(r'(\d+)x(\d+)', name)
        w, h = map(int, dimensions.groups()) if dimensions else (160, 64)
        image = QImage(w, h, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        disabled = 'Off' in name or 'Unchecked' in name or 'Desactivated' in name
        if disabled:
            color = QColor('#5d476b')
        elif 'Mute' in name and 'Checked' in name:
            color = QColor('#fb3a29')
        elif 'Check' in name or 'Checkbox' in name or 'Volume' in name:
            color = QColor('#fc77a6')
        else:
            color = QColor('#7fffff')
        painter.setPen(QPen(color, max(1.0, w / 24.0)))
        if 'Logo' in name:
            icon_png = ROOT / 'app/nahimic.png'
            if icon_png.exists():
                src_img = QImage(str(icon_png))
                scaled = src_img.scaled(min(w, h), min(w, h), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                painter.drawImage((w - scaled.width()) // 2, (h - scaled.height()) // 2, scaled)
            else:
                painter.setFont(QFont('Sans', 10, QFont.Weight.Bold))
                painter.setPen(QPen(QColor('#fc77a6')))
                painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "That's So Sound")
        elif 'Check' in name or 'Checkbox' in name:
            painter.drawRoundedRect(QRectF(w*.12, h*.15, w*.76, h*.7), w*.12, w*.12)
            if 'Checked' in name:
                painter.drawLine(int(w*.25), int(h*.5), int(w*.43), int(h*.65))
                painter.drawLine(int(w*.43), int(h*.65), int(w*.75), int(h*.32))
        else:
            for index, height in enumerate((.3, .55, .85, .55, .3)):
                x = int(w * (.18 + index * .16))
                painter.drawLine(x, int(h*(1-height)/2), x, int(h*(1+height)/2))
            if 'Surround' in name:
                painter.drawEllipse(QRectF(w*.08,h*.08,w*.84,h*.84))
        painter.end()
        if not image.save(str(destination / name)):
            raise RuntimeError('Unable to save ' + name)

if __name__ == '__main__':
    app = QApplication([])
    generate(ROOT / 'app/assets')
