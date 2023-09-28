import sys
import re
import colorsys
import random

def calc_percent_along_loop(percent, start, end, loop):
    dist = abs(end-start)
    if loop != None:
        alt_dist = loop-dist
        if alt_dist < dist:
            return ((percent*alt_dist)+start)%loop
    return percent*dist+start

def calc_tuple_percent_along_loop(percent, start_tup, end_tup, loop_tup):
    return tuple([calc_percent_along_loop(percent,min,max,loop) for min, max, loop in zip(start_tup, end_tup, loop_tup)])
    
def bound(lower, higher, i, loop):
    if loop and (i < lower or i > higher):
        return ((i-lower)%(higher-lower))+lower
    if i < lower:
        return lower
    elif i > higher:
        return higher
    return i

def simplify_spaces(line):
    return re.sub(r'[ \t]+', ' ', line.strip())

def read_tuple(str_):
    return tuple(map(lambda x: int(x), str_.split(',')))

def str_to_colorgen(str_):
    str_ = simplify_spaces(str_)
    format = None
    base_color = None
    portions = [s.strip() for s in str_.split(';')]
    arguments = {}
    if portions[0][0] == '#':
        format = "hex"
        base_color = portions[0]
        portions = portions[1:]
    elif portions[0][0].isdigit():
        base_color = portions[0]
        portions = portions[1:]
        
    for portion in portions:
        rule, thing = portion.split(' ', 1)
        if rule == "vary":
            # vary h,s,l
            arguments['vary'] = read_tuple(thing)
        elif rule == "type":
            format = thing
        elif rule == "gradient":
            # gradient row 0 0,0,0 50 100,50,50 100 360,100,100
            arguments['gradient_type'], gradient = thing.strip().split(' ', 1)
            gradient = gradient.split(' ')
            arguments['gradient'] = sorted([(int(percent)/100, read_tuple(thing)) for (percent, thing) in zip(gradient[::2], gradient[1::2])])
    return ColorGen(base_color, arguments, format=format)
            
class ColorGen:
    def __init__(self, base_color_str, arg_dict, format='hsl'):
        self.format = format if format != None else 'hsl'
        if format == 'hex':
            self._color = tuple(int(base_color_str.lstrip("#")[i:i+2], 16)/255 for i in (0, 2, 4))
        else:
            self._color = read_tuple(base_color_str) if base_color_str != None and base_color_str != '' else (0,0,0)
        self.arguments = arg_dict
    
    def _hsl_to_rgb(tup):
        h,s,l = tup
        return tuple([round(x*bound) for x,bound in zip(colorsys.hls_to_rgb(h,l,s), ColorGen._full_bound('rgb')[0])])
    
    def _hsv_to_rgb(tup):
        h,s,v = tup
        return tuple([round(x*bound) for x,bound in zip(colorsys.hsv_to_rgb(h,s,v), ColorGen._full_bound('rgb')[0])])
    
    def _full_bound(typ):
        if typ == 'hsl':
            return ((360,100,100),(True,False,False))
        elif typ == 'hsv':
            return ((360,100,100),(True,False,False))
        elif typ == 'rgb':
            return ((255,255,255),(False,False,False))
        elif typ == 'hex':
            return ((255,255,255),(False,False,False))
            
    def loop(typ):
        full_bound = ColorGen._full_bound(typ)
        return tuple([bound if loops else None for bound, loops in zip(full_bound[0], full_bound[1])])
    
    def _to_rgb(color, typ):
        if typ == 'rgb' or typ == 'hex':
            return color
        elif typ == 'hsv' or typ == 'hsl':
            full_bound = ColorGen._full_bound(typ)
            func = ColorGen._hsv_to_rgb if typ == 'hsv' else ColorGen._hsl_to_rgb
            return func([x/b for (x,b) in zip(color, full_bound[0])])
            
    def _grad_percent_min_max(gradient, percentage_along):
        prev_percent = gradient[0][0]
        prev_col = gradient[0][1]
        for next_percent, next_col in gradient:
            if next_percent >= percentage_along:
                if percentage_along == next_percent:
                    p = 1
                else:
                    p = (percentage_along-prev_percent)/(next_percent-prev_percent)
                return (p,prev_col,next_col)
            prev_percent,prev_col = (next_percent,next_col)
        return (1,prev_col,next_col)
    
    def get_color_on_gradient(self, type, environment):
        gradient = self.arguments['gradient']
        type_max = type+'_max'
        x = environment[type]
        x_max = environment[type_max]
        percent_along = x/x_max
        percent_between, start_col, end_col = ColorGen._grad_percent_min_max(gradient, percent_along)
        return calc_tuple_percent_along_loop(percent_between, start_col, end_col, ColorGen.loop(self.format))
        
    def vary(color, variance, full_bound):
        varied = [x+random.randint(-v,v) for x,v in zip(color, variance)]
        bounded = [bound(0,max,x,loop) for x,max,loop in zip(varied, full_bound[0], full_bound[1])]
        return tuple(bounded)
        
    def rgb_to_ansi_str(rgb, type):
        r,g,b = rgb
        if type == 'background':
            return f"\x1b[48;2;{r};{g};{b}m"
        elif type == 'foreground':
            return f"\x1b[38;2;{r};{g};{b}m"
        else:
            return ''
    
    def generate_rgb(self, environment):
        if 'gradient' in self.arguments and 'gradient_type' in self.arguments:
            color = self.get_color_on_gradient(self.arguments["gradient_type"], environment)
            if color == None:
                color = self._color
        else:
            color = self._color
        if 'vary' in self.arguments:
            color = ColorGen.vary(color, self.arguments['vary'], ColorGen._full_bound(self.format))
        return ColorGen._to_rgb(color,self.format)

def extend(str_, char, len_):
    if len(str_) < len_:
        return str_+char*(len_-len(str_))
    return str_

def squarify(lines, length):
    for i in range(len(lines)):
        if len(lines[i]) < length:
            lines[i] = extend(lines[i], " ", length)
    return lines

# rule: (True, set()) -> in set of characters, (False, set()) -> not in set of characters
def replace(rules, input_lines, output_lines, end, sublayer):
    environment = {'sublayer': sublayer, 'row_max': len(input_lines), 'col_max': len(input_lines[0])}
    for i in range(len(input_lines)):
        for j in range(len(input_lines[i])):
            if rules == None:
                output_lines[i][j] += input_lines[i][j]+end
            else:
                if input_lines[i][j] in rules:
                    colorgen = rules[input_lines[i][j]]
                    environment['row'] = i
                    environment['col'] = j
                    output_lines[i][j] += ColorGen.rgb_to_ansi_str(colorgen.generate_rgb(environment), sublayer)
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
    
class FileHandler:
    def __init__(self, *args, **kwargs):
        self.prev_lines = []
        self._file = open(*args, **kwargs)
    
    def put_back(self,line):
        self.prev_lines.append(line)
    
    def __iter__(self):
        return self
        
    def __next__(self, *args, **kwargs):
        if len(self.prev_lines) > 0:
            return self.prev_lines.pop()
        return self._file.__next__(*args, **kwargs)
        
    def readline(self, *args, **kwargs):
        if len(self.prev_lines) > 0:
            return self.prev_lines.pop()
        return self._file.readline(*args, **kwargs)
        
    def at_end(self):
        line = self.readline()
        if line == '':
            return True
        self.put_back(line)
        return False
        
    def readlines(self, *args, **kwargs):
        prev_lines = list(reversed(self.prev_lines))
        self.prev_lines = []
        return prev_lines+self._file.readlines(*args, **kwargs)
        
    def close(self):
        self._file.close()
    
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
        
def get_rules(f, type_):
    rules = {"type":type_}
    for line in f:
        line = line.rstrip('\n')
        if line in sublayer_types:
            f.put_back(line)
            if len(rules) == 1:
                return None
            return rules
        char,output = line.split('->')
        rules[char] = str_to_colorgen(output)
    if len(rules) == 1:
        return None
    return rules

sublayer_types = ["background", "foreground", "chars"]
def read_layerfile(layerfile):
    sublayers = {typ: None for typ in sublayer_types}
    size = None
    f = FileHandler(layerfile)
    while not f.at_end():
        current_layer_type = f.readline().rstrip('\n')
        if size == None:
            uncalc_drawing = get_drawing(f)
            size = calc_size(uncalc_drawing)
            drawing = squarify(uncalc_drawing, size[1])
        else:
            drawing = squarify(get_drawing(f), size[1])
        rules = get_rules(f, current_layer_type)
        sublayers[current_layer_type] = (drawing, rules)
    f.close()
    return (sublayers,size)


end = {"background":None, "foreground":None, "chars":'\x1b[0m'}
if __name__ == "__main__":
    args = sys.argv[1:]
    layer, size = read_layerfile(args[0])
    output = create_output(size[0], size[1])
    
    for sublayer in sublayer_types:
        replace(layer[sublayer][1], layer[sublayer][0], output, end[sublayer], sublayer)
    with open("output.csl", 'w') as f:
        output_lines = [''.join(l) for l in output]
        f.write('\n'.join(output_lines))
        f.write('\n')
