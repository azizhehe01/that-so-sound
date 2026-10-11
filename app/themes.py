"""Semantic palettes shared by Qt styles, native popups and custom painting.

Blush/plum follows the supplied Rosé direction; dark variants reduce surface
luminance, not text contrast. Pink is reserved for selection and audio values.
"""
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWidget

PALETTES = {
    'rose': dict(name='Rosé', root='#faeef2', nav='#f2dfe7', surface='#f5e0e9',
                 inset='#f0d6e2', hover='#ecd3df', border='#d9bccb',
                 text='#392335', secondary='#705064', muted='#705064',
                 accent='#ad2459', accent_hover='#8e1947', on_accent='#ffffff',
                 track='#d6b9c9', thumb='#fff8fb', focus='#8b1746',
                 success='#256a4a', error='#a7243f'),
    'midnight-rose': dict(name='Midnight Rose', root='#21151d', nav='#291923', surface='#30212b',
                 inset='#3d2a37', hover='#513345', border='#634457',
                 text='#ffedf5', secondary='#d9b8c9', muted='#cba7bd',
                 accent='#ff87b1', accent_hover='#ffb2cd', on_accent='#381324',
                 track='#795467', thumb='#ffedf5', focus='#ffb2cd',
                 success='#91d8af', error='#ffabba'),
    'dark': dict(name='Dark', root='#151517', nav='#19191d', surface='#202025',
                 inset='#2b2b32', hover='#36343e', border='#49454f',
                 text='#f6f1f5', secondary='#c6bdc8', muted='#b5aab9',
                 accent='#ff79aa', accent_hover='#ffacca', on_accent='#351322',
                 track='#625b6a', thumb='#fff7fb', focus='#ffacca',
                 success='#8ed6aa', error='#ffabba'),
    'light': dict(name='Light', root='#ffffff', nav='#ededf0', surface='#f5f5f7',
                 inset='#eeedf1', hover='#e5e2e8', border='#cdc7d0',
                 text='#28242c', secondary='#615867', muted='#675c6c',
                 accent='#ac245b', accent_hover='#861943', on_accent='#ffffff',
                 track='#c9c0cf', thumb='#ffffff', focus='#8b1746',
                 success='#246748', error='#a7243f'),
}


# Exact PIL pixel samples, left-to-right then top-to-bottom in the supplied image.
SOURCE_PALETTES = {
    'ocean-sand': ('#086288', '#4d8dba', '#97d7ff', '#ffefc4'),
    'citrus-grove': ('#d98327', '#ece8af', '#4a943e', '#186049'),
    'marigold-chili': ('#4f7d32', '#ffd16a', '#f5b52e', '#d9361e'),
    'blush-sage': ('#f6e2e9', '#fefaf3', '#b8cfb3', '#84a282'),
    'coral-mint': ('#de7272', '#ffca88', '#fff6a9', '#b4e4d6'),
    'amber-espresso': ('#fef3e2', '#f4ae52', '#d4621a', '#2a1a0e'),
    'lagoon-lemon': ('#287a74', '#55a9a0', '#aeeed3', '#fff8b0'),
    'aqua-papaya': ('#8ad6d1', '#359fa0', '#fff0c5', '#ff8c52'),
    'woodland-sage': ('#5c7057', '#89a482', '#acc5a6', '#d1edd3'),
    'honey-olive': ('#fcf0da', '#aeac78', '#f2c46a', '#4c4541'),
    'terracotta-peach': ('#a14646', '#da6556', '#eb895b', '#fdb773'),
    'orchid-petal': ('#8e1ea2', '#c654c3', '#ed96d7', '#ffc0de'),
}


def _mix(color, target, amount):
    channels = [round(int(color[i:i+2], 16) * (1 - amount) +
                      int(target[i:i+2], 16) * amount) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(channels)


def _luminance(color):
    rgb = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return sum(weight * (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4)
               for weight, v in zip((.2126, .7152, .0722), rgb))


def _contrast(first, second):
    low, high = sorted((_luminance(first), _luminance(second)))
    return (high + .05) / (low + .05)


def _readable(color, backgrounds, minimum=4.6):
    """Retain source hue, moving only as far as needed for the actual surfaces."""
    target = max(('#000000', '#ffffff'),
                 key=lambda value: min(_contrast(value, bg) for bg in backgrounds))
    for step in range(101):
        candidate = _mix(color, target, step / 100)
        if min(_contrast(candidate, bg) for bg in backgrounds) >= minimum:
            return candidate
    return target


def _source_theme(key, colors):
    # The supplied swatches ARE the large opaque fills, not a tint suggestion.
    # Light content and a contrasting sidebar keep hue while scoping readable ink.
    nav, inset, surface, root = sorted(colors, key=_luminance)
    selected = nav
    if key == 'marigold-chili':
        # Chili red needs its own light foreground, rather than black body text.
        selected = inset
        inset = _mix(root, '#ffffff', .24)
    hover = _mix(inset, '#ffffff', .12)
    bases = (root, surface, inset, hover)
    accent = _readable(nav, bases)
    text = _readable(_mix(nav, '#000000', .75), bases)
    secondary = _readable(_mix(nav, '#000000', .35), bases)
    nav_hover = _mix(nav, '#000000', .12)
    nav_bases = (nav, nav_hover)
    nav_text = _readable(root, nav_bases)
    nav_secondary = _readable(surface, nav_bases)
    return dict(
        name=key.replace('-', ' ').title(), root=root, nav=nav, surface=surface,
        inset=inset, hover=hover, border=_mix(nav, surface, .35),
        text=text, secondary=secondary, muted=_readable(nav, bases),
        accent=accent, accent_hover=_mix(accent, '#000000', .16),
        on_accent=_readable(root, (accent,)), track=_mix(nav, inset, .22),
        thumb=root, focus=accent, success=_readable('#256a4a', bases),
        error=_readable('#a7243f', bases), selected=selected,
        on_selected=_readable(root, (selected,)), nav_text=nav_text,
        nav_secondary=nav_secondary, nav_muted=nav_secondary,
        nav_accent=_readable(surface, nav_bases), nav_hover=nav_hover,
        nav_focus=nav_text, nav_selected=surface,
        on_nav_selected=_readable(nav, (surface,)),
    )


PALETTES.update({key: _source_theme(key, colors)
                 for key, colors in SOURCE_PALETTES.items()})


class ThemePreference:
    def __init__(self, path):
        self.settings = QSettings(str(path), QSettings.IniFormat)
        saved = self.settings.value('theme', 'rose')
        self.choice = saved if saved in PALETTES else 'rose'

    def select(self, choice):
        if choice not in PALETTES:
            raise ValueError('Unknown color theme: ' + str(choice))
        old = self.choice
        self.settings.setValue('theme', choice)
        self.settings.sync()
        if self.settings.status() != QSettings.NoError:
            self.settings.setValue('theme', old)
            raise OSError('Could not save color theme')
        self.choice = choice


def tokens_for(widget):
    navigation = False
    while widget is not None:
        navigation |= widget.objectName() in ('navigation', 'titleBar')
        if hasattr(widget, 'theme_tokens'):
            tokens = widget.theme_tokens
            if navigation and 'nav_text' in tokens:
                return dict(tokens, text=tokens['nav_text'], secondary=tokens['nav_secondary'],
                            muted=tokens['nav_muted'], accent=tokens['nav_accent'],
                            focus=tokens['nav_focus'], on_selected=tokens['on_nav_selected'])
            return tokens
        widget = widget.parentWidget()
    return PALETTES['rose']


def stylesheet(t):
    # Native sans-serif is deliberately retained for readable multilingual labels.
    return f"""
    QWidget {{ color: {t['text']}; font-family: 'Noto Sans'; font-size: 12px; }}
    QMainWindow, QWidget#root, QDialog {{ background: {t['root']}; }}
    QFrame#navigation, QWidget#titleBar {{ background: {t['nav']}; }}
    QFrame#navigation {{ border-right: 1px solid {t['border']}; }}
    QFrame#effect, QFrame#profileBar {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 7px; }}
    QLabel {{ background: transparent; }}
    QLabel#heading {{ font-size: 26px; font-weight: 700; }}
    QLabel#effectTitle {{ font-size: 14px; font-weight: 600; }}
    QLabel#caption, QLabel#windowTitle {{ color: {t['secondary']}; }}
    QLabel#muted {{ color: {t['muted']}; font-size: 11px; }}
    QLabel#brand {{ color: {t['accent']}; font-size: 13px; font-weight: 700; }}
    QLabel#value {{ color: {t['accent']}; font-size: 25px; font-weight: 600; }}
    QLabel#readout {{ font-size: 11px; font-weight: 600; }}
    QLabel#status {{ color: {t['secondary']}; padding: 8px 0; }}
    QLabel#status[state="error"] {{ color: {t['error']}; }}
    QLabel#status[state="active"] {{ color: {t['success']}; }}
    QFrame#footer {{ border-top: 1px solid {t['border']}; }}
    QPushButton, QToolButton {{ background: {t['inset']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 5px; padding: 7px 12px; }}
    QPushButton:hover, QToolButton:hover {{ background: {t['hover']}; border-color: {t['accent']}; }}
    QPushButton:pressed, QToolButton:pressed {{ background: {t['hover']}; }}
    QToolButton:checked {{ background: {t['hover']}; color: {t['accent']}; }}
    QToolButton#navigationButton, QToolButton#profileButton {{ background: transparent; border: 1px solid transparent; }}
    QToolButton#navigationButton:checked, QToolButton#profileButton:checked {{ background: {t['inset']}; color: {t['accent']}; }}
    QToolButton#navigationButton:hover, QToolButton#profileButton:hover {{ background: {t['hover']}; }}
    QPushButton:focus, QToolButton:focus, QComboBox:focus, QCheckBox:focus {{ border: 2px solid {t['focus']}; }}
    QPushButton:disabled, QToolButton:disabled, QComboBox:disabled {{ color: {t['muted']}; background: {t['inset']}; border-color: {t['border']}; }}
    QToolButton#windowButton, QToolButton#closeWindow {{ border: 1px solid transparent; border-radius: 3px; padding: 0; background: transparent; }}
    QToolButton#windowButton:hover {{ background: {t['hover']}; }}
    QToolButton#closeWindow:hover {{ background: {t['error']}; color: {t['root']}; }}
    QToolButton#windowButton:focus, QToolButton#closeWindow:focus {{ border: 2px solid {t['focus']}; }}
    QComboBox {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 5px; padding: 8px 12px; min-width: 180px; }}
    QComboBox:hover {{ border-color: {t['accent']}; }}
    QComboBox QAbstractItemView {{ background: {t['surface']}; color: {t['text']}; selection-background-color: {t['accent']}; selection-color: {t['on_accent']}; border: 1px solid {t['border']}; padding: 4px; }}
    QToolTip {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border']}; padding: 6px; }}
    QScrollArea#audioScroll, QScrollArea#audioScroll > QWidget > QWidget {{ background: {t['root']}; border: none; }}
    QScrollBar:vertical {{ background: {t['root']}; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {t['track']}; min-height: 32px; border-radius: 4px; }}
    QScrollBar::handle:vertical:hover {{ background: {t['accent']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {t['root']}; }}
    QSlider {{ background: transparent; }}
    QSlider::groove:horizontal {{ height: 5px; background: {t['track']}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {t['accent']}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ width: 12px; margin: -4px 0; background: {t['thumb']}; border: 2px solid {t['accent']}; border-radius: 7px; }}
    QSlider::groove:vertical {{ width: 4px; background: {t['track']}; border-radius: 2px; }}
    QSlider::add-page:vertical {{ background: {t['accent']}; border-radius: 2px; }}
    QSlider::handle:vertical {{ height: 10px; margin: 0 -4px; background: {t['thumb']}; border: 2px solid {t['accent']}; border-radius: 6px; }}
    QSlider::handle:hover {{ background: {t['accent_hover']}; }}
    QSlider:focus {{ border: 1px solid {t['focus']}; border-radius: 4px; }}
    QSlider::handle:disabled {{ background: {t['inset']}; border-color: {t['muted']}; }}
    QSlider::sub-page:horizontal:disabled, QSlider::add-page:vertical:disabled {{ background: {t['muted']}; }}
    QCheckBox {{ spacing: 10px; border: 2px solid transparent; border-radius: 4px; padding: 4px; }}
    QCheckBox:disabled {{ color: {t['muted']}; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {t['track']}; background: {t['surface']}; border-radius: 3px; }}
    QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; }}
    """ + _surface_styles(t)


def _surface_styles(t):
    # Scoped ink lets source-colored dark chrome coexist with light content.
    # No extension is applied to the original four themes.
    if 'nav_text' not in t:
        return ''
    return f"""
    QFrame#navigation QLabel, QWidget#titleBar QLabel {{ color: {t['nav_text']}; }}
    QFrame#navigation QLabel#muted, QWidget#titleBar QLabel#windowTitle {{ color: {t['nav_secondary']}; }}
    QFrame#navigation QLabel#brand {{ color: {t['nav_accent']}; }}
    QToolButton#navigationButton {{ color: {t['nav_secondary']}; }}
    QToolButton#navigationButton:hover {{ background: {t['nav_hover']}; }}
    QToolButton#navigationButton:checked, QToolButton#navigationButton:checked:hover {{ background: {t['nav_selected']}; color: {t['on_nav_selected']}; }}
    QToolButton#navigationButton:focus {{ border-color: {t['nav_focus']}; }}
    QToolButton#profileButton:checked, QToolButton#profileButton:checked:hover {{ background: {t['selected']}; color: {t['on_selected']}; }}
    QToolButton#profileButton:disabled {{ background: {t['inset']}; color: {t['muted']}; }}
    QToolButton#windowButton, QToolButton#closeWindow {{ color: {t['nav_text']}; }}
    QToolButton#windowButton:hover {{ background: {t['nav_hover']}; }}
    QToolButton#windowButton:focus, QToolButton#closeWindow:focus {{ border-color: {t['nav_focus']}; }}
    QToolButton#closeWindow:hover {{ background: {t['error']}; color: {t['root']}; }}
    QComboBox QAbstractItemView {{ selection-background-color: {t['selected']}; selection-color: {t['on_selected']}; }}
    QCheckBox::indicator:disabled {{ background: {t['inset']}; border-color: {t['muted']}; }}
    """


def apply_theme(window, choice):
    t = PALETTES[choice]
    window.theme_tokens = t
    palette = QPalette()
    roles = {'Window': 'root', 'WindowText': 'text', 'Base': 'surface',
             'AlternateBase': 'inset', 'Text': 'text', 'Button': 'inset',
             'ButtonText': 'text', 'BrightText': 'on_accent', 'Highlight': 'accent',
             'HighlightedText': 'on_accent', 'ToolTipBase': 'surface',
             'ToolTipText': 'text', 'PlaceholderText': 'muted', 'Link': 'accent',
             'Light': 'surface', 'Midlight': 'inset', 'Mid': 'border',
             'Dark': 'track', 'Shadow': 'border'}
    if 'selected' in t:
        roles.update(Highlight='selected', HighlightedText='on_selected')
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        for role, token in roles.items():
            if group == QPalette.Disabled and token == 'text': token = 'muted'
            palette.setColor(group, getattr(QPalette, role), QColor(t[token]))
    window.setPalette(palette)
    window.setStyleSheet(stylesheet(t))
    for widget in window.findChildren(QWidget):
        scoped = tokens_for(widget)
        if scoped is not t and 'nav_text' in t:
            chrome_palette = QPalette(palette)
            for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
                for role in (QPalette.WindowText, QPalette.ButtonText, QPalette.Text):
                    chrome_palette.setColor(group, role, QColor(scoped['text']))
            widget.setPalette(chrome_palette)
        else:
            widget.setPalette(palette)
        widget.update()
    window.update()
