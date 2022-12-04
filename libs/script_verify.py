import random
from math import gcd

import zlib
import base64

from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes


def zip_str(text: str) -> str:
    b = zlib.compress(text.encode())
    return base64.b85encode(b).decode()


def unzip_str(text: str) -> str:
    b = base64.b85decode(text)
    return zlib.decompress(b).decode()


def lcm(p: int, q: int) -> int:
    """
    最小公倍数を求める。
    """
    return (p * q) // gcd(p, q)


def generate_keys(p: int, q: int) -> tuple:
    """
    与えられた 2 つの素数 p, q から秘密鍵と公開鍵を生成する。
    """
    n = p * q
    l = lcm(p - 1, q - 1)
    e = 0
    for i in range(2, l):
        if gcd(i, l) == 1:
            e = i
            break
    d = 0
    for i in range(2, l):
        if (e * i) % l == 1:
            d = i
            break

    return (e, n), (d, n)


def encrypt(plain_text: str, public_key: str) -> str:
    """
    公開鍵 public_key を使って平文 plain_text を暗号化する。
    """
    e, n = public_key
    plain_integers = [ord(char) for char in plain_text]
    encrypted_integers = [pow(i, e, n) for i in plain_integers]
    print(encrypted_integers)
    encrypted_text = ''.join(chr(i) for i in encrypted_integers)

    return encrypted_text


def decrypt(encrypted_text: str, private_key: str) -> str:
    """
    秘密鍵 private_key を使って暗号文 encrypted_text を復号する。
    """
    d, n = private_key
    encrypted_integers = [ord(char) for char in encrypted_text]
    decrypted_integers = [pow(i, d, n) for i in encrypted_integers]
    decrypted_text = ''.join(chr(i) for i in decrypted_integers)

    return decrypted_text


def sanitize(encrypted_text):
    """
    UnicodeEncodeError が置きないようにする。
    """
    return encrypted_text.encode('utf-8', 'replace').decode('utf-8')


def modular_exp(a, b, n):
    res = 1
    while b != 0:
        if b & 1 != 0:
            res = (res * a) % n
        a = (a * a) % n
        b = b >> 1

    return res


def gen_rand(bit_length):
    bits = [random.randint(0, 1) for _ in range(bit_length - 2)]
    ret = 1
    for b in bits:
        ret = ret * 2 + int(b)
    return ret * 2 + 1


def mr_primary_test(n, k=100):
    if n == 1:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    d = n - 1
    s = 0
    while d % 2 != 0:
        d /= 2
        s += 1

    r = [random.randint(1, n - 1) for _ in range(k)]
    for a in r:
        if modular_exp(a, d, n) != 1:
            pl = [(2 ** rr) * d for rr in range(s)]
            flg = True
            for p in pl:
                if modular_exp(a, p, n) == 1:
                    flg = False
                    break
            if flg:
                return False
    return True


def gen_prime(bit):
    while True:
        ret = gen_rand(bit)
        if mr_primary_test(ret):
            break
    return ret


def xgcd(b, n):
    x0, x1, y0, y1 = 1, 0, 0, 1
    while n != 0:
        q, b, n = b // n, n, b % n
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    return b, x0, y0


def gen_d(e, l):
    _, x, _ = xgcd(e, l)
    return x % l


def crypt(name, filename):
    recipient_key = RSA.import_key(open(pub_file_path).read())
    session_key = get_random_bytes(16)

    data = name.encode("utf-8")
    # セッションキーをRSA公開鍵で暗号化する
    cipher_rsa = PKCS1_OAEP.new(recipient_key)
    enc_session_key = cipher_rsa.encrypt(session_key)

    # データをAESセッションキーで暗号化
    cipher_aes = AES.new(session_key, AES.MODE_EAX)
    ciphertext, tag = cipher_aes.encrypt_and_digest(data)
    file_out = open(f"../Commands/Python/verification/{filename}.key", "wb")
    [file_out.write(x) for x in (enc_session_key, cipher_aes.nonce, tag, ciphertext)]
    file_out.close()

    file_in = open(f"../Commands/Python/verification/{filename}.key", "rb")

    private_key = RSA.import_key(open(private_file_path).read())

    enc_session_key, nonce, tag, ciphertext = \
        [file_in.read(x) for x in (private_key.size_in_bytes(), 16, 16, -1)]

    # セッションキーをRSA秘密鍵で復号する
    cipher_rsa = PKCS1_OAEP.new(private_key)
    session_key = cipher_rsa.decrypt(enc_session_key)

    # データをAESセッションキーで復号する
    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    data = cipher_aes.decrypt_and_verify(ciphertext, tag)
    print(data.decode("utf-8"))


if __name__ == '__main__':
    pub_file_path = "../config/pub_key.pem"
    private_file_path = "../config/private_key.pem"

    # # 秘密鍵の作成
    # key = RSA.generate(4096)
    # private_key = key.export_key()
    # file_out = open(private_file_path, "wb")
    # file_out.write(private_key)
    # file_out.close()
    #
    # # 公開鍵の作成
    # public_key = key.publickey().export_key()
    # file_out = open(pub_file_path, "wb")
    # file_out.write(public_key)
    # file_out.close()
    name = input("NAME: ")
    filename = input("filename: ")

    ls = [["ログ出力のサンプル", "LoggingSample"],
          ["マクロ実行テスト", "RunMacro"],
          ["Sample", "Sample"],
          ["ABXY連打", "Test"],
          ["ナワバトラー自動敗北", "TableTurfAutoLose"],
          ["Readme", "Tutorial"]
          ]

    for v in ls:

        crypt(v[0],v[1])

#
#
#     _public_key, _private_key = generate_keys(101, 3259)
#
#     _plain_text = 'Hello Worlds!'
#     _encrypted_text = encrypt(_plain_text, _public_key)
#     _decrypted_text = decrypt(_encrypted_text, _private_key)
#
#     print(f'''
# 秘密鍵: {_public_key}
# 公開鍵: {_private_key}
#
# 平文:
# 「{_plain_text}」
#
# 暗号文:
# 「{sanitize(_encrypted_text)}」
#
# 平文 (復号後):
# 「{_decrypted_text}」
# '''[1:-1])
#
#     bit_length = 512
#     p = gen_prime(bit_length)
#     q = gen_prime(bit_length)
#     e = gen_prime(bit_length)
#     d = gen_d(e, (p - 1) * (q - 1))
#     n = p * q
#
#     print(hex(p))
#     print(hex(q))
#
#     m = b"test"
#     # m = base64.urlsafe_b64encode(str(m).encode())
#     print(m)
#     c = modular_exp(m, e, n)  # 暗号文
#     m_ = modular_exp(c, d, n)  # 123456789
#     # m_ = base64.urlsafe_b64decode(str(m_).encode())
#     print(c)
#     print(m_)
