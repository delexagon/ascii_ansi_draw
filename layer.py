from filehandler import FileHandler
from colorgen import str_to_colorgen, ColorGen

def extend(str_, char, len_):
    if len(str_) < len_:
        return str_+char*(len_-len(str_))
    return str_

def squarify(lines, size):
    for i in range(len(lines)):
        if len(lines[i]) < size[1]:
            lines[i] = extend(lines[i], " ", size[1])
    while i < size[0]-1:
        lines.append(' '*size[1])
        i += 1
    return lines
    
def get_drawing(f):
    lines = []
    for line in f:
        if line[0] != '`':
            f.put_back(line)
            if len(lines) == 0:
                return None
            return lines
        lines.append(line[1:].rstrip('\n'))
    if len(lines) == 0:
        return None
    return lines
            
# Make a map from char -> rule string for output.
# How these rule strings will be interpreted depends on the sublayer type.
def get_rulestrs(f):
    rules = {}
    for line in f:
        line = line.rstrip('\n')
        if line in sublayer_types:
            f.put_back(line)
            return rules
        char,output = line.split('->')
        rules[char] = output
    return rules
    
def calc_size(lines):
    max_len = 0
    for line in lines:
        if len(line) > max_len:
            max_len = len(line)
    return (len(lines), max_len)

def get_sublayer(layerfile):
    layer_type = layerfile.readline().rstrip('\n')
    unsized_drawing = get_drawing(layerfile)
    size = calc_size(unsized_drawing)
    rulestrs = get_rulestrs(layerfile)
    return (layer_type, unsized_drawing, rulestrs, size)
   
def interpret_rulestrs(rulestrs, sublayer_type):
    for char, rulestr in rulestrs.items():
        if sublayer_type == 'background' or sublayer_type == 'foreground':
            rulestrs[char] = str_to_colorgen(rulestrs[char])
        else:
            rulestrs[char] = None
    return rulestrs

class LayerOutput:
    def __init__(self, size):
        self.chars = []
        self.fg = []
        self.bg = []
        for i in range(size[0]):
            self.chars.append([None]*size[1])
            self.fg.append([None]*size[1])
            self.bg.append([None]*size[1])
    
    # Puts another layer in the 'background', if there is nothing there already
    def append(self, other):
        attrs = 'chars', 'fg', 'bg'
        for i in range(len(self.chars)):
            for j in range(len(self.chars[i])):
                for attr in attrs:
                    if getattr(self, attr)[i][j] == None and getattr(other, attr)[i][j] != None:
                        getattr(self, attr)[i][j] = getattr(other, attr)[i][j]
    
    def to_string(self):
        strout = ""
        for i in range(len(self.chars)):
            for j in range(len(self.chars[i])):
                strout += ColorGen.rgb_to_ansi_str(self.bg[i][j], 'background')
                strout += ColorGen.rgb_to_ansi_str(self.fg[i][j], 'foreground')
                strout += self.chars[i][j]
            strout += '\x1b[0m\n'
        return strout

def place_colorgen_rules(chars, placemat, rules, environment):
    for i in range(len(chars)):
        environment['row'] = i
        for j in range(len(chars[i])):
            environment['col'] = j
            if chars[i][j] in rules:
                placemat[i][j] = rules[chars[i][j]].generate_rgb(environment)
    return placemat

def place_char_rules(chars, placemat, rules, environment):
    for i in range(len(chars)):
        environment['row'] = i
        for j in range(len(chars[i])):
            environment['col'] = j
            placemat[i][j] = chars[i][j]
    return placemat

sublayer_types = ['background', 'foreground', 'chars']
class Layer:
    def __init__(self, layerfile_path):
        self.size = (0,0)
        self.sublayers = []
        layerfile = FileHandler(layerfile_path)
        while not layerfile.at_end():
            sublayer_type, unsized_drawing, rulestrs, size = get_sublayer(layerfile)
            self.size = tuple(map(max, self.size, size))
            self.sublayers.append((sublayer_type, unsized_drawing, rulestrs))
        for i, (sublayer_type, unsized_drawing, rulestrs) in enumerate(self.sublayers):
            drawing = squarify(unsized_drawing, size)
            rules = interpret_rulestrs(rulestrs, sublayer_type)
            self.sublayers[i] = (sublayer_type, drawing, rules)
        layerfile.close()
        
    def compose(self, other_layers):
        environment = {
            'row_max': self.size[0],
            'col_max': self.size[1]
        }
        output = LayerOutput(self.size)
        for sublayer in self.sublayers:
            sublayer_type, drawing, rules = sublayer
            environment['sublayer'] = sublayer_type
            if sublayer_type == 'background':
                place_colorgen_rules(drawing, output.bg, rules, environment)
            elif sublayer_type == 'foreground':
                place_colorgen_rules(drawing, output.fg, rules, environment)
            elif sublayer_type == 'chars':
                place_char_rules(drawing, output.chars, rules, environment)
        return output
