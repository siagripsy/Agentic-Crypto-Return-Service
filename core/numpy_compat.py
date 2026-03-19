"""
Custom pickle handler for numpy compatibility
Handles old pickled numpy models that reference classes that no longer exist
"""
import sys
import numpy as np

def setup_numpy_compatibility():
    """
    Setup numpy compatibility for old pickles.
    Adds compatibility shims for numpy.random classes that changed between versions.
    """
    import numpy.random as nr
    
    # Create dummy classes for old numpy.random internals
    class MT19937:
        """Dummy MT19937 for old pickles"""
        def __init__(self):
            self.state = None
    
    class RandomState:
        """Dummy RandomState for old pickles"""
        def __init__(self):
            self.state = None
    
    class Generator:
        """Dummy Generator for old pickles"""
        def __init__(self):
            self.bit_generator = None
    
    # Register these in numpy.random so pickle can find them
    if not hasattr(nr, 'MT19937'):
        nr.MT19937 = MT19937
    if not hasattr(nr, 'RandomState'):
        nr.RandomState = RandomState
    if not hasattr(nr, 'Generator'):
        nr.Generator = Generator
    
    # Also add to sys.modules for pickle's import system
    numpy_random_module = sys.modules.get('numpy.random')
    if numpy_random_module:
        if not hasattr(numpy_random_module, 'MT19937'):
            numpy_random_module.MT19937 = MT19937
        if not hasattr(numpy_random_module, 'RandomState'):
            numpy_random_module.RandomState = RandomState
        if not hasattr(numpy_random_module, 'Generator'):
            numpy_random_module.Generator = Generator

if __name__ == "__main__":
    setup_numpy_compatibility()
    print("✅ Numpy compatibility patching activated")
