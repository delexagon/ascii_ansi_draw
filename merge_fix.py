import sys
from layer import Layer

if __name__ == "__main__":
    args = sys.argv[1:]
    
    layers = []
    for arg in args:
        layers.append(Layer(arg))
    outputs = []
    for layer in layers:
        outputs.append(layer.compose(outputs))
    
    with open("output.csl", 'w') as f:
        f.write(outputs[-1].to_string())
