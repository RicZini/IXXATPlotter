import tkinter as tk
from tkinter import filedialog, ttk
import csv
import os
import logging
from datetime import datetime

# Configurazione logging (utile se eseguito come script standalone)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CanLogParser:
    """
    Engine per la decodifica dei log CSV generati da IXXAT canAnalyser.
    Estrae i payload e li organizza per CAN ID associando un asse temporale relativo.
    """
    def __init__(self):
        # Struttura: { "0x320": {"time": [0.0, 0.01, ...], "data": [[0x00, 0x53...], ...]} }
        self.log_data: dict[str, dict[str, list]] = {}
        self.total_messages = 0

    def load_csv(self, filepath: str) -> bool:
        logging.info(f"Avvio parsing del file di log: {filepath}")
        self.log_data.clear()
        self.total_messages = 0
        start_time_obj = None

        try:
            with open(filepath, mode='r', encoding='utf-8') as file:
                # Il CSV IXXAT usa il punto e virgola come delimitatore
                reader = csv.DictReader(file, delimiter=';')
                
                for row in reader:
                    raw_id = row.get('ID (hex)')
                    raw_time = row.get('Time (abs)')
                    raw_data = row.get('Data (hex)')
                    
                    # Ignora righe vuote o malformate
                    if not raw_id or not raw_time or not raw_data:
                        continue
                        
                    # 1. Normalizzazione ID (da "320" a "0x320")
                    can_id = f"0x{raw_id.strip().upper()}"
                    
                    # 2. Calcolo del tempo relativo in secondi (Asse X per i plot)
                    try:
                        time_obj = datetime.strptime(raw_time.strip(), "%H:%M:%S.%f")
                        if start_time_obj is None:
                            start_time_obj = time_obj
                        
                        delta = time_obj - start_time_obj
                        relative_time_sec = delta.total_seconds()
                    except ValueError:
                        # Se il formato dell'ora fallisce, skippiamo la riga
                        continue

                    # 3. Conversione payload esadecimale in lista di interi (Byte)
                    # "00 53 32" -> [0, 83, 50]
                    try:
                        byte_list = [int(b, 16) for b in raw_data.strip().split()]
                    except ValueError:
                        continue

                    # 4. Inserimento nel dizionario strutturato
                    if can_id not in self.log_data:
                        self.log_data[can_id] = {"time": [], "data": []}
                        
                    self.log_data[can_id]["time"].append(relative_time_sec)
                    self.log_data[can_id]["data"].append(byte_list)
                    self.total_messages += 1

            logging.info(f"Parsing completato: {self.total_messages} messaggi elaborati su {len(self.log_data)} ID distinti.")
            return True
            
        except Exception as e:
            logging.error(f"Errore critico durante la lettura del CSV: {e}", exc_info=True)
            return False


class CsvLoaderUI:
    """
    Interfaccia Grafica standalone per testare il caricamento del file CSV.
    Mostra un riepilogo dei dati acquisiti.
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("IXXAT CSV Log Loader")
        self.root.geometry("500x400")
        
        self.parser = CanLogParser()
        self.setup_ui()

    def setup_ui(self):
        # --- Top Frame: Selezione File ---
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.btn_load = tk.Button(top_frame, text="Load IXXAT CSV", command=self.open_file_dialog)
        self.btn_load.pack(side=tk.LEFT)
        
        self.lbl_file = tk.Label(top_frame, text="Nessun file selezionato", fg="gray")
        self.lbl_file.pack(side=tk.LEFT, padx=10)
        
        # --- Middle Frame: Risultati ---
        mid_frame = tk.Frame(self.root)
        mid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview per mostrare quanti messaggi ci sono per ogni ID
        self.tree = ttk.Treeview(mid_frame, columns=("ID", "Messaggi"), show="headings")
        self.tree.heading("ID", text="CAN ID")
        self.tree.heading("Messaggi", text="Numero di Messaggi (Samples)")
        self.tree.column("ID", anchor=tk.CENTER)
        self.tree.column("Messaggi", anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(mid_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

    def open_file_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Seleziona log CSV IXXAT",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        
        if filepath:
            self.lbl_file.config(text=os.path.basename(filepath), fg="black")
            success = self.parser.load_csv(filepath)
            
            if success:
                self.populate_results()

    def populate_results(self):
        # Svuota la tabella
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Inserisci i risultati ordinati per ID
        for can_id in sorted(self.parser.log_data.keys()):
            num_messages = len(self.parser.log_data[can_id]["time"])
            self.tree.insert("", tk.END, values=(can_id, num_messages))
            
        logging.debug("Tabella risultati aggiornata.")

if __name__ == "__main__":
    # Avvio in modalità standalone per testare SOLO questa componente
    root = tk.Tk()
    app = CsvLoaderUI(root)
    root.mainloop()