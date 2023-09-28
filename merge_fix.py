import sys
import re
from colorsys import hls_to_rgb, rgb_to_hls
import random
    
def bound(lower, higher, i):
    if i < lower:
        return lower
    elif i > higher:
        return higher
    return i

def simplify_spaces(line):
    return re.sub(r'[ \t]+', ' ', line.strip())

class Rule:
    def __init__(self, str_):
        str_ = simplify_spaces(str_)
        self.typ = "hsl"
        portions = [s.strip() for s in str_.split(';')]
        if portions[0][0] == '#':
            self.typ = "hex"
            self.tup = portions[0]
        else:
            self.tup = tuple(map(lambda x: int(x), portions[0].split(',')))
        for portion in portions[1:]:
            rule, thing = portion.split(' ')
            if rule == "vary":
                self.variance = tuple(map(lambda x: int(x), thing.split(',')))
    
    def vary(self, i):
        return self.tup[i]+random.randint(-self.variance[i],self.variance[i])
    
    def color_tup(self):
        if hasattr(self, "variance"):
            return (self.vary(0),self.vary(1),self.vary(2))
        else:
            return self.tup
    
    def color(self):
        return Color(self.typ, self.color_tup())

# stored internally as rgb (0-1) 
class Color:
    def __init__(self, typ, tup):
        self.__setitem__(typ,tup)

    def __getitem__(self, typ):
        if typ == "hsl":
            r,g,b=self.rgb
            h,l,s = rgb_to_hls()
            return (round(h*360), round(s*100), round(l*100))
        elif typ == "hex":
            return '#%02x%02x%02x' % tuple(map(lambda x: round(x*255), self.rgb))
        elif typ == "rgb":
            return tuple(map(lambda x: round(x*255), self.rgb))
    
    def __setitem__(self, typ, tup):
        if typ == "hsl":
            h,s,l=tup
            h=bound(0,360,h)
            s=bound(0,100,s)
            l=bound(0,100,l)
            self.rgb = hls_to_rgb(h/360,l/100,s/100)
        elif typ == "hex":
            self.rgb = tuple(int(tup.lstrip("#")[i:i+2], 16)/255 for i in (0, 2, 4))
        elif typ == "rgb":
            self.rgb = tuple(map(lambda x: x/255, rgb))

def extend(str_, char, len_):
    if len(str_) < len_:
        return str_+char*(len_-len(str_))
    return str_

def squarify(lines, length):
    for i in range(len(lines)):
        if len(lines[i]) < length:
            lines[i] = extend(lines[i], " ", length)
    return lines

def create_str(typ, col):
    r,g,b = col["rgb"]
    if typ == 'background':
        return f"\x1b[48;2;{r};{g};{b}m"
    elif typ == 'foreground':
        return f"\x1b[38;2;{r};{g};{b}m"
    else:
        return ""

# rule: (True, set()) -> in set of characters, (False, set()) -> not in set of characters
def replace(rules, input_lines, output_lines, end):
    for i in range(len(input_lines)):
        for j in range(len(input_lines[i])):
            if rules == None:
                output_lines[i][j] += input_lines[i][j]+end
            else:
                if input_lines[i][j] in rules:
                    output_lines[i][j] += create_str(rules["type"],rules[input_lines[i][j]].color())
    return output_lines

def create_output(lines, chars):
    output = []
    for i in range(lines):
        output.append([""]*chars)
    return output
    
def calc_size(lines):
    max_len = 0
    for line in lines:
        if len(line) > max_len:
            max_len = len(line)
    return (len(lines), max_len)

def import_rules(rulefile):
    rules = {}
    with open(rulefile) as f:
        rules["type"] = f.readline().rstrip('\n')
        for line in f:
            line = line.rstrip('\n')
            char,output = line.split('->')
            rules[char] = Rule(output)
    return rules
    
def import_layer(layerfile):
    lines = []
    with open(layerfile) as f:
        for line in f:
            lines.append(line.rstrip('\n'))
    return lines

if __name__ == "__main__":
    final_layer = sys.argv[-1]
    args = sys.argv[1:-1]
    final_layer = import_layer(final_layer)
    size = calc_size(final_layer)
    final_layer = squarify(final_layer, size[1])
    
    output = create_output(size[0], size[1])
    for layerfile, rulesfile in zip(args[::2], args[1::2]):
        layer = squarify(import_layer(layerfile), size[1])
        rules = import_rules(rulesfile)
        replace(rules, layer, output, None)
    replace(None, final_layer, output, '\x1b[0m')
    with open("output.csl", 'w') as f:
        output_lines = [''.join(l) for l in output]
        f.write('\n'.join(output_lines))
        f.write('\n')
