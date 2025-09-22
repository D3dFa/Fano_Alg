import argparse
import json
import struct
from collections import Counter

MAGIC = b"FANO1"

# ---------- Построение кода Фано (итеративно, без рекурсии) ----------
def build_fano_code(symbols_weights, show_splits=False):

    if not symbols_weights:
        return {}

    # Стабильная сортировка: по убыванию веса, при равенстве — по символу
    items = sorted(symbols_weights, key=lambda x: (-x[1], x[0]))
    n = len(items)
    if n == 1:
        return {items[0][0]: "0"}

    code = {}
    stack = [(items, "")]  # LIFO

    while stack:
        arr, pref = stack.pop()
        m = len(arr)

        if m == 1:
            sym = arr[0][0]
            code[sym] = pref or "0"
            continue

        if m == 2:
            code[arr[0][0]] = pref + "0"
            code[arr[1][0]] = pref + "1"
            continue

        # Ищем точку разделения с минимальной разницей от половины суммы
        total = sum(w for _, w in arr)
        half = total / 2
        acc = 0.0
        best_i = 0
        best_diff = float("inf")
        for i, (_, w) in enumerate(arr):
            acc += w
            diff = abs(half - acc)
            if diff < best_diff:
                best_diff = diff
                best_i = i

        # Гарантируем, что обе части непустые
        if best_i <= 0:
            best_i = 0
        if best_i >= m - 1:
            best_i = m - 2

        left = arr[:best_i + 1]
        right = arr[best_i + 1:]

        if show_splits:
            print(f"SPLIT prefix={pref!r}: LEFT={[s for s,_ in left]} | RIGHT={[s for s,_ in right]}")

        # Обрабатываем левую часть раньше правой (пушим правую первой)
        stack.append((right, pref + "1"))
        stack.append((left, pref + "0"))

    return code

# ---------- Кодирование/декодирование (с печатью шагов) ----------
def encode_to_bits(text, codebook, verbose=True):
    if verbose:
        print("\n=== Кодирование ===")
    bits = []
    for ch in text:
        try:
            code = codebook[ch]
        except KeyError:
            raise KeyError(f"Символ {repr(ch)} отсутствует в кодовой книге")
        if verbose:
            print(f"Символ: {repr(ch)} → Код: {code}")
        bits.append(code)
    return "".join(bits)

def decode_from_bits(bitstring, codebook, verbose=True):
    if verbose:
        print("\n=== Декодирование ===")
    reverse = {v: k for k, v in codebook.items()}
    buf = ""
    out_chars = []
    for b in bitstring:
        buf += b
        if buf in reverse:
            ch = reverse[buf]
            if verbose:
                print(f"Код: {buf} → Символ: {repr(ch)}")
            out_chars.append(ch)
            buf = ""
    if buf:
        raise ValueError("Непустой буфер после чтения битов — повреждён поток или неверная кодовая книга.")
    return "".join(out_chars)

# ---------- Упаковка/распаковка битов ----------
def pack_bits(bitstring):
  
    num_bits = len(bitstring)
    out = bytearray()
    cur = 0
    cnt = 0
    for ch in bitstring:
        cur = (cur << 1) | (1 if ch == '1' else 0)
        cnt += 1
        if cnt == 8:
            out.append(cur)
            cur = 0
            cnt = 0
    if cnt:
        cur <<= (8 - cnt)
        out.append(cur)
    return bytes(out), num_bits

def unpack_bits(data_bytes, num_bits):

    bits = []
    for byte in data_bytes:
        for i in range(7, -1, -1):
            bits.append('1' if (byte >> i) & 1 else '0')
    return "".join(bits[:num_bits])

# ---------- Запись/чтение бинарного контейнера ----------
def write_binary(filename, codebook, bitstring, text_len):
    payload, num_bits = pack_bits(bitstring)
    header_obj = {
        "codebook": codebook,
        "num_bits": num_bits,
        "text_len": text_len,
    }
    header_bytes = json.dumps(header_obj, ensure_ascii=False).encode("utf-8")
    with open(filename, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">I", len(header_bytes)))
        f.write(header_bytes)
        f.write(payload)
    print(f"\nФайл сохранён: {filename}")
    print(f"Размер хедера: {len(header_bytes)} байт, полезных бит: {num_bits}, полезных байт: {len(payload)}")

def read_binary(filename):
    with open(filename, "rb") as f:
        magic = f.read(len(MAGIC))
        if magic != MAGIC:
            raise ValueError("Неверная сигнатура файла (magic).")
        (hdr_len,) = struct.unpack(">I", f.read(4))
        header_bytes = f.read(hdr_len)
        header_obj = json.loads(header_bytes.decode("utf-8"))
        payload = f.read()

    codebook = header_obj.get("codebook", {})
    num_bits = int(header_obj.get("num_bits", 0))
    text_len = int(header_obj.get("text_len", 0))
    bitstring = unpack_bits(payload, num_bits)

    print(f"\nФайл прочитан: {filename}")
    print(f"Размер хедера: {hdr_len} байт, полезных бит: {num_bits}, полезных байт: {len(payload)}")
    return codebook, bitstring, text_len

# ---------- Основной CLI ----------
def main():
    parser = argparse.ArgumentParser(description="Fano coding CLI (итеративная реализация, без рекурсии)")
    subparsers = parser.add_subparsers(dest="command")

    # encode
    enc = subparsers.add_parser("encode", help="Закодировать текстовый файл в бинарный")
    enc.add_argument("input", help="Входной текстовый файл (UTF-8)")
    enc.add_argument("output", help="Выходной бинарный файл")
    enc.add_argument("-q", "--quiet", action="store_true", help="Без показа шагов кодирования")
    enc.add_argument("--show-splits", action="store_true", help="Показывать разбиения при построении кодовой книги")

    # decode
    dec = subparsers.add_parser("decode", help="Декодировать бинарный файл в текстовый")
    dec.add_argument("input", help="Входной бинарный файл")
    dec.add_argument("output", help="Выходной текстовый файл (UTF-8)")
    dec.add_argument("-q", "--quiet", action="store_true", help="Без показа шагов декодирования")

    args = parser.parse_args()

    if args.command == "encode":
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()

        if not text:
            print("⚠️ Внимание: входной файл пуст. Будет записан пустой контейнер.")
            codebook = {}
            bitstring = ""
            write_binary(args.output, codebook, bitstring, text_len=0)
            return

        # Используем целочисленные веса (частоты) — это устойчивее, чем вероятности с float-округлением
        freqs = Counter(text)
        weights = list(freqs.items())
        codebook = build_fano_code(weights, show_splits=args.show_splits)

        print("\n=== Словарь кодов ===")
        for s, c in sorted(codebook.items(), key=lambda x: (len(x[1]), x[0])):
            print(f"{repr(s)}: {c}")

        bitstring = encode_to_bits(text, codebook, verbose=not args.quiet)
        write_binary(args.output, codebook, bitstring, text_len=len(text))

    elif args.command == "decode":
        codebook, bitstring, _ = read_binary(args.input)
        decoded_text = decode_from_bits(bitstring, codebook, verbose=not args.quiet)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(decoded_text)
        print(f"\nДекодированный текст сохранён в: {args.output}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()

