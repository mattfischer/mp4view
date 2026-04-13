from .file import File

from syntax import SyntaxView

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def analyze(self):
        view = SyntaxView('MP4 File', self.stream, self.file.syntax_items())
        return [view]