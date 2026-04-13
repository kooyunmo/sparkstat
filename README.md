# sparkstat

Real-time GPU monitoring for NVIDIA DGX Spark and other unified memory (UMA) systems.

`sparkstat` fills the gap left by `nvidia-smi` and `gpustat` on iGPU/UMA machines. On these platforms, `nvidia-smi` typically reports “Memory-Usage: Not Supported” because iGPUs do not have dedicated framebuffer memory. By combining GPU metrics with `/proc/meminfo`, `sparkstat` shows memory that is actually available to GPU workloads.

![sparkstat screenshot](./assets/sparkstat.png)

## Requirements

- Linux
- Python 3.9+
- NVIDIA driver with `nvidia-smi`

## Install

```bash
pip install sparkstat
pipx install sparkstat
uv tool install sparkstat
curl -fsSL https://raw.githubusercontent.com/kooyunmo/sparkstat/main/install.sh | sh
```

## Usage

```bash
sparkstat           # Single snapshot
sparkstat -i        # Watch mode (3s interval)
sparkstat -i 1      # Watch mode (1s interval)
sparkstat --no-proc # Hide process list
```

## Example output

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

## What it shows

- DRAM and swap usage
- Effective available memory for GPU workloads
- GPU utilization, temperature, power, clock, and P-State
- Per-process GPU allocation

## License

MIT
