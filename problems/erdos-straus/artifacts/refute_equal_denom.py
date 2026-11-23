"""Certificate AGAINST the claim: "a solution with a = b = c exists for every n".

a = b = c forces 4/n = 3/a, i.e. a = 3n/4. The first failure is already at
n = 2, which would need a = 3/2. Refutations are results; this one is filed
with thanks.

Anyone can re-run:  python refute_equal_denom.py
The last stdout line is the machine-readable verdict the oracle reads.
"""
import json
from fractions import Fraction


def main() -> None:
    for n in range(2, 10_000):
        a = Fraction(3 * n, 4)
        if a.denominator != 1:
            print(json.dumps({"result": "fails",
                              "counterexample": {"n": n, "required_denominator": str(a)}}))
            return
    print(json.dumps({"result": "holds", "note": "unexpected: no counterexample below 10,000"}))


if __name__ == "__main__":
    main()
