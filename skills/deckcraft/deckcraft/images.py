"""Read the pixel size of a PNG or JPEG without any image library."""
import struct


def image_size(path):
    """(width, height) of a PNG or JPEG file; raises ValueError for anything else."""
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", head[16:24])
            return w, h
        if head[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    break
                length = struct.unpack(">H", f.read(2))[0]
                if marker[1] in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack(">xHH", f.read(5))
                    return w, h
                f.seek(length - 2, 1)
    raise ValueError(f"{path} is not a PNG or JPEG image.")


def mime(path):
    return "image/png" if path.lower().endswith(".png") else "image/jpeg"
