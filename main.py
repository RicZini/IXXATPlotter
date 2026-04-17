import tkinter as tk
from tkinter import ttk
import logging
import argparse
import sys
import os
import matplotlib.pyplot as plt

from src.candb_selector import CanDbSelectorApp

def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource. 
    This is required for PyInstaller, which unpacks assets into a temporary _MEIPASS folder.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # If running as a standard Python script, use the current directory
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def setup_professional_environment():
    """
    Configures global graphical settings for Matplotlib 
    to give plots a professional telemetry software appearance.
    """
    try:
        plt.style.use('ggplot')
    except Exception:
        pass 
        
    plt.rcParams['figure.autolayout'] = True
    plt.rcParams['lines.linewidth'] = 1.5
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['figure.facecolor'] = '#f4f4f4'
    plt.rcParams['axes.facecolor'] = '#ffffff'

class SplashScreen(tk.Toplevel):
    """
    A borderless window that appears while the main application is loading.
    """
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Loading...")
        
        # Remove standard window borders and title bar
        self.overrideredirect(True)
        
        # Define splash screen dimensions (Increased to prevent cutting off images)
        width = 350
        height = 350
        
        # Center the splash screen on the user's monitor
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.geometry(f'{width}x{height}+{int(x)}+{int(y)}')
        
        # Professional dark theme background
        bg_color = '#2c3e50'
        self.configure(bg=bg_color)
        
        # --- UPDATE YOUR NAME HERE ---
        DEVELOPER_NAME = "Riccardo Zini x UBM-EV"
        
        # 1. Load and display the logo (Packed at the top)
        self.logo_img = None
        logo_path = get_resource_path(os.path.join('assets', 'logo.png'))
        
        if os.path.exists(logo_path):
            try:
                self.logo_img = tk.PhotoImage(file=logo_path)
                tk.Label(self, image=self.logo_img, bg=bg_color).pack(pady=(30, 15))
            except Exception as e:
                logging.warning(f"Could not load logo image: {e}")

        # 2. Display Title (Packed below logo)
        tk.Label(
            self, 
            text="NI-XNET Telemetry Explorer", 
            font=("Helvetica", 18, "bold"), 
            fg="white", 
            bg=bg_color
        ).pack(pady=(0, 5))
        
        # 3. Display Developer info (Packed below title)
        tk.Label(
            self, 
            text=f"Developed by: {DEVELOPER_NAME}", 
            font=("Helvetica", 11), 
            fg="#bdc3c7", 
            bg=bg_color
        ).pack(pady=0)
        
        # 4. Display Loading text (Anchored to the very bottom)
        tk.Label(
            self, 
            text="Initializing environment...", 
            font=("Helvetica", 9, "italic"), 
            fg="#7f8c8d", 
            bg=bg_color
        ).pack(side=tk.BOTTOM, pady=20)
        
        # Force the OS to draw the splash screen immediately
        self.update()

def main():
    """
    Main application entry point.
    """
    parser = argparse.ArgumentParser(description="NI-XNET CAN Explorer & Telemetry")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging to console")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - [%(levelname)s] - %(message)s'
    )
    
    # Silence external libraries to keep the terminal clean
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting application bootstrapping process...")
    
    try:
        # Initialize the main hidden root window
        root = tk.Tk()
        root.withdraw() # Hide the main window immediately
        
        # Set the main application icon
        icon_path = get_resource_path(os.path.join('assets', 'icon.ico'))
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
            
        # Display the Splash Screen
        splash = SplashScreen(root)
        
        # Simulate heavy loading (Matplotlib setup) while splash is visible
        logger.info("Configuring Matplotlib environment...")
        setup_professional_environment()
        
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        logger.info("Instantiating main GUI components...")
        app = CanDbSelectorApp(root)
        
        # Transition function to close splash and reveal the main app
        def start_main_application():
            splash.destroy()
            root.deiconify() # Reveal the main window
            logger.info("Bootstrapping complete. UI is now active.")

        # Keep the splash screen visible for at least 2.5 seconds (2500 ms)
        root.after(2500, start_main_application)
        
        root.mainloop()
        
    except Exception as e:
        logger.critical(f"Fatal execution error: {e}", exc_info=True)
    finally:
        plt.close('all')
        logger.info("Application terminated successfully.")

if __name__ == "__main__":
    main()