import tkinter as tk
from tkinter import ttk
import logging
import matplotlib.pyplot as plt

# Importiamo l'applicazione dal nostro modulo sorgente
from src.candb_selector import CanDbSelectorApp

def setup_professional_environment():
    """
    Configura le impostazioni grafiche globali per Matplotlib 
    per dare ai plot un aspetto da software di telemetria professionale.
    """
    try:
        # Usa uno stile pulito (ggplot o seaborn-darkgrid sono ottimi per i dati)
        plt.style.use('ggplot')
    except Exception:
        pass # Fallback silenzioso allo stile base
        
    # Parametri globali per i grafici
    plt.rcParams['figure.autolayout'] = True
    plt.rcParams['lines.linewidth'] = 1.5
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['figure.facecolor'] = '#f4f4f4'
    plt.rcParams['axes.facecolor'] = '#ffffff'

def main():
    """
    Punto di ingresso principale dell'applicazione.
    Gestisce il setup dell'ambiente, il logging e il ciclo di vita della GUI.
    """
    # 1. Setup del Logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - [%(levelname)s] - %(message)s'
    )
    
    logging.info("Avvio del tool di Telemetria NI-XNET/IXXAT...")
    
    # 2. Setup dell'ambiente Matplotlib
    setup_professional_environment()
    
    try:
        # 3. Inizializzazione del motore grafico principale
        root = tk.Tk()
        
        # 4. Miglioramento dell'estetica dell'interfaccia OS-native
        style = ttk.Style()
        # 'clam' o 'vista' o 'winnative' rendono i bottoni e i treeview molto più moderni
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
            
        # 5. Avvio dell'Applicazione
        app = CanDbSelectorApp(root)
        
        # 6. Avvio del Loop degli Eventi (blocca l'esecuzione finché non si chiude la finestra)
        root.mainloop()
        
    except Exception as e:
        logging.critical(f"Errore fatale durante l'esecuzione: {e}", exc_info=True)
    finally:
        # Si assicura che tutti i grafici aperti vengano chiusi quando si chiude il programma
        plt.close('all')
        logging.info("Applicazione terminata. Chiusura sicura dei processi.")

if __name__ == "__main__":
    main()