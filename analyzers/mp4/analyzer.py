from .file import File

import analyzers.aac
import syntax

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def get_views(self):
        views = []
        views.append(syntax.SyntaxView('MP4 File', self.stream, self.file.syntax_items()))
        views.append(analyzers.aac.StreamView(self.file.track(0)))
        return views