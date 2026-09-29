"""Restricted image inputs and cancellable, address-pinned HTTP downloads."""

import http.client
import ipaddress
import socket
import ssl
import threading
import time
import queue
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urljoin, urlsplit

from PIL import Image, UnidentifiedImageError

from ...domain.models import StudioError
from .svg_source import sanitize_svg

DNS_SLOTS = threading.BoundedSemaphore(4)


def resolve_host(host, port, transfer, remaining):
    """Bound DNS waiting too; at most four blocked resolver threads can outlive a request."""
    while not DNS_SLOTS.acquire(timeout=min(0.05, remaining())):
        remaining()
    result = queue.Queue(maxsize=1)

    def resolve():
        try:
            result.put(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except OSError as error:
            result.put(error)
        finally:
            DNS_SLOTS.release()
    threading.Thread(target=resolve, daemon=True, name="markdown-dns").start()
    while True:
        try:
            answer = result.get(timeout=min(0.05, remaining()))
            if isinstance(answer, OSError):
                raise answer
            return answer
        except queue.Empty:
            remaining()


@dataclass(frozen=True)
class MediaLimits:
    transferred: int = 16 * 1024 * 1024
    pixels: int = 32_000_000
    concurrent: int = 4
    redirects: int = 5
    inactivity: float = 15.0
    total: float = 60.0
    memory: int = 128 * 1024 * 1024


class Cancelled(StudioError):
    def __init__(self):
        super().__init__("cancelled", "Laden abgebrochen. Erneut versuchen möglich.")


class Transfer:
    def __init__(self):
        self.cancelled = threading.Event()
        self.connection = None
        self.socket = None

    def cancel(self):
        self.cancelled.set()
        connection = self.connection
        stream = self.socket or (connection.sock if connection else None)
        if stream:
            try:
                stream.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def origin(url):
    parts = urlsplit(url)
    try:
        port = parts.port if parts.port is not None else (443
            if parts.scheme.lower() == "https" else 80)
    except ValueError as error:
        raise StudioError("blocked", "Ungültiger Port in der Bildadresse.") from error
    if (parts.scheme.lower() not in {"http", "https"} or not parts.hostname or port < 1
            or parts.username is not None or parts.password is not None
            or any(ord(c) < 33 for c in url) or "\\" in url):
        raise StudioError("blocked", "Bildadresse benötigt HTTP/HTTPS ohne Zugangsdaten.")
    return parts.scheme.lower(), parts.hostname.lower().encode("idna").decode("ascii"), port


def download(url, *, limits, transfer, permitted_origins, private_origins=frozenset()):
    """No cookies, proxy environment, credentials, referrer or unverified TLS."""
    expired = threading.Event()

    def expire():
        expired.set()
        transfer.cancel()
    watchdog = threading.Timer(limits.total, expire)
    watchdog.daemon = True
    watchdog.start()
    try:
        result = _download(url, limits=limits, transfer=transfer,
                           permitted_origins=permitted_origins, private_origins=private_origins)
        if expired.is_set():
            raise StudioError("timeout", "Gesamtdauer des Bildabrufs überschritten.")
        return result
    except (OSError, StudioError, http.client.HTTPException) as error:
        if expired.is_set():
            raise StudioError("timeout", "Gesamtdauer des Bildabrufs überschritten.") from error
        raise
    finally:
        watchdog.cancel()


def _download(url, *, limits, transfer, permitted_origins, private_origins):
    deadline = time.monotonic() + limits.total

    def remaining():
        if transfer.cancelled.is_set():
            raise Cancelled()
        value = deadline - time.monotonic()
        if value <= 0:
            raise StudioError("timeout", "Gesamtdauer des Bildabrufs überschritten.")
        return min(limits.inactivity, value)

    for redirect in range(limits.redirects + 1):
        remaining()
        current = origin(url)
        if current not in permitted_origins:
            raise StudioError("permission",
                "Weiterleitungsziel benötigt eine eigene Freigabe: " + url)
        scheme, host, port = current
        addresses = resolve_host(host, port, transfer, remaining)
        remaining()
        if not addresses or (current not in private_origins and any(
                not ipaddress.ip_address(item[4][0]).is_global for item in addresses)):
            raise StudioError("permission",
                "Lokaler Medienserver benötigt eine begrenzte Freigabe: " + url)
        connection = http.client.HTTPConnection(host, port, timeout=remaining())
        transfer.connection = connection
        raw_socket = None
        try:
            last_error = None
            for family, socktype, protocol, _, address in addresses:
                remaining()
                raw_socket = socket.socket(family, socktype, protocol)
                raw_socket.settimeout(remaining())
                transfer.socket = raw_socket
                try:
                    raw_socket.connect(address)
                    break
                except OSError as error:
                    last_error = error
                    raw_socket.close()
            else:
                raise last_error or OSError("Kein erreichbares Bildziel.")
            connection.sock = raw_socket
            if scheme == "https":
                connection.sock = ssl.create_default_context().wrap_socket(raw_socket,
                    server_hostname=host, do_handshake_on_connect=False)
            transfer.socket = connection.sock
            if scheme == "https":
                connection.sock.do_handshake()
            connection.sock.settimeout(remaining())
            parts = urlsplit(url)
            target = (parts.path or "/") + ("?" + parts.query if parts.query else "")
            connection.request("GET", target, headers={"Accept": "image/*", "Connection": "close"})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                if redirect == limits.redirects:
                    raise StudioError("blocked", "Zu viele Bildweiterleitungen.")
                location = response.getheader("Location")
                if not location:
                    raise StudioError("unavailable", "Weiterleitung ohne Ziel.")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise StudioError("unavailable", f"Bildserver meldet HTTP {response.status}.")
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise StudioError("blocked", "Komprimierte HTTP-Übertragung nicht unterstützt.")
            length = response.getheader("Content-Length")
            if length and (not length.isdigit() or int(length) > limits.transferred):
                raise StudioError("blocked", "Bild überschreitet die Übertragungsgrenze.")
            data = bytearray()
            while True:
                transfer.socket.settimeout(remaining())
                chunk = response.read1(min(65536, limits.transferred + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > limits.transferred:
                    raise StudioError("blocked", "Bild überschreitet die Übertragungsgrenze.")
            if length and len(data) != int(length):
                raise StudioError("unavailable", "Bildübertragung ist unvollständig.")
            remaining()
            return bytes(data)
        except (socket.timeout, TimeoutError) as error:
            raise StudioError("timeout", "Bildabruf hat das Zeitlimit überschritten.") from error
        finally:
            connection.close()
            if raw_socket:
                raw_socket.close()
            transfer.connection = None
            transfer.socket = None
    raise StudioError("blocked", "Weiterleitungsgrenze überschritten.")


def inspect_image(raw, limits):
    if len(raw) > limits.transferred:
        raise StudioError("blocked", "Bild überschreitet die Dateigröße.")
    stripped = raw.lstrip(b"\xef\xbb\xbf \t\r\n")
    if stripped.startswith((b"<svg", b"<?xml", b"<!--")):
        return {"format": "SVG", "data": sanitize_svg(raw, max_bytes=limits.transferred)}
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP", "GIF"}:
                raise StudioError("unsupported", "Bildformat nicht unterstützt.")
            if image.width * image.height > limits.pixels:
                raise StudioError("blocked", "Bild überschreitet die Pixelgrenze.")
            frames = gif_frames(raw, limits) if image.format == "GIF" else 1
            animated = frames > 1
            if image.format != "GIF" and getattr(image, "is_animated", False):
                raise StudioError("unsupported", "Nur GIF-Animationen werden unterstützt.")
            # Reserve decoder/compositing storage too, never cache all GIF frames.
            size, image_format = image.size, image.format
            memory = size[0] * size[1] * 4 * (6 if animated else 2) + len(raw)
            if memory > limits.memory:
                raise StudioError("blocked", "Bild überschreitet den verfügbaren Bildspeicher.")
            image.verify()
            return {"format": image_format, "data": raw, "size": size,
                    "animated": animated, "frames": frames, "memory": memory}
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise StudioError("unsupported", "Datei enthält kein sicher lesbares Bild.") from error


def gif_frames(raw, limits):
    """Check all frame rectangles/sub-blocks before a decoder can allocate a grown canvas."""
    import struct
    if len(raw) < 13 or raw[:6] not in {b"GIF87a", b"GIF89a"}:
        raise StudioError("unsupported", "GIF-Kopf ist unvollständig.")
    width, height = struct.unpack_from("<HH", raw, 6)
    if not width or not height or width * height > limits.pixels:
        raise StudioError("blocked", "GIF überschreitet die Pixelgrenze.")
    packed = raw[10]
    position = 13 + (3 * 2 ** ((packed & 7) + 1) if packed & 128 else 0)
    count = 0

    def skip_blocks(position):
        while position < len(raw):
            size = raw[position]
            position += 1
            if size == 0:
                return position
            position += size
        raise StudioError("unsupported", "GIF-Datenblock ist unvollständig.")

    while position < len(raw):
        marker = raw[position]
        position += 1
        if marker == 0x3B:
            if not count:
                raise StudioError("unsupported", "GIF enthält keine Frames.")
            return count
        if marker == 0x21:
            position = skip_blocks(position + 1)
        elif marker == 0x2C:
            if position + 9 > len(raw):
                break
            left, top, frame_width, frame_height, packed = struct.unpack_from("<HHHHB", raw,
                position)
            if (not frame_width or not frame_height or left + frame_width > width
                    or top + frame_height > height or frame_width * frame_height > limits.pixels):
                raise StudioError("blocked", "GIF-Frame überschreitet seine geprüfte Bildfläche.")
            position += 9 + (3 * 2 ** ((packed & 7) + 1) if packed & 128 else 0)
            if position >= len(raw) or not 2 <= raw[position] <= 8:
                raise StudioError("unsupported", "GIF-Datenformat nicht unterstützt.")
            position = skip_blocks(position + 1)
            count += 1
            if count > 10000:
                raise StudioError("blocked", "GIF überschreitet 10.000 Frames.")
        else:
            raise StudioError("unsupported", "Ungültiger GIF-Datenblock.")
    raise StudioError("unsupported", "GIF ist nicht vollständig übertragen.")
