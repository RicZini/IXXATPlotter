import tkinter as tk
from tkinter import filedialog, ttk
import xml.etree.ElementTree as ET
import os
import logging

# Configure standard logging for professional debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CanDbSelectorApp:
    """
    Graphical User Interface application to parse and display 
    NI-XNET CAN Database XML files (FIBEX format).
    """

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the main application window and internal data structures."""
        logging.debug("Initializing CanDbSelectorApp...")
        self.root = root
        self.root.title("NI-XNET CAN Database Selector")
        self.root.geometry("600x500")
        
        # Data storage dictionary to hold frames and their corresponding signals
        # Format: { "Frame_Name": ["Signal1", "Signal2", ...] }
        self.can_data: dict[str, list[str]] = {} 
        
        self.setup_ui()
        logging.debug("GUI setup complete.")

    def setup_ui(self) -> None:
        """Build and arrange User Interface components."""
        logging.debug("Building UI components...")
        
        # --- Top Frame: File Selection ---
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.btn_load = tk.Button(top_frame, text="Load XML Database", command=self.load_file)
        self.btn_load.pack(side=tk.LEFT)
        
        self.lbl_file = tk.Label(top_frame, text="No file selected", fg="gray")
        self.lbl_file.pack(side=tk.LEFT, padx=10)
        
        # --- Middle Frame: Treeview for Packages and Signals ---
        mid_frame = tk.Frame(self.root)
        mid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(mid_frame, selectmode="extended")
        self.tree.heading("#0", text="CAN Frames and Signals", anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(mid_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # --- Bottom Frame: Next Action Integration ---
        bot_frame = tk.Frame(self.root)
        bot_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        self.btn_next = tk.Button(bot_frame, text="Execute Next Action", command=self.next_step, state=tk.DISABLED)
        self.btn_next.pack(side=tk.RIGHT)

    def load_file(self) -> None:
        """Open a file dialog to select the XML database."""
        logging.debug("Triggered file selection dialog.")
        filepath = filedialog.askopenfilename(
            title="Select NI-XNET XML Database",
            filetypes=(("XML files", "*.xml"), ("All files", "*.*"))
        )
        
        if not filepath:
            logging.debug("File selection cancelled by user.")
            return
            
        logging.info(f"File selected: {filepath}")
        self.lbl_file.config(text=os.path.basename(filepath), fg="black")
        
        self.btn_next.config(state=tk.NORMAL)
        self.parse_xml(filepath)

    def parse_xml(self, filepath: str) -> None:
        """
        Parse the selected XML file, strip namespaces, and extract
        FRAME and SIGNAL elements into the internal dictionary.
        """
        logging.info(f"Starting XML parsing engine for: {filepath}")
        self.can_data.clear()
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            logging.debug(f"XML loaded into memory. Root Tag: {root.tag}")
            
            # Strip namespaces for robust parsing
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            
            logging.debug("Stripped XML namespaces for standardized processing.")
            
            frames = root.findall('.//FRAME')
            logging.info(f"Parsing detected {len(frames)} FRAME elements.")
            
            for frame in frames:
                frame_name_elem = frame.find('.//SHORT-NAME')
                if frame_name_elem is None:
                    frame_name_elem = frame.find('NAME')
                    
                frame_name = frame_name_elem.text if frame_name_elem is not None else "Unknown_Frame"
                logging.debug(f"Extracting data for Frame: {frame_name}")
                
                self.can_data[frame_name] = []
                
                signals = frame.findall('.//SIGNAL')
                if not signals:
                    signals = frame.findall('.//SIGNAL-INSTANCE')
                    
                logging.debug(f"Found {len(signals)} Signals inside Frame '{frame_name}'.")
                
                for sig in signals:
                    sig_name_elem = sig.find('.//SHORT-NAME')
                    if sig_name_elem is None:
                        sig_name_elem = sig.find('NAME')
                        
                    sig_name = sig_name_elem.text if sig_name_elem is not None else "Unknown_Signal"
                    self.can_data[frame_name].append(sig_name)
                    logging.debug(f"  --> Mapped Signal: {sig_name}")
            
            if not self.can_data:
                logging.warning("No frames were mapped. The XML schema might not match expected FIBEX format.")
                self.can_data["[Error] No frames found"] = ["Check XML tag structure"]
                
            self.populate_tree()
            
        except ET.ParseError as e:
            logging.error(f"XML Parse Error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during XML parsing: {e}", exc_info=True)

    def populate_tree(self) -> None:
        """Clear existing UI nodes and populate the Treeview with parsed data."""
        logging.debug("Clearing existing items in the Treeview...")
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        logging.debug("Populating Treeview with extracted CAN database information...")
        for frame, signals in self.can_data.items():
            frame_id = self.tree.insert("", tk.END, text=f"Frame: {frame}", open=False)
            logging.debug(f"Added GUI Node for Frame: {frame}")
            
            for sig in signals:
                self.tree.insert(frame_id, tk.END, text=f"Signal: {sig}")
                logging.debug(f"Added GUI Sub-node for Signal: {sig} (Parent: {frame})")
                
        logging.info("Treeview population complete.")

    def on_select(self, event: tk.Event) -> None:
        """Handle tree item selection events."""
        selected_items = self.tree.selection()
        logging.debug(f"Selection event. {len(selected_items)} item(s) currently selected.")
        
        for item in selected_items:
            item_text = self.tree.item(item, "text")
            logging.debug(f"Highlighted item: {item_text}")

    def next_step(self) -> None:
        """Trigger the next feature execution."""
        logging.info("'Execute Next Action' button clicked.")
        logging.debug("Waiting for integration of the next pipeline stage.")


if __name__ == "__main__":
    logging.info("Booting up NI-XNET Database Selector application...")
    root = tk.Tk()
    app = CanDbSelectorApp(root)
    root.mainloop()
    logging.info("Mainloop terminated. Application shut down cleanly.")