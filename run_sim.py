# run_sim.py
import os
import sys
import subprocess
import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# ANSI colors for beautiful terminal output
COLOR_HEADER = "\033[95m"
COLOR_BLUE = "\033[94m"
COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

def log_info(msg):
    print(f"{COLOR_BLUE}[INFO]{COLOR_RESET} {msg}")

def log_success(msg):
    print(f"{COLOR_GREEN}[SUCCESS]{COLOR_RESET} {msg}")

def log_warning(msg):
    print(f"{COLOR_YELLOW}[WARNING]{COLOR_RESET} {msg}")

def log_error(msg):
    print(f"{COLOR_RED}[ERROR]{COLOR_RESET} {msg}")

def to_wsl_path(win_path):
    """Converts a Windows absolute path to a WSL path."""
    p = Path(win_path).resolve()
    parts = list(p.parts)
    if parts and (parts[0].endswith(':\\') or parts[0].endswith(':')):
        drive = parts[0][0].lower()
        # Join other parts using forward slashes
        wsl_path = f"/mnt/{drive}/" + "/".join(parts[1:])
    else:
        wsl_path = p.as_posix()
    return wsl_path

def find_gtkwave_windows(custom_path=None):
    """Locate the native Windows gtkwave.exe."""
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return str(p)
        log_warning(f"Custom GTKWave path not found: {custom_path}")

    # Check env var
    env_path = os.environ.get("GTKWAVE_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    # Check Windows host PATH
    which_path = shutil.which("gtkwave")
    if which_path:
        return which_path
    which_exe_path = shutil.which("gtkwave.exe")
    if which_exe_path:
        return which_exe_path

    # Check common installation locations
    standard_paths = [
        r"C:\gtkwave\bin\gtkwave.exe",
        r"C:\gtkwave\gtkwave.exe",
        r"C:\Program Files\gtkwave\bin\gtkwave.exe",
        r"C:\Program Files (x86)\gtkwave\bin\gtkwave.exe",
        r"C:\msys64\mingw64\bin\gtkwave.exe"
    ]
    for sp in standard_paths:
        if Path(sp).exists():
            return sp

    return None

def parse_results(results_xml_path):
    """Parse cocotb results.xml JUnit file."""
    if not os.path.exists(results_xml_path):
        return None

    try:
        tree = ET.parse(results_xml_path)
        root = tree.getroot()
        tests = []
        for suite in root.findall('.//testsuite'):
            for tc in suite.findall('.//testcase'):
                name = tc.get('name')
                time_val = tc.get('time') or "0.0"
                failure = tc.find('failure')
                
                if failure is not None:
                    status = "FAIL"
                    msg = failure.get('message') or "Assertion failed"
                    # Clean up long traceback outputs to keep summary concise
                    details = msg.split('\n')[0][:50]
                else:
                    status = "PASS"
                    details = "Success"
                
                tests.append({
                    'name': name,
                    'status': status,
                    'time': float(time_val),
                    'details': details
                })
        return tests
    except Exception as e:
        log_error(f"Failed to parse results.xml: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Hybrid Windows/WSL cocotb Simulation Runner")
    parser.add_argument("--view", action="store_true", help="Launch GTKWave to view waveforms on completion or failure")
    parser.add_argument("--gtkwave-path", type=str, help="Custom path to the native Windows gtkwave.exe")
    parser.add_argument("--clean", action="store_true", help="Run 'make clean' inside the simulation backend first")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    is_windows = sys.platform.startswith('win')

    log_info(f"Detected Platform: {'Windows' if is_windows else 'Linux/Unix'}")

    if is_windows:
        # Cross-environment path mapping
        wsl_script_dir = to_wsl_path(script_dir)
        log_info(f"Mapped Windows path '{script_dir}' to WSL '{wsl_script_dir}'")
        
        # Check for virtual environment inside WSL (either local .venv or sibling rtl_project .venv)
        local_venv = script_dir / ".venv"
        sibling_venv = script_dir.parent.parent / "rtl_project" / ".venv"
        
        if local_venv.exists():
            wsl_venv_path = to_wsl_path(local_venv)
            log_info(f"Using local virtual environment: {local_venv}")
        elif sibling_venv.exists():
            wsl_venv_path = to_wsl_path(sibling_venv)
            log_info(f"Using sibling project virtual environment: {sibling_venv}")
        else:
            wsl_venv_path = None
            log_warning("No Python virtual environment (.venv) found. Simulation will run using global WSL Python context.")

        # Construct WSL execution command
        cmd_parts = []
        if wsl_venv_path:
            cmd_parts.append(f"source {wsl_venv_path}/bin/activate")
        
        if args.clean:
            cmd_parts.append("make clean")
        cmd_parts.append("make")

        bash_cmd = " && ".join(cmd_parts)
        full_cmd = f'wsl -e bash -c "cd {wsl_script_dir} && {bash_cmd}"'
    else:
        # Native Linux/Unix CI context
        log_info("Running natively in Linux context (e.g. CI)")
        cmd_parts = []
        if args.clean:
            cmd_parts.append("make clean")
        cmd_parts.append("make")
        full_cmd = " && ".join(cmd_parts)

    log_info(f"Executing: {full_cmd}")
    
    # Run the simulation process
    process = subprocess.run(
        full_cmd,
        shell=True,
        cwd=script_dir if not is_windows else None,  # On Windows, wsl handles directories
        text=True
    )

    # Resolve results paths
    results_xml = script_dir / "results.xml"
    waveform_vcd = script_dir / "waveform.vcd"
    session_gtkw = script_dir / "session.gtkw"

    tests = parse_results(str(results_xml))
    
    # Determine test success
    simulation_success = (process.returncode == 0)
    testbench_success = False

    if tests:
        # Check if all individual testcases passed
        testbench_success = all(t['status'] == 'PASS' for t in tests)
        
        # Build beautiful ANSI summary table
        print("\n" + "="*80)
        print(f"{COLOR_BOLD}{COLOR_CYAN}                     RTL VERIFICATION SIMULATION RESULTS{COLOR_RESET}")
        print("="*80)
        print(f"{COLOR_BOLD}{'Test Case Name':<35} | {'Status':<6} | {'Time (ms)':<10} | {'Details':<20}{COLOR_RESET}")
        print("-"*80)
        
        for t in tests:
            status_color = COLOR_GREEN if t['status'] == 'PASS' else COLOR_RED
            status_str = f"{status_color}{t['status']:<6}{COLOR_RESET}"
            print(f"{t['name']:<35} | {status_str} | {t['time']*1000:<10.3f} | {t['details']}")
            
        print("="*80)
        total_tests = len(tests)
        passed_tests = sum(1 for t in tests if t['status'] == 'PASS')
        log_success(f"Verification completed. Passed: {passed_tests}/{total_tests}")
        print("="*80 + "\n")
    else:
        log_error("No test results found in results.xml! Check simulator compile or runtime logs.")
        testbench_success = False

    # Launch GTKWave if explicitly requested, or if tests failed and we are running locally on Windows
    should_launch_gtkwave = args.view or (not testbench_success and is_windows)
    
    if should_launch_gtkwave:
        if not is_windows:
            log_info("Waveform viewer auto-launch is only supported on Windows host system.")
        else:
            if not waveform_vcd.exists():
                log_error(f"Waveform file '{waveform_vcd}' not found! Cannot launch GTKWave.")
            else:
                gtkwave_exe = find_gtkwave_windows(args.gtkwave_path)
                if not gtkwave_exe:
                    log_error("GTKWave executable not found. Install GTKWave or set the --gtkwave-path parameter.")
                else:
                    log_info(f"Launching GTKWave: {gtkwave_exe}")
                    log_info(f"Loading VCD: {waveform_vcd}")
                    
                    # Launch GTKWave asynchronously
                    cmd = [gtkwave_exe, str(waveform_vcd)]
                    if session_gtkw.exists():
                        cmd.append(str(session_gtkw))
                        log_info(f"Loading GTKWave Session: {session_gtkw}")
                    
                    try:
                        subprocess.Popen(cmd, close_fds=True)
                        log_success("GTKWave launched successfully in background.")
                    except Exception as e:
                        log_error(f"Failed to start GTKWave: {e}")

    # Return final exit code
    if simulation_success and testbench_success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
