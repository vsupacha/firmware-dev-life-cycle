import ctypes
import errno
import json
import os
import threading
import time
from pathlib import Path

import pytest

from reqstudio import worker


def test_atomic_status_recovers_from_transient_replace_denial(tmp_path, monkeypatch):
    target = tmp_path / 'status.json'
    worker.atomic_json(target, {'sequence': 1})
    original = Path.replace
    attempts = []
    def replace(path, destination):
        attempts.append(1)
        if len(attempts) < 3:
            raise PermissionError(errno.EACCES, 'temporary file sharing lock')
        return original(path, destination)
    monkeypatch.setattr(Path, 'replace', replace)
    monkeypatch.setattr(worker.time, 'sleep', lambda _: None)
    worker.atomic_json(target, {'sequence': 2})
    assert worker.read_json(target) == {'sequence': 2}
    assert len(attempts) == 3
    assert not list(tmp_path.glob('*.tmp'))


def test_permanent_denial_is_bounded_and_preserves_last_good_status(tmp_path, monkeypatch):
    target = tmp_path / 'status.json'
    worker.atomic_json(target, {'sequence': 1})
    attempts = []
    def deny(*args):
        attempts.append(1)
        raise PermissionError(errno.EACCES, 'denied')
    monkeypatch.setattr(Path, 'replace', deny)
    monkeypatch.setattr(worker.time, 'sleep', lambda _: None)
    with pytest.raises(PermissionError):
        worker.atomic_json(target, {'sequence': 2})
    assert len(attempts) == 8
    assert worker.read_json(target) == {'sequence': 1}
    assert not list(tmp_path.glob('*.tmp'))


def test_heartbeat_lock_is_nonfatal_and_recovers(tmp_path, monkeypatch):
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    original = worker.atomic_json
    def locked(*args):
        raise PermissionError(errno.EACCES, 'sharing lock')
    monkeypatch.setattr(worker, 'atomic_json', locked)
    state = {'pid': os.getpid()}
    assert worker.publish_status(state, 'running') is False
    assert 'status_write_error' in state
    monkeypatch.setattr(worker, 'atomic_json', original)
    assert worker.publish_status(state, 'idle') is True
    assert state['state'] == 'idle' and 'status_write_error' not in state


def test_concurrent_shared_readers_observe_whole_json(tmp_path):
    target = tmp_path / 'status.json'
    worker.atomic_json(target, {'sequence': 0})
    stop = threading.Event()
    errors = []
    def reader():
        while not stop.is_set():
            try:
                value = json.loads(worker.shared_read_text(target))
                assert isinstance(value['sequence'], int)
            except Exception as exc:
                errors.append(exc)
    threads = [threading.Thread(target=reader) for _ in range(2)]
    for thread in threads: thread.start()
    try:
        for index in range(40): worker.atomic_json(target, {'sequence': index})
    finally:
        stop.set()
        for thread in threads: thread.join(timeout=5)
    assert not errors
    assert worker.read_json(target)['sequence'] == 39


@pytest.mark.skipif(os.name != 'nt', reason='Windows file sharing regression')
def test_actual_windows_delete_sharing_lock_is_retried(tmp_path):
    from ctypes import wintypes
    target = tmp_path / 'status.json'
    worker.atomic_json(target, {'sequence': 1})
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = create(str(target), 0x80000000, 0x1 | 0x2, None, 3, 0x80, None)
    assert handle != ctypes.c_void_p(-1).value
    probe = tmp_path / 'probe.tmp'
    probe.write_text('{}', encoding='utf8')
    with pytest.raises(PermissionError):
        probe.replace(target)  # proves the original failure without touching user files
    errors = []
    def writer():
        try: worker.atomic_json(target, {'sequence': 2})
        except Exception as exc: errors.append(exc)
    thread = threading.Thread(target=writer)
    thread.start()
    time.sleep(.1)
    kernel.CloseHandle(handle)
    thread.join(timeout=5)
    assert not thread.is_alive() and not errors
    assert worker.read_json(target) == {'sequence': 2}
