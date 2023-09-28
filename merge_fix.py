import sys
import re
from colorsys import hls_to_rgb, rgb_to_hls
import random

def calc_percent_along_loop(percent, start, end, loop):
    dist = abs(end-start)
    if loop != None:
        alt_dist = loop-dist
        if alt_dist < dist:
            return ((percent*alt_dist)+start)%loop
    return percent*dist+start

def col_on_gradient(percent, min_col, max_col, loop_col):
    return tuple([calc_percent_along_loop(percent,min,max,loop) for min, max, loop in zip(min_col, max_col, loop_col)])
    
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

class Rule:
    def __init__(self, str_):
        str_ = simplify_spaces(str_)
        self.typ = "hsl"
        portions = [s.strip() for s in str_.split(';')]
        if portions[0][0] == '#':
            self.typ = "hex"
            self.tup = portions[0]
        else:
            self.tup = read_tuple(portions[0])
        for portion in portions[1:]:
            rule, thing = portion.split(' ', 1)
            if rule == "vary":
                # vary h,s,l
                self.variance = read_tuple(thing)
            elif rule == "type":
                self.typ = thing
            elif rule == "gradient":
                # gradient row 0 0,0,0 50 100,50,50 100 360,100,100
                self.gradient = {}
                grad_typ, grads = thing.strip().split(' ', 1)
                grads = grads.split(' ')
                gradients = sorted([(int(percent)/100, read_tuple(thing)) for (percent, thing) in zip(grads[::2], grads[1::2])])
                self.gradient[grad_typ] = gradients
    
    def vary(self, col):
        return tuple([x+random.randint(-v,v) for x,v in zip(col, self.variance)])
        
    def get_our_grad(self, grad_typ, x, max_x):
        x = x/max_x
        prev_x = 2
        prev_col = self.gradient[grad_typ][0][1]
        for next_x, next_col in self.gradient[grad_typ]:
            if next_x > x:
                if x == next_x:
                    p = 1
                else:
                    p = (x-prev_x)/(next_x-prev_x)
                return (p,prev_col,next_col)
            prev_x = next_x
            prev_col = next_col
        return (1,prev_col,next_col)
        
    def gen_grad(self, row, col, max_row, max_col):
        if "row" in self.gradient:
            percent, begin_grad, end_grad = self.get_our_grad("row", row, max_row)
            return col_on_gradient(percent, begin_grad, end_grad, Color.loop(self.typ))
        elif "col" in self.gradient:
            percent, begin_grad, end_grad = self.get_our_grad("col", col, max_col)
            return col_on_gradient(percent, begin_grad, end_grad, Color.loop(self.typ))
    
    def color_tup(self, row,col,max_row,max_col):
        if hasattr(self, "gradient"):
            start_color = self.gen_grad(row,col,max_row,max_col)
        else:
            start_color = self.tup
        if hasattr(self, "variance"):
            return self.vary(start_color)
        else:
            return self.tup
    
    def color(self,row,col,max_row,max_col):
        return Color(self.typ, self.color_tup(row,col,max_row,max_col))

# stored internally as rgb (0-1) 
class Color:
    def __init__(self, typ, tup):
        self.__setitem__(typ,tup)
        
    def bound(typ):
        if typ == 'hsl':
            return ((360,100,100),(True,False,False))
        if typ == 'rgb':
            return ((255,255,255),(False,False,False))
    
    def loop(typ):
        bound1 = Color.bound(typ)
        return tuple([bound if loops else None for bound, loops in zip(bound1[0], bound1[1])])

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
        if typ == "hsl" or typ == 'rgb':
            h,s,l=tup
            (hb,sb,lb),(hl,sl,ll) = Color.bound('hsl')
            h=bound(0,hb,h,hl)
            s=bound(0,sb,s,sl)
            l=bound(0,lb,l,ll)
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
                    output_lines[i][j] += create_str(rules["type"],rules[input_lines[i][j]].color(i,j,len(input_lines),len(input_lines[i])))
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
