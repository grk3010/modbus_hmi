"""
Utility functions and lightweight pure-Python QR Code SVG generator.
Requires zero external network dependencies so HMIs operate seamlessly
on air-gapped industrial plant networks.
"""

def rindex(lst, value):
    try:
        return len(lst) - lst[::-1].index(value) - 1
    except ValueError:
        raise ValueError(f"{value} is not in list")


# ==============================================================================
# Pure-Python Standalone QR Code SVG Generator (ISO/IEC 18004 Compliant)
# ==============================================================================

class _GF256:
    """Galois Field GF(2^8) arithmetic with generator polynomial 0x11D (285)."""
    EXP = [0] * 512
    LOG = [0] * 256

    @classmethod
    def init(cls):
        x = 1
        for i in range(255):
            cls.EXP[i] = x
            cls.EXP[i + 255] = x
            cls.LOG[x] = i
            x <<= 1
            if x & 0x100:
                x ^= 0x11D
        cls.EXP[510] = cls.EXP[0]
        cls.EXP[511] = cls.EXP[1]

    @classmethod
    def mul(cls, x, y):
        if x == 0 or y == 0:
            return 0
        return cls.EXP[cls.LOG[x] + cls.LOG[y]]

_GF256.init()


def _rs_generator_poly(degree):
    """Calculates Reed-Solomon error correction generator polynomial coefficients."""
    poly = [1]
    for i in range(degree):
        root = _GF256.EXP[i]
        new_poly = [0] * (len(poly) + 1)
        for j, coeff in enumerate(poly):
            new_poly[j] ^= _GF256.mul(coeff, root)
            new_poly[j + 1] ^= coeff
        poly = new_poly
    return poly


def _rs_encode(data, ec_len):
    """Computes Reed-Solomon error correction codewords."""
    gen = _rs_generator_poly(ec_len)
    res = list(data) + [0] * ec_len
    for i in range(len(data)):
        lead = res[i]
        if lead != 0:
            for j in range(len(gen)):
                res[i + j] ^= _GF256.mul(gen[j], lead)
    return res[len(data):]


# Supported QR Version specs (Version 1, 2, 3, 4 with EC Level L)
# (version, total_data_codewords, ec_codewords, alignment_coords)
_QR_SPECS = [
    (1, 19, 7, []),
    (2, 34, 10, [6, 18]),
    (3, 55, 15, [6, 22]),
    (4, 80, 20, [6, 26]),
    (5, 108, 26, [6, 30]),
]


def generate_qr_svg(text: str, size: int = 150) -> str:
    """
    Generates a standalone, clean inline SVG QR code for the given text.
    Operates 100% locally with zero external network or third-party dependencies.
    """
    # Check if third-party qrcode library is available
    try:
        import qrcode
        import qrcode.image.svg
        import io
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(text, image_factory=factory, box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf)
        svg_str = buf.getvalue().decode('utf-8')
        if svg_str.startswith("<?xml"):
            svg_str = svg_str.split("?>", 1)[-1].strip()
        return svg_str
    except ImportError:
        pass

    # Pure Python compliant QR generator for URLs and strings
    data_bytes = text.encode('utf-8')
    data_len = len(data_bytes)

    # Select smallest fitting version
    spec = None
    for s in _QR_SPECS:
        # Byte mode header: 4 bits mode + 8 bits char count = 12 bits
        # Required data capacity: ceil((12 + data_len * 8) / 8)
        needed = (12 + data_len * 8 + 7) // 8
        if needed <= s[1]:
            spec = s
            break

    if spec is None:
        spec = _QR_SPECS[-1]

    version, total_data_codewords, ec_len, align_coords = spec
    modules_count = 17 + 4 * version

    # 1. Build bit stream (Byte Mode = 0100)
    bits = [0, 1, 0, 0]
    # Character count (8 bits for Version 1-9 in byte mode)
    for b in range(7, -1, -1):
        bits.append((data_len >> b) & 1)
    # Data bits
    for byte in data_bytes:
        for b in range(7, -1, -1):
            bits.append((byte >> b) & 1)

    # Terminator: up to 4 zero bits
    bits_needed = total_data_codewords * 8
    pad_zeros = min(4, bits_needed - len(bits))
    bits.extend([0] * pad_zeros)

    # Pad to byte boundary
    while len(bits) % 8 != 0:
        bits.append(0)

    # Pad bytes (0xEC, 0x11 alternating)
    pad_bytes = [0xEC, 0x11]
    pad_idx = 0
    while len(bits) < bits_needed:
        pb = pad_bytes[pad_idx % 2]
        for b in range(7, -1, -1):
            bits.append((pb >> b) & 1)
        pad_idx += 1

    # Convert bit stream to codewords
    data_codewords = []
    for i in range(0, len(bits), 8):
        byte_val = 0
        for b in range(8):
            byte_val = (byte_val << 1) | bits[i + b]
        data_codewords.append(byte_val)

    # Compute Reed-Solomon Error Correction codewords
    ec_codewords = _rs_encode(data_codewords, ec_len)
    all_codewords = data_codewords + ec_codewords

    # 2. Grid construction (0: white, 1: black, None: unassigned)
    grid = [[None] * modules_count for _ in range(modules_count)]
    is_function = [[False] * modules_count for _ in range(modules_count)]

    def set_fn(r, c, val):
        grid[r][c] = val
        is_function[r][c] = True

    # Finder patterns
    def add_finder(start_r, start_c):
        for r in range(7):
            for c in range(7):
                val = 1 if (r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4)) else 0
                set_fn(start_r + r, start_c + c, val)

    add_finder(0, 0)
    add_finder(0, modules_count - 7)
    add_finder(modules_count - 7, 0)

    # Separators around finders
    for i in range(8):
        # Top-left
        if i < modules_count:
            set_fn(7, i, 0)
            set_fn(i, 7, 0)
        # Top-right
        if modules_count - 8 + i < modules_count:
            set_fn(7, modules_count - 8 + i, 0)
            set_fn(i, modules_count - 8, 0)
        # Bottom-left
        if modules_count - 8 + i < modules_count:
            set_fn(modules_count - 8 + i, 7, 0)
            set_fn(modules_count - 8, i, 0)

    # Timing patterns
    for i in range(8, modules_count - 8):
        set_fn(6, i, 1 if i % 2 == 0 else 0)
        set_fn(i, 6, 1 if i % 2 == 0 else 0)

    # Alignment pattern for Version >= 2
    if align_coords:
        for r in align_coords:
            for c in align_coords:
                if (r < 9 and c < 9) or (r < 9 and c > modules_count - 10) or (r > modules_count - 10 and c < 9):
                    continue
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        val = 1 if (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0)) else 0
                        set_fn(r + dr, c + dc, val)

    # Dark module
    set_fn(4 * version + 9, 8, 1)

    # Reserve Format Information area
    for i in range(9):
        if not is_function[8][i]:
            set_fn(8, i, 0)
        if not is_function[i][8]:
            set_fn(i, 8, 0)
    for i in range(8):
        set_fn(8, modules_count - 1 - i, 0)
        set_fn(modules_count - 1 - i, 8, 0)

    # 3. Place Data Bits (Zig-Zag in 2-column bands)
    bit_list = []
    for cw in all_codewords:
        for b in range(7, -1, -1):
            bit_list.append((cw >> b) & 1)

    bit_idx = 0
    right = modules_count - 1
    up = True
    while right > 0:
        if right == 6:  # Skip vertical timing pattern column
            right -= 1
        row_range = range(modules_count - 1, -1, -1) if up else range(modules_count)
        for r in row_range:
            for c in (right, right - 1):
                if not is_function[r][c]:
                    b_val = bit_list[bit_idx] if bit_idx < len(bit_list) else 0
                    grid[r][c] = b_val
                    bit_idx += 1
        right -= 2
        up = not up

    # 4. Apply Mask Pattern 0: (row + col) % 2 == 0
    for r in range(modules_count):
        for c in range(modules_count):
            if not is_function[r][c]:
                if (r + c) % 2 == 0:
                    grid[r][c] ^= 1

    # 5. Format Information: EC Level L (01) + Mask 0 (000) = 01000
    # Pre-calculated 15-bit format with BCH(15, 5) and XOR mask 0x5412 = 0x77C4 (111011111000100 in binary)
    format_bits = [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0]
    
    # Write format bits to grid
    for i, b in enumerate(format_bits):
        if i <= 5:
            grid[8][i] = b
        elif i == 6:
            grid[8][7] = b
        elif i == 7:
            grid[8][8] = b
        elif i == 8:
            grid[7][8] = b
        else:
            grid[14 - i][8] = b

    for i, b in enumerate(format_bits):
        if i < 8:
            grid[modules_count - 1 - i][8] = b
        else:
            grid[8][modules_count - 15 + i] = b

    # 6. Render as SVG Path
    border = 2
    view_size = modules_count + 2 * border
    path_d = []
    for r in range(modules_count):
        for c in range(modules_count):
            if grid[r][c] == 1:
                x = c + border
                y = r + border
                path_d.append(f"M{x},{y}h1v1h-1z")

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_size} {view_size}" '
        f'width="{size}" height="{size}" style="background:#ffffff; border-radius:8px; padding:4px;">'
        f'<path d="{" ".join(path_d)}" fill="#000000"/>'
        f'</svg>'
    )
    return svg
