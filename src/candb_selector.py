import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import xml.etree.ElementTree as ET
import os
import logging
import matplotlib.pyplot as plt

from src.can_log_parser import CanLogParser

class CanDbSelectorApp:
    def __init__(self, root: tk.Tk) -> None:
        logging.debug("Initializing Integrated CAN Explorer...")
        self.root = root
        self.root.title("NI-XNET CAN Explorer & Telemetry")
        self.root.geometry("700x600")
        
        self.can_data: dict[str, dict] = {} 
        self.log_parser = CanLogParser()
        self.csv_loaded = False
        
        self.setup_ui()

    def setup_ui(self) -> None:
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        row_csv = tk.Frame(top_frame)
        row_csv.pack(side=tk.TOP, fill=tk.X, pady=2)
        tk.Button(row_csv, text="1. Load IXXAT CSV (Dati)", command=self.load_csv, width=25, bg="lightblue").pack(side=tk.LEFT)
        self.lbl_csv = tk.Label(row_csv, text="Nessun dato caricato", fg="gray")
        self.lbl_csv.pack(side=tk.LEFT, padx=10)
        
        row_xml = tk.Frame(top_frame)
        row_xml.pack(side=tk.TOP, fill=tk.X, pady=2)
        tk.Button(row_xml, text="2. Load NI-XNET XML (Database)", command=self.load_xml, width=25, bg="lightgreen").pack(side=tk.LEFT)
        self.lbl_xml = tk.Label(row_xml, text="Nessun database selezionato", fg="gray")
        self.lbl_xml.pack(side=tk.LEFT, padx=10)
        
        mid_frame = tk.Frame(self.root)
        mid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(mid_frame, selectmode="browse")
        self.tree.heading("#0", text="CAN Architecture (Doppio click su Segnale per Plot)", anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(mid_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.bind("<<TreeviewOpen>>", self.on_frame_expand)
        self.tree.bind("<Double-1>", self.on_double_click)
        
    def load_csv(self) -> None:
        filepath = filedialog.askopenfilename(title="Select IXXAT CSV", filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
        if filepath:
            success = self.log_parser.load_csv(filepath)
            if success:
                self.lbl_csv.config(text=f"{os.path.basename(filepath)} ({self.log_parser.total_messages} msgs)", fg="black")
                self.csv_loaded = True

    def load_xml(self) -> None:
        filepath = filedialog.askopenfilename(title="Select NI-XNET XML", filetypes=(("XML files", "*.xml"), ("All files", "*.*")))
        if filepath:
            self.lbl_xml.config(text=os.path.basename(filepath), fg="black")
            self.parse_xml(filepath)

    def parse_xml(self, filepath: str) -> None:
        logging.info(f"Avvio parsing XML robusto: {filepath}")
        self.can_data.clear()
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # 1. Normalizzazione namespace
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            
            # Funzione Helper infallibile per trovare i nomi
            def get_name(node):
                for child in node.iter('SHORT-NAME'):
                    if child.text: return child.text.strip()
                for child in node.iter('NAME'):
                    if child.text: return child.text.strip()
                return None

            # 2. Mappatura Segnali
            signal_map = {}
            for sig in root.iter('SIGNAL'):
                sig_id = sig.get('ID')
                sig_name = get_name(sig)
                if sig_id and sig_name:
                    signal_map[sig_id] = sig_name
            logging.debug(f"Mappati {len(signal_map)} segnali fisici.")

            # 3. Mappatura PDU
            pdu_map = {}
            pdu_elements = list(root.iter('PDU'))
            for pdu in pdu_elements:
                pdu_id = pdu.get('ID')
                sigs = [signal_map[s.get('ID-REF')] for s in pdu.iter('SIGNAL-REF') if s.get('ID-REF') in signal_map]
                if pdu_id: pdu_map[pdu_id] = sigs

            for pdu in pdu_elements:
                pdu_id = pdu.get('ID')
                for p_ref in pdu.iter('PDU-REF'):
                    r_id = p_ref.get('ID-REF')
                    if r_id in pdu_map and pdu_id in pdu_map:
                        pdu_map[pdu_id].extend(pdu_map[r_id])

            # 4. Mappatura ID Esadecimali
            frame_id_map = {}
            for trig in root.iter('FRAME-TRIGGERING'):
                ident = next((c.text for c in trig.iter('IDENTIFIER-VALUE') if c.text), None)
                f_ref = next((c.get('ID-REF') for c in trig.iter('FRAME-REF')), None)
                if ident and f_ref:
                    try:
                        frame_id_map[f_ref] = f"0x{int(ident):03X}"
                    except ValueError:
                        pass

            # 5. Costruzione Finale Dizionario
            frames_count = 0
            for frame in root.iter('FRAME'):
                f_id = frame.get('ID')
                if not f_id: continue
                
                frames_count += 1
                # Se il nome manca, garantisce una chiave univoca usando l'ID del nodo!
                frame_name = get_name(frame) or f"Unknown_Frame_{f_id}"
                can_id = frame_id_map.get(f_id, "N/A")
                
                f_sigs = []
                for p_ref in frame.iter('PDU-REF'):
                    r_id = p_ref.get('ID-REF')
                    if r_id in pdu_map: f_sigs.extend(pdu_map[r_id])
                
                self.can_data[frame_name] = {
                    'id': can_id,
                    'signals': list(dict.fromkeys(f_sigs))
                }
            
            logging.info(f"Parsing XML completato: {frames_count} Frame validi inseriti in memoria.")
            self.populate_tree_base()
            
        except Exception as e:
            logging.error(f"Errore critico durante il parsing: {e}", exc_info=True)
            messagebox.showerror("Errore XML", f"Errore nel processare il database: {e}")

    def populate_tree_base(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for frame_name, data in sorted(self.can_data.items()):
            can_id = data['id']
            node_id = self.tree.insert("", tk.END, text=f"ID: {can_id} | Frame: {frame_name}", values=(frame_name, can_id))
            self.tree.insert(node_id, tk.END, text="__dummy__")

    def on_frame_expand(self, event: tk.Event) -> None:
        node_id = self.tree.focus()
        if not node_id: return
        
        logging.debug(f"[{node_id}] Evento Espansione attivato.")
        children = self.tree.get_children(node_id)
        
        if len(children) == 1 and self.tree.item(children[0], "text") == "__dummy__":
            vals = self.tree.item(node_id, "values")
            if len(vals) < 2: return
            frame_name, can_id = vals[0], vals[1]
            
            logging.debug(f"Caricamento Segnali per: {frame_name} ({can_id})")
            self.tree.delete(children[0])
            
            signals = self.can_data.get(frame_name, {}).get('signals', [])
            if not signals:
                self.tree.insert(node_id, tk.END, text="[Nessun Segnale Mappato]")
                logging.debug("--> Nessun segnale all'interno.")
                return
                
            for sig in signals:
                self.tree.insert(node_id, tk.END, text=f"Signal: {sig}", values=("SIGNAL", sig, can_id, frame_name))
            logging.debug(f"--> Inseriti {len(signals)} segnali.")

    def on_double_click(self, event: tk.Event) -> None:
        node_id = self.tree.focus()
        if not node_id: return
        
        vals = self.tree.item(node_id, "values")
        logging.debug(f"Doppio Click rilevato: Valori Nodo -> {vals}")
        
        if len(vals) == 4 and vals[0] == "SIGNAL":
            logging.debug("E' un segnale! Avvio plot...")
            self.plot_signal(vals[1], vals[2], vals[3])
        else:
            logging.debug("Non e' una foglia 'Segnale', plot ignorato.")

    def plot_signal(self, sig_name: str, can_id: str, frame_name: str) -> None:
        if not self.csv_loaded:
            messagebox.showwarning("Dati mancanti", "Carica prima il file CSV.")
            return
        if can_id not in self.log_parser.log_data:
            messagebox.showinfo("Nessun Dato", f"L'ID {can_id} non è presente nel file CSV caricato.")
            return
            
        times = self.log_parser.log_data[can_id]["time"]
        payloads = self.log_parser.log_data[can_id]["data"]
        
        # Estraggo temporaneamente il primo byte per provare il grafico
        values = [p[0] if len(p) > 0 else 0 for p in payloads]

        plt.figure(figsize=(8, 4))
        plt.plot(times, values, label=f"{sig_name} (Byte 0 Raw)", color='blue')
        plt.title(f"{sig_name} @ {frame_name} ({can_id})")
        plt.xlabel("Tempo (s)")
        plt.ylabel("Valore (Raw)")
        plt.grid(True)
        plt.legend()
        plt.show(block=False)