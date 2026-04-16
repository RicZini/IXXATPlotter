import tkinter as tk
import logging
# Importiamo la classe dal file rinominato cand_selector.py all'interno di src/
from src.candb_selector import CanDbSelectorApp

def main():
    """
    Punto di ingresso principale dell'applicazione.
    Configura il logging e avvia l'interfaccia grafica.
    """
    
    # Configurazione del logging professionale
    # I messaggi verranno stampati in console con timestamp e livello di gravità
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Starting NI-XNET CAN Explorer...")
    
    try:
        # Inizializzazione della finestra radice di Tkinter
        root = tk.Tk()
        root.title("NI-XNET CAN Explorer v1.0")
        
        # Istanza dell'applicazione passando la root
        # La logica è contenuta in src/cand_selector.py
        app = CanDbSelectorApp(root)
        
        # Avvio del ciclo degli eventi (Main Loop)
        # Questo blocca l'esecuzione finché la finestra non viene chiusa
        root.mainloop()
        
    except Exception as e:
        logging.critical(f"A critical error occurred during startup: {e}", exc_info=True)
    finally:
        logging.info("Application context terminated.")

if __name__ == "__main__":
    main()