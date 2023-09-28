import sys
from colorgen import str_to_colorgen, ColorGen
from filehandler import FileHandler

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
