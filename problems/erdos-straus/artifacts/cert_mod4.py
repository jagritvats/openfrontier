"""Certificate: the family n = 4k + 3 is solvable, explicitly, for all k <= K.

Identity (exact, verified instance by instance below):
    4/(4k+3) = 1/(k+1) + 1/(m+1) + 1/(m(m+1))   where m = (4k+3)(k+1)
because 4/(4k+3) - 1/(k+1) = 1/((4k+3)(k+1))  and  1/m = 1/(m+1) + 1/(m(m+1)).

Anyone can re-run:  python cert_mod4.py --k-max 1000
The last stdout line is the machine-readable verdict the oracle reads.
"""
import argparse
import json
from fractions import Fraction


def solve(k: int):
    a = k + 1
    m = (4 * k + 3) * (k + 1)
    return a, m + 1, m * (m + 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k-max", type=int, default=1000)
    args = ap.parse_args()
    for k in range(args.k_max + 1):
        n = 4 * k + 3
        a, b, c = solve(k)
        if Fraction(4, n) != Fraction(1, a) + Fraction(1, b) + Fraction(1, c):
            print(json.dumps({"result": "fails", "counterexample": {"k": k, "n": n}}))
            return
    print(json.dumps({"result": "holds", "family": "n = 3 (mod 4)",
                      "instances_checked": args.k_max + 1, "max_n": 4 * args.k_max + 3}))


if __name__ == "__main__":
    main()
