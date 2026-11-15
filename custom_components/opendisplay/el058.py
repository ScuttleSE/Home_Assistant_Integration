"""Local patch: SoluM EL058F5W4C (5.8" BWRY 792x272, two cascaded controllers).

The tag (OpenDisplay fork build 3.0.200+) splits the frame at its two IMAGE_SLICE markers:
the first 26928 bytes go to the master controller (right half), the rest to the slave (left
half). Here the picture is dithered and encoded as BWRY 2 bpp, and each half is reordered
into the controller's row order 0, 271, 1, 270, ...

Only applies to displays with panel_ic_type 0x0579 (set by the local Toolbox preset).
"""

from __future__ import annotations

from opendisplay import device as _od
from opendisplay.encoding.compression import FIRMWARE_ZLIB_WINDOW_BITS, compress_image_data
from opendisplay.models.capabilities import DeviceCapabilities
from opendisplay.models.enums import ColorScheme

from . import services as _services

EL058_PANEL_IC_TYPE = 0x0579

_orig_prepare = _services.prepare_image
_orig_preview = _services.preview_image


def _is_el058(config) -> bool:
    return bool(config and config.displays and config.displays[0].panel_ic_type == EL058_PANEL_IC_TYPE)


def _bwry_caps(config) -> DeviceCapabilities:
    caps = _od._capabilities_from_config(config)
    return DeviceCapabilities(width=caps.width, height=caps.height,
                              color_scheme=ColorScheme.BWRY, rotation=caps.rotation)


def reorder(data: bytes, width: int = 792, height: int = 272) -> bytes:
    """Row-major BWRY 2 bpp frame -> master (right) half then slave (left) half,
    each with rows in the order 0, H-1, 1, H-2, ..."""
    row = width // 4
    half = row // 2
    out = bytearray()
    for offset in (half, 0):
        for k in range(height // 2):
            for r in (k, height - 1 - k):
                start = r * row + offset
                out += data[start:start + half]
    return bytes(out)


def prepare_image(image, config=None, capabilities=None, **kwargs):
    if not _is_el058(config):
        return _orig_prepare(image, config=config, capabilities=capabilities, **kwargs)
    compress = kwargs.pop("compress", True)
    caps = _bwry_caps(config)
    data, _, dithered = _orig_prepare(image, config=config, capabilities=caps, compress=False, **kwargs)
    data = reorder(data, caps.width, caps.height)
    compressed = (compress_image_data(data, level=6, window_bits=FIRMWARE_ZLIB_WINDOW_BITS)
                  if compress else None)
    return data, compressed, dithered


def preview_image(processed, config=None, capabilities=None, **kwargs):
    if _is_el058(config):
        capabilities = _bwry_caps(config)
    return _orig_preview(processed, config=config, capabilities=capabilities, **kwargs)


_services.prepare_image = prepare_image
_services.preview_image = preview_image
