from . import parse

import analyzers.aac
import syntax

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = parse.File(stream)

    def get_views(self):
        views = []
        views.append(syntax.SyntaxView('MP4 File', self.stream, self.file.syntax_items()))
        for i in range(self.file.numtracks()):
            track = self.file.track(i)
            es_descriptor = track.es_descriptor()
            if es_descriptor:
                decoder_config = es_descriptor.decConfigDescr
                if decoder_config.streamType == 5 and decoder_config.objectTypeIndication == 0x40:
                    audio_specific = decoder_config.decSpecificInfo
                    if audio_specific.audioObjectType == 2:
                        title = 'Track %i (AAC audio)' % i
                        views.append(analyzers.aac.StreamView(track, title))

        return views