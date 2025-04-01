import subprocess
import time
import argparse
import os
import sys
import shutil

# --- Configuration ---
# Default categories for Systrace (can be overridden)
DEFAULT_SYSTRACE_CATEGORIES = [
    "gfx", "input", "view", "wm", "am", "sched", "freq",
    "binder_driver", "binder_lock", "hal", "res", "dalvik", "app"
]

# Base Perfetto config (duration and app tracing will be added)
# Includes common categories useful for general performance and startup analysis
# Refer to https://perfetto.dev/docs/concepts/config for more options
DEFAULT_PERFETTO_CONFIG_TEMPLATE = """
buffers: {{
    size_kb: 63488 # 64MB buffer size
    fill_policy: RING_BUFFER
}}
buffers: {{
    size_kb: 2048  # Smaller buffer for less frequent metadata
    fill_policy: RING_BUFFER
}}
data_sources: {{
    config {{
        name: "linux.process_stats"
        target_buffer: 1
        process_stats_config {{
            scan_all_processes_on_start: true
        }}
    }}
}}
# --- Ftrace config: Add categories relevant to startup and rendering ---
data_sources: {{
    config {{
        name: "linux.ftrace"
        ftrace_config {{
            # Core scheduling and power events
            ftrace_events: "sched/sched_switch"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
            ftrace_events: "sched/sched_waking"
            ftrace_events: "sched/sched_wakeup_new"
            # App lifecycle events (might require specific Android versions/OEMs)
            ftrace_events: "am/am_activity_launch"
            ftrace_events: "am/am_proc_start"
            ftrace_events: "am/am_activity_resume"
            # Binder (IPC) tracing
            ftrace_events: "binder/binder_transaction"
            ftrace_events: "binder/binder_transaction_received"
            # Disk I/O
            ftrace_events: "ext4/ext4_sync_file_enter" # Example for ext4
            ftrace_events: "f2fs/f2fs_sync_file_enter" # Example for f2fs
            # Atrace categories mirror Systrace for high-level events
            atrace_categories: "gfx"           # Graphics
            atrace_categories: "view"          # View System / UI Toolkit
            atrace_categories: "input"         # Input Pipeline
            atrace_categories: "wm"            # Window Manager
            atrace_categories: "am"            # Activity Manager
            atrace_categories: "res"           # Resource Loading
            atrace_categories: "dalvik"        # ART/Dalvik VM Info
            atrace_categories: "sched"         # CPU Scheduling
            atrace_categories: "freq"          # CPU Frequency Scaling
            atrace_categories: "binder_driver" # Binder Kernel Driver
            atrace_categories: "binder_lock"   # Binder Lock Contention
            atrace_categories: "hal"           # Hardware Abstraction Layers
            # Add specific app to trace if provided
            {atrace_apps_config}
        }}
    }}
}}
# --- Trace duration placeholder ---
{duration_config}
# Optional: Add memory or other data sources if needed
# data_sources: { ... heapprofd config ... }
# data_sources: { ... android.gpu.memory ... }
"""

# --- Helper Functions ---

def run_command(cmd_list, capture_output=True, text=True, check=False, **kwargs):
    """Runs a command using subprocess and returns the result."""
    print(f"--- Executing: {' '.join(cmd_list)}")
    try:
        result = subprocess.run(cmd_list, capture_output=capture_output, text=text, check=check, **kwargs)
        if result.returncode != 0:
            print(f"--- WARNING: Command returned non-zero exit code {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(f"--- Stderr:\n{result.stderr}", file=sys.stderr)
        return result
    except FileNotFoundError:
        print(f"--- ERROR: Command not found: {cmd_list[0]}. Is it in your PATH?", file=sys.stderr)
        return None
    except Exception as e:
        print(f"--- ERROR executing command: {e}", file=sys.stderr)
        return None

def run_adb_command(adb_args, **kwargs):
    """Prepends 'adb' to the command list and runs it."""
    return run_command(['adb'] + adb_args, **kwargs)

def check_device_connected():
    """Checks if an ADB device is connected and authorized."""
    result = run_adb_command(['devices'])
    if result is None or result.returncode != 0:
        return False
    # Output format:
    # List of devices attached
    # emulator-5554	device
    # <serial>      offline|unauthorized|device
    lines = result.stdout.strip().splitlines()
    if len(lines) <= 1:
        print("--- ERROR: No ADB devices found. Ensure device is connected and USB Debugging is enabled.", file=sys.stderr)
        return False
    for line in lines[1:]: # Skip header line
        if '\tdevice' in line:
            print(f"--- Found device: {line.split()[0]}")
            return True
    print("--- ERROR: No authorized ADB device found. Check device screen for authorization prompt.", file=sys.stderr)
    return False

def find_systrace_script(systrace_path_hint=None):
    """Tries to find systrace.py."""
    # 1. Use provided hint
    if systrace_path_hint and os.path.isfile(systrace_path_hint) and systrace_path_hint.endswith('systrace.py'):
        print(f"--- Using provided systrace path: {systrace_path_hint}")
        return systrace_path_hint

    # 2. Check common locations (Android SDK platform-tools)
    sdk_root = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    if sdk_root:
        potential_path = os.path.join(sdk_root, 'platform-tools', 'systrace', 'systrace.py')
        if os.path.isfile(potential_path):
            print(f"--- Found systrace.py in SDK: {potential_path}")
            return potential_path

    # 3. Check system PATH (less common for systrace.py)
    systrace_in_path = shutil.which('systrace.py')
    if systrace_in_path:
         print(f"--- Found systrace.py in PATH: {systrace_in_path}")
         return systrace_in_path

    print("--- ERROR: Could not automatically find systrace.py.", file=sys.stderr)
    print("--- Please install Android SDK Platform-Tools and ensure ANDROID_HOME is set,", file=sys.stderr)
    print("--- or provide the path using the --systrace-path argument.", file=sys.stderr)
    return None

def force_stop_app(package_name):
    """Forces the target application to stop for a cold start."""
    print(f"--- Force stopping app: {package_name}")
    run_adb_command(['shell', 'am', 'force-stop', package_name])
    time.sleep(1) # Give system a moment to settle

def launch_app(package_name, activity_name):
    """Launches the specified activity."""
    print(f"--- Launching: {package_name}/{activity_name}")
    # -S: Force stop before launch (redundant if force_stop_app was called, but safe)
    # -W: Wait for launch to complete (optional here, as trace runs for fixed duration)
    # --activity-clear-task: Ensure a new task is created
    component = f"{package_name}/{activity_name}"
    run_adb_command(['shell', 'am', 'start', '-S', '-W', '--activity-clear-task', component])
    print("--- App launch command sent.")

# --- Tracing Functions ---

def run_perfetto_trace(package_name, duration_s, output_file):
    """Runs Perfetto tracing on the device."""
    print("--- Starting Perfetto trace...")
    device_trace_path = "/data/misc/perfetto-traces/perfetto_trace.pftrace" # Standard location
    duration_ms = duration_s * 1000

    # Prepare Perfetto config
    duration_config = f"duration_ms: {duration_ms}"
    atrace_apps_config = ""
    if package_name:
         # Note: Ensure your app uses android.os.Trace for app-level sections to appear
         atrace_apps_config = f'atrace_apps: "{package_name}"'

    perfetto_config = DEFAULT_PERFETTO_CONFIG_TEMPLATE.format(
        duration_config=duration_config,
        atrace_apps_config=atrace_apps_config
    ).strip()

    # Command to start tracing on device. This command blocks until tracing is done.
    cmd = [
        'shell', 'perfetto',
        '-c', '-', # Read config from stdin
        '--txt',   # Input config is text proto
        '-o', device_trace_path
    ]

    # Run the command, feeding the config via stdin
    perfetto_proc = run_adb_command(cmd, stdin=perfetto_config, check=False) # Don't check=True as it might return non-zero sometimes

    if perfetto_proc is None or (perfetto_proc.returncode != 0 and "Tracer FAILED" in (perfetto_proc.stderr or "")):
        print("--- ERROR: Perfetto tracing failed to start or execute properly on device.", file=sys.stderr)
        return False

    print(f"--- Perfetto trace completed on device. Trace duration: {duration_s}s")

    # Pull the trace file
    print(f"--- Pulling trace file from {device_trace_path} to {output_file}")
    pull_result = run_adb_command(['pull', device_trace_path, output_file])
    if pull_result is None or pull_result.returncode != 0 or "error" in (pull_result.stderr or "").lower():
         print(f"--- ERROR: Failed to pull Perfetto trace file from device.", file=sys.stderr)
         # Attempt to remove the device file anyway if pull failed partially
         run_adb_command(['shell', 'rm', device_trace_path])
         return False

    # Clean up trace file on device
    print(f"--- Cleaning up trace file on device: {device_trace_path}")
    run_adb_command(['shell', 'rm', device_trace_path])

    print(f"--- Perfetto trace saved successfully to: {output_file}")
    return True


def run_systrace_trace(package_name, duration_s, output_file, systrace_script_path, categories):
    """Runs Systrace using the systrace.py script."""
    print("--- Starting Systrace trace...")

    if not systrace_script_path:
        systrace_script_path = find_systrace_script()
        if not systrace_script_path:
            return False # Error message already printed

    # Build the command
    # Note: systrace.py is often Python 2, but recent versions might support Python 3
    # Try 'python' first, which might resolve to python3 or python2 depending on system.
    python_executable = sys.executable # Use the same python running this script
    cmd = [
        python_executable,
        systrace_script_path,
        '--time', str(duration_s),
        '-o', output_file
    ]
    if package_name:
        cmd.extend(['-a', package_name]) # Trace specific app

    # Add categories (filter out 'app' if package_name is not provided)
    trace_categories = categories[:] # Copy list
    if not package_name and 'app' in trace_categories:
        trace_categories.remove('app')
    cmd.extend(trace_categories)

    # Systrace runs for the specified duration and then exits
    systrace_result = run_command(cmd, check=False) # Don't check, handle errors manually

    if systrace_result is None or systrace_result.returncode != 0:
        print("--- ERROR: Systrace execution failed.", file=sys.stderr)
        if systrace_result and systrace_result.stderr:
             # Provide more specific feedback if possible
             if "No such file or directory" in systrace_result.stderr and python_executable == 'python':
                  print("--- Hint: Try specifying 'python2' or 'python3' explicitly if 'python' is not correct.", file=sys.stderr)
             elif "No devices found" in systrace_result.stderr:
                  print("--- Hint: Ensure device is connected and authorized via ADB.", file=sys.stderr)
        return False
    elif "Unable to find package" in (systrace_result.stdout or ""):
         print(f"--- ERROR: Systrace could not find the package '{package_name}'. Is it installed?", file=sys.stderr)
         # Clean up potentially empty/invalid trace file
         if os.path.exists(output_file):
            os.remove(output_file)
         return False


    print(f"--- Systrace trace saved successfully to: {output_file}")
    return True

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Run Perfetto or Systrace for Android app performance analysis.")
    parser.add_argument("-p", "--package", required=True, help="Package name of the target application (e.g., com.example.app).")
    parser.add_argument("-a", "--activity", required=True, help="Fully qualified name of the main activity to launch (e.g., .MainActivity or com.example.app.MainActivity).")
    parser.add_argument("-t", "--tool", choices=['perfetto', 'systrace'], default='perfetto', help="Tracing tool to use (default: perfetto).")
    parser.add_argument("-d", "--duration", type=int, default=10, help="Duration of the trace in seconds (default: 10).")
    parser.add_argument("--perfetto-out", default="perfetto_trace.pftrace", help="Output filename for Perfetto trace (default: perfetto_trace.pftrace).")
    parser.add_argument("--systrace-out", default="systrace_trace.html", help="Output filename for Systrace trace (default: systrace_trace.html).")
    parser.add_argument("--systrace-path", help="Explicit path to systrace.py script (optional, attempts auto-detection).")
    parser.add_argument("--systrace-categories", nargs='+', default=DEFAULT_SYSTRACE_CATEGORIES, help=f"Space-separated list of Systrace categories (default: {' '.join(DEFAULT_SYSTRACE_CATEGORIES)}).")
    parser.add_argument("--skip-launch", action="store_true", help="Skip force-stopping and launching the app (useful if app is already running).")

    args = parser.parse_args()

    # --- Pre-flight Checks ---
    if not check_device_connected():
        sys.exit(1)

    systrace_script_path = args.systrace_path
    if args.tool == 'systrace' and not systrace_script_path:
        systrace_script_path = find_systrace_script()
        if not systrace_script_path:
             sys.exit(1)

    # --- Prepare App (Cold Start) ---
    if not args.skip_launch:
        force_stop_app(args.package)
        # Add a small delay AFTER force-stop and BEFORE starting trace/launch
        time.sleep(1)


    # --- Start Tracing ---
    trace_started = False
    if args.tool == 'perfetto':
        print("\n=== Starting Perfetto Test ===")
        trace_started = run_perfetto_trace(args.package, args.duration, args.perfetto_out)

    elif args.tool == 'systrace':
        print("\n=== Starting Systrace Test ===")
        # Systrace needs app launch DURING tracing window
        # Start systrace command (it will run for args.duration)
        # We will launch the app immediately after starting the trace process
        python_executable = sys.executable
        cmd = [
            python_executable,
            systrace_script_path,
            '--time', str(args.duration),
            '-o', args.systrace_out
        ]
        if args.package:
            cmd.extend(['-a', args.package])
        
        trace_categories = args.systrace_categories[:] # Copy list
        if not args.package and 'app' in trace_categories:
            trace_categories.remove('app')
        cmd.extend(trace_categories)

        print(f"--- Starting Systrace process (will run for {args.duration}s)...")
        # Run Systrace in the background conceptually (subprocess.run blocks, but that's okay)
        # We launch the app while it's running
        systrace_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        trace_started = True # Assume started, will check result later
        print("--- Systrace process initiated.")
        time.sleep(1) # Give systrace a moment to initialize fully before launch

    else:
        print(f"--- ERROR: Unknown tool '{args.tool}'", file=sys.stderr)
        sys.exit(1)

    # --- Launch App (if trace started successfully and not skipping) ---
    if trace_started and not args.skip_launch:
        launch_app(args.package, args.activity)
    elif not trace_started:
        print("--- Skipping app launch because tracing failed to start.", file=sys.stderr)
        if args.tool == 'systrace' and 'systrace_proc' in locals():
             systrace_proc.terminate() # Terminate if it was started but failed conceptually
        sys.exit(1)


    # --- Wait for Trace Completion & Collect Results ---
    if args.tool == 'perfetto':
        # Perfetto function already handled waiting and pulling
        print("\n=== Perfetto Test Finished ===")
        print(f"Trace file: {args.perfetto_out}")
        print("Analyze using: https://ui.perfetto.dev/")

    elif args.tool == 'systrace':
        print(f"--- Waiting for Systrace process to complete (max {args.duration}s)...")
        try:
            stdout, stderr = systrace_proc.communicate(timeout=args.duration + 10) # Wait a bit longer than duration
            print("--- Systrace process finished.")
            if systrace_proc.returncode != 0:
                 print(f"--- ERROR: Systrace exited with code {systrace_proc.returncode}", file=sys.stderr)
                 print(f"--- Stdout:\n{stdout}", file=sys.stderr)
                 print(f"--- Stderr:\n{stderr}", file=sys.stderr)
                 if os.path.exists(args.systrace_out): # Clean up partial/failed trace
                    try: os.remove(args.systrace_out)
                    except OSError: pass
                 sys.exit(1)
            elif "Unable to find package" in stdout:
                 print(f"--- ERROR: Systrace could not find package '{args.package}'.", file=sys.stderr)
                 if os.path.exists(args.systrace_out): # Clean up partial/failed trace
                    try: os.remove(args.systrace_out)
                    except OSError: pass
                 sys.exit(1)

            print("\n=== Systrace Test Finished ===")
            print(f"Trace file: {args.systrace_out}")
            print("Analyze using Chrome browser: chrome://tracing")

        except subprocess.TimeoutExpired:
            print("--- ERROR: Systrace process timed out. Terminating.", file=sys.stderr)
            systrace_proc.kill()
            stdout, stderr = systrace_proc.communicate()
            sys.exit(1)
        except Exception as e:
             print(f"--- ERROR interacting with Systrace process: {e}", file=sys.stderr)
             systrace_proc.kill()
             sys.exit(1)


if __name__ == "__main__":
    main()