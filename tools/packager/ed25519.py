"""
RFC 8032 Ed25519 Signing Implementation.
Prefers standard audited OpenSSL-backed 'cryptography' library (RFC 8032 / FIPS compliant).
Falls back to pure-Python implementation when cryptography is unavailable.
"""
import hashlib
import os
from typing import Tuple

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519 as crypto_ed25519
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

b = 256
q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493

def H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()

def expmod(b: int, e: int, m: int) -> int:
    if e == 0:
        return 1
    t = expmod(b, e // 2, m) ** 2 % m
    if e & 1:
        t = (t * b) % m
    return t

def inv(x: int) -> int:
    return expmod(x, q - 2, q)

d = -121665 * inv(121666) % q
I = expmod(2, (q - 1) // 4, q)

def xrecover(y: int) -> int:
    xx = (y * y - 1) * inv(d * y * y + 1) % q
    x = expmod(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x

By = 4 * inv(5) % q
Bx = xrecover(By)
B = [Bx % q, By % q]

def edwards_add(P: list, Q: list) -> list:
    x1, y1 = P[0], P[1]
    x2, y2 = Q[0], Q[1]
    x3 = (x1 * y2 + x2 * y1) * inv(1 + d * x1 * x2 * y1 * y2) % q
    y3 = (y1 * y2 + x1 * x2) * inv(1 - d * x1 * x2 * y1 * y2) % q
    return [x3, y3]

def scalarmult(P: list, e: int) -> list:
    if e == 0:
        return [0, 1]
    Q = scalarmult(P, e // 2)
    Q = edwards_add(Q, Q)
    if e & 1:
        Q = edwards_add(Q, P)
    return Q

def encodeint(y: int) -> bytes:
    bits = [(y >> i) & 1 for i in range(b)]
    return bytes(sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8))

def encodepoint(P: list) -> bytes:
    x, y = P[0], P[1]
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes(sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8))

def bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1

def parseint(s: bytes) -> int:
    return sum(2**i * bit(s, i) for i in range(b))

def decodepoint(s: bytes) -> list:
    y = sum(2**i * bit(s, i) for i in range(b - 1))
    x = xrecover(y)
    if x & 1 != bit(s, b - 1):
        x = q - x
    P = [x, y]
    if not isoncurve(P):
        raise ValueError("decoding point that is not on curve")
    return P

def isoncurve(P: list) -> bool:
    x, y = P[0], P[1]
    return (-x * x + y * y - 1 - d * x * x * y * y) % q == 0

def publickey(sk: bytes) -> bytes:
    if HAS_CRYPTOGRAPHY:
        priv = crypto_ed25519.Ed25519PrivateKey.from_private_bytes(sk)
        pub = priv.public_key()
        return pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    h = H(sk)
    a = 2**(b - 2) + sum(2**i * bit(h, i) for i in range(3, b - 2))
    A = scalarmult(B, a)
    return encodepoint(A)

def Hint(m: bytes) -> int:
    h = H(m)
    return sum(2**i * bit(h, i) for i in range(2 * b))

def signature(m: bytes, sk: bytes, pk: bytes) -> bytes:
    if HAS_CRYPTOGRAPHY:
        priv = crypto_ed25519.Ed25519PrivateKey.from_private_bytes(sk)
        return priv.sign(m)
    h = H(sk)
    a = 2**(b - 2) + sum(2**i * bit(h, i) for i in range(3, b - 2))
    r = Hint(bytes([h[b // 8 + j] for j in range(b // 8)]) + m)
    R = scalarmult(B, r)
    S = (r + Hint(encodepoint(R) + pk + m) * a) % l
    return encodepoint(R) + encodeint(S)

def checkvalid(s: bytes, m: bytes, pk: bytes) -> bool:
    if len(s) != 64 or len(pk) != 32:
        return False
    if HAS_CRYPTOGRAPHY:
        try:
            pub = crypto_ed25519.Ed25519PublicKey.from_public_bytes(pk)
            pub.verify(s, m)
            return True
        except Exception:
            return False
    R = decodepoint(s[:b // 8])
    A = decodepoint(pk)
    S = parseint(s[b // 8:])
    h = Hint(encodepoint(R) + pk + m)
    v1 = scalarmult(B, S)
    v2 = edwards_add(R, scalarmult(A, h))
    return v1[0] == v2[0] and v1[1] == v2[1]

def generate_keypair() -> Tuple[bytes, bytes]:
    """Generates a cryptographically random (private_key, public_key) pair."""
    if HAS_CRYPTOGRAPHY:
        priv = crypto_ed25519.Ed25519PrivateKey.generate()
        sk = priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        pub = priv.public_key()
        pk = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return sk, pk
    sk = os.urandom(32)
    pk = publickey(sk)
    return sk, pk
