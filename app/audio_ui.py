"""Audio-first workbench layout and palette-aware controls.

The inline band-gain plot is a view of settings, never a simulated level meter.
Flat functional panels group independently adjustable effects. Existing branding
is retained; utility artwork is tinted so it remains legible in every palette.
"""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QPixmap, QPainterPath, QLinearGradient
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSlider, QFrame, QDialog, QToolButton, QButtonGroup, QSizePolicy,
    QStyle, QStyleOptionToolButton, QStylePainter, QComboBox, QScrollArea)
from backend import PROFILES
from i18n import LANGUAGES
from themes import PALETTES, tokens_for
from window_frame import decorate

ASSETS = Path(__file__).with_name('assets')
EQ_BANDS = ('31Hz', '62Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', '16kHz')


def asset(name):
    return QPixmap(str(ASSETS / name))


def tinted(pixmap, color):
    result = QPixmap(pixmap.size()); result.fill(Qt.transparent)
    painter = QPainter(result); painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(result.rect(), QColor(color)); painter.end()
    return result


class Themed:
    @property
    def tokens(self):
        return tokens_for(self)


class Toggle(Themed, QCheckBox):
    """Native keyboard/accessible checkbox semantics with a painted switch."""
    def __init__(self, label, parent=None, mute=False):
        super().__init__(label, parent)
        self.setAccessibleName(label); self.setToolTip(label)
        self.setCursor(Qt.PointingHandCursor); self.setFixedSize(48, 36)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        t = self.tokens; p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        active = self.isChecked() and self.isEnabled()
        color = t['accent_hover'] if active and self.underMouse() else t['accent'] if active else t['track']
        p.setPen(Qt.NoPen); p.setBrush(QColor(color)); p.drawRoundedRect(QRectF(4, 8, 40, 20), 10, 10)
        p.setBrush(QColor(t['on_accent'] if active else t['surface']))
        p.drawEllipse(QRectF(26 if self.isChecked() else 7, 11, 14, 14))
        if self.hasFocus():
            p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor(t['focus']), 2))
            p.drawRoundedRect(QRectF(1, 3, 46, 30), 6, 6)


class ControlSlider(QSlider):
    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                           Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_Home, Qt.Key_End):
            self.sliderReleased.emit()

    def wheelEvent(self, event):
        before = self.value(); super().wheelEvent(event)
        if self.value() != before: self.sliderReleased.emit()


class SpacedToolButton(Themed, QToolButton):
    def sizeHint(self):
        return QSize(self.fontMetrics().horizontalAdvance(self.text()) + 68, 44)

    def paintEvent(self, event):
        option = QStyleOptionToolButton(); self.initStyleOption(option)
        option.text = ''; option.icon = QIcon()
        p = QStylePainter(self); p.drawComplexControl(QStyle.CC_ToolButton, option)
        t = self.tokens
        color = t['muted'] if not self.isEnabled() else t['accent'] if self.isChecked() else t['secondary']
        icon = tinted(self.icon().pixmap(self.iconSize()), color)
        width = self.iconSize().width()
        # Profiles center their icon/text group; sidebar labels remain left aligned.
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        left = max(10, (self.width() - width - 10 - text_width) // 2) if self.objectName() == 'profileButton' else 14
        p.drawPixmap(left, (self.height() - icon.height()) // 2, icon)
        p.setPen(QColor(color))
        p.drawText(self.rect().adjusted(left + width + 10, 0, -6, 0), Qt.AlignLeft | Qt.AlignVCenter, self.text())
        if self.objectName() == 'profileButton' and self.isChecked():
            p.fillRect(1, self.height() - 3, self.width() - 2, 2, QColor(color))


class EffectArt(Themed, QLabel):
    def __init__(self, switch, on, off):
        super().__init__(); self.switch = switch; self.on = on; self.off = off
        self.setFixedSize(88, 64); switch.toggled.connect(self.update)

    def paintEvent(self, event):
        color = self.tokens['accent'] if self.switch.isChecked() and self.isEnabled() else self.tokens['muted']
        image = tinted(asset(self.on if self.switch.isChecked() else self.off), color)
        image = image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter = QPainter(self)
        painter.drawPixmap((self.width()-image.width())//2, (self.height()-image.height())//2, image)


class EqualizerCurve(Themed, QWidget):
    def __init__(self, sliders):
        super().__init__(); self.sliders = sliders
        self.setMinimumHeight(82); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAccessibleName('Equalizer band gains, not an audio level meter')
        self.setToolTip('The line connects the ten band gains. It is not a measured frequency response.')
        for slider in sliders:
            slider.valueChanged.connect(self.update); slider.rangeChanged.connect(self.update)

    def values(self):
        return [s.value() for s in self.sliders]

    def paintEvent(self, event):
        t = self.tokens; p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        area = QRectF(34, 10, max(1, self.width()-48), max(1, self.height()-22))
        low = min(s.minimum() for s in self.sliders); high = max(s.maximum() for s in self.sliders)
        span = max(1, high-low)
        def y(value): return area.bottom() - (value-low) / span * area.height()
        p.setFont(self.font())
        for value in (high, 0, low):
            p.setPen(QPen(QColor(t['border']), 1, Qt.DotLine if value else Qt.SolidLine))
            p.drawLine(QPointF(area.left(), y(value)), QPointF(area.right(), y(value)))
            p.setPen(QColor(t['muted']))
            p.drawText(QRectF(0, y(value)-8, 29, 16), Qt.AlignRight | Qt.AlignVCenter, f'{value:+d}' if value else '0')
        points = [QPointF(area.left() + i*area.width()/9, y(v)) for i, v in enumerate(self.values())]
        line = QPainterPath(points[0])
        for a, b in zip(points, points[1:]):
            midpoint = (a.x()+b.x())/2
            line.cubicTo(QPointF(midpoint, a.y()), QPointF(midpoint, b.y()), b)
        fill = QPainterPath(line); fill.lineTo(area.right(), area.bottom()); fill.lineTo(area.left(), area.bottom()); fill.closeSubpath()
        color = QColor(t['accent'] if self.isEnabled() else t['muted'])
        gradient = QLinearGradient(0, area.top(), 0, area.bottom())
        tint = QColor(color); tint.setAlpha(48); gradient.setColorAt(0, tint)
        tint.setAlpha(0); gradient.setColorAt(1, tint)
        p.fillPath(fill, gradient); p.setPen(QPen(color, 2)); p.drawPath(line)
        p.setBrush(QColor(t['surface']))
        for point in points: p.drawEllipse(point, 3, 3)


def label(text, role='caption', wrap=False):
    result = QLabel(text); result.setObjectName(role); result.setWordWrap(wrap)
    if wrap: result.setMinimumWidth(0)
    return result


def panel_layout():
    frame = QFrame(); frame.setObjectName('effect')
    layout = QVBoxLayout(frame); layout.setContentsMargins(16, 10, 16, 12); layout.setSpacing(4)
    return frame, layout


def build_panel(p):
    p.resize(1280, 800); p.setMinimumSize(1060, 720)
    central = QWidget(); central.setObjectName('root'); p.setCentralWidget(central)
    outer = QVBoxLayout(central); outer.setContentsMargins(1, 1, 1, 1); outer.setSpacing(0)
    content = QWidget(); outer.addWidget(content, 1); p.titlebar = decorate(p, outer)
    shell = QHBoxLayout(content); shell.setContentsMargins(0, 0, 0, 0); shell.setSpacing(0)
    navigation = QFrame(); navigation.setObjectName('navigation'); navigation.setFixedWidth(184)
    nav = QVBoxLayout(navigation); nav.setContentsMargins(10, 16, 10, 16); nav.setSpacing(6)
    brand = QHBoxLayout(); logo = QLabel(); logo.setPixmap(asset('LogoNahimicSteelSeries.png').scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    brand.addWidget(logo); brand.addWidget(label("That's So\nSound", 'brand'), 1); nav.addLayout(brand); nav.addSpacing(14)
    p.audio_navigation = SpacedToolButton(); p.audio_navigation.setObjectName('navigationButton')
    p.audio_navigation.setText('音频'); p.audio_navigation.setIcon(QIcon.fromTheme('audio-volume-high', p.style().standardIcon(QStyle.SP_MediaVolume)))
    p.audio_navigation.setCheckable(True); p.audio_navigation.setChecked(True)
    p.audio_navigation.clicked.connect(lambda: (p.audio_navigation.setChecked(True), p.preferences.hide()))
    p.settings_navigation = SpacedToolButton(); p.settings_navigation.setObjectName('navigationButton')
    p.settings_navigation.setText('设置'); p.settings_navigation.setIcon(QIcon.fromTheme('preferences-system', p.style().standardIcon(QStyle.SP_FileDialogDetailedView)))
    p.settings_navigation.clicked.connect(p.show_preferences)
    for button in (p.audio_navigation, p.settings_navigation):
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon); button.setMinimumHeight(44); nav.addWidget(button)
    nav.addStretch(); nav.addWidget(label("Gracie Abrams Edition", 'muted')); nav.addWidget(label('0.3.0', 'muted'))
    shell.addWidget(navigation)
    workbench = QWidget(); page = QVBoxLayout(workbench); page.setContentsMargins(20, 10, 20, 0); page.setSpacing(10); shell.addWidget(workbench, 1)
    p.controls = QWidget(); controls = QVBoxLayout(p.controls); controls.setContentsMargins(0, 0, 0, 0); controls.setSpacing(10)
    header = QHBoxLayout(); titles = QVBoxLayout(); titles.setSpacing(0)
    titles.addWidget(label('音频', 'heading')); titles.addWidget(label('Tune your internal speakers.', 'caption'))
    header.addLayout(titles, 1)
    p.power_label = label('正在连接'); header.addWidget(p.power_label)
    p.power = Toggle('启用音效'); p.power.clicked.connect(lambda checked: p.submit(lambda: p.backend.enabled(checked), 'state', 'enabled', checked))
    p.power.toggled.connect(lambda checked: p.translations.bind(p.power_label, 'text', '音效已开启' if checked else '音效已关闭'))
    header.addWidget(p.power); controls.addLayout(header)
    p.profiles = QFrame(); p.profiles.setObjectName('profileBar')
    profiles = QHBoxLayout(p.profiles); profiles.setContentsMargins(2, 1, 2, 1); profiles.setSpacing(2)
    group = QButtonGroup(p); group.setExclusive(True)
    profile_icons = {'Music': ('audio-x-generic', QStyle.SP_MediaVolume),
                     'Movie': ('video-x-generic', QStyle.SP_MediaPlay),
                     'Communication': ('call-start', QStyle.SP_MessageBoxInformation),
                     'Gaming': ('input-gaming', QStyle.SP_ComputerIcon)}
    for name in ('Music', 'Movie', 'Communication', 'Gaming'):
        button = SpacedToolButton(); button.setObjectName('profileButton'); button.setText(PROFILES[name][0])
        icon_name, fallback = profile_icons[name]
        button.setIcon(QIcon.fromTheme(icon_name, p.style().standardIcon(fallback))); button.setIconSize(QSize(22, 22))
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon); button.setCheckable(True)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); button.setFixedHeight(44)
        button.clicked.connect(lambda checked, n=name: p.submit(lambda: p.backend.profile(n), 'settings', 'profile', n))
        group.addButton(button); p.modes[name] = button; profiles.addWidget(button, 1)
    controls.addWidget(p.profiles)
    tuning = QHBoxLayout(); tuning.setSpacing(10)
    p.equalizer, eq = panel_layout(); p.equalizer.setMinimumHeight(300)
    eq_head = QHBoxLayout(); eq_head.addWidget(label('均衡器', 'effectTitle')); eq_head.addStretch()
    eq_head.addWidget(label('Band gains · dB', 'muted'))
    eq_head.addWidget(p.effect_switch('kSet_EQState', '启用均衡器')); eq.addLayout(eq_head)
    sliders = []
    for band in EQ_BANDS:
        key = 'kSet_EQ'+band+'GainDB'; slider = ControlSlider(Qt.Vertical); slider.setRange(-12, 12)
        slider.setFixedWidth(26); slider.setMinimumHeight(64)
        p.translations.bind(slider, 'accessibleName', '{frequency} Hz 增益', frequency=band.removesuffix('Hz'))
        slider.sliderReleased.connect(lambda n=key, s=slider: p.submit(lambda v=s.value(): p.backend.set_setting(n, v), 'settings', n, s.value()))
        p.values[key] = slider; sliders.append(slider)
    p.eq_curve = EqualizerCurve(sliders); eq.addWidget(p.eq_curve, 1)
    bands = QHBoxLayout(); bands.setContentsMargins(22, 0, 0, 0); bands.setSpacing(0)
    for band, slider in zip(EQ_BANDS, sliders):
        column = QVBoxLayout(); column.setSpacing(2)
        value = label('0', 'readout'); value.setAlignment(Qt.AlignCenter)
        slider.valueChanged.connect(lambda v, target=value: target.setText(f'{v:+d}' if v else '0'))
        column.addWidget(value); column.addWidget(slider, 1, Qt.AlignHCenter)
        frequency = label(band.replace('Hz', ''), 'muted'); frequency.setAlignment(Qt.AlignCenter)
        column.addWidget(frequency); bands.addLayout(column, 1)
    eq.addLayout(bands, 1); tuning.addWidget(p.equalizer, 3)
    # Kept as labels for compatibility with the backend range refresh path.
    p.scale_high = QLabel(p.equalizer); p.scale_high.hide(); p.scale_low = QLabel(p.equalizer); p.scale_low.hide()
    output, volume = panel_layout(); output.setMinimumWidth(220); output.setMaximumWidth(300)
    volume.addWidget(label('Output', 'effectTitle')); volume.addWidget(label('扬声器', 'caption'))
    p.output_name = label('Internal speakers', 'effectTitle', True)
    p.output_name.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
    volume.addSpacing(8); volume.addWidget(p.output_name)
    volume.addWidget(label('This panel controls internal speakers only.', 'muted', True)); volume.addStretch()
    volume_head = QHBoxLayout(); volume_head.addWidget(label('Master volume')); volume_head.addStretch()
    p.volume_value = label('Not connected', 'readout'); volume_head.addWidget(p.volume_value); volume.addLayout(volume_head)
    p.volume = ControlSlider(Qt.Horizontal); p.volume.setRange(0, 100); p.volume.setMinimumHeight(28); p.volume.setAccessibleName('扬声器音量')
    p.volume.sliderReleased.connect(lambda: p.submit(lambda v=p.volume.value(): p.backend.volume(v), 'state', 'volume', p.volume.value()))
    p.volume.valueChanged.connect(lambda v: p.volume_value.setText(f'{v}%')); volume.addWidget(p.volume)
    mute_row = QHBoxLayout(); mute_row.addWidget(label('静音')); mute_row.addStretch()
    p.mute = Toggle('静音'); p.mute.clicked.connect(lambda checked: p.submit(lambda: p.backend.mute(checked), 'state', 'muted', checked)); mute_row.addWidget(p.mute)
    volume.addLayout(mute_row); tuning.addWidget(output, 1); controls.addLayout(tuning, 3)
    upper = QHBoxLayout(); upper.setSpacing(10)
    for title, key, description, on, off in (
        ('环绕声', 'kSet_SpkVirtualSurroundState', '让声音从四周传来，带来更有空间感的聆听体验。', 'SoundSurroundOn255x255.png', 'SoundSurroundOff255x255.png'),
        ('音量稳定器', 'kSet_CompressorState', '保持音量均衡，减少声音忽大忽小。', 'VolumeStabiliserOn80x60.png', 'VolumeStabilizerOff80x60.png')):
        frame, column = panel_layout(); row = QHBoxLayout(); row.addWidget(label(title, 'effectTitle'), 1)
        switch = p.effect_switch(key, '启用'+title); row.addWidget(switch); column.addLayout(row)
        row = QHBoxLayout(); art = EffectArt(switch, on, off); row.addWidget(art); row.addSpacing(10)
        row.addWidget(label(description, 'caption', True), 1); column.addLayout(row)
        p.effect_images[key] = art; upper.addWidget(frame, 1)
    controls.addLayout(upper, 1)
    lower = QHBoxLayout(); lower.setSpacing(10)
    for title, state, gain, description in (
        ('人声', 'kSet_VoiceBoostState', 'kSet_VoiceBoostGainDB', '调整对白与歌声的清晰度'),
        ('低音', 'kSet_BassBoostState', 'kSet_BassBoostGainDB', '调整低频声音的力度与厚度'),
        ('高音', 'kSet_TrebleBoostState', 'kSet_TrebleBoostGainDB', '调整声音细节与明亮度')):
        frame, column = panel_layout(); row = QHBoxLayout(); row.addWidget(label(title, 'effectTitle'), 1)
        row.addWidget(p.effect_switch(state, '启用'+title)); column.addLayout(row)
        row = QHBoxLayout(); value = label('0', 'value'); row.addWidget(value); row.addWidget(label('dB', 'muted')); row.addStretch(); column.addLayout(row)
        slider = ControlSlider(Qt.Horizontal); slider.setAccessibleName(title+'增益'); slider.setMinimumHeight(24)
        slider.valueChanged.connect(lambda v, target=value: target.setText(str(v)))
        slider.sliderReleased.connect(lambda n=gain, s=slider: p.submit(lambda v=s.value(): p.backend.set_setting(n, v), 'settings', n, s.value()))
        p.values[gain] = slider; column.addWidget(slider); column.addWidget(label(description, 'caption', True)); lower.addWidget(frame, 1)
    controls.addLayout(lower, 1)
    # A short desktop scrolls the effects instead of compressing band labels.
    p.controls.setMinimumHeight(730)
    scroll = QScrollArea(); scroll.setObjectName('audioScroll'); scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(p.controls); page.addWidget(scroll, 1)
    footer = QFrame(); footer.setObjectName('footer'); foot = QHBoxLayout(footer); foot.setContentsMargins(0, 0, 0, 0)
    p.status = label('正在连接音效服务…', 'status', True); foot.addWidget(p.status, 1); page.addWidget(footer)


def build_preferences(p):
    p.preferences = QDialog(p); p.preferences.setWindowTitle('设置'); p.preferences.setMinimumWidth(510)
    outer = QVBoxLayout(p.preferences); outer.setContentsMargins(1, 1, 1, 1); outer.setSpacing(0)
    body = QWidget(); outer.addWidget(body); layout = QVBoxLayout(body); layout.setContentsMargins(24, 18, 24, 24); layout.setSpacing(16)
    layout.addWidget(label('Appearance', 'effectTitle'))
    row = QHBoxLayout(); theme_label = label('Color Theme'); row.addWidget(theme_label)
    p.theme_combo = QComboBox(); p.theme_combo.setAccessibleName('Color Theme'); theme_label.setBuddy(p.theme_combo)
    for key, tokens in PALETTES.items(): p.theme_combo.addItem(tokens['name'], key)
    p.theme_combo.setCurrentIndex(p.theme_combo.findData(p.theme_preference.choice))
    p.theme_combo.activated.connect(p.change_theme); row.addWidget(p.theme_combo, 1); layout.addLayout(row)
    row = QHBoxLayout(); language_label = label('语言'); row.addWidget(language_label)
    p.language = QComboBox(); p.language.setAccessibleName('语言'); language_label.setBuddy(p.language)
    p.language.addItem(p.translations.text('跟随系统'), 'system')
    for code, name in LANGUAGES.items(): p.language.addItem(name, code)
    p.language.setCurrentIndex(p.language.findData(p.translations.choice))
    p.language.activated.connect(p.change_language); row.addWidget(p.language, 1); layout.addLayout(row)
    p.auto = QCheckBox('登录后自动运行音效')
    p.auto.clicked.connect(lambda checked: p.submit(lambda: p.backend.autostart(checked), 'state', 'autostart', checked)); layout.addWidget(p.auto)
    layout.addWidget(label('关闭窗口后，音效继续运行。模式和参数会自动保存。', 'muted', True))
    layout.addWidget(label('关于', 'effectTitle')); layout.addWidget(label("That's So Sound  0.3.0"))
    layout.addWidget(label("Audio tuning & equalizer for Linux.\nInspired by 'That's So True' by Gracie Abrams.", 'muted', True))
    done = QPushButton('完成'); done.clicked.connect(p.preferences.accept); layout.addWidget(done, 0, Qt.AlignRight)
    p.preferences_titlebar = decorate(p.preferences, outer)
