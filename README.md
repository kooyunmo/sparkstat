# sparkstat

A real-time GPU monitor for NVIDIA DGX Spark and other unified memory architecture (UMA) systems.

Unlike `gpustat` or `nvidia-smi`, which report "Memory-Usage: Not Supported" on iGPU/UMA systems, `sparkstat` combines `nvidia-smi` metrics with `/proc/meminfo` to provide an accurate view of system memory available to GPU workloads.

## Key Features

*   **DRAM Monitoring**: Color-coded usage bars (green/yellow/red) based on severity.
*   **Effective Available Memory**: Calculates real GPU-allocatable memory (DRAM available + swap free).
*   **GPU Metrics**: Utilization, temperature (color-coded), power, clock speed, and P-State.
*   **Alloc Metric**: Reports GPU-allocated memory as a percentage of total DRAM, replacing the typically zeroed `utilization.memory` metric on iGPUs.
*   **Process Breakdown**: Per-process GPU memory allocation.
*   **Flexible Output**: Full-screen in-place refresh on TTY, sequential output when piped.
*   **Zero Dependencies**: Pure Python, using only the standard library.

## Requirements

*   Linux
*   Python 3.9+
*   NVIDIA driver (`nvidia-smi`)

## Installation

Install via pip:
```bash
pip install sparkstat
```

Install via pipx:
```bash
pipx install sparkstat
```

Install via uv:
```bash
uv tool install sparkstat
```

Quick install script:
```bash
curl -fsSL https://raw.githubusercontent.com/kooyunmo/sparkstat/main/install.sh | sh
```

## Usage

```bash
sparkstat           # Single snapshot
sparkstat -i        # Watch mode, default 3s interval
sparkstat -i 1      # Watch mode, 1s interval
sparkstat -i 0      # Single snapshot (same as no -i)
sparkstat --no-proc # Hide process list
sparkstat --no-header # Suppress timestamp header
sparkstat --no-color  # Disable color
sparkstat --force-color # Force color when piped
sparkstat -v        # Show version
```

## Example Output

```text
spark-838f      Fri Apr 10 01:05:26 2026  NVIDIA GB10
═════════════════════════════════════════════════════════
 DGX Spark  ·  121.7GiB Unified Memory (UMA)
───────────────────────────────────────────────────────
 DRAM  [█████░░░░░]  53.8%  65.5GiB / 121.7GiB
 Avail 69.3GiB  (DRAM: 56.2GiB + Swap free: 13.1GiB)
 Swap  [█░░░░░░░░░]  18.1%  2.9GiB / 16.0GiB
───────────────────────────────────────────────────────
 GPU   NVIDIA GB10
 Util  GPU    2%  │  Alloc  51%  │  Temp   46°C
 Pwr     13.2W  │  Clk   2411MHz  │  P-State P0
───────────────────────────────────────────────────────
 Processes  (1 active, 62.2GiB GPU alloc)
     62928  VLLM::EngineCore                62.2GiB
═════════════════════════════════════════════════════════
```

## Color Scheme

*   **Bars**: Green <50%, Yellow 50-80%, Red >80%
*   **Temperature**: Cyan <50°C, Yellow 50-70°C, Red >70°C
*   **GPU Utilization**: Dim <10%, Green 10-50%, Yellow 50-80%, Red >80%
*   **Labels**: Bold white
*   **GPU Name**: Bold green
*   **Process Names & Clock**: Cyan
*   **Power**: Yellow
*   **Borders**: Dim gray

Colors are automatically disabled when output is piped. Use `--force-color` to override this behavior.

## License

MIT

## Repository

https://github.com/kooyunmo/sparkstat
