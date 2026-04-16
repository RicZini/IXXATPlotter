import tkinter as tk
from tkinter import filedialog, ttk
import xml.etree.ElementTree as ET
import os
import logging

# Configure standard logging for clear, professional console output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CanDbSelectorApp:
    """
    Python Desktop Application to parse and selectively load 
    NI-XNET CAN Database XML files (FIBEX format).
    Implements Lazy Loading to ensure UI responsiveness with large datasets.
    """

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the main application window and application state."""
        logging.debug("Initializing CanDbSelectorApp...")
        self.root = root
        self.root.title("NI-XNET CAN Database Selector")
        self.root.geometry("600x500")
        
        # In-memory data store for parsed XML content
        # Structure: { "Frame_Name": ["Signal1", "Signal2", ...] }
        self.can_data: dict[str, list[str]] = {} 
        
        self.setup_ui()
        logging.debug("GUI initialized and ready.")

    def setup_ui(self) -> None:
        """Construct the Tkinter widget layout."""
        # --- Top Frame: File Selection ---
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.btn_load = tk.Button(top_frame, text="Load XML Database", command=self.load_file)
        self.btn_load.pack(side=tk.LEFT)
        
        self.lbl_file = tk.Label(top_frame, text="No file selected", fg="gray")
        self.lbl_file.pack(side=tk.LEFT, padx=10)
        
        # --- Middle Frame: Treeview for CAN Hierarchy ---
        mid_frame = tk.Frame(self.root)
        mid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(mid_frame, selectmode="extended")
        self.tree.heading("#0", text="CAN Frames and Signals", anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(mid_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind events for Lazy Loading and selection tracking
        self.tree.bind("<<TreeviewOpen>>", self.on_frame_expand)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # --- Bottom Frame: Next Action ---
        bot_frame = tk.Frame(self.root)
        bot_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        self.btn_next = tk.Button(bot_frame, text="Execute Next Action", command=self.next_step, state=tk.DISABLED)
        self.btn_next.pack(side=tk.RIGHT)

    def load_file(self) -> None:
        """Callback to open file dialog and initiate XML parsing."""
        logging.debug("File selection dialog opened by user.")
        filepath = filedialog.askopenfilename(
            title="Select NI-XNET XML Database",
            filetypes=(("XML files", "*.xml"), ("All files", "*.*"))
        )
        
        if not filepath:
            logging.debug("File selection cancelled.")
            return
            
        logging.info(f"Selected file: {filepath}")
        self.lbl_file.config(text=os.path.basename(filepath), fg="black")
        
        self.btn_next.config(state=tk.NORMAL)
        self.parse_xml(filepath)

    def parse_xml(self, filepath: str) -> None:
        """
        Advanced FIBEX/AUTOSAR XML parser.
        Resolves cross-references between FRAME -> PDU -> SIGNAL using IDs.
        """
        logging.info("Starting relational XML parser (FIBEX standard)...")
        self.can_data.clear()
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Normalize tags by stripping XML namespaces to simplify searching
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            
            logging.debug("Namespaces stripped. Building relational memory maps...")

            # --- STEP 1: Map all Signals (ID -> Name) ---
            signal_map = {}
            for sig in root.findall('.//SIGNAL'):
                sig_id = sig.get('ID')
                name_elem = sig.find('.//SHORT-NAME')
                if name_elem is None:
                    name_elem = sig.find('NAME')
                    
                if sig_id and name_elem is not None and name_elem.text:
                    signal_map[sig_id] = name_elem.text.strip()
                    
            logging.debug(f"Mapped {len(signal_map)} distinct Signals.")

            # --- STEP 2: Map all PDUs (ID -> List of Signal Names) ---
            pdu_map = {}
            pdu_elements = root.findall('.//PDU')
            
            # Pass 2A: Extract direct signals within each PDU
            for pdu in pdu_elements:
                pdu_id = pdu.get('ID')
                signals = []
                
                # Find all signal references inside this PDU
                for sig_ref in pdu.findall('.//SIGNAL-REF'):
                    ref_id = sig_ref.get('ID-REF')
                    if ref_id in signal_map:
                        signals.append(signal_map[ref_id])
                
                if pdu_id:
                    pdu_map[pdu_id] = signals

            # Pass 2B: Resolve nested PDUs (Multiplexers)
            # Some PDUs contain references to other PDUs (e.g. dpdu)
            for pdu in pdu_elements:
                pdu_id = pdu.get('ID')
                for pdu_ref in pdu.findall('.//PDU-REF'):
                    ref_id = pdu_ref.get('ID-REF')
                    # If this PDU references another PDU, inherit its signals
                    if ref_id in pdu_map and pdu_id in pdu_map:
                        pdu_map[pdu_id].extend(pdu_map[ref_id])

            logging.debug(f"Mapped {len(pdu_map)} PDUs and resolved multiplexed references.")

            # --- STEP 3: Map Frames and link them to PDUs ---
            frames = root.findall('.//FRAME')
            logging.info(f"Successfully extracted {len(frames)} FRAME definitions.")
            
            for frame in frames:
                frame_name_elem = frame.find('.//SHORT-NAME')
                if frame_name_elem is None:
                    frame_name_elem = frame.find('NAME')
                    
                frame_name = frame_name_elem.text.strip() if frame_name_elem is not None else "Unknown_Frame"
                frame_signals = []
                
                # A Frame references PDUs. We fetch the signals mapped to those PDUs.
                for pdu_ref in frame.findall('.//PDU-REF'):
                    ref_id = pdu_ref.get('ID-REF')
                    if ref_id in pdu_map:
                        frame_signals.extend(pdu_map[ref_id])
                
                # Remove any duplicates (caused by complex multiplexing) and assign to main dictionary
                # dict.fromkeys() is the fastest, order-preserving way to remove duplicates in Python
                self.can_data[frame_name] = list(dict.fromkeys(frame_signals))
                
                logging.debug(f"  --> Frame [{frame_name}] mapped with {len(self.can_data[frame_name])} signals.")
            
            if not self.can_data:
                logging.warning("No frames found. Verify the file structure.")
                self.can_data["[Error] Setup failed"] = ["Invalid schema"]
                
            # Initialize User Interface components
            self.populate_tree_base()
            
        except ET.ParseError as e:
            logging.error(f"XML parsing failed: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during parsing: {e}", exc_info=True)

    def populate_tree_base(self) -> None:
        """
        Populate only the root nodes (Frames) in the Treeview.
        Injects a dummy node to enable the expand arrow for lazy loading.
        """
        logging.debug("Clearing previous Treeview contents...")
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        logging.debug("Populating root Frame nodes (Lazy Loading strategy)...")
        for frame in self.can_data.keys():
            # Store the frame key in the 'values' tuple to retrieve it easily later
            frame_id = self.tree.insert("", tk.END, text=f"Frame: {frame}", values=(frame,), open=False)
            
            # Insert a dummy child to force tkinter to draw the expand [+] icon
            self.tree.insert(frame_id, tk.END, text="__dummy__")
                
        logging.info("Treeview base layer populated.")

    def on_frame_expand(self, event: tk.Event) -> None:
        """
        Callback triggered when a user expands a node.
        Checks for the dummy node, removes it, and loads actual Signals on the fly.
        """
        # Get the ID of the node being expanded
        node_id = self.tree.focus()
        if not node_id:
            return

        children = self.tree.get_children(node_id)
        
        # If the first child is our dummy node, it means we need to load the data
        if len(children) == 1 and self.tree.item(children[0], "text") == "__dummy__":
            # Extract the actual frame name we hid inside the 'values' attribute
            frame_name = self.tree.item(node_id, "values")[0]
            logging.debug(f"Lazy loading triggered for Frame: {frame_name}")
            
            # Remove the dummy node
            self.tree.delete(children[0])
            
            # Fetch the signals from our fast in-memory dictionary
            signals = self.can_data.get(frame_name, [])
            
            # Populate the actual signals
            for sig in signals:
                self.tree.insert(node_id, tk.END, text=f"Signal: {sig}")
                
            logging.debug(f"Loaded {len(signals)} signals dynamically.")

    def on_select(self, event: tk.Event) -> None:
        """Callback to handle standard selection clicks."""
        selected_items = self.tree.selection()
        if selected_items:
            item_text = self.tree.item(selected_items[0], "text")
            logging.debug(f"User highlighted: {item_text}")

    def next_step(self) -> None:
        """Placeholder for the next processing pipeline."""
        logging.info("'Execute Next Action' invoked.")
        logging.debug("Ready for implementation of data export/processing logic.")

if __name__ == "__main__":
    logging.info("Starting application main event loop...")
    root = tk.Tk()
    app = CanDbSelectorApp(root)
    root.mainloop()
    logging.info("Application shut down cleanly.")