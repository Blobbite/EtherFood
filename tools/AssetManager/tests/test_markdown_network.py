"""M11/M12: actual local HTTP transfers, approvals, redirects, cancellation and limits."""

import threading
import time
import ssl
import subprocess
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from etherfood_studio.domain.models import StudioError
from etherfood_studio.ui.documents.media_source import MediaLimits, Transfer, download, origin


@pytest.fixture
def server():
    hits = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            hits.append((self.path, dict(self.headers)))
            if self.path == '/trickle-headers':
                try:
                    for part in (b'HTTP/1.1 200 OK\r\n', b'X-Slow: ' + b'x' * 80, b'\r\n\r\n'):
                        for byte in part:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            time.sleep(0.01)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            if self.path in {'/redirect', '/loop', '/foreign', '/protocol'}:
                self.send_response(302)
                target = {'/redirect': '/ok', '/loop': '/loop', '/foreign':
                          f'http://localhost:{self.server.server_port}/ok',
                              '/protocol': 'file:///etc/passwd'}[self.path]
                self.send_header('Location', target)
                self.end_headers()
                return
            self.send_response(200)
            if self.path == '/length':
                self.send_header('Content-Length', '999999999')
            self.end_headers()
            if self.path == '/slow':
                time.sleep(0.3)
            try:
                self.wfile.write(b'x' * (200 if self.path == '/large' else 20))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{httpd.server_port}', hits
    httpd.shutdown()
    httpd.server_close()
    thread.join(2)


def fetch(base, path, **kwargs):
    return download(base + path, limits=kwargs.pop('limits', MediaLimits()),
                    transfer=kwargs.pop('transfer', Transfer()),
                    permitted_origins={origin(base)}, private_origins={origin(base)}, **kwargs)


def test_m11_no_private_request_without_its_own_permission(server):
    base, hits = server
    with pytest.raises(StudioError, match='Lokaler Medienserver'):
        download(base + '/ok', limits=MediaLimits(), transfer=Transfer(),
            permitted_origins={origin(base)})
    assert hits == []


def test_m12_transfer_and_same_origin_redirect_send_no_credentials(server):
    base, hits = server
    assert fetch(base, '/redirect') == b'x' * 20
    assert [path for path, _ in hits] == ['/redirect', '/ok']
    for _, headers in hits:
        assert not {'Cookie', 'Authorization', 'Referer'} & headers.keys()


@pytest.mark.parametrize('path,limits', [
    ('/length', MediaLimits()), ('/large', replace(MediaLimits(), transferred=100)),
    ('/loop', replace(MediaLimits(), redirects=2)), ('/foreign', MediaLimits()),
    ('/protocol', MediaLimits()), ('/slow', replace(MediaLimits(), inactivity=0.05)),
    ('/slow', replace(MediaLimits(), total=0.05)),
])
def test_m12_actual_limits_and_unapproved_redirect_targets(server, path, limits):
    base, hits = server
    with pytest.raises((StudioError, OSError)):
        fetch(base, path, limits=limits)
    if path == '/foreign':
        assert [p for p, _ in hits] == ['/foreign']


def test_m12_cancel_running_transfer(server):
    base, hits = server
    transfer, errors = Transfer(), []
    def run():
        try:
            fetch(base, '/slow', transfer=transfer)
        except (StudioError, OSError) as error:
            errors.append(error)
    thread = threading.Thread(target=run)
    thread.start()
    deadline = time.monotonic() + 1
    while not hits and time.monotonic() < deadline:
        time.sleep(0.005)
    transfer.cancel()
    thread.join(1)
    assert errors and not thread.is_alive()


@pytest.mark.parametrize('url', ['http://user:secret@example.org/x', 'ftp://example.org/x',
                                  'file:///x', 'http://example.org:wrong/x'])
def test_m12_reject_credentials_and_protocols(url):
    with pytest.raises(StudioError):
        origin(url)


def test_m12_tls_verification_rejects_an_actual_untrusted_local_certificate(tmp_path):
    import shutil
    if shutil.which('openssl') is None:
        pytest.skip('OpenSSL CLI fehlt für das synthetische TLS-Testzertifikat.')
    certificate, key = tmp_path / 'certificate.pem', tmp_path / 'key.pem'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                    '-subj', '/CN=localhost', '-keyout', str(key), '-out', str(certificate)],
                   check=True, capture_output=True)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'https://127.0.0.1:{server.server_port}'
    try:
        with pytest.raises(ssl.SSLCertVerificationError):
            fetch(base, '/image')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_m12_dns_wait_is_included_in_total_deadline(monkeypatch):
    import socket
    original = socket.getaddrinfo
    def slow(*args, **kwargs):
        time.sleep(0.2)
        return original('127.0.0.1', 9, type=socket.SOCK_STREAM)
    monkeypatch.setattr(socket, 'getaddrinfo', slow)
    started = time.monotonic()
    with pytest.raises(StudioError, match='Gesamtdauer'):
        download('https://example.org/x', limits=replace(MediaLimits(), total=0.05),
                 transfer=Transfer(), permitted_origins={origin('https://example.org')})
    assert time.monotonic() - started < 0.18


def test_m12_total_deadline_interrupts_headers_even_when_server_keeps_sending(server):
    base, _ = server
    started = time.monotonic()
    with pytest.raises(StudioError, match='Gesamtdauer'):
        fetch(base, '/trickle-headers', limits=replace(MediaLimits(), inactivity=0.3, total=0.15))
    assert time.monotonic() - started < 0.7
