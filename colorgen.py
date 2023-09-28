import colorsys
import re
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