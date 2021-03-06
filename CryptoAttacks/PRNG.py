from CryptoAttacks.Utils import log
from CryptoAttacks.Math import gcd, invmod


class LCG(object):
    def __init__(self, seed, a, b, m):
        """Linear Congruence Generator

        Args:
            seed(int)
            a,b,m(ints): next_state = a*seed + b mod m
        """
        self.seed = seed
        self.a = a
        self.b = b
        self.m = m
        self.state = seed

    def next(self):
        """Returns next state"""
        new_state = (self.state*self.a + self.b) % self.m
        self.state = new_state
        return new_state

    def prev(self):
        """Returns previous state"""
        new_state = ((self.state - b) * invmod(a, self.m)) % self.m
        self.state = new_state
        return new_state


def compute_params(s):
    """Compute parameters and initial seed for LCG prng

    Args:
        s(list): subsequent outputs from LCG oracle

    Returns:
        seed(int): assuming first state in s was derived from seed
        a, b, m(ints): a,b,m(ints): next_state = a*seed + b mod m
    """
    t = [s[n + 1] - s[n] for n in xrange(len(s) - 1)]
    u = [abs(t[n + 2] * t[n] - t[n + 1] ** 2) for n in xrange(len(t) - 2)]
    m = gcd(*u)
    log.success("m = {}".format(m))

    if gcd(s[1] - s[0], m) == 1:
        a = (s[2] - s[1]) * invmod(s[1] - s[0], m)
    elif gcd(s[2] - s[0], m) == 1:
        a = (s[3] - s[1]) * invmod(s[2] - s[0], m)
    else:
        log.critical_error("a not found")
    log.succes("a = {}".format(a))

    b = (s[1] - s[0] * a) % m
    log.success("b = {}".format(b))

    seed = (((s[0] - b) % m) * invmod(a, m)) % m
    log.success("seed = {}".format(seed))
    return seed, a, b, m
