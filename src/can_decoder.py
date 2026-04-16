import logging

# Configurazione logging per i test standalone
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

class CanDecoder:
    """
    Motore matematico per il Bit Unpacking dei payload CAN.
    Isola la logica di estrazione dei bit per garantirne la testabilità.
    """
    
    @staticmethod
    def extract_raw_value(payload: list[int], start_bit: int, bit_length: int, is_little_endian: bool = True) -> int:
        """
        Estrae un valore intero crudo (Raw Integer) da un array di byte.
        
        :param payload: Lista di interi che rappresentano i byte (es. [0x00, 0x03, 0x09, 0x0A, ...])
        :param start_bit: Il bit di partenza (0-63)
        :param bit_length: La lunghezza del segnale in bit (1-64)
        :param is_little_endian: True per Intel, False per Motorola
        :return: Valore intero estratto
        """
        # Assicuriamoci che il payload sia di 8 byte (64 bit) riempiendo con zeri se è più corto (DLC < 8)
        padded_payload = payload + [0] * (8 - len(payload))
        
        if is_little_endian:
            # 1. Convertiamo l'intero array di byte in un gigantesco numero intero a 64 bit.
            # In Little Endian, il Byte 0 è la parte destra (meno significativa) del numero.
            full_64bit_int = int.from_bytes(padded_payload, byteorder='little')
            
            # 2. Shifto a destra il numero in modo che il nostro 'start_bit' diventi il bit 0.
            shifted_int = full_64bit_int >> start_bit
            
            # 3. Creo una maschera composta da '1' lunga esattamente 'bit_length'.
            # Se bit_length è 8, la maschera sarà 11111111 in binario (0xFF).
            mask = (1 << bit_length) - 1
            
            # 4. Applico l'AND logico per "ritagliare" solo i nostri bit.
            extracted_value = shifted_int & mask
            
            return extracted_value
            
        else:
            # Il formato Motorola (Big Endian) ha una numerazione dei bit a dente di sega.
            # Lo implementeremo nel prossimo step se il tuo database lo richiede.
            raise NotImplementedError("Formato Motorola non ancora implementato.")

    @staticmethod
    def apply_scaling(raw_value: int, factor: float, offset: float) -> float:
        """
        Applica la trasformazione lineare per ottenere il valore fisico (es. Volt, RPM).
        """
        return (raw_value * factor) + offset