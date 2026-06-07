#!/usr/bin/env python3
import math
import sys
import time


def progress_line(epoch, step, total_steps):
    pct = int(step * 100 / total_steps)
    width = 32
    filled = int(step * width / total_steps)
    bar = "#" * filled + "-" * (width - filled)
    loss = 1.0 / epoch + 0.08 * math.cos(step / 4)
    acc = min(99.0, 72.0 + epoch * 6 + step * 0.09)
    return (
        f"\rEpoch {epoch}/4 [{bar}] {pct:3d}% "
        f"step={step:03d}/{total_steps} loss={loss:.4f} acc={acc:.2f}%"
    )


def main():
    total_steps = 70
    print("Long progress test started", flush=True)
    print("This script emits normal logs and in-place progress updates.", flush=True)

    for epoch in range(1, 5):
        print(f"\nPreparing epoch {epoch}/4", flush=True)
        for step in range(total_steps + 1):
            sys.stdout.write(progress_line(epoch, step, total_steps))
            sys.stdout.flush()
            time.sleep(0.12)
        sys.stdout.write("\n")
        sys.stdout.flush()
        print(
            f"Epoch {epoch}/4 completed - checkpoint saved, validation queued",
            flush=True,
        )
        time.sleep(0.5)

    print("\nValidation summary", flush=True)
    for fold in range(1, 6):
        print(f"fold={fold} val_loss={0.42 / fold:.4f} val_acc={91 + fold * 0.7:.2f}%", flush=True)
        time.sleep(0.7)

    print("Long progress test done", flush=True)


if __name__ == "__main__":
    main()
