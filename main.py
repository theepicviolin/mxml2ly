import warnings
import xml.etree.ElementTree as ET
import configparser
import os
import tkinter as tk
from tkinter import filedialog


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
    art_dict = {"staccato": '.', "tenuto": '-', "snap-pizzicato": '\\snappizzicato', 'accent': '>'}
    slur_dict = {"start": '(', "stop": ')'}
    tie_dict = {"start": '~', "stop": ''}

    def __init__(self, note_element, time_info, measure_num):
        self.pitch = ['']
        self.duration = ''
        self.duration_num = 0
        self.dot = ''
        self.grace = ''
        self.tuplet_start = ''
        self.tuplet_end = ''
        self.articulations = ''
        self.slur = ''
        self.tie = ''
        self.chord = False
        self.expression = Expression('')
        self.start_poly = ''
        self.end_poly = ''

        divisions, measure_duration = time_info
        written_duration = 0

        if isinstance(note_element, tuple):
            self.pitch, self.duration_num, self.dot = note_element
            self.duration_num = self.duration_num / divisions
            self.duration = f"{divisions}*{int(divisions * self.duration_num)}"
            return

        for noteChild in note_element:
            match noteChild.tag:
                case "chord":
                    self.chord = True
                case "pitch":
                    pitch = noteChild.find("step").text.lower()
                    alter = noteChild.find("alter")
                    if alter is not None:
                        alter = alter.text
                    alter = self.alter_dict[alter]
                    ly_octave = ''
                    octave = int(noteChild.find("octave").text) - 3
                    if octave < 0:
                        ly_octave = ("," * (0 - octave))
                    elif octave > 0:
                        ly_octave = ("'" * octave)
                    self.pitch = [pitch + alter + ly_octave]

                case "rest":
                    if noteChild.get("measure") == "yes":
                        self.pitch = ['R']
                        self.duration = f"{divisions}*{int(divisions * measure_duration)}"
                        written_duration = measure_duration
                    else:
                        self.pitch = ["r"]
                case "duration":
                    self.duration_num = int(noteChild.text)
                    self.duration_num = self.duration_num / divisions
                case "dot":
                    self.dot = '.'
                    written_duration *= 1.5
                case "grace":
                    if noteChild.get("slash") != "yes":
                        warnings.warn("Unslashed grace note in measure " + measure_num)
                    self.grace = "\\acciaccatura "
                case "accidental":
                    pass
                case "time-modification":
                    num = int(noteChild.find("actual-notes").text)
                    den = int(noteChild.find("normal-notes").text)
                    written_duration *= (den / num)
                case "tie":
                    # handled in the notations section
                    pass
                case "voice":
                    pass
                case "type":
                    self.duration = self.duration_dict[noteChild.text]
                    written_duration = 1 / int(self.duration_dict[noteChild.text])
                case "stem":
                    pass
                case "beam":
                    pass
                case "notations":
                    for child in noteChild:
                        match child.tag:
                            case "tuplet":
                                tuplet_type = child.get("type")
                                if tuplet_type == "start":
                                    self.tuplet_start = f"\\tuplet {num}/{den} {{"
                                elif tuplet_type == "stop":
                                    self.tuplet_end = "}"
                                pass
                            case "articulations" | "technical":
                                for articulation in child:
                                    articulation_type = articulation.tag
                                    if articulation_type == "fingering":
                                        self.articulations += '-' + articulation.text
                                    elif articulation_type in self.art_dict:
                                        self.articulations += '-' + self.art_dict[articulation_type]
                                    else:
                                        raise ImportError("Unrecognized articulation type: " + articulation_type)
                            case "slur":
                                self.slur = self.slur_dict[child.get("type")]
                            case "tied":
                                self.tie = self.tie_dict[child.get("type")]
                            case "ornaments":
                                pass  # TODO: add ornaments (trills)
                            case _:
                                raise ImportError("Unrecognized notation child: " + child.tag)
                case "notehead":
                    match noteChild.text:
                        case "diamond":
                            self.pitch += ["\\harmonic"]
                        case "none":
                            self.pitch = ['s']
                case "lyric":
                    pass  # TODO: add lyrics parsing
                case _:
                    raise ImportError("Unrecognized note child: " + noteChild.tag)
        if note_element.get("print-object") == "no":
            self.pitch = ['s']
        if not self.grace:
            assert written_duration == self.duration_num

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
        return self.start_poly + self.tuplet_start + self.grace + note + self.duration + self.dot + \
            self.articulations + str(self.expression) + self.slur + self.tie + self.tuplet_end + self.end_poly


class Expression:
    dynamics = {'\\pp', '\\p', '\\mp', '\\mf', '\\f', '\\ff', '\\fp', '\\sf', '\\sfz', '\\<', '\\>', '\\cresc'}

    def __init__(self, text):
        self.text = {text}

    def add(self, new):
        self.text.add(new)
        if self.text.intersection(self.dynamics):
            self.text.discard("\\!")

    def __str__(self):
        return ''.join(self.text)


class Instrument:
    def __init__(self, instrument_element, part_list):
        key_dict = {
            '0': 'c',
            '1': 'g',
            '2': 'd',
            '3': 'a',
            '4': 'e',
            '5': 'b',
            '6': 'fs',
            '7': 'cs',
            '-1': 'f',
            '-2': 'bf',
            '-3': 'ef',
            '-4': 'af',
            '-5': 'df',
            '-6': 'gf',
            '-7': 'cf'
        }
        divisions = 4
        measure_duration = 1
        time_info = (divisions, measure_duration)
        self.id = instrument_element.get("id")
        part = [part for part in part_list if part.get("id") == self.id][0]
        self.full_name = part.find("part-name").text
        self.var_name = self.full_name.replace(' ', '_')
        instrument_str = self.var_name + ' = {\n'
        last_chord = None
        remaining_backup_duration = 0
        expression_buffer = None
        for measure in instrument_element:
            assert measure.tag == "measure"
            measure_strs = []
            measure_num = measure.get("number")
            for measure_child in measure:
                match measure_child.tag:
                    case "attributes":
                        for attribute_child in measure_child:
                            match attribute_child.tag:
                                case "divisions":
                                    divisions = int(measure_child.find("divisions").text) * 4
                                case "key":
                                    key = key_dict[measure_child.find("key").find("fifths").text]
                                    measure_strs += [f"\\key {key} \\major"]
                                case "time":
                                    time_num = int(measure_child.find("time").find("beats").text)
                                    time_den = int(measure_child.find("time").find("beat-type").text)
                                    measure_duration = time_num / time_den
                                    time_info = (divisions, measure_duration)
                                    measure_strs += [f"\\time {time_num}/{time_den}"]
                                case "clef":
                                    clef = attribute_child.find("sign").text
                                    if attribute_child.find("clef-octave-change") is not None:
                                        if attribute_child.find("clef-octave-change").text == "-1" and clef == "G":
                                            clef = "GG"
                                    measure_strs += [f'\\clef {clef}']
                                case "measure-style":
                                    if attribute_child.find("multiple-rest") is not None:
                                        continue
                                    else:
                                        raise ImportError("Unrecognized attribute: " + attribute_child.tag)
                                case "transpose":
                                    # this is relevant only for the difference between sounded and written
                                    pass
                                case _:
                                    raise ImportError("Unrecognized attribute: " + attribute_child.tag)
                    case "direction":
                        for direction_child in measure_child:
                            if direction_child.tag not in ["direction-type", "sound"]:
                                raise ImportError("Unrecognized direction: " + direction_child.tag)
                            for direction_type_child in direction_child:
                                this_buffer = ''
                                match direction_type_child.tag:
                                    case "dynamics":
                                        for dynamic in direction_type_child:
                                            assert dynamic.tag in ['pp', 'p', 'mp', 'mf', 'f', 'ff', 'fp', 'sf', 'sfz']
                                            this_buffer = '\\' + dynamic.tag
                                    case "wedge":
                                        match direction_type_child.get("type"):
                                            case "crescendo":
                                                this_buffer = "\\<"
                                            case "diminuendo":
                                                this_buffer = "\\>"
                                            case "stop":
                                                this_buffer = "\\!"
                                            case _:
                                                raise ImportError(
                                                    "Unrecognized wedge type: " + direction_type_child.get("type"))
                                    case "words":
                                        text = direction_type_child.text
                                        if text in ["cresc."]:
                                            this_buffer = "\\cresc"
                                        else:
                                            this_buffer = '-\\markup{\\italic "' + text + '"}'
                                    case "dashes":
                                        match direction_type_child.get("type"):
                                            case "start":
                                                pass
                                            case "stop":
                                                this_buffer = "\\!"
                                    case "metronome":
                                        beat_unit = Note.duration_dict[direction_type_child.find("beat-unit").text]
                                        tempo = direction_type_child.find("per-minute").text
                                        measure_strs += [f'\\tempo {beat_unit} = {tempo}']
                                    case "octave-shift":
                                        shift_amount = direction_type_child.get("number")
                                        match direction_type_child.get("type"):
                                            case "up":
                                                shift_amount = '-' + shift_amount
                                            case "stop":
                                                shift_amount = '0'
                                            case "down":
                                                pass
                                            case _:
                                                raise ImportError("Unrecognized octave shift details")
                                        measure_strs += [f'\\ottava #{shift_amount} ']
                                    case _:
                                        raise ImportError("Unrecognized direction type: " + direction_type_child.tag)
                                if expression_buffer:
                                    expression_buffer.add(this_buffer)
                                else:
                                    expression_buffer = Expression(this_buffer)
                    case "forward" | "note":
                        if measure_child.tag == "forward":
                            duration = int(measure_child.find("duration").text)
                            note = Note((['s'], duration, ''), time_info, measure_num)
                        else:
                            note = Note(measure_child, time_info, measure_num)

                        if expression_buffer:
                            note.add_expression(expression_buffer)
                            expression_buffer = None
                        if not note.chord:
                            measure_strs += [note]
                            if remaining_backup_duration > 0:
                                remaining_backup_duration -= note.duration_num
                                if remaining_backup_duration == 0:
                                    note.end_poly = "} >>"
                                    rev_idx = 0
                                    for s in reversed(measure_strs):
                                        rev_idx -= 1
                                        if s != "} \\\\ {":
                                            if isinstance(s, Note) and s.pitch != ['s']:
                                                break
                                            else:
                                                continue
                                        measure_strs[rev_idx] = "} {"
                            if remaining_backup_duration < 0:
                                raise ImportError("Backup duration surpassed")
                        else:
                            assert isinstance(measure_strs[-1], Note)
                            measure_strs[-1].add_chord(note)
                    case "barline":
                        bars = {
                            "light-light": '"||"',
                            "light-heavy": '"|."'
                        }
                        bar_style = bars[measure_child.find("bar-style").text]
                        measure_strs += [f"\\bar {bar_style}"]
                    case "backup":
                        # go back by duration amount in the measure_strs list
                        backup_duration = int(measure_child.find('duration').text) / divisions
                        cur_backed_up = 0
                        n_backup = 0
                        for s in reversed(measure_strs):
                            n_backup -= 1
                            if not isinstance(s, Note):
                                continue
                            cur_backed_up += s.duration_num
                            if cur_backed_up == backup_duration:
                                s.start_poly = "<< {"
                                break
                            elif cur_backed_up > backup_duration:
                                raise ImportError("Backup duration could not be met")
                        assert cur_backed_up == backup_duration
                        measure_strs.append("} \\\\ {")
                        remaining_backup_duration = backup_duration
                    case _:
                        raise ImportError("Unrecognized measure child: " + measure_child.tag)
            print(f"Measure: {measure_num}")
            for s in measure_strs:
                instrument_str += " "
                if isinstance(s, Note) and s.same_chord(last_chord):
                    s.pitch = ['q']
                elif isinstance(s, Note) and s.chord:
                    last_chord = s
                instrument_str += str(s)
            instrument_str += "| "
            if int(measure_num) % 4 == 0:
                instrument_str += "\n"
        instrument_str += "}"
        self.instrument_str = instrument_str
        self.full_name_var = self.var_name + "_name"
        self.short_name_var = self.var_name + "_short_name"
        self.name_str = f"""{self.full_name_var} = "{self.full_name}"\n{self.short_name_var} = "{self.full_name}"\n"""
        self.book_str = f"""
%%{{
\\book {{
  \\bookOutputSuffix \\{self.var_name}_name
  \\header {{ instrument = \\{self.var_name}_name }}
  \\score {{
    \\{self.var_name}
  }}
}}
%}}
"""


def parse(filename, config_info):
    arranger = config_info['Preferences']['Arranger']
    tree = ET.parse(filename)
    root = tree.getroot()
    if root.tag != "score-partwise":
        raise ImportError("MusicXML file must be partwise")
    part_list = root.find('part-list')
    title = root.find('work').find('work-title').text
    composer = root.find('identification').find('creator').text
    file_str = '\\version "2.24.1"\n\\language "english"\n#(set-default-paper-size "letter")\n\n'
    file_str += f"""\\header {{
      title = "{title}"
      subtitle = \\markup {{the \\italic "Subtitle"}}
      composer = "{composer}"
      arranger = "arr. {arranger}"
    }}
    """
    instruments = [Instrument(instr_elem, part_list) for instr_elem in root if instr_elem.tag == 'part']
    file_str += '\n\n\n'.join([i.instrument_str for i in instruments])
    file_str += '\n\n'
    file_str += ''.join([i.name_str for i in instruments])
    file_str += ''.join([i.book_str for i in instruments])

    file_str += """
%%{
\\book {
  \\paper {
    #(layout-set-staff-size 17)
    left-margin = 0.5\\cm
    indent = 1.5\\cm
    short-indent = 1.0\\cm  
  }

  \\bookOutputSuffix "Full Score"
  \\header { instrument = "Full Score" }
  \\score {
    <<
"""
    file_str += '\n'.join([f'      \\new Staff \\with {{ instrumentName = \\{i.full_name_var} shortInstrumentName = '
                           f'\\{i.short_name_var} }} \\{i.var_name}' for i in instruments])
    file_str += """
    >>
  }
}
%}
"""
    return file_str


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('preferences.ini')

    root = tk.Tk()
    root.withdraw()
    file = filedialog.askopenfilename(initialdir=config['Preferences']['DefaultInputDir'],
                                      filetypes=[("MusicXML Files", "*.musicxml")])

    file_str = parse(file, config)

    file_basename = os.path.splitext(os.path.basename(file))[0]
    output_file = filedialog.asksaveasfilename(initialdir=config['Preferences']['DefaultOutputDir'],
                                               filetypes=[("LilyPond Files", "*.ly")],
                                               initialfile=file_basename,
                                               defaultextension=".ly")
    with open(output_file, "w") as out_file:
        out_file.write(file_str)
