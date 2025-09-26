import argparse
from collections import defaultdict
import struct

class Node:
    def __init__(self, freq, char=None, left=None, right=None):
        self.freq = freq  # Частота символа
        self.char = char  # Символ (для листьев)
        self.left = left  # Левый потомок
        self.right = right  # Правый потомок

    def __lt__(self, other):
        return self.freq < other.freq

def build_frequency_table(text):
    frequency = defaultdict(int)
    for char in text:
        frequency[char] += 1
    return frequency

# -------------------- Шеннон–Фано --------------------
def _split_index_by_balance(pairs):
    if not pairs:
        return 0
    total = sum(freq for _, freq in pairs)
    running = 0
    best_i = 1
    best_diff = float('inf')
    for i in range(1, len(pairs)):
        running += pairs[i-1][1]
        diff = abs(total/2 - running)
        if diff < best_diff:
            best_diff = diff
            best_i = i
    return best_i

def _build_fano_from_sorted(pairs):
    if not pairs:
        return None
    if len(pairs) == 1:
        ch, fr = pairs[0]
        return Node(fr, ch)
    i = _split_index_by_balance(pairs)
    left_pairs = pairs[:i]
    right_pairs = pairs[i:]
    left = _build_fano_from_sorted(left_pairs)
    right = _build_fano_from_sorted(right_pairs)
    return Node(sum(freq for _, freq in pairs), None, left, right)

def build_fano_tree(frequency):
    pairs = sorted(frequency.items(), key=lambda kv: kv[1], reverse=True)
    if len(pairs) == 0:
        return None
    return _build_fano_from_sorted(pairs)
# -----------------------------------------------------

def build_codes_iterative(root):
    codebook = {}
    if root is None:
        return codebook
    stack = [(root, "")]
    while stack:
        node, prefix = stack.pop()
        if node.char is not None:
            codebook[node.char] = prefix or "0"
        else:
            if node.right:
                stack.append((node.right, prefix + "1"))
            if node.left:
                stack.append((node.left, prefix + "0"))
    return codebook

def encode(text, codebook):
    return ''.join(codebook[char] for char in text)

def decode(encoded_bits, root):
    decoded = []
    node = root
    for bit in encoded_bits:
        node = node.left if bit == '0' else node.right
        if node.char is not None:
            decoded.append(node.char)
            node = root
    return ''.join(decoded)

def serialize_tree_iterative(root):
    bits = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.char is not None:
            bits.append('1')
            char_bits = format(ord(node.char), '08b')
            bits.extend(char_bits)
        else:
            bits.append('0')
            if node.right:
                stack.append(node.right)
            if node.left:
                stack.append(node.left)
    bit_string = ''.join(bits)
    return bit_string_to_bytes(bit_string)

def deserialize_tree_iterative(bit_bytes):
    bit_string = bytes_to_bit_string(bit_bytes)
    it = iter(bit_string)
    stack = []
    root = None
    try:
        while True:
            bit = next(it)
            if bit == '1':
                char_bits = ''.join(next(it) for _ in range(8))
                leaf = Node(0, chr(int(char_bits, 2)))
                if not stack:
                    root = leaf
                else:
                    parent = stack[-1]
                    if parent.left is None:
                        parent.left = leaf
                    elif parent.right is None:
                        parent.right = leaf
                        stack.pop()
            else:  # bit == '0'
                internal = Node(0, None)
                if not stack:
                    root = internal
                else:
                    parent = stack[-1]
                    if parent.left is None:
                        parent.left = internal
                    elif parent.right is None:
                        parent.right = internal
                        stack.pop()
                stack.append(internal)
    except StopIteration:
        pass
    return root

def bit_string_to_bytes(s):
    padding = (8 - len(s) % 8) % 8
    s += '0' * padding
    byte_array = bytearray()
    for i in range(0, len(s), 8):
        byte = s[i:i+8]
        byte_array.append(int(byte, 2))
    return bytes([padding]) + bytes(byte_array)

def bytes_to_bit_string(b):
    padding = b[0]
    bit_string = ''.join(f'{byte:08b}' for byte in b[1:])
    if padding > 0:
        bit_string = bit_string[:-padding]
    return bit_string

def save_encoded_file(encoded_bits, tree_bits, output_file):
    with open(output_file, 'wb') as f:
        tree_length = len(tree_bits)
        f.write(struct.pack('>I', tree_length))  # 4 байта для длины
        f.write(tree_bits)
        f.write(encoded_bits)

def load_encoded_file(input_file):
    with open(input_file, 'rb') as f:
        tree_length_bytes = f.read(4)
        if len(tree_length_bytes) < 4:
            raise ValueError("Файл поврежден или некорректен.")
        tree_length = struct.unpack('>I', tree_length_bytes)[0]
        tree_bits = f.read(tree_length)
        encoded_bits = f.read()
    return tree_bits, encoded_bits

def display_codes(codebook):
    print("Коды Шеннона–Фано:")
    for char, code in sorted(codebook.items()):
        if char == ' ':
            display_char = "' ' (пробел)"
        elif char == '\n':
            display_char = "'\\n' (новая строка)"
        else:
            display_char = repr(char)
        print(f"{display_char}: {code}")

def display_tree_iterative(root):
    stack = [(root, '')]
    while stack:
        node, prefix = stack.pop()
        if node.char is not None:
            print(f"{prefix}Leaf: {repr(node.char)}")
        else:
            print(f"{prefix}Node:")
            if node.right:
                stack.append((node.right, prefix + " 1-"))
            if node.left:
                stack.append((node.left, prefix + " 0-"))

def encode_file(input_file, output_file, display=False, display_tree_flag=False):
    with open(input_file, 'r', encoding='ascii') as f:
        text = f.read()
    frequency = build_frequency_table(text)
    tree = build_fano_tree(frequency)
    if tree is None:
        print("Входной файл пуст.")
        return
    codebook = build_codes_iterative(tree)
    encoded_bit_string = encode(text, codebook)
    encoded_bits = bit_string_to_bytes(encoded_bit_string)
    tree_bits = serialize_tree_iterative(tree)
    save_encoded_file(encoded_bits, tree_bits, output_file)
    if display:
        display_codes(codebook)
    if display_tree_flag:
        print("Дерево Шеннона–Фано:")
        display_tree_iterative(tree)

def decode_file(input_file, output_file, display=False, display_tree_flag=False):
    tree_bits, encoded_bits = load_encoded_file(input_file)
    tree = deserialize_tree_iterative(tree_bits)
    if tree is None:
        print("Входной файл не содержит данных для декодирования.")
        return
    if display_tree_flag:
        print("Дерево Шеннона–Фано:")
        display_tree_iterative(tree)
    encoded_bit_string = bytes_to_bit_string(encoded_bits)
    decoded_text = decode(encoded_bit_string, tree)
    with open(output_file, 'w', encoding='ascii') as f:
        f.write(decoded_text)
    if display:
        print("Декодированный текст:")
        print(decoded_text)

def main():
    parser = argparse.ArgumentParser(description="Система кодирования и декодирования с использованием алгоритма Шеннона–Фано.")
    subparsers = parser.add_subparsers(dest='command', help='Команда: encode или decode')

    # Подкоманда encode
    encode_parser = subparsers.add_parser('encode', help='Кодирование файла')
    encode_parser.add_argument('input', help='Входной текстовый файл для кодирования')
    encode_parser.add_argument('output', help='Выходной файл с закодированными данными')
    encode_parser.add_argument('-c', '--codes', action='store_true', help='Отобразить коды Шеннона–Фано')
    encode_parser.add_argument('-t', '--tree', action='store_true', help='Отобразить дерево Шеннона–Фано')

    # Подкоманда decode
    decode_parser = subparsers.add_parser('decode', help='Декодирование файла')
    decode_parser.add_argument('input', help='Входной файл с закодированными данными')
    decode_parser.add_argument('output', help='Выходной текстовый файл с декодированными данными')
    decode_parser.add_argument('-c', '--codes', action='store_true', help='Отобразить декодированный текст')
    decode_parser.add_argument('-t', '--tree', action='store_true', help='Отобразить дерево Шеннона–Фано')

    args = parser.parse_args()

    if args.command == 'encode':
        encode_file(args.input, args.output, display=args.codes, display_tree_flag=args.tree)
    elif args.command == 'decode':
        decode_file(args.input, args.output, display=args.codes, display_tree_flag=args.tree)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
