"""
Cascade Error Correction Protocol for BB84 QKD

Implements the Cascade protocol for error correction in quantum key distribution.
Cascade uses multiple rounds with random shuffling and binary search to locate
and correct errors in Bob's key.

Algorithm:
1. Multiple rounds (typically 3-5)
2. In each round, randomly shuffle indices
3. Divide into blocks and compute parity
4. If parity differs, use binary search to locate error
5. Flip the erroneous bit
6. Repeat for multiple rounds to catch remaining errors
"""

import random


def cascade_error_correction(alice_bits, bob_bits, num_rounds=4, initial_block_size=8):
    """
    Perform Cascade error correction protocol on Bob's bits.
    
    Args:
        alice_bits (list): Alice's sifted key bits (reference)
        bob_bits (list): Bob's sifted key bits (to be corrected)
        num_rounds (int): Number of Cascade rounds (default: 4)
        initial_block_size (int): Initial block size for first round (default: 8)
    
    Returns:
        list: Bob's corrected key bits
    """
    if len(alice_bits) != len(bob_bits):
        raise ValueError("Alice and Bob bit sequences must have the same length")
    
    if len(alice_bits) == 0:
        return []
    
    # Work with copies to avoid modifying originals
    alice = list(alice_bits)
    bob = list(bob_bits)
    n = len(alice)
    
    # Create index mapping for shuffling
    indices = list(range(n))
    
    # Track which positions have been corrected (for efficiency)
    # In practice, we'll correct all errors we find
    
    # Perform multiple rounds
    for round_num in range(num_rounds):
        # Calculate block size for this round
        # Block size doubles each round: 8, 4, 2, 1, ...
        block_size = initial_block_size // (2 ** round_num)
        if block_size < 1:
            block_size = 1
        
        # Randomly shuffle indices at the start of each round (except first)
        if round_num > 0:
            random.shuffle(indices)
        
        # Process blocks
        i = 0
        while i < n:
            # Get current block
            block_end = min(i + block_size, n)
            block_indices = indices[i:block_end]
            
            if len(block_indices) == 0:
                break
            
            # Compute parity for Alice and Bob
            alice_parity = sum(alice[idx] for idx in block_indices) % 2
            bob_parity = sum(bob[idx] for idx in block_indices) % 2
            
            # If parities differ, there's an error in this block
            if alice_parity != bob_parity:
                # Use binary search to locate the error
                error_idx = _binary_search_error(alice, bob, block_indices)
                if error_idx is not None:
                    # Flip the erroneous bit
                    bob[error_idx] ^= 1
            
            i = block_end
    
    return bob


def _binary_search_error(alice, bob, block_indices):
    """
    Use binary search to locate the error within a block.
    
    Args:
        alice (list): Alice's bits
        bob (list): Bob's bits
        block_indices (list): Indices in the current block
    
    Returns:
        int or None: Index of the error, or None if not found
    """
    if len(block_indices) == 0:
        return None
    
    if len(block_indices) == 1:
        # Single bit block - this must be the error
        return block_indices[0]
    
    # Split block in half
    mid = len(block_indices) // 2
    left_indices = block_indices[:mid]
    right_indices = block_indices[mid:]
    
    # Check parity of left half
    left_alice_parity = sum(alice[idx] for idx in left_indices) % 2
    left_bob_parity = sum(bob[idx] for idx in left_indices) % 2
    
    # If left half has parity mismatch, error is in left half
    if left_alice_parity != left_bob_parity:
        return _binary_search_error(alice, bob, left_indices)
    else:
        # Error is in right half
        return _binary_search_error(alice, bob, right_indices)
