"""
Verhoeff Checksum Algorithm implementation for Aadhaar number validation.
Dihedral group D5 based error-detecting code.
"""

# Multiplication table d
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# Permutation table p
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# Inverse table inv
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def validate_verhoeff(num_str: str) -> bool:
    """
    Validate a numeric string with the Verhoeff algorithm.
    Returns True if checksum is 0.
    """
    clean = "".join(c for c in num_str if c.isdigit())
    if not clean:
        return False

    c = 0
    reversed_digits = [int(d) for d in reversed(clean)]
    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[i % 8][digit]]

    return c == 0


def calculate_verhoeff(num_str: str) -> int:
    """
    Compute the Verhoeff checksum digit for a numeric string.
    """
    clean = "".join(c for c in num_str if c.isdigit())
    c = 0
    reversed_digits = [int(d) for d in reversed(clean)]
    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[(i + 1) % 8][digit]]

    return _INV[c]
