ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)

def encode_base62(num: int) -> str:
    """Encodes a base-10 integer to a Base62 string."""
    if num == 0:
        return ALPHABET[0]
    arr = []
    while num > 0:
        remainder = num % BASE
        arr.append(ALPHABET[remainder])
        num //= BASE
    return "".join(arr[::-1])

def decode_base62(s: str) -> int:
    """Decodes a Base62 string to a base-10 integer."""
    num = 0
    for char in s:
        num = num * BASE + ALPHABET.index(char)
    return num
