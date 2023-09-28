    
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
        