import warnings

from expression import Expression


def duration_num_to_str(duration_num, measure_duration):
    max_denominator = 1024
    if duration_num <= measure_duration:
        if 1 / duration_num == int(1 / duration_num):
            return str(int(1 / duration_num))
        elif 1.5 / duration_num == int(1.5 / duration_num):
            return f"{int(1.5 / duration_num)}."
        else:
            denominator = 1
            while (abs(duration_num - int(duration_num)) > denominator / (max_denominator * 2) and
                   denominator < max_denominator):
                duration_num *= 2
                denominator *= 2
            return f"{denominator}*{int(duration_num)}"
    else:
        measure_str = duration_num_to_str(measure_duration, measure_duration)
        if duration_num / measure_duration == int(duration_num / measure_duration):
            return f"{measure_str}*{int(duration_num / measure_duration)}"
        else:
            return duration_num_to_str(duration_num, duration_num)


class Note:
    alter_dict = {None: "", '1': "s", '-1': "f"}
    duration_dict = {
        "whole": '1',
        "half": '2',
        "quarter": '4',
        "eighth": '8',
        "16th": '16',
        "32nd": '32'
    }
    art_dict = {"staccato": '.', "tenuto": '-', "snap-pizzicato": '\\snappizzicato', 'accent': '>', 'down-bow': '\\db',
                'up-bow': '\\ub'}
    slur_dict = {"start": '(', "stop": ')'}
    tie_dict = {"start": '~', "stop": ''}

    def __init__(self, note_element, time_info, measure_num="-1", in_cue=False, **kwargs):
        self.pitch = ['']
        self.duration = ''
        self.duration_num = 0  # as a float, proportion of a whole note
        self.dot = ''
        self.grace = ''
        self.start_tuplet = ''
        self.end_tuplet = ''
        self.articulations = ''
        self.slur = ''
        self.tie = ''
        self.chord = False
        self.expression = Expression('')
        self.start_poly = ''
        self.end_poly = ''
        self.trill = ''
        self.next_expression_buffer = Expression('')
        self.in_cue = in_cue
        self.cue = False
        self.start_cue = ''
        self.end_cue = ''
        self.should_end_cue = False
        self.glissando = ''

        divisions, measure_duration = time_info
        written_duration = 0
        num = 0
        den = 0

        if note_element is None:
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.duration = duration_num_to_str(self.duration_num, measure_duration)
            return

        for note_child in note_element:
            match note_child.tag:
                case "chord":
                    self.chord = True
                case "pitch":
                    pitch = note_child.find("step").text.lower()
                    alter = note_child.find("alter")
                    if alter is not None:
                        alter = alter.text
                    alter = self.alter_dict[alter]
                    ly_octave = ''
                    octave = int(note_child.find("octave").text) - 3
                    if octave < 0:
                        ly_octave = ("," * (0 - octave))
                    elif octave > 0:
                        ly_octave = ("'" * octave)
                    self.pitch = [pitch + alter + ly_octave]

                case "rest":
                    is_mismatched = False
                    if note_element.find("type") is not None and note_element.find("duration") is not None:
                        is_mismatched = (note_element.find("type").text == "whole" and
                                         int(note_element.find("duration").text) / divisions == measure_duration)
                    if note_child.get("measure") == "yes" or is_mismatched:
                        self.pitch = ['R']
                        self.duration = duration_num_to_str(measure_duration, measure_duration)
                        written_duration = measure_duration
                    else:
                        self.pitch = ["r"]
                case "duration":
                    self.duration_num = int(note_child.text)
                    self.duration_num = self.duration_num / divisions
                case "dot":
                    self.dot = '.'
                    written_duration *= 1.5
                case "grace":
                    if note_child.get("slash") != "yes":
                        warnings.warn("Unslashed grace note in measure " + measure_num)
                    self.grace = "\\acciaccatura "
                case "accidental":
                    if note_child.get("parentheses") == "yes":
                        self.pitch[0] += '?'
                case "time-modification":
                    num = int(note_child.find("actual-notes").text)
                    den = int(note_child.find("normal-notes").text)
                    written_duration *= (den / num)
                case "tie":
                    # handled in the notations section
                    pass
                case "voice":
                    pass
                case "type":
                    if self.pitch != ['R']:
                        self.duration = self.duration_dict[note_child.text]
                        written_duration = 1 / int(self.duration)
                case "stem":
                    pass
                case "beam":
                    pass
                case "notations":
                    self.parse_notation(note_child, num, den)
                case "notehead":
                    match note_child.text:
                        case "diamond":
                            self.pitch += ["\\harmonic"]
                        case "none":
                            self.pitch = ['s']
                case "lyric":
                    pass  # TODO: add lyrics parsing
                case "instrument" | "staff":
                    pass  # TODO: make sure this isn't important
                case "cue":
                    self.cue = True
                    if not self.in_cue:
                        self.in_cue = True
                        self.start_cue = "\\new CueVoice { "
                case _:
                    raise ImportError(f"Unrecognized note child: \"{note_child.tag}\" in mm. {measure_num}")
        if note_element.get("print-object") == "no":
            self.pitch = ['s']
        if not self.cue and self.in_cue:
            self.in_cue = False
            self.should_end_cue = True
        if not self.grace:
            assert abs(written_duration - self.duration_num) < (1 / divisions)

    def add_chord(self, chord):
        self.pitch.extend(chord.pitch)
        self.chord = True

    def add_expression(self, expression):
        self.expression = expression

    def same_chord(self, other):
        if not isinstance(other, Note):
            return False
        if not self.chord or not other.chord:
            return False
        return set(self.pitch) == set(other.pitch)

    def __str__(self):
        if not self.chord or (self.chord and self.pitch == ['q']):
            note = self.pitch[0]
        else:
            if set(self.pitch) == {'s'}:
                note = 's'
            else:
                note = '<' + ' '.join(self.pitch) + '>'
        return (self.start_poly + self.start_cue + self.start_tuplet + self.grace + note + self.duration + self.dot +
                self.articulations + str(self.expression) + self.trill + self.glissando + self.slur + self.tie +
                self.end_tuplet + self.end_cue + self.end_poly)

    def parse_notation(self, notation, num, den):
        for notation_child in notation:
            match notation_child.tag:
                case "tuplet":
                    tuplet_type = notation_child.get("type")
                    if tuplet_type == "start":
                        self.start_tuplet = f"\\tuplet {num}/{den} {{"
                    elif tuplet_type == "stop":
                        self.end_tuplet = "}"
                    pass
                case "articulations" | "technical":
                    for articulation in notation_child:
                        articulation_type = articulation.tag
                        if articulation_type == "fingering":
                            self.articulations += '-' + articulation.text
                        elif articulation_type in self.art_dict:
                            self.articulations += '-' + self.art_dict[articulation_type]
                        else:
                            raise ImportError("Unrecognized articulation type: " + articulation_type)
                case "slur":
                    self.slur = self.slur_dict[notation_child.get("type")]
                case "tied":
                    self.tie = self.tie_dict[notation_child.get("type")]
                case "ornaments":
                    for ornament in notation_child:
                        match ornament.tag:
                            case "trill-mark":
                                self.trill = '\\trill'
                            case "wavy-line":
                                if ornament.get("type") == "start":
                                    if self.trill == "\\trill":
                                        self.trill = "\\startTrillSpan"
                                    else:
                                        raise ImportError("Wavy line without trill")
                                elif ornament.get("type") == "stop":
                                    self.next_expression_buffer.add("\\stopTrillSpan")
                                elif ornament.get("type") == "continue":
                                    warnings.warn("Wavy line continue not implemented")
                                else:
                                    raise ImportError(
                                        "Unrecognized wavy line type: " + ornament.get("type"))
                            case "inverted-mordent":
                                self.trill = "\\prall"
                            case _:
                                raise ImportError("Unrecognized ornament: " + ornament.tag)
                case "slide":
                    if notation_child.get("type") == "start":
                        self.glissando = "\\glissando"
                case _:
                    raise ImportError("Unrecognized notation child: " + notation_child.tag)

    def __eq__(self, other):
        if not isinstance(other, Note):
            return False
        return (self.pitch == other.pitch and self.duration == other.duration and self.dot == other.dot and
                self.grace == other.grace and self.start_tuplet == other.start_tuplet and
                self.end_tuplet == other.end_tuplet and self.articulations == other.articulations and
                self.slur == other.slur and self.tie == other.tie and self.chord == other.chord and
                self.trill == other.trill and self.cue == other.cue and self.glissando == other.glissando)
