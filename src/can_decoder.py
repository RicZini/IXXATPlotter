import logging

class CanDecoder:
    """
    Mathematical engine for CAN payload Bit Unpacking.
    Isolates the bit extraction logic to ensure testability.
    """
    
    @staticmethod
    def extract_raw_value(payload: list[int], start_bit: int, bit_length: int, is_little_endian: bool = True) -> int:
        """
        Extracts a raw integer value from a byte array.
        
        :param payload: List of integers representing the bytes (e.g., [0x00, 0x03, 0x09, 0x0A, ...])
        :param start_bit: The starting bit (0-63)
        :param bit_length: The signal length in bits (1-64)
        :param is_little_endian: True for Intel format, False for Motorola format
        :return: Extracted integer value
        """
        # Ensure the payload is 8 bytes (64 bits) by padding with zeros if it's shorter (DLC < 8)
        padded_payload = payload + [0] * (8 - len(payload))
        
        if is_little_endian:
            # 1. Convert the entire byte array into a giant 64-bit integer.
            # In Little Endian, Byte 0 is the rightmost (least significant) part of the number.
            full_64bit_int = int.from_bytes(padded_payload, byteorder='little')
            
            # 2. Shift the number to the right so that our 'start_bit' becomes bit 0.
            shifted_int = full_64bit_int >> start_bit
            
            # 3. Create a mask composed of '1's exactly 'bit_length' long.
            # If bit_length is 8, the mask will be 11111111 in binary (0xFF).
            mask = (1 << bit_length) - 1
            
            # 4. Apply logical AND to "cut out" only our specific bits.
            extracted_value = shifted_int & mask
            
            return extracted_value
            
        else:
            # The Motorola format (Big Endian) uses a sawtooth bit numbering scheme.
            # It can be implemented here if the database requires it in the future.
            raise NotImplementedError("Motorola format is not implemented yet.")

    @staticmethod
    def apply_scaling(raw_value: int, factor: float, offset: float) -> float:
        """
        Applies the linear transformation to obtain the physical value (e.g., Volts, RPM).
        """
        return (raw_value * factor) + offset

if __name__ == "__main__":
    # =====================================================================
    # TEST DRIVE: Let's use a sample payload to verify the math
    # =====================================================================

    # Logging configuration for standalone testing
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

    print("--- Testing Multiplexer and Data Decoding ---")
    
    # Example payload: 00 03 09 0A (Remaining bytes are 00)
    test_payload = [0x00, 0x03, 0x09, 0x0A, 0x00, 0x00, 0x00, 0x00]
    
    # 1. Extract the OFFSET (Byte 0 -> bits 0 to 7)
    offset_val = CanDecoder.extract_raw_value(test_payload, start_bit=0, bit_length=8)
    logging.info(f"Multiplexer (Offset): {offset_val}  [Expected: 0]")
    
    # 2. Extract X1 (Byte 1 -> bits 8 to 15)
    x1_val = CanDecoder.extract_raw_value(test_payload, start_bit=8, bit_length=8)
    logging.info(f"Data X1: {x1_val}  [Expected: 3]")
    
    # 3. Extract X2 (Byte 2 -> bits 16 to 23)
    x2_val = CanDecoder.extract_raw_value(test_payload, start_bit=16, bit_length=8)
    logging.info(f"Data X2: {x2_val}  [Expected: 9]")
    
    # 4. Extract X3 (Byte 3 -> bits 24 to 31)
    x3_val = CanDecoder.extract_raw_value(test_payload, start_bit=24, bit_length=8)
    logging.info(f"Data X3: {x3_val}  [Expected: 10]")
    
    # Extreme test: a 12-bit signal crossing a byte boundary!
    # Using FF FF (11111111 11111111). Taking the first 12 bits, we expect 4095 (0xFFF)
    test_payload_12bit = [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    val_12bit = CanDecoder.extract_raw_value(test_payload_12bit, start_bit=0, bit_length=12)
    logging.info(f"Test 12-bit crossing byte boundary: {val_12bit} [Expected: 4095]")