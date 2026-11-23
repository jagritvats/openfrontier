"""Certificate: for every 2 <= n <= LIMIT, 4/n = 1/a + 1/b + 1/c in positive integers.

Anyone can re-run this file:  python cert_bound.py --limit 1000
The last stdout line is the machine-readable verdict the oracle reads.
Exact integer arithmetic throughout; deterministic.
"""
import argparse
import json
from math import gcd


def solve(n: int):
    # 1/a <= 4/n and a <= b <= c  =>  n/4 <= a <= 3n/4
    a_lo = (n + 3) // 4
    a_hi = (3 * n) // 4
    for a in range(a_lo, a_hi + 1):
        # r = 4/n - 1/a = p/q (reduced); need 1/b + 1/c = r with a <= b <= c
        p = 4 * a - n
        if p <= 0:
            continue
        q = n * a
        g = gcd(p, q)
        p //= g
        q //= g
        # 1/b < r  =>  b > q/p ;  1/b >= r/2  =>  b <= 2q/p
        for b in range(max(a, q // p + 1), (2 * q) // p + 1):
            # c = 1 / (r - 1/b) = q*b / (p*b - q); must be an integer >= b
            num = p * b - q
            den = q * b
            if num > 0 and den % num == 0:
                c = den // num
                if c >= b:
                    return a, b, c
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=1000)
    args = ap.parse_args()
    for n in range(2, args.limit + 1):
        sol = solve(n)
        if sol is None:
            print(json.dumps({"result": "fails", "counterexample": n}))
            return
        last = (n, sol)
    print(json.dumps({"result": "holds", "bound": args.limit,
                      "last_checked": last[0], "last_solution": last[1]}))


if __name__ == "__main__":
    main()
