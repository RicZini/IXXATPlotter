import xml.etree.ElementTree as ET
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_fibex_parameter_extraction(filepath: str):
    logging.info(f"--- Avvio Analisi Multiplexing FIBEX: {filepath} ---")
    
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Rimuoviamo i namespace
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]

        signals_final_info = {}

        # =========================================================
        # 1. MAPPATURA MATEMATICA E NOMI
        # =========================================================
        codings_map = {}
        for coding in root.iter('CODING'):
            c_id = coding.get('ID')
            if not c_id: continue
            
            bit_length = 0
            bl_elem = coding.find('.//BIT-LENGTH')
            if bl_elem is not None and bl_elem.text: bit_length = int(bl_elem.text)
                
            factor = 1.0; offset = 0.0
            coeffs = coding.find('.//COMPU-RATIONAL-COEFFS/COMPU-NUMERATOR')
            if coeffs is not None:
                v_elements = list(coeffs.iter('V'))
                if len(v_elements) >= 1 and v_elements[0].text: offset = float(v_elements[0].text)
                if len(v_elements) >= 2 and v_elements[1].text: factor = float(v_elements[1].text)
                    
            codings_map[c_id] = {"bit_length": bit_length, "factor": factor, "offset": offset}

        signal_map = {}
        for sig in root.iter('SIGNAL'):
            s_id = sig.get('ID')
            s_name = next((c.text.strip() for c in sig.iter('SHORT-NAME') if c.text), None)
            if not s_name: s_name = next((c.text.strip() for c in sig.iter('NAME') if c.text), None)
            
            c_ref = None
            coding_ref_elem = sig.find('.//CODING-REF')
            if coding_ref_elem is not None: c_ref = coding_ref_elem.get('ID-REF')
                
            if s_id and s_name:
                signal_map[s_id] = {"name": s_name, "coding_id": c_ref}

        start_bit_map = {}
        for parent in root.iter():
            bp = parent.find('./BIT-POSITION')
            sr = parent.find('./SIGNAL-REF')
            if bp is not None and sr is not None and bp.text:
                start_bit_map[sr.get('ID-REF')] = int(bp.text.strip())

        # =========================================================
        # 2. IDENTIFICAZIONE DELLE REGOLE DI SWITCHING
        # =========================================================
        # Mappa per capire quale PDU è attivato da quale valore di offset
        # Formato: { "pdu_id": "valore_switch" }
        multiplexed_pdus_rules = {}
        for spi in root.iter('SWITCHED-PDU-INSTANCE'):
            switch_code = spi.find('./SWITCH-CODE')
            pdu_ref = spi.find('./PDU-REF')
            if switch_code is not None and pdu_ref is not None and switch_code.text:
                multiplexed_pdus_rules[pdu_ref.get('ID-REF')] = switch_code.text.strip()

        # =========================================================
        # 3. ESTRAZIONE DIRETTA DEI MULTIPLEXER (Gli Offset)
        # =========================================================
        for mux in root.iter('MULTIPLEXER'):
            switch = mux.find('./SWITCH')
            if switch is not None:
                s_name = switch.find('./SHORT-NAME').text.strip()
                s_bit = int(switch.find('./BIT-POSITION').text)
                s_len = int(switch.find('./BIT-LENGTH').text)
                # I multiplexer (offset) di solito non hanno scaling, sono raw integers
                signals_final_info[s_name] = {
                    "role": "MULTIPLEXER",
                    "start_bit": s_bit,
                    "bit_length": s_len,
                    "factor": 1.0,
                    "offset": 0.0,
                    "mux_code": "CTRL" # È il controller
                }

        # =========================================================
        # 4. ESTRAZIONE DEI SEGNALI NORMALI E MULTIPLEXATI
        # =========================================================
        for pdu in root.iter('PDU'):
            pdu_id = pdu.get('ID')
            
            # Controlliamo se questa PDU è soggetta a un offset
            is_muxed = pdu_id in multiplexed_pdus_rules
            mux_activation_value = multiplexed_pdus_rules.get(pdu_id, "N/A")
            
            for sig_ref in pdu.iter('SIGNAL-REF'):
                s_ref_id = sig_ref.get('ID-REF')
                if not s_ref_id or s_ref_id not in signal_map: continue
                
                sig_info = signal_map[s_ref_id]
                sig_name = sig_info["name"]
                c_id = sig_info["coding_id"]
                
                # Attribuiamo il ruolo
                role = "multiplexed" if is_muxed else "single"
                
                start_bit = start_bit_map.get(s_ref_id, 0)
                math_data = codings_map.get(c_id, {"bit_length": 8, "factor": 1.0, "offset": 0.0})
                
                signals_final_info[sig_name] = {
                    "role": role,
                    "start_bit": start_bit,
                    "bit_length": math_data["bit_length"],
                    "factor": math_data["factor"],
                    "offset": math_data["offset"],
                    "mux_code": mux_activation_value
                }
        
        # Stampiamo i risultati tabulati
        print("\n" + "="*95)
        print(f"{'NOME SEGNALE':<25} | {'RUOLO':<12} | {'CODE':<5} | {'START':<5} | {'LEN':<3} | {'FACTOR':<6} | {'OFFSET'}")
        print("="*95)
        
        for name, data in sorted(signals_final_info.items()):
            print(f"{name:<25} | {data['role']:<12} | {data['mux_code']:<5} | {data['start_bit']:<5} | {data['bit_length']:<3} | {data['factor']:<6} | {data['offset']}")
        print("="*95)
            
        return signals_final_info

    except Exception as e:
        logging.error(f"Errore critico: {e}", exc_info=True)

if __name__ == "__main__":
    test_fibex_parameter_extraction("FSAEE_CAN_DB.xml")