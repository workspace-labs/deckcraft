"""Read the pixel size of a PNG or JPEG without any image library."""
import struct


def image_size(path):
    """(width, height) of a PNG or JPEG file; raises ValueError for anything else."""
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            if len(head) >= 24 and head[8:16] == b"\x00\x00\x00\rIHDR":
                w, h = struct.unpack(">II", head[16:24])
                if w > 0 and h > 0:
                    return w, h
        elif head[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                if f.read(1) != b"\xff":
                    break
                marker = f.read(1)
                # JPEG allows repeated FF fill bytes before a marker identifier.
                while marker == b"\xff":
                    marker = f.read(1)
                if not marker:
                    break
                length_bytes = f.read(2)
                if len(length_bytes) != 2:
                    break
                length = struct.unpack(">H", length_bytes)[0]
                if length < 2:
                    break
                if marker[0] in (0xC0, 0xC1, 0xC2):
                    frame = f.read(5)
                    if length < 7 or len(frame) != 5:
                        break
                    h, w = struct.unpack(">xHH", frame)
                    if w > 0 and h > 0:
                        return w, h
                    break
                f.seek(length - 2, 1)
    raise ValueError(f"{path} is not a PNG or JPEG image with a readable, nonzero size.")


def mime(path):
    return "image/png" if path.lower().endswith(".png") else "image/jpeg"
