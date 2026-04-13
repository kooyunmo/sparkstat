import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

from sparkstat import __version__

RST = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
B_RED = "\033[1;31m"
B_GREEN = "\033[1;32m"
B_YELLOW = "\033[1;33m"
B_CYAN = "\033[1;36m"
B_WHITE = "\033[1;37m"

_color_enabled = True


def c(code: str, text: str) -> str:
    if not _color_enabled:
        return text
    return f"{code}{text}{RST}"


def color_pct_bar(pct: float, bar: str, pct_str: str) -> str:
    if not _color_enabled:
        return f"[{bar}] {pct_str}"
    bar_color = GREEN if pct < 50 else (YELLOW if pct < 80 else RED)
    filled_len = len(bar) - bar.count("░")
    empty_len = bar.count("░")
    colored_bar = c(bar_color, "█" * filled_len) + c(DIM, "░" * empty_len)
    return f"[{colored_bar}] {c(bar_color, pct_str)}"


def color_temp(temp: Optional[int]) -> str:
    if temp is None:
        return "   N/A"
    s = f"{temp:>4}°C"
    if not _color_enabled:
        return s
    if temp < 50:
        return c(CYAN, s)
    elif temp < 70:
        return c(YELLOW, s)
    else:
        return c(RED, s)


def color_util(util: Optional[int]) -> str:
    if util is None:
        return "  N/A"
    s = f"{util:>4}%"
    if not _color_enabled:
        return s
    if util < 10:
        return c(DIM, s)
    elif util < 50:
        return c(GREEN, s)
    elif util < 80:
        return c(YELLOW, s)
    else:
        return c(RED, s)


def color_alloc(pct: float) -> str:
    s = f"{pct:>3.0f}%"
    if not _color_enabled:
        return s
    if pct < 50:
        return c(GREEN, s)
    elif pct < 80:
        return c(YELLOW, s)
    else:
        return c(RED, s)


def fmt_mib(kib: int) -> str:
    mib = kib / 1024
    if mib >= 1024:
        return f"{mib / 1024:.1f}GiB"
    return f"{mib:.0f}MiB"


def fmt_pct(used: int, total: int) -> str:
    if total == 0:
        return "N/A"
    pct = used / total * 100
    bar_len = 10
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    pct_str = f"{pct:5.1f}%"
    return color_pct_bar(pct, bar, pct_str)


@dataclass
class MemInfo:
    total_kib: int
    available_kib: int
    swap_total_kib: int
    swap_free_kib: int
    hugepages_total: int = 0
    hugepages_free: int = 0
    hugepages_size_kib: int = 0


@dataclass
class GPUInfo:
    name: str
    utilization_gpu: Optional[int]
    utilization_mem: Optional[int]
    temperature: Optional[int]
    power_draw: Optional[float]
    power_limit: Optional[float]
    clock_sm: Optional[int]
    pstate: str


@dataclass
class GPUProcess:
    pid: int
    name: str
    used_memory_mib: int


def read_meminfo() -> MemInfo:
    info = {}
    with open("/proc/meminfo", "r") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                val = int(parts[1])
                info[key] = val

    return MemInfo(
        total_kib=info.get("MemTotal", 0),
        available_kib=info.get("MemAvailable", 0),
        swap_total_kib=info.get("SwapTotal", 0),
        swap_free_kib=info.get("SwapFree", 0),
        hugepages_total=info.get("HugePages_Total", 0),
        hugepages_free=info.get("HugePages_Free", 0),
        hugepages_size_kib=info.get("Hugepagesize", 0),
    )


def get_effective_available(mem: MemInfo) -> int:
    if mem.hugepages_total > 0 and mem.hugepages_size_kib > 0:
        return mem.hugepages_free * mem.hugepages_size_kib
    return mem.available_kib + mem.swap_free_kib


def query_gpu() -> GPUInfo:
    fields = [
        "name",
        "utilization.gpu",
        "utilization.memory",
        "temperature.gpu",
        "power.draw",
        "power.limit",
        "clocks.current.sm",
        "pstate",
    ]
    cmd = [
        "nvidia-smi",
        "--query-gpu=" + ",".join(fields),
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return GPUInfo("N/A", None, None, None, None, None, None, "N/A")

    if result.returncode != 0:
        return GPUInfo("N/A", None, None, None, None, None, None, "N/A")

    parts = [p.strip() for p in result.stdout.strip().split(",")]
    if len(parts) < len(fields):
        return GPUInfo("N/A", None, None, None, None, None, None, "N/A")

    def parse_int(s: str) -> Optional[int]:
        if s in ("[N/A]", "N/A", ""):
            return None
        try:
            return int(float(s))
        except ValueError:
            return None

    def parse_float(s: str) -> Optional[float]:
        if s in ("[N/A]", "N/A", ""):
            return None
        try:
            return float(s)
        except ValueError:
            return None

    return GPUInfo(
        name=parts[0],
        utilization_gpu=parse_int(parts[1]),
        utilization_mem=parse_int(parts[2]),
        temperature=parse_int(parts[3]),
        power_draw=parse_float(parts[4]),
        power_limit=parse_float(parts[5]),
        clock_sm=parse_int(parts[6]),
        pstate=parts[7] if parts[7] != "[N/A]" else "N/A",
    )


def query_processes() -> list[GPUProcess]:
    cmd = [
        "nvidia-smi",
        "--query-compute-apps=pid,process_name,used_gpu_memory",
        "--format=csv,noheader",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    procs = []
    for line in result.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            name = parts[1]
            mem_str = parts[2]
            mem_val = int(mem_str.replace("MiB", "").strip()) if "MiB" in mem_str else 0
            procs.append(GPUProcess(pid=pid, name=name, used_memory_mib=mem_val))
        except (ValueError, IndexError):
            continue
    return procs


def get_terminal_width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except (AttributeError, ValueError):
        return 80


def render_once(
    show_procs: bool = True,
    show_header: bool = False,
    width: int = 60,
) -> str:
    lines = []

    mem = read_meminfo()
    gpu = query_gpu()
    procs = query_processes() if show_procs else []

    used_kib = mem.total_kib - mem.available_kib
    effective_avail = get_effective_available(mem)
    swap_used_kib = mem.swap_total_kib - mem.swap_free_kib
    total_gpu_alloc_mib = sum(p.used_memory_mib for p in procs)

    total_dram_mib = mem.total_kib / 1024
    gpu_alloc_pct = (
        total_gpu_alloc_mib / total_dram_mib * 100 if total_dram_mib > 0 else 0.0
    )

    if show_header:
        hostname = os.uname().nodename.split(".")[0]
        ts = time.strftime("%a %b %d %H:%M:%S %Y")
        lines.append(
            f"{c(B_WHITE, hostname)}      {c(DIM, ts)}  {c(B_GREEN, gpu.name)}"
        )

    lines.append(c(DIM, "═" * width))
    lines.append(
        f" {c(B_WHITE, 'DGX Spark')}  ·  "
        f"{fmt_mib(mem.total_kib)} {c(DIM, 'Unified Memory (UMA)')}"
    )
    lines.append(c(DIM, "─" * width))
    lines.append(
        f" {c(B_WHITE, 'DRAM')}  {fmt_pct(used_kib, mem.total_kib)}  "
        f"{fmt_mib(used_kib)} / {fmt_mib(mem.total_kib)}"
    )
    lines.append(
        f" {c(B_WHITE, 'Avail')} {fmt_mib(effective_avail)}  "
        f"{
            c(
                DIM,
                f'(DRAM: {fmt_mib(mem.available_kib)}'
                f' + Swap free: {fmt_mib(mem.swap_free_kib)})',
            )
        }"
    )
    if mem.swap_total_kib > 0:
        lines.append(
            f" {c(B_WHITE, 'Swap')}  {fmt_pct(swap_used_kib, mem.swap_total_kib)}  "
            f"{fmt_mib(swap_used_kib)} / {fmt_mib(mem.swap_total_kib)}"
        )

    lines.append(c(DIM, "─" * width))
    lines.append(f" {c(B_WHITE, 'GPU')}   {c(B_GREEN, gpu.name)}")

    util_str = color_util(gpu.utilization_gpu)
    alloc_str = color_alloc(gpu_alloc_pct)
    temp_str = color_temp(gpu.temperature)
    power_str = f"{gpu.power_draw:.1f}W" if gpu.power_draw is not None else "    N/A"
    clock_str = f"{gpu.clock_sm}MHz" if gpu.clock_sm is not None else "      N/A"

    lines.append(
        f" {c(B_WHITE, 'Util')}  GPU{util_str}  │  Alloc {alloc_str}  │  "
        f"Temp {temp_str}"
    )
    lines.append(
        f" {c(B_WHITE, 'Pwr')}   {c(YELLOW, power_str):>7}  │  "
        f"Clk {c(CYAN, clock_str):>9}  │  "
        f"P-State {c(DIM, gpu.pstate)}"
    )

    if show_procs:
        lines.append(c(DIM, "─" * width))
        if procs:
            lines.append(
                f" {c(B_WHITE, 'Processes')}  "
                f"{c(DIM, f'({len(procs)} active,')}"
                f" {c(B_CYAN, f'{total_gpu_alloc_mib / 1024:.1f}GiB')}"
                f" {c(DIM, 'GPU alloc)')}"
            )
            for p in procs:
                lines.append(
                    f"   {c(DIM, f'{p.pid:>7}')}  "
                    f"{c(CYAN, f'{p.name:<30}')}  "
                    f"{p.used_memory_mib / 1024:.1f}GiB"
                )
        else:
            lines.append(f" {c(B_WHITE, 'Processes')}  {c(DIM, '(none)')}")

    lines.append(c(DIM, "═" * width))
    return "\n".join(lines)


def is_tty() -> bool:
    return sys.stdout.isatty()


def setup_color(args) -> None:
    global _color_enabled
    if args.force_color:
        _color_enabled = True
    elif args.no_color:
        _color_enabled = False
    else:
        _color_enabled = is_tty()


def main():
    parser = argparse.ArgumentParser(
        description="Real-time GPU monitor for NVIDIA DGX Spark and unified memory (UMA) systems",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-i",
        "--interval",
        nargs="?",
        type=float,
        default=None,
        const=3,
        help="Watch mode; seconds between updates (default: 3). Set 0 for single snapshot.",
    )
    parser.add_argument(
        "--no-proc",
        action="store_true",
        help="Hide per-process info",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Suppress timestamp header",
    )
    color_grp = parser.add_mutually_exclusive_group()
    color_grp.add_argument(
        "--force-color",
        action="store_true",
        help="Force color output even when piped",
    )
    color_grp.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output",
    )
    args = parser.parse_args()

    setup_color(args)
    show_procs = not args.no_proc
    show_header = not args.no_header

    if args.interval is None or args.interval <= 0:
        width = get_terminal_width() if is_tty() else 60
        print(render_once(show_procs, show_header=False, width=width))
        return

    tty = is_tty()

    try:
        while True:
            if tty:
                width = get_terminal_width()
                frame = render_once(show_procs, show_header=show_header, width=width)
                sys.stdout.write(f"\033[H\033[J{frame}")
                sys.stdout.flush()
            else:
                print(
                    render_once(show_procs, show_header=show_header, width=60),
                    flush=True,
                )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        if tty:
            sys.stdout.write("\033[H\033[J")
            sys.stdout.flush()
