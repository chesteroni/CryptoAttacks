#!/usr/bin/env python

import os
import subprocess

from CryptoAttacks.PublicKey.rsa import *
from CryptoAttacks.Utils import *
from CryptoAttacks.Math import *

key_to_oracle = None


def test_small_e_msg(key):
    print "Test: small_e_msg"
    for x in range(10):
        plaintext = b2i(random_str(10))
        ciphertext = key.encrypt(plaintext)
        key.add_ciphertext(ciphertext)
        recovered_plaintext = small_e_msg(key)
        assert len(recovered_plaintext) == 1
        assert recovered_plaintext[0] == plaintext
        key.clear_texts()


def signing_oracle(plaintext):
    global key_to_oracle
    signature = subprocess.check_output(["./rsa_oracles.py", "sign", key_to_oracle.identifier, i2h(plaintext)]).strip()
    return h2i(signature)


def decryption_oracle(ciphertext):
    global key_to_oracle
    plaintext = subprocess.check_output(["./rsa_oracles.py", "decrypt", key_to_oracle.identifier, i2h(ciphertext)]).strip()
    return h2i(plaintext)


def test_blinding(key):
    global key_to_oracle
    key_to_oracle = key

    print "\nTest: blinding(key, signing_oracle=signing_oracle)"
    for x in range(10):
        msg_to_sign = b2i(random_str(random.randint(10, (key.size/8)-1)).replace('\n', ''))
        key.add_plaintext(msg_to_sign)
        signature = blinding(key, signing_oracle=signing_oracle)
        assert len(signature) == 1
        is_correct = subprocess.check_output(["./rsa_oracles.py", "verify", key_to_oracle.identifier, i2h(msg_to_sign), i2h(signature[0])]).strip()
        assert is_correct == 'True'
        key.clear_texts()

    print "\nTest: blinding(key, decryption_oracle=decryption_oracle)"
    for x in range(10):
        plaintext = b2i(random_str(random.randint(10, (key.size/8)-1)).replace('\n', ''))
        ciphertext = key.encrypt(plaintext)
        key.add_ciphertext(ciphertext)
        plaintext_recovered = blinding(key, decryption_oracle=decryption_oracle)
        assert len(plaintext_recovered) == 1
        assert plaintext_recovered[0] == plaintext
        key.clear_texts()

    key_to_oracle = None


def test_wiener(tries=10):
    print "\nTest: wiener"
    for x in xrange(tries):
        n_size = 1024
        p = random_prime(n_size / 2)
        q = random_prime(n_size / 2)
        n = p*q
        phi = (p-1)*(q-1)
        while True:
            d = random.getrandbits(n_size / 4)
            if gmpy2.gcd(phi, d) == 1 and 81 * pow(d, 4) < n:
                break
        e = invmod(d, phi)
        key = RSAKey.construct(long(n), long(e))
        key_recovered = wiener(key.publickey())
        if key_recovered:
            assert key_recovered.d == d
        else:
            print "Not recovered"


def test_common_primes():
    print "\nTest: common primes"
    keys_path = "./common_prime/"
    keys = []
    for f in os.listdir(keys_path):
        if f.endswith('.pem'):
            tmp = RSAKey.import_key(keys_path+f)
            keys.append(tmp)
    priv_keys = common_primes(keys)
    assert len(priv_keys) != 0


def test_hastad():
    print "\nTest: hastad"
    n_size = 1024
    for e in [3, 17, 49]:
        print "Test: e={}".format(e)
        msg = random.randint(1000, 1 << (n_size-25))
        keys = []
        for count in xrange(e):
            tmp = RSAKey.generate(n_size, e=e).publickey()
            ciphertext = tmp.encrypt(msg)
            tmp.texts.append({'cipher': ciphertext})
            keys.append(tmp)
        msg_recovered = hastad(keys)
        assert msg_recovered == msg


def test_faulty():
    print "\nTest: faulty"
    for x in xrange(5):
        key = RSAKey.generate(1024)
        m = random.randint(0x13373371, key.n)
        sp = pow(m, key.d % (key.p - 1), key.p)
        sq = pow(m, key.d % (key.q - 1), key.q)
        sq_f = sq ^ random.randint(1, sq)  # random error

        s_f = crt([sp, sq_f], [key.p, key.q]) % key.n
        s = crt([sp, sq], [key.p, key.q]) % key.n

        key.texts.append({'cipher': s_f, 'plain': m})
        key_recovered = faulty(key.publickey())
        assert key_recovered and key_recovered.d == key.d

        key.texts = [{'cipher': s}, {'cipher': s_f}]
        key_recovered = faulty(key.publickey())
        assert key_recovered and key_recovered.d == key.d

        key.texts = [{'cipher': s}, {'cipher': s_f}, {'cipher': random.randint(1, key.n)},
                     {'cipher': random.randint(1, key.n), 'plain': random.randint(1, key.n)}]
        key_recovered = faulty(key.publickey())
        assert key_recovered and key_recovered.d == key.d

        key.texts = [{'cipher': s, 'plain': m}]
        key_recovered = faulty(key.publickey())
        assert key_recovered is False


def parity_oracle(ciphertext):
    global key_to_oracle
    ciphertext = i2b(ciphertext)
    message = subprocess.check_output(["./rsa_oracles.py", "parity", key_to_oracle.identifier, b2h(ciphertext)]).strip()
    if message == '1':
        return 1
    return 0


def test_parity(key):
    global key_to_oracle
    key_to_oracle = key

    print "\nTest: parity"
    plaintext1 = "Some plaintext " + random_str(10) + " anything can it be"
    plaintext2 = "Some plaintext " + random_str(10) + " anything can it be2"
    ciphertext1 = h2b(subprocess.check_output(["./rsa_oracles.py", "encrypt", key.identifier, b2h(plaintext1)]).strip())
    ciphertext2 = h2b(subprocess.check_output(["./rsa_oracles.py", "encrypt", key.identifier, b2h(plaintext2)]).strip())

    key.texts.append({'cipher': b2i(ciphertext1)})
    key.texts.append({'cipher': b2i(ciphertext2)})
    msgs_recovered = parity(parity_oracle, key)
    assert msgs_recovered[0] == b2i(plaintext1)
    assert msgs_recovered[1] == b2i(plaintext2)
    key.texts = []
    key_to_oracle = None


def test_bleichenbacher_signature_forgery(key):
    print "\nTest bleichenbacher_signature_forgery(key, garbage='suffix', hash_function='sha1')"
    for x in xrange(10):
        message1 = "Some plaintext " + random_str(10) + " anything can it be"
        message2 = "Some plaintext " + random_str(10) + " anything can it be"

        key.add_plaintext(b2i(message1))
        key.add_plaintext(b2i(message2))

        forged_signatures = bleichenbacher_signature_forgery(key, garbage='suffix', hash_function='sha1')
        assert len(forged_signatures) == 2

        verify_signature1 = subprocess.check_output(["./rsa_oracles.py", "verify_bleichenbacher_suffix", key.identifier,
                                                     b2h(message1), i2h(forged_signatures[0]),
                                                     'sha1']).strip()
        assert verify_signature1 == 'True'
        verify_signature2 = subprocess.check_output(["./rsa_oracles.py", "verify_bleichenbacher_suffix", key.identifier,
                                                     b2h(message2), i2h(forged_signatures[1]),
                                                     'sha1']).strip()
        assert verify_signature2 == 'True'
        key.texts = []

    print "\nTest bleichenbacher_signature_forgery(key, garbage='middle', hash_function='sha1')"
    for x in xrange(10):
        message1 = "Some plaintext " + random_str(10) + " anything can it be"
        message2 = "Some plaintext " + random_str(10) + " anything can it be"

        key.add_plaintext(b2i(message1))
        key.add_plaintext(b2i(message2))

        forged_signatures = bleichenbacher_signature_forgery(key, garbage='middle', hash_function='sha1')

        if 0 in forged_signatures:
            verify_signature1 = subprocess.check_output(["./rsa_oracles.py", "verify_bleichenbacher_middle", key.identifier,
                                                         b2h(message1), i2h(forged_signatures[0]),
                                                         'sha1']).strip()
            assert verify_signature1 == 'True'
        if 1 in forged_signatures:
            verify_signature2 = subprocess.check_output(["./rsa_oracles.py", "verify_bleichenbacher_middle", key.identifier,
                                                         b2h(message2), i2h(forged_signatures[1]),
                                                         'sha1']).strip()
            assert verify_signature2 == 'True'
        key.texts = []


def run():
    key_static_2048 = RSAKey.import_key("private_key_2048.pem")
    key_static_1024 = RSAKey.import_key("private_key_1024.pem")
    key_static_1024_small_e = RSAKey.import_key("private_key_1024_small_e.pem")
    log.level = 'info'

    test_blinding(key_static_2048)
    test_small_e_msg(key_static_1024_small_e)
    test_faulty()
    test_hastad()
    test_common_primes()
    test_wiener()
    test_parity(key_static_1024)
    test_bleichenbacher_signature_forgery(key_static_1024_small_e)

if __name__ == "__main__":
    run()
