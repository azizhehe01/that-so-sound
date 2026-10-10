"""Native desktop controls for Nahimic speaker effects."""
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import os
from pathlib import Path
import subprocess
import sys
import time

from PySide6.QtCore import QTimer, QLockFile
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from backend import Backend, DATA, SERVICE
from i18n import Translations
from themes import ThemePreference, apply_theme
from audio_ui import Toggle, build_panel, build_preferences


class Panel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.backend = Backend()
        self.translations = Translations(DATA / 'interface.ini')
        self.theme_preference = ThemePreference(DATA / 'interface.ini')
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending = None
        self.jobs = deque()
        self.awaiting_state = {}
        self.error_message = None
        self.last_status = None
        self.busy_timer = QTimer(self); self.busy_timer.setSingleShot(True)
        self.busy_timer.timeout.connect(self.show_pending_status)
        self.settings_loaded = False
        self.loaded_pid = None
        self.values = {}; self.switches = {}; self.modes = {}; self.effect_images = {}
        self.setWindowTitle("That's So Sound")
        icon = QIcon.fromTheme(SERVICE.removesuffix('.service'), QIcon(str(Path(__file__).with_name('nahimic.svg'))))
        self.setWindowIcon(icon)
        build_panel(self)
        build_preferences(self)
        self.translations.capture(self)
        apply_theme(self, self.theme_preference.choice)
        self.controls.setEnabled(False); self.equalizer.setEnabled(False); self.auto.setEnabled(False)
        self.timer = QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(100)
        self.status_timer = QTimer(self); self.status_timer.timeout.connect(self.refresh); self.status_timer.start(2000)
        self.refresh()

    def change_theme(self, index):
        choice = self.theme_combo.itemData(index)
        try:
            self.theme_preference.select(choice)
        except (OSError, ValueError) as error:
            self.theme_combo.setCurrentIndex(self.theme_combo.findData(self.theme_preference.choice))
            QMessageBox.warning(self, self.translations.text('设置'), str(error))
            return
        apply_theme(self, choice)

    def change_language(self, index):
        try:
            self.translations.select(self.language.itemData(index))
        except OSError as error:
            self.language.setCurrentIndex(self.language.findData(self.translations.choice))
            QMessageBox.warning(self, self.translations.text('设置'), str(error))
            return
        self.language.setItemText(0, self.translations.text('跟随系统'))
        self.preferences.adjustSize()

    def effect_switch(self, name, label):
        switch = Toggle(label)
        switch.clicked.connect(lambda checked: self.submit(lambda: self.backend.set_setting(name, int(checked)), 'settings', name, int(checked)))
        switch.toggled.connect(self.update_effect_images)
        self.switches[name] = switch
        return switch

    def show_equalizer(self):
        self.values['kSet_EQ31HzGainDB'].setFocus()

    def show_preferences(self):
        self.preferences.show()
        self.preferences.raise_()
        self.preferences.activateWindow()

    def pending_keys(self):
        keys = {job[2] for job in self.jobs if job[2] is not None}
        if self.pending and self.pending[2] is not None:
            keys.add(self.pending[2])
        return keys | self.awaiting_state.keys()

    def show_pending_status(self):
        if self.pending_keys() and not self.error_message:
            self.translations.bind(self.status, 'text', '正在应用…')

    def submit(self, function, kind, key=None, value=None):
        if key is not None:
            self.error_message = None
            if kind == 'state':
                self.awaiting_state[key] = (value, None)
            if not self.busy_timer.isActive():
                self.busy_timer.start(400)
        job = (function, kind, key, value)
        if self.pending:
            if kind != 'status':
                # Only coalesce adjacent edits; a profile change remains an ordering barrier.
                if key is not None and self.jobs and self.jobs[-1][2] == key:
                    self.jobs[-1] = job
                else:
                    self.jobs.append(job)
            return
        self.pending = (self.pool.submit(function), kind, key, value)

    def refresh(self):
        if not self.pending:
            if self.jobs:
                function, kind, key, value = self.jobs.popleft()
                self.pending = (self.pool.submit(function), kind, key, value)
            else:
                self.submit(self.backend.status, 'status')

    def set_available(self, ready):
        available = ready and self.settings_loaded
        self.controls.setEnabled(available)
        self.equalizer.setEnabled(available)
        self.auto.setEnabled(available)

    def show_status(self):
        state = 'idle'
        if self.error_message:
            state = 'error'
            self.translations.bind(self.status, 'text', '操作未完成：{error}', error=self.error_message)
        elif self.pending_keys():
            if not self.busy_timer.isActive(): self.show_pending_status()
        elif self.last_status:
            result = self.last_status
            if result['ready']:
                state = 'active' if result['active'] else 'idle'
                self.translations.bind(self.status, 'text', '音效正在运行' if result['active'] else
                    '正在播放原声' if not result['enabled'] else '音效已开启，等待扬声器播放')
            elif result.get('waiting_for_speakers'):
                self.translations.bind(self.status, 'text', '等待内置扬声器，其他输出正常使用')
            else:
                self.translations.bind(self.status, 'text', '正在准备音效，请稍候…' if
                    result['service'] in ('active', 'activating') else '音效服务未运行，请关闭并重新打开软件。')
        if self.status.property('state') != state:
            self.status.setProperty('state', state)
            self.status.style().unpolish(self.status); self.status.style().polish(self.status)

    def apply_status(self, result):
        self.last_status = result
        ready = result['ready']
        if not ready or result['instance'] != self.loaded_pid:
            if ready: self.loaded_pid = result['instance']
            self.settings_loaded = False
        self.set_available(ready)
        queued = {job[2] for job in self.jobs}
        for key, (wanted, deadline) in list(self.awaiting_state.items()):
            if key in queued or deadline is None:
                continue
            if key in result and result[key] == wanted:
                del self.awaiting_state[key]
            elif time.monotonic() >= deadline:
                del self.awaiting_state[key]
                self.error_message = self.translations.text('设置未获系统确认，已重新读取当前状态。')
        protected = self.pending_keys()
        if 'autostart' not in protected: self.auto.setChecked(result['autostart'])
        if ready:
            self.output_name.setText(str(result.get('output') or 'Internal speakers'))
            if 'enabled' not in protected:
                self.power.setChecked(result['enabled'])
                self.translations.bind(self.power_label, 'text', '音效已开启' if result['enabled'] else '音效已关闭')
            if 'volume' not in protected and not self.volume.isSliderDown():
                self.volume.setValue(result['volume'])
                self.volume_value.setText(f"{result['volume']}%")
            if 'muted' not in protected: self.mute.setChecked(result['muted'])
            if not self.settings_loaded:
                self.jobs.appendleft((self.backend.settings, 'settings', None, None))
        else:
            self.translations.bind(self.power_label, 'text', '等待连接')
        self.show_status()

    def poll(self):
        if not self.pending or not self.pending[0].done(): return
        future, kind, key, value = self.pending
        self.pending = None
        try:
            result = future.result()
            if kind == 'settings':
                self.apply_settings(result)
                self.set_available(bool(self.last_status and self.last_status['ready']))
            elif kind == 'state':
                # Desktop state is published asynchronously by the audio service.
                if key not in {job[2] for job in self.jobs}:
                    self.awaiting_state[key] = (value, time.monotonic() + 5)
            else:
                self.apply_status(result)
        except Exception as error:
            self.error_message = str(error)
            if kind == 'settings':
                if key == 'profile':
                    # Do not apply edits to a different profile after a failed switch.
                    self.jobs = deque(job for job in self.jobs if job[1] != 'settings')
                if key is not None:
                    self.jobs.appendleft((self.backend.settings, 'settings', None, None))
                else:
                    self.settings_loaded = False
                    self.set_available(False)
            elif kind == 'state' and key not in {job[2] for job in self.jobs}:
                self.awaiting_state.pop(key, None)
            elif kind == 'status':
                self.set_available(False)
            self.show_status()
        if not self.pending_keys(): self.busy_timer.stop()
        self.show_status()
        if self.jobs or kind != 'status': self.refresh()

    def update_effect_images(self):
        for image in self.effect_images.values(): image.update()

    def apply_settings(self, state):
        if state['profile'] not in self.modes:
            raise ValueError(self.translations.text('未知音效预设：{profile}', profile=state['profile']))
        protected = self.pending_keys()
        if 'profile' in protected:
            return
        for name, button in self.modes.items():
            button.setChecked(name == state['profile'])
        for name, slider in self.values.items():
            if name in protected or slider.isSliderDown(): continue
            item = state['settings'][name]; slider.setRange(round(item['min']), round(item['max'])); slider.setValue(round(item['value']))
        for name, switch in self.switches.items():
            if name not in protected: switch.setChecked(bool(state['settings'][name]['value']))
        self.scale_high.setText(f"+{round(state['settings']['kSet_EQ31HzGainDB']['max'])}")
        self.scale_low.setText(str(round(state['settings']['kSet_EQ31HzGainDB']['min'])))
        self.update_effect_images()
        self.settings_loaded = True


def main():
    app = QApplication(sys.argv)
    desktop_name = os.environ.get('NAHIMIC_DESKTOP_NAME', SERVICE.removesuffix('.service'))
    app.setDesktopFileName(desktop_name)
    app.setApplicationName("That's So Sound")
    app.setStyle('Fusion')
    runtime = Path(os.environ['XDG_RUNTIME_DIR']); lock = QLockFile(str(runtime/'nahimic-panel.lock'))
    socket_name = str(runtime/'nahimic-panel.socket')
    if not lock.tryLock(0):
        socket = QLocalSocket(); socket.connectToServer(socket_name)
        if not socket.waitForConnected(1000): raise RuntimeError("音效窗口已运行，但无法联系窗口")
        socket.write(b'show'); socket.waitForBytesWritten(1000)
        return
    QLocalServer.removeServer(socket_name); server = QLocalServer()
    if not server.listen(socket_name): raise RuntimeError(server.errorString())
    subprocess.run(['systemctl', '--user', 'start', SERVICE], check=True, timeout=15)
    panel = Panel()
    def activate():
        connection = server.nextPendingConnection(); connection.close(); connection.deleteLater()
        if panel.settings_loaded:
            panel.submit(panel.backend.settings, 'settings')
        panel.showNormal(); panel.raise_(); panel.activateWindow()
    server.newConnection.connect(activate)
    panel.show(); app.exec(); panel.pool.shutdown(wait=True, cancel_futures=True)


if __name__ == '__main__': main()
