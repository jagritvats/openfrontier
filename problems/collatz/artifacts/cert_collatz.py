"""Certificate: every starting value 1 <= n <= LIMIT reaches 1 under the Collatz map.

Anyone can re-run:  python cert_collatz.py --limit 100000
The last stdout line is the machine-readable verdict the oracle reads.
Memoized step counts; deterministic.
"""
import argparse
import json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10_000_000)
    args = ap.parse_args()

    steps = {1: 0}
    max_steps, argmax = 0, 1
    for n in range(1, args.limit + 1):
        path = []
        x = n
        while x not in steps:
            path.append(x)
            x = x // 2 if x % 2 == 0 else 3 * x + 1
        s = steps[x]
        for x in reversed(path):
            s += 1
            steps[x] = s
        if steps[n] > max_steps:
            max_steps, argmax = steps[n], n

    print(json.dumps({"result": "holds", "bound": args.limit,
                      "max_steps": max_steps, "argmax": argmax}))


if __name__ == "__main__":
    main()
