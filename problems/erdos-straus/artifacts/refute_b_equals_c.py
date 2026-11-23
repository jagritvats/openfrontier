"""Certificate AGAINST the claim: "4/n always has a solution with b = c".

With b = c the equation is 4/n = 1/a + 2/b. If a > n/3 then 1/a < 3/n, hence
2/b > 1/n and b < 2n. So it suffices to check a in (n/4, n/3] and b in
(n/2, 2n) — a finite, exact search.

First failure: n = 5.

Anyone can re-run:  python refute_b_equals_c.py
The last stdout line is the machine-readable verdict the oracle reads.
"""
import json
from fractions import Fraction


def solvable(n: int) -> bool:
    # small a: 4/n = 1/a + 2/b  =>  b = 2 / (4/n - 1/a) must be a positive integer
    for a in range(n // 4 + 1, n // 3 + 1):
        b = 2 / (Fraction(4, n) - Fraction(1, a))
        if b.denominator == 1 and b > 0:
            return True
    # large a (so b < 2n):  a = 1 / (4/n - 2/b) must be a positive integer
    for b in range(n // 2 + 1, 2 * n):
        a = 1 / (Fraction(4, n) - Fraction(2, b))
        if a.denominator == 1 and a > 0:
            return True
    return False


def main() -> None:
    for n in range(2, 10_000):
        if not solvable(n):
            print(json.dumps({"result": "fails",
                              "counterexample": {"n": n, "claim": "b = c"}}))
            return
    print(json.dumps({"result": "holds", "note": "unexpected: no counterexample below 10,000"}))


if __name__ == "__main__":
    main()
