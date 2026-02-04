"""
Privacy Amplification using Toeplitz Matrix Universal Hashing

Implements QKD-standard privacy amplification using Toeplitz matrices.
This provides information-theoretically secure key compression based on
universal hashing theory.

Algorithm:
1. Generate a random Toeplitz matrix
2. Perform binary matrix-vector multiplication (mod 2)
3. Output compressed secret key

A Toeplitz matrix is defined by its first row and first column,
where each descending diagonal is constant.
"""

import random


def toeplitz_privacy_amplification(error_corrected_key_bits, output_length=None, qber=None):
    """
    Perform privacy amplification using Toeplitz matrix universal hashing.
    
    Args:
        error_corrected_key_bits (list or str): Error-corrected key as list of bits (0/1)
                                               or string of '0'/'1' characters
        output_length (int, optional): Desired output key length in bits.
                                       If None, uses QBER-based or default reduction
        qber (float, optional): Quantum Bit Error Rate (0-1) for security parameter calculation
    
    Returns:
        str: Final secret key as hexadecimal string (compatible with existing code)
    """
    # Convert input to list of bits
    if isinstance(error_corrected_key_bits, str):
        # If it's a string like "101010", convert to list
        key_bits = [int(b) for b in error_corrected_key_bits]
    else:
        # Assume it's already a list
        key_bits = [int(b) for b in error_corrected_key_bits]
    
    input_length = len(key_bits)
    
    if input_length == 0:
        return ""
    
    # Determine output length
    if output_length is None:
        # Default: reduce by ~25% or use QBER-based calculation
        if qber is not None:
            # Security: reduce key length based on error rate
            # Simple approach: output_length = input_length * (1 - qber - security_margin)
            security_margin = 0.1  # 10% security margin
            output_length = int(input_length * (1 - qber - security_margin))
            output_length = max(8, output_length)  # Minimum 8 bits
        else:
            # Default: reduce by 25%
            output_length = int(input_length * 0.75)
            output_length = max(8, min(output_length, input_length - 1))
    
    # Ensure output_length is valid
    output_length = max(1, min(output_length, input_length))
    
    # Generate random Toeplitz matrix
    # A Toeplitz matrix T of size (output_length x input_length) is defined by:
    # - First row: [t_0, t_1, ..., t_{input_length-1}]
    # - First column: [t_0, t_{-1}, ..., t_{-(output_length-1)}]
    # For a total of (input_length + output_length - 1) random bits
    
    # Generate random bits for Toeplitz matrix construction
    toeplitz_seed_bits = [random.randint(0, 1) for _ in range(input_length + output_length - 1)]
    
    # Construct Toeplitz matrix
    # Matrix element T[i][j] = toeplitz_seed_bits[input_length - 1 + i - j]
    # where i in [0, output_length-1] and j in [0, input_length-1]
    
    # Perform matrix-vector multiplication: output = T * key_bits (mod 2)
    output_bits = []
    for i in range(output_length):
        result = 0
        for j in range(input_length):
            # Get Toeplitz matrix element T[i][j]
            idx = input_length - 1 + i - j
            if 0 <= idx < len(toeplitz_seed_bits):
                matrix_element = toeplitz_seed_bits[idx]
            else:
                matrix_element = 0
            
            # Multiply and accumulate (mod 2)
            result = (result + matrix_element * key_bits[j]) % 2
        
        output_bits.append(result)
    
    # Convert binary list to hex string (compatible with existing code)
    # Group bits into bytes (8 bits per byte)
    hex_string = ""
    for i in range(0, len(output_bits), 8):
        byte_bits = output_bits[i:i+8]
        # Pad if needed
        while len(byte_bits) < 8:
            byte_bits.append(0)
        
        # Convert 8 bits to integer
        byte_value = sum(bit * (2 ** (7 - j)) for j, bit in enumerate(byte_bits))
        # Convert to hex (2 characters)
        hex_string += f"{byte_value:02x}"
    
    return hex_string


def privacy_amplify(error_corrected_key, qber=None):
    """
    Convenience wrapper for privacy amplification.
    Converts error_corrected_key string to bits and applies Toeplitz hashing.
    
    Args:
        error_corrected_key (str): Error-corrected key as string of '0'/'1' characters
        qber (float, optional): Quantum Bit Error Rate for security parameter
    
    Returns:
        str: Final secret key as hexadecimal string
    """
    # Use default output length (will be calculated based on input length and QBER)
    return toeplitz_privacy_amplification(error_corrected_key, output_length=None, qber=qber)
