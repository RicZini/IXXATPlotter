import xml.etree.ElementTree as ET
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_fibex_parameter_extraction(filepath: str):
    logging.info(f"--- Starting COMPLETE FIBEX Global Extraction: {filepath} ---")
    
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Safely remove XML namespaces to ensure all tags are found
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]

        signals_final_info = {}
        codings_map = {}
        signal_map = {}
        start_bit_map = {}
        sig_to_pdu = {}
        pdu_rules = {}

        # =========================================================
        # STEP 1: Global Search for CODINGS (Math & Data Types)
        # =========================================================
        for coding in root.iter('CODING'):
            c_id = coding.get('ID')
            if not c_id: continue
            
            bit_length = 0
            bl_elem = coding.find('.//BIT-LENGTH')
            if bl_elem is not None and bl_elem.text: 
                bit_length = int(bl_elem.text)
                
            is_signed = False
            coded_type = coding.find('.//CODED-TYPE')
            if coded_type is not None:
                if coded_type.get('ENCODING', '').upper() == 'SIGNED':
                    is_signed = True
                else:
                    for attr_name, attr_value in coded_type.attrib.items():
                        if 'BASE-DATA-TYPE' in attr_name.upper():
                            if 'UINT' not in attr_value.upper() and 'INT' in attr_value.upper():
                                is_signed = True
            
            factor = 1.0; offset = 0.0
            coeffs = coding.find('.//COMPU-RATIONAL-COEFFS/COMPU-NUMERATOR')
            if coeffs is not None:
                v_elements = list(coeffs.iter('V'))
                if len(v_elements) >= 1 and v_elements[0].text: offset = float(v_elements[0].text)
                if len(v_elements) >= 2 and v_elements[1].text: factor = float(v_elements[1].text)
                
            codings_map[c_id] = {
                "bit_length": bit_length, "factor": factor, "offset": offset, "is_signed": is_signed
            }

        # =========================================================
        # STEP 2: Global Search for ALL Defined SIGNALS
        # =========================================================
        for sig in root.iter('SIGNAL'):
            s_id = sig.get('ID')
            if not s_id: continue

            # Robust name extraction
            s_name = next((c.text.strip() for c in sig.iter('SHORT-NAME') if c.text), None)
            if not s_name: 
                s_name = next((c.text.strip() for c in sig.iter('NAME') if c.text), f"UnknownSig_{s_id}")
            
            c_ref = None
            coding_ref_elem = sig.find('.//CODING-REF')
            if coding_ref_elem is not None: c_ref = coding_ref_elem.get('ID-REF')
                
            signal_map[s_id] = {"name": s_name, "coding_id": c_ref}

        # =========================================================
        # STEP 3: Map Start Bits and PDU Relationships
        # =========================================================
        # Find every instance where a signal is placed in a payload (Start Bit)
        for parent in root.iter():
            sr = parent.find('./SIGNAL-REF')
            if sr is not None:
                ref_id = sr.get('ID-REF')
                bp = parent.find('./BIT-POSITION')
                if ref_id and bp is not None and bp.text:
                    start_bit_map[ref_id] = int(bp.text.strip())

        # Link signals to their specific PDU (if they are inside one)
        for pdu in root.iter('PDU'):
            pdu_id = pdu.get('ID')
            for sr in pdu.iter('SIGNAL-REF'):
                if sr.get('ID-REF'): sig_to_pdu[sr.get('ID-REF')] = pdu_id

        # =========================================================
        # STEP 4: Map Multiplexing Rules
        # =========================================================
        for spi in root.iter('SWITCHED-PDU-INSTANCE'):
            switch_code = spi.find('./SWITCH-CODE')
            pdu_ref = spi.find('./PDU-REF')
            if switch_code is not None and pdu_ref is not None and switch_code.text:
                pdu_rules[pdu_ref.get('ID-REF')] = switch_code.text.strip()

        # =========================================================
        # STEP 5: Extract Controller Multiplexers (Offsets)
        # =========================================================
        for mux in root.iter('MULTIPLEXER'):
            switch = mux.find('./SWITCH')
            if switch is not None:
                s_name = switch.find('./SHORT-NAME').text.strip() if switch.find('./SHORT-NAME') is not None else "UnknownMux"
                s_bit = int(switch.find('./BIT-POSITION').text) if switch.find('./BIT-POSITION') is not None else 0
                s_len = int(switch.find('./BIT-LENGTH').text) if switch.find('./BIT-LENGTH') is not None else 8
                
                signals_final_info[s_name] = {
                    "role": "MULTIPLEXER", "start_bit": s_bit, "bit_length": s_len,
                    "factor": 1.0, "offset": 0.0, "is_signed": False, "mux_code": "CTRL" 
                }

        # =========================================================
        # STEP 6: Final Data Assembly
        # =========================================================
        for s_id, sig_info in signal_map.items():
            name = sig_info["name"]
            c_id = sig_info["coding_id"]
            
            # Determine role based on PDU mapping
            pdu_id = sig_to_pdu.get(s_id)
            mux_code = pdu_rules.get(pdu_id, "N/A") if pdu_id else "N/A"
            role = "multiplexed" if mux_code != "N/A" else "single"
            
            start_bit = start_bit_map.get(s_id, 0)
            math_data = codings_map.get(c_id, {"bit_length": 8, "factor": 1.0, "offset": 0.0, "is_signed": False})
            
            signals_final_info[name] = {
                "role": role,
                "start_bit": start_bit,
                "bit_length": math_data["bit_length"],
                "factor": math_data["factor"],
                "offset": math_data["offset"],
                "is_signed": math_data["is_signed"],
                "mux_code": mux_code
            }
        
        # =========================================================
        # PRINT OUTPUT
        # =========================================================
        print("\n" + "="*115)
        print(f"{'SIGNAL NAME':<30} | {'ROLE':<12} | {'CODE':<5} | {'START':<5} | {'LEN':<3} | {'S/U':<3} | {'FACTOR':<6} | {'OFFSET'}")
        print("="*115)
        
        count = 0
        for name, data in sorted(signals_final_info.items()):
            sign_char = "S" if data['is_signed'] else "U"
            print(f"{name:<30} | {data['role']:<12} | {data['mux_code']:<5} | {data['start_bit']:<5} | {data['bit_length']:<3} | {sign_char:<3} | {data['factor']:<6} | {data['offset']}")
            count += 1
            
        print("="*115)
        print(f"TOTAL SIGNALS EXTRACTED: {count}")
        print("="*115)
            
        return signals_final_info

    except Exception as e:
        logging.error(f"Critical Error: {e}", exc_info=True)

if __name__ == "__main__":
    test_fibex_parameter_extraction("FSAEE_CAN_DB.xml")