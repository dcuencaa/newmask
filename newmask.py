import os
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog

# Define paths
CONFIG_DIR = Path.home() / ".newmask_profiles"
HOSTS_FILE = Path("/etc/hosts")

DEFAULT_TEMPLATE = """##
# Host Database
#
# localhost is used to configure the loopback interface
# when the system is booting.  Do not change this entry.
##
127.0.0.1        localhost
255.255.255.255  broadcasthost
::1              localhost
"""

class HostsManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NewMask - Hosts Manager")
        self.root.geometry("800x500")

        # Ensure config directory exists
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        self.current_profile = None

        # Capture current /etc/hosts on first run
        self.initialize_original_profile()

        self.setup_ui()
        self.load_profiles()

    def initialize_original_profile(self):
        original_profile_path = CONFIG_DIR / "original profile.txt"
        
        # Only create it if it doesn't already exist
        if not original_profile_path.exists():
            try:
                with open(HOSTS_FILE, "r") as f:
                    current_hosts_content = f.read()
                    
                with open(original_profile_path, "w") as f:
                    f.write(current_hosts_content)
            except Exception as e:
                print(f"Failed to read original /etc/hosts: {e}")

    def get_active_profile_name(self):
        """Compares /etc/hosts to saved profiles to see which is active."""
        try:
            with open(HOSTS_FILE, "r") as f:
                system_hosts_content = f.read()
                
            for file in CONFIG_DIR.glob("*.txt"):
                with open(file, "r") as f:
                    if f.read() == system_hosts_content:
                        return file.stem
        except Exception:
            pass
        return None

    def setup_ui(self):
        # Left Panel - Profile List
        self.left_frame = tk.Frame(self.root, width=200, bg="#f0f0f0")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(self.left_frame, text="Profiles", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(pady=5)

        self.profile_listbox = tk.Listbox(self.left_frame, width=25, height=20, selectbackground="#0078D7", selectforeground="white")
        self.profile_listbox.pack(fill=tk.Y, expand=True)
        self.profile_listbox.bind("<<ListboxSelect>>", self.on_profile_select)

        self.btn_new = tk.Button(self.left_frame, text="New Profile", command=self.create_profile)
        self.btn_new.pack(fill=tk.X, pady=5)

        # Right Panel - Editor
        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.lbl_current = tk.Label(self.right_frame, text="No profile selected", font=("Arial", 12, "bold"))
        self.lbl_current.pack(anchor=tk.W, pady=5)

        self.text_editor = tk.Text(self.right_frame, wrap=tk.WORD, undo=True)
        self.text_editor.pack(fill=tk.BOTH, expand=True)

        # Bottom Buttons (Right Panel)
        self.btn_frame = tk.Frame(self.right_frame)
        self.btn_frame.pack(fill=tk.X, pady=10)

        self.btn_save = tk.Button(self.btn_frame, text="Save Profile", command=self.save_profile)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.btn_activate = tk.Button(self.btn_frame, text="Activate", command=self.activate_profile, bg="#a4de99")
        self.btn_activate.pack(side=tk.RIGHT, padx=5)

    def load_profiles(self):
        # Remember the currently selected profile so we don't lose focus on reload
        current_selection_name = None
        selection = self.profile_listbox.curselection()
        if selection:
            current_selection_name = self.profile_listbox.get(selection[0])

        self.profile_listbox.delete(0, tk.END)
        active_profile_name = self.get_active_profile_name()

        for idx, file in enumerate(sorted(CONFIG_DIR.glob("*.txt"))):
            name = file.stem
            self.profile_listbox.insert(tk.END, name)
            
            # Highlight the active profile in green
            if name == active_profile_name:
                self.profile_listbox.itemconfig(idx, {'bg': '#a4de99'})
                
            # Restore previous selection
            if name == current_selection_name:
                self.profile_listbox.selection_set(idx)

    def on_profile_select(self, event):
        selection = self.profile_listbox.curselection()
        if not selection:
            return
        
        profile_name = self.profile_listbox.get(selection[0])
        self.current_profile = CONFIG_DIR / f"{profile_name}.txt"
        
        self.lbl_current.config(text=f"Editing: {profile_name}")
        
        with open(self.current_profile, "r") as f:
            content = f.read()
            
        self.text_editor.delete(1.0, tk.END)
        self.text_editor.insert(tk.END, content)

    def create_profile(self):
        name = simpledialog.askstring("New Profile", "Enter profile name:")
        if not name:
            return
            
        new_file = CONFIG_DIR / f"{name}.txt"
        if new_file.exists():
            messagebox.showerror("Error", "A profile with this name already exists.")
            return

        with open(new_file, "w") as f:
            f.write(DEFAULT_TEMPLATE)
            
        self.load_profiles()
        
        # Auto-select the new profile
        idx = self.profile_listbox.get(0, tk.END).index(name)
        self.profile_listbox.selection_clear(0, tk.END)
        self.profile_listbox.selection_set(idx)
        self.profile_listbox.event_generate("<<ListboxSelect>>")

    def save_profile(self):
        if not self.current_profile:
            messagebox.showwarning("Warning", "No profile selected to save.")
            return
            
        content = self.text_editor.get(1.0, tk.END).strip() + "\n"
        with open(self.current_profile, "w") as f:
            f.write(content)
            
        # Refresh colors in case the saved profile now matches /etc/hosts
        self.load_profiles()
        messagebox.showinfo("Success", "Profile saved successfully.")

    def activate_profile(self):
        if not self.current_profile:
            messagebox.showwarning("Warning", "No profile selected to activate.")
            return
            
        # Ensure we save any unsaved changes before activating
        self.save_profile()
        
        # Check for root privileges (required to write to /etc/hosts)
        if os.geteuid() != 0:
            messagebox.showerror(
                "Permission Denied", 
                "You must run this script as root (sudo) to activate a hosts file.\n\n"
                "Try running: sudo python3 newmask_clone.py"
            )
            return

        try:
            shutil.copy2(self.current_profile, HOSTS_FILE)
            # Fix permissions just in case
            os.chmod(HOSTS_FILE, 0o644)
            
            # Refresh listbox to apply the green highlight to the newly activated profile
            self.load_profiles()
            
            messagebox.showinfo("Success", f"Profile '{self.current_profile.stem}' activated!\n/etc/hosts updated.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update /etc/hosts:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = HostsManagerApp(root)
    root.mainloop()