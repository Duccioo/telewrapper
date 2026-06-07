#!/usr/bin/env python3
import math
import sys
import time


def sleep_tick(seconds=0.08):
    time.sleep(seconds)


def simple_bar(label, step, total, width=28):
    pct = int(step * 100 / total)
    filled = int(step * width / total)
    bar = "#" * filled + "-" * (width - filled)
    return f"\r{label:<14} [{bar}] {pct:3d}% {step:03d}/{total}"


def metric_bar(epoch, step, total_steps):
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


def run_spinner_section():
    print("\n[1/5] Manual spinner with carriage returns", flush=True)
    frames = "|/-\\"
    for idx in range(80):
        sys.stdout.write(f"\rIndexing files {frames[idx % len(frames)]} item={idx:03d}")
        sys.stdout.flush()
        sleep_tick(0.05)
    sys.stdout.write("\rIndexing files done                 \n")
    sys.stdout.flush()


def run_single_bar_section():
    print("\n[2/5] Manual single-line progress bar", flush=True)
    total = 90
    for step in range(total + 1):
        sys.stdout.write(simple_bar("download", step, total))
        sys.stdout.flush()
        sleep_tick(0.055)
    sys.stdout.write("\nDownload completed\n")
    sys.stdout.flush()


def run_metric_bar_section():
    print("\n[3/5] Training-style progress with metrics", flush=True)
    total_steps = 55
    for epoch in range(1, 5):
        print(f"\nPreparing epoch {epoch}/4", flush=True)
        for step in range(total_steps + 1):
            sys.stdout.write(metric_bar(epoch, step, total_steps))
            sys.stdout.flush()
            sleep_tick(0.07)
        sys.stdout.write("\n")
        sys.stdout.flush()
        print(
            f"Epoch {epoch}/4 completed - checkpoint saved, validation queued",
            flush=True,
        )
        sleep_tick(0.25)


def run_multiline_terminal_section():
    print("\n[4/5] Manual multi-line dashboard using cursor-up", flush=True)
    print("loader       [--------------------]   0%")
    print("preprocess   [--------------------]   0%")
    print("trainer      [--------------------]   0%")
    for step in range(41):
        loader = min(100, step * 4)
        preprocess = min(100, max(0, (step - 8) * 4))
        trainer = min(100, max(0, (step - 16) * 4))
        rows = [
            simple_bar("loader", loader, 100, width=20).lstrip("\r"),
            simple_bar("preprocess", preprocess, 100, width=20).lstrip("\r"),
            simple_bar("trainer", trainer, 100, width=20).lstrip("\r"),
        ]
        sys.stdout.write("\x1b[3A")
        sys.stdout.write("\x1b[2K" + rows[0] + "\n")
        sys.stdout.write("\x1b[2K" + rows[1] + "\n")
        sys.stdout.write("\x1b[2K" + rows[2] + "\n")
        sys.stdout.flush()
        sleep_tick(0.10)
    print("Manual multi-line dashboard completed", flush=True)


def run_rich_section():
    print("\n[5/5] Rich progress bars", flush=True)
    try:
        from rich.console import Console
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
        )
    except ImportError:
        print("Rich is not installed; install it with: pip install rich", flush=True)
        return

    console = Console(force_terminal=True, color_system="standard", width=100)
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
        refresh_per_second=8,
    )

    with progress:
        download = progress.add_task("rich download", total=90)
        preprocess = progress.add_task("rich preprocess", total=70)
        train = progress.add_task("rich train", total=110)

        for step in range(120):
            if not progress.finished:
                if step < 90:
                    progress.update(download, advance=1)
                if 20 <= step < 90:
                    progress.update(preprocess, advance=1)
                if 45 <= step < 115:
                    progress.update(train, advance=1)
            sleep_tick(0.07)

        progress.update(download, completed=90)
        progress.update(preprocess, completed=70)
        progress.update(train, completed=110)

    console.print("[green]Rich progress section completed[/green]")


def run_validation_summary():
    print("\nValidation summary", flush=True)
    for fold in range(1, 6):
        print(
            f"fold={fold} val_loss={0.42 / fold:.4f} val_acc={91 + fold * 0.7:.2f}%",
            flush=True,
        )
        sleep_tick(0.35)


def main():
    print("Long progress test started", flush=True)
    print(
        "This script emits normal logs, CR progress bars, cursor-up dashboards, and Rich output.",
        flush=True,
    )

    run_spinner_section()
    run_single_bar_section()
    run_metric_bar_section()
    run_multiline_terminal_section()
    run_rich_section()
    run_validation_summary()

    print("Long progress test done", flush=True)


if __name__ == "__main__":
    main()
