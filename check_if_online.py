# ================================ BEGIN SCRIPT ================================
# Wi-Fi Auto-Recover + Hotspot Launcher (Windows-only)
# Behavior:
#   1) Ping 1.1.1.1 and 8.8.8.8 (1 packet each, 2000 ms timeout). If either replies => "online".
#   2) If offline, disable and re-enable the "Wi-Fi" adapter exactly once.
#   3) Wait 5 seconds (visible countdown), then re-check connectivity.
#   4) If back online, open Mobile Hotspot Settings (cannot be toggled via CLI anymore).
#   5) Return to a simple menu: Run again or Exit.
#
# Notes:
#   - Requires Administrator rights (netsh needs elevation).
#   - No files are written; everything is printed to the console.
#   - Extremely verbose + heavily commented for learning purposes.

# ----------------------------- Standard Library ------------------------------
import subprocess  # Run external commands like ping, netsh, and "start ms-settings:..."
import time        # Sleep for countdowns and brief waits
import ctypes      # Windows API calls (for admin check + elevation prompt)
import sys         # Access argv, executable path, and exit
import os          # Included for completeness; not strictly required here but commonly useful

# ------------------------------- Configuration -------------------------------
PING_TARGETS = ["1.1.1.1", "8.8.8.8"]  # Two IPs = no DNS dependency; success if either replies
PING_COUNT = "1"                        # Exactly one ping attempt per target
PING_TIMEOUT_MS = "2000"                # 2000 ms timeout per ping (user-requested)
WIFI_ADAPTER_NAME = "Wi-Fi"             # Exact Windows default adapter name (capitalization + hyphen)
POST_TOGGLE_WAIT_SECONDS = 5            # Visible countdown after toggling before re-check
TOGGLE_ATTEMPTS = 1                     # Exactly one toggle cycle per run

# ------------------------- Console-printing Helpers --------------------------
def banner(text: str) -> None:
    """
    Prints a clear section banner to make the verbose output easy to read.
    """
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70 + "\n")

def info(msg: str) -> None:
    """
    Standard informational line.
    """
    print(f"[INFO] {msg}")

def ok(msg: str) -> None:
    """
    Positive confirmation line.
    """
    print(f"[ OK ] {msg}")

def warn(msg: str) -> None:
    """
    Warning line (not fatal).
    """
    print(f"[WARN] {msg}")

def err(msg: str) -> None:
    """
    Error line (may be fatal).
    """
    print(f"[ERR ] {msg}")

# ------------------------- Elevation (Administrator) -------------------------
def ensure_admin() -> None:
    """
    Confirms we are running with Administrator privileges. If not, relaunches
    this script with elevation via ShellExecuteW + the "runas" verb (triggers UAC).
    After launching the elevated copy, the current (non-admin) process exits.
    """
    try:
        # IsUserAnAdmin returns nonzero if the current token is elevated/admin.
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        # If the check fails for any reason, assume not admin.
        is_admin = False

    if not is_admin:
        warn("Administrator rights required. Requesting elevation (UAC prompt)...")
        # ShellExecuteW parameters:
        #   hwnd=None, lpOperation="runas" (elevate), lpFile=sys.executable (python.exe),
        #   lpParameters=" ".join(sys.argv) (script + args), lpDirectory=None, nShowCmd=1 (SW_SHOWNORMAL)
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        # Terminate this non-elevated instance; the elevated instance takes over.
        sys.exit(0)
    else:
        ok("Running with Administrator privileges.")

# ----------------------------- Connectivity Check ----------------------------
def check_connectivity() -> bool:
    """
    Pings each target in PING_TARGETS exactly once with a 2000 ms timeout.
    Returns True if ANY target replies (exit code 0); False if ALL fail.
    """
    banner("Connectivity Check (1 packet each, 2000 ms timeout)")
    for target in PING_TARGETS:
        info(f"Pinging {target} ...")
        # Windows ping syntax:
        #   -n 1      => send exactly one echo request
        #   -w 2000   => wait up to 2000 ms for a reply
        result = subprocess.run(
            ["ping", "-n", PING_COUNT, "-w", PING_TIMEOUT_MS, target],
            capture_output=True,   # capture stdout/stderr so we can parse or suppress if needed
            text=True              # decode output as text (str), not bytes
        )
        # On Windows, ping exit code 0 means at least one response was received.
        if result.returncode == 0:
            ok(f"{target} reachable (online).")
            return True
        else:
            warn(f"{target} did not respond. (This alone is not final yet.)")
    err("All targets failed to respond. Considered OFFLINE.")
    return False

# ------------------------------- Wi-Fi Toggling ------------------------------
def toggle_wifi_once() -> None:
    """
    Disables and then re-enables the Wi-Fi adapter exactly once using netsh.
    Uses a short 2-second pause between disable and enable to let Windows update state.
    """
    banner(f"Toggling Adapter '{WIFI_ADAPTER_NAME}' (1 cycle)")
    # Disable the adapter:
    info(f"Disabling '{WIFI_ADAPTER_NAME}' ...")
    # netsh interface set interface "Wi-Fi" admin=disabled
    subprocess.run(
        ["netsh", "interface", "set", "interface", WIFI_ADAPTER_NAME, "admin=disabled"]
    )
    # Brief pause to ensure the interface state changes fully before enabling again.
    time.sleep(2)

    # Enable the adapter:
    info(f"Enabling '{WIFI_ADAPTER_NAME}' ...")
    # netsh interface set interface "Wi-Fi" admin=enabled
    subprocess.run(
        ["netsh", "interface", "set", "interface", WIFI_ADAPTER_NAME, "admin=enabled"]
    )
    ok("Adapter disable/enable cycle complete.")

# ------------------------------- Countdown Wait ------------------------------
def countdown(seconds: int) -> None:
    """
    Visible countdown after toggling to give Windows a moment to reconnect.
    Writes over the same line using carriage returns; clears line when done.
    """
    info(f"Waiting {seconds} seconds before re-checking connectivity ...")
    for remaining in range(seconds, 0, -1):
        # end="\r" returns carriage to the start of the line and overwrites text on the next print
        print(f"  {remaining:2d} ", end="\r")
        time.sleep(1)
    # Clear the countdown line (print spaces, return to start)
    print(" " * 20, end="\r")
    ok("Wait complete.")

# -------------------------- Open Mobile Hotspot Page -------------------------
def open_hotspot_settings() -> None:
    """
    Opens the Windows 10/11 Settings page for Mobile Hotspot.
    We call 'start' via the shell so that Windows processes the ms-settings URI.
    (CLI hotspot enablement was deprecated; we can only open the UI.)
    """
    banner("Opening Mobile Hotspot Settings")
    info("Launching ms-settings:network-mobilehotspot ...")
    # Using shell=True so the shell can resolve the URI scheme "ms-settings:"
    # 'start' is a shell built-in; it won't work without shell=True here.
    subprocess.run(["start", "ms-settings:network-mobilehotspot"], shell=True)
    ok("Settings window launched (if supported by OS policy).")

# ------------------------------ One Full Run -------------------------------
def run_once() -> None:
    """
    Executes one full cycle:
      1) Check connectivity.
      2) If offline, toggle Wi-Fi once.
      3) Wait 5 seconds (countdown).
      4) Re-check connectivity.
      5) If online after recovery, open Hotspot Settings.
    """
    banner("Wi-Fi Auto-Recover: Start")
    # Step 1 — Initial connectivity check:
    if check_connectivity():
        info("Already online; no toggle needed.")
    else:
        # Step 2 — Toggle Wi-Fi exactly once:
        toggle_wifi_once()

        # Step 3 — Wait a bit before re-testing:
        countdown(POST_TOGGLE_WAIT_SECONDS)

        # Step 4 — Re-check connectivity:
        if check_connectivity():
            ok("Back online after toggle.")
            # Step 5 — Launch Hotspot settings, per requirement:
            open_hotspot_settings()
        else:
            err("Still offline after one toggle attempt.")

# ------------------------------ Main Menu Loop -------------------------------
def main() -> None:
    """
    Ensures admin rights, then provides a small loop with:
        R = run the recovery flow once
        E = exit
    The loop continues until the user chooses Exit.
    """
    banner("Privilege Check")
    ensure_admin()  # Elevate if necessary; returns only when running as admin.

    # Simple text UI loop:
    while True:
        banner("Menu")
        print("  (R) Run now")
        print("  (E) Exit")
        choice = input("\nSelect option: ").strip().lower()  # Read user choice; normalize to lowercase.

        if choice == "r":
            run_once()   # Execute one full recovery cycle (as described above).
        elif choice == "e":
            info("Exiting. Goodbye.")
            sys.exit(0)  # Exit with success code.
        else:
            warn("Invalid choice. Please enter 'R' or 'E'.")

# ------------------------------- Entry Point --------------------------------
if __name__ == "__main__":  # Ensures this block only runs when executed directly (not imported).
    main()                  # Start the program by invoking main().
# ================================= END SCRIPT ================================
