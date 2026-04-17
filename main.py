import tkinter as tk
from tkinter import ttk
import logging
import argparse
import matplotlib.pyplot as plt

# Import the application from our source module
from src.candb_selector import CanDbSelectorApp

def setup_professional_environment():
    """
    Configures global graphical settings for Matplotlib 
    to give plots a professional telemetry software appearance.
    """
    try:
        # Use a clean style (ggplot or seaborn-darkgrid are excellent for data visualization)
        plt.style.use('ggplot')
    except Exception:
        pass # Silent fallback to default style
        
    # Global parameters for plots
    plt.rcParams['figure.autolayout'] = True
    plt.rcParams['lines.linewidth'] = 1.5
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['figure.facecolor'] = '#f4f4f4'
    plt.rcParams['axes.facecolor'] = '#ffffff'

def main():
    """
    Main application entry point.
    Handles environment setup, argument parsing, logging configuration, and GUI lifecycle.
    """
    # 1. Setup command line arguments
    parser = argparse.ArgumentParser(description="NI-XNET CAN Explorer & Telemetry")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging to console")
    args = parser.parse_args()

    # Determine logging level based on the command line flag
    log_level = logging.DEBUG if args.debug else logging.INFO

    # 2. Setup Logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - [%(levelname)s] - %(message)s'
    )
    
    # SILENCE EXTERNAL LIBRARIES
    # Prevent matplotlib and PIL from flooding the terminal with internal debug messages
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting NI-XNET/IXXAT Telemetry tool...")
    
    # 3. Setup Matplotlib environment
    setup_professional_environment()
    
    try:
        # 4. Initialize main graphical engine
        root = tk.Tk()
        
        # 5. Enhance OS-native interface aesthetics
        style = ttk.Style()
        # 'clam', 'vista', or 'winnative' make buttons and treeviews look much more modern
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
            
        # 6. Launch the Application
        app = CanDbSelectorApp(root)
        
        # 7. Start the Event Loop (blocks execution until the window is closed)
        root.mainloop()
        
    except Exception as e:
        logger.critical(f"Fatal execution error: {e}", exc_info=True)
    finally:
        # Ensure all open plots are closed when the program terminates
        plt.close('all')
        logger.info("Application terminated. Processes safely closed.")

if __name__ == "__main__":
    main()