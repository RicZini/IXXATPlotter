import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import xml.etree.ElementTree as ET
import os
import logging
import matplotlib.pyplot as plt

from src.can_log_parser import CanLogParser
from src.can_decoder import CanDecoder

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
            if self.log_parser.load_csv(filepath):
                self.lbl_csv.config(text=f"{os.path.basename(filepath)} ({self.log_parser.total_messages} msgs)", fg="black")
                self.csv_loaded = True

    def load_xml(self) -> None:
        filepath = filedialog.askopenfilename(title="Select NI-XNET XML", filetypes=(("XML files", "*.xml"), ("All files", "*.*")))
        if filepath:
            self.lbl_xml.config(text=os.path.basename(filepath), fg="black")
            self.parse_xml(filepath)

    def parse_xml(self, filepath: str) -> None:
        logging.info("Avvio parsing XML Relazionale FIBEX...")
        self.can_data.clear()
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            for elem in root.iter():
                if '}' in elem.tag: elem.tag = elem.tag.split('}', 1)[1]

            # 1. CODING (Matematica)
            codings = {}
            for c in root.iter('CODING'):
                c_id = c.get('ID')
                if not c_id: continue
                bl = int(c.find('.//BIT-LENGTH').text) if c.find('.//BIT-LENGTH') is not None else 8
                f = 1.0; o = 0.0
                num = c.find('.//COMPU-RATIONAL-COEFFS/COMPU-NUMERATOR')
                if num is not None:
                    v_elems = list(num.iter('V'))
                    if len(v_elems) >= 1 and v_elems[0].text: o = float(v_elems[0].text)
                    if len(v_elems) >= 2 and v_elems[1].text: f = float(v_elems[1].text)
                codings[c_id] = {"bit_length": bl, "factor": f, "offset": o}

            # 2. SEGNALI BASE
            signals = {}
            for sig in root.iter('SIGNAL'):
                s_name = next((c.text.strip() for c in sig.iter('SHORT-NAME') if c.text), None)
                if not s_name: s_name = next((c.text.strip() for c in sig.iter('NAME') if c.text), None)
                c_ref = sig.find('.//CODING-REF')
                if sig.get('ID') and s_name: 
                    signals[sig.get('ID')] = {"name": s_name, "coding_id": c_ref.get('ID-REF') if c_ref is not None else None}

            # 3. START BITS
            start_bits = {}
            for parent in root.iter():
                bp = parent.find('./BIT-POSITION')
                sr = parent.find('./SIGNAL-REF')
                if bp is not None and sr is not None and bp.text:
                    start_bits[sr.get('ID-REF')] = int(bp.text.strip())

            # 4. PDU ANALYSIS (Struttura Multiplexing)
            pdu_direct_signals = {}
            pdu_mux_roots = {}
            pdu_dynamic_links = {}

            for pdu in root.iter('PDU'):
                p_id = pdu.get('ID')
                
                # Segnali diretti
                pdu_direct_signals[p_id] = [sr.get('ID-REF') for sr in pdu.iter('SIGNAL-REF') if sr.get('ID-REF')]
                
                # Cerca Multiplexer Root
                switch = pdu.find('.//MULTIPLEXER/SWITCH')
                if switch is not None:
                    m_name = switch.find('./SHORT-NAME').text.strip()
                    m_sb = int(switch.find('./BIT-POSITION').text)
                    m_bl = int(switch.find('./BIT-LENGTH').text)
                    pdu_mux_roots[p_id] = {"name": m_name, "start_bit": m_sb, "bit_length": m_bl}

                # Cerca Dynamic Links
                links = []
                for spi in pdu.iter('SWITCHED-PDU-INSTANCE'):
                    code = spi.find('./SWITCH-CODE')
                    p_ref = spi.find('./PDU-REF')
                    if code is not None and p_ref is not None and code.text:
                        links.append({"code": code.text.strip(), "pdu_ref": p_ref.get('ID-REF')})
                pdu_dynamic_links[p_id] = links

            # 5. ID TRIGGERING
            frame_id_map = {}
            for trig in root.iter('FRAME-TRIGGERING'):
                ident = next((c.text for c in trig.iter('IDENTIFIER-VALUE') if c.text), None)
                f_ref = next((c.get('ID-REF') for c in trig.iter('FRAME-REF')), None)
                if ident and f_ref: frame_id_map[f_ref] = f"0x{int(ident):03X}"

            # 6. FRAME ASSEMBLY
            for frame in root.iter('FRAME'):
                f_id = frame.get('ID')
                if not f_id: continue
                
                f_name = next((c.text.strip() for c in frame.iter('SHORT-NAME') if c.text), f"Unknown_{f_id}")
                can_id = frame_id_map.get(f_id, "N/A")
                frame_signals = {}

                for p_ref in frame.iter('PDU-REF'):
                    root_pdu_id = p_ref.get('ID-REF')
                    
                    # 6.a Controlla se questa PDU comanda un Multiplexer
                    frame_mux_info = pdu_mux_roots.get(root_pdu_id, None)

                    # 6.b Aggiungi i segnali single (non multiplexati)
                    for s_ref in pdu_direct_signals.get(root_pdu_id, []):
                        if s_ref not in signals: continue
                        sig_name = signals[s_ref]["name"]
                        
                        # SCARTA IL SEGNALE MULTIPLEXER DALLA GUI
                        if frame_mux_info and sig_name == frame_mux_info["name"]:
                            continue
                            
                        cod = codings.get(signals[s_ref]["coding_id"], {})
                        frame_signals[sig_name] = {
                            "role": "single",
                            "start_bit": start_bits.get(s_ref, 0),
                            "bit_length": cod.get("bit_length", 8),
                            "factor": cod.get("factor", 1.0),
                            "offset": cod.get("offset", 0.0),
                            "mux_code": None,
                            "mux_ctrl": None
                        }

                    # 6.c Aggiungi i segnali Multiplexed dalle PDU dinamiche
                    for link in pdu_dynamic_links.get(root_pdu_id, []):
                        dyn_pdu_id = link["pdu_ref"]
                        switch_code = link["code"]
                        
                        for s_ref in pdu_direct_signals.get(dyn_pdu_id, []):
                            if s_ref not in signals: continue
                            sig_name = signals[s_ref]["name"]
                            cod = codings.get(signals[s_ref]["coding_id"], {})
                            
                            frame_signals[sig_name] = {
                                "role": "multiplexed",
                                "start_bit": start_bits.get(s_ref, 0),
                                "bit_length": cod.get("bit_length", 8),
                                "factor": cod.get("factor", 1.0),
                                "offset": cod.get("offset", 0.0),
                                "mux_code": int(switch_code) if switch_code.isdigit() else switch_code,
                                "mux_ctrl": frame_mux_info # Alleghiamo direttamente le info dell'offset!
                            }

                self.can_data[f_name] = {'id': can_id, 'signals': frame_signals}
            
            logging.info("XML Parser completato. GUI in aggiornamento.")
            self.populate_tree_base()
            
        except Exception as e:
            logging.error(f"Errore XML: {e}", exc_info=True)
            messagebox.showerror("Errore XML", str(e))

    def populate_tree_base(self) -> None:
        for item in self.tree.get_children(): self.tree.delete(item)
        for frame_name, data in sorted(self.can_data.items()):
            node_id = self.tree.insert("", tk.END, text=f"ID: {data['id']} | Frame: {frame_name}", values=(frame_name, data['id']))
            self.tree.insert(node_id, tk.END, text="__dummy__")

    def on_frame_expand(self, event: tk.Event) -> None:
        node_id = self.tree.focus()
        if not node_id: return
        children = self.tree.get_children(node_id)
        if len(children) == 1 and self.tree.item(children[0], "text") == "__dummy__":
            vals = self.tree.item(node_id, "values")
            frame_name, can_id = vals[0], vals[1]
            self.tree.delete(children[0])
            
            signals = self.can_data.get(frame_name, {}).get('signals', {})
            for sig_name in sorted(signals.keys()):
                # Niente più icone
                self.tree.insert(node_id, tk.END, text=sig_name, values=("SIGNAL", sig_name, can_id, frame_name))

    def on_double_click(self, event: tk.Event) -> None:
        node_id = self.tree.focus()
        if not node_id: return
        vals = self.tree.item(node_id, "values")
        if len(vals) == 4 and vals[0] == "SIGNAL":
            self.plot_signal(vals[1], vals[2], vals[3])

    def plot_signal(self, sig_name: str, can_id: str, frame_name: str) -> None:
        if not self.csv_loaded: return messagebox.showwarning("Dati", "Carica il CSV.")
        if can_id not in self.log_parser.log_data: return messagebox.showinfo("Dati", f"ID {can_id} non nel CSV.")
        
        sig_info = self.can_data[frame_name]['signals'][sig_name]
        role = sig_info['role']

        times = self.log_parser.log_data[can_id]["time"]
        payloads = self.log_parser.log_data[can_id]["data"]
        
        plot_times = []
        plot_values = []

        for i, payload in enumerate(payloads):
            if not payload: continue

            # 1. FILTRO MULTIPLEXING
            if role == 'multiplexed':
                mux_ctrl = sig_info.get('mux_ctrl')
                if not mux_ctrl: 
                    continue # Se manca il controller, la riga è illeggibile, la scarto
                
                # Estrae il valore dell'offset corrente dal payload
                current_mux_val = CanDecoder.extract_raw_value(
                    payload, 
                    start_bit=mux_ctrl['start_bit'], 
                    bit_length=mux_ctrl['bit_length']
                )
                
                # Se l'offset letto non coincide con il codice di sblocco della cella, salta il pacchetto!
                if str(current_mux_val) != str(sig_info['mux_code']):
                    continue 

            # 2. ESTRAZIONE VALORE
            raw_val = CanDecoder.extract_raw_value(
                payload, 
                start_bit=sig_info['start_bit'], 
                bit_length=sig_info['bit_length']
            )
            
            # 3. SCALING
            phys_val = CanDecoder.apply_scaling(raw_val, factor=sig_info['factor'], offset=sig_info['offset'])

            plot_times.append(times[i])
            plot_values.append(phys_val)

        if not plot_values:
            messagebox.showinfo("Nessun dato", "Il segnale richiesto non è mai apparso in questo log CSV (Offset mai attivato).")
            return

        plt.figure(figsize=(10, 5))
        plt.plot(plot_times, plot_values, label=f"{sig_name}", color='#2c3e50', linewidth=1.5)
        
        info_str = f"Bit:{sig_info['start_bit']} | Len:{sig_info['bit_length']} | MuxCode:{sig_info.get('mux_code', 'N/A')} | Factor:{sig_info['factor']}"
        plt.title(f"{sig_name}  [{frame_name}]", fontsize=12)
        plt.suptitle(info_str, fontsize=9, color='gray', y=0.92)
        
        plt.xlabel("Tempo (s)")
        plt.ylabel("Valore")
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show(block=False)