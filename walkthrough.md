# RTL Verification Pipeline Walkthrough

We have successfully built and verified the automated, cross-environment RTL verification pipeline. The environment enables running Python-based `cocotb` tests against an Icarus Verilog design inside WSL from a Windows host command line, automatically printing a beautiful summary, and natively launching Windows GTKWave to view waveforms.

## Scaffolding & Directory Structure

All verification assets are scaffolded under `src/rtl_verification/`:

```
src/rtl_verification/
├── design.v          # Parameterizable Synchronous ALU
├── test_design.py    # cocotb Python Testbench with Edge & Randomized Tests
├── Makefile          # cocotb Makefile targeting iverilog
├── run_sim.py        # Windows Host Orchestrator & Results Parser
└── session.gtkw      # Pre-saved GTKWave layout configuration
```

Additionally, the CI/CD pipeline has been created in:
```
.github/workflows/
└── rtl_ci.yml        # GitHub Actions runner configuration
```

---

## 1. Verilog Design & cocotb Testbench

The ALU in [design.v](file:///C:/Users/NEAL/VLSI_PORTFOLIO/src/rtl_verification/design.v) is fully parameterized and clocked. It implements 12 distinct operations (arithmetic, logical, shifts, and signed comparisons) and registers its outputs (`result`, `carry_out`, `zero`, `overflow`, `negative`).

The cocotb testbench in [test_design.py](file:///C:/Users/NEAL/VLSI_PORTFOLIO/src/rtl_verification/test_design.py) contains 7 verification tasks:
1. `test_reset_state`: Asserts reset and verifies outputs go to 0.
2. `test_enable_gate`: Verifies outputs hold state when `en` is low.
3. `test_arithmetic_ops`: Validates addition, subtraction, carry, and signed overflows.
4. `test_logical_ops`: Tests bitwise AND, OR, XOR, NOT.
5. `test_shift_ops`: Validates shifts (LSL, LSR, and sign-extended ASR).
6. `test_comparison_ops`: Tests EQ, GT, LT signed comparisons.
7. `test_randomized_fuzzing`: Runs 100 randomized inputs, asserting outputs against a Python reference model.

> [!NOTE]
> To eliminate race conditions and avoid the cocotb `ReadOnly` phase exception, the testbench drives inputs on the `FallingEdge(clk)` and asserts outputs on the `RisingEdge(clk)` after a delta delay.

---

## 2. Windows/WSL Cross-Environment Runner

The orchestrator in [run_sim.py](file:///C:/Users/NEAL/VLSI_PORTFOLIO/src/rtl_verification/run_sim.py) dynamically detects the platform:
- **On Windows**: It converts the current Windows folder path to a WSL mount (e.g. `/mnt/c/...`), finds the Python virtual environment under `/mnt/c/Users/NEAL/VLSI_PORTFOLIO/rtl_project/.venv`, activates it, and executes `make` inside WSL.
- **On Linux (CI)**: It runs `make` natively in the local terminal.

It parses `results.xml` to display a clean summary table of test runs:

```ansi
================================================================================
                     RTL VERIFICATION SIMULATION RESULTS
================================================================================
Test Case Name                      | Status | Time (ms)  | Details             
--------------------------------------------------------------------------------
test_reset_state                    | PASS   | 3.411      | Success
test_enable_gate                    | PASS   | 1.152      | Success
test_arithmetic_ops                 | PASS   | 1.408      | Success
test_logical_ops                    | PASS   | 1.181      | Success
test_shift_ops                      | PASS   | 2.231      | Success
test_comparison_ops                 | PASS   | 1.235      | Success
test_randomized_fuzzing             | PASS   | 17.311     | Success
================================================================================
[SUCCESS] Verification completed. Passed: 7/7
================================================================================
```

---

## 3. GTKWave Integration

During the simulation, Icarus Verilog outputs a `waveform.vcd` tracing file in `src/rtl_verification/`.

If a test fails, or if the runner is called with `--view`, the runner resolves the native Windows GTKWave executable path by checking:
1. Environment variables (`GTKWAVE_PATH`) or user override `--gtkwave-path`.
2. Windows `%PATH%`.
3. Common installation paths (e.g., `C:\gtkwave\bin\gtkwave.exe` or `C:\Program Files\gtkwave\bin\gtkwave.exe`).

It then spawns Windows GTKWave asynchronously:
```bash
gtkwave.exe src/rtl_verification/waveform.vcd src/rtl_verification/session.gtkw
```
This automatically opens the waveform viewer with the clock, operands, result, and flags populated in the viewer, matching the pre-saved session configuration.

---

## 4. GitHub Actions CI/CD Pipeline

The [.github/workflows/rtl_ci.yml](file:///C:/Users/NEAL/VLSI_PORTFOLIO/.github/workflows/rtl_ci.yml) workflow:
- Spins up an Ubuntu runner.
- Installs `iverilog` and `make`.
- Sets up Python and pip-installs `cocotb`, `cocotb-bus`, and `pytest`.
- Runs `python src/rtl_verification/run_sim.py` which executes the testbench natively.
- Blocks pull requests if any test fails by forwarding the runner's exit code.
