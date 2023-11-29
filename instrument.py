from expression import Expression
from note import Note
import note
import warnings


def add_note(new_note, instrument_strs, expression_buffer, measure_strs, remaining_backup_duration):
    if new_note.should_end_cue:
        for s in reversed(instrument_strs):
            if isinstance(s, Note):
                s.end_cue = " } "
                break
    in_cue = new_note.in_cue
    new_note.add_expression(expression_buffer)
    expression_buffer = new_note.next_expression_buffer
    if not new_note.chord:
        measure_strs.append(new_note)
        if remaining_backup_duration > 0:
            remaining_backup_duration -= new_note.duration_num
            if remaining_backup_duration == 0:
                new_note.end_poly = "} >>"
                # if there are no notes in the second voice, replace "} \\ {" with "} {" to avoid
                # issues with ties not being able to reach into the polyphonic section
                rev_idx = 0
                found_notes = False
                for s in reversed(measure_strs):
                    rev_idx -= 1
                    if isinstance(s, Note) and s.pitch != ['s']:
                        found_notes = True
                    elif s == "} \\\\ {":
                        if not found_notes:
                            measure_strs[rev_idx] = "} {"
                        else:
                            new_voice_idx = rev_idx
                        break
                poly_in_cue = False
                if found_notes:
                    found_notes = False
                    for s in measure_strs[new_voice_idx:]:
                        if isinstance(s, Note):
                            if s.start_cue != "":
                                poly_in_cue = True
                            if s.end_cue != "":
                                poly_in_cue = False
                            if s.pitch != ['s'] and not poly_in_cue:
                                found_notes = True
                                break
                    if not found_notes:
                        measure_strs[new_voice_idx] = "} {"
        if remaining_backup_duration < 0:
            raise ImportError("Backup duration surpassed")
    else:
        assert isinstance(measure_strs[-1], Note)
        measure_strs[-1].add_chord(new_note)
    return expression_buffer, remaining_backup_duration, in_cue


class Instrument:
    def __init__(self, instrument_element, part_list, debug):
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
        instrument_strs = [self.var_name + ' = \\compressMMRests {\n\\accidentalStyle Score.modern-cautionary\n']
        last_chord = None
        remaining_backup_duration = 0
        expression_buffer = Expression('')
        in_cue = False
        n_measures_rest = 0
        end_extended_rest = False

        for measure in instrument_element:
            assert measure.tag == "measure"
            measure_strs = []
            measure_num = measure.get("number")
            if int(measure_num) % 4 == 1:  # new line every 4 measures
                instrument_strs.append(f"% Measure {measure_num}\n")
            for measure_child in measure:
                measure_rest_note = Note(None, time_info, in_cue=False, cue=False, pitch=['R'], duration_num=measure_duration)
                match measure_child.tag:
                    case "forward" | "note":
                        if measure_child.tag == "note":
                            new_note = Note(measure_child, time_info, measure_num, in_cue=in_cue)
                        else:
                            duration = int(measure_child.find("duration").text) / divisions
                            new_note = Note(None, time_info, in_cue=in_cue, cue=in_cue, pitch=['s'], duration_num=duration)

                        ret = add_note(new_note, instrument_strs, expression_buffer, measure_strs, remaining_backup_duration)
                        if new_note == measure_rest_note:
                            n_measures_rest += 1
                        else:
                            end_extended_rest = True
                        expression_buffer, remaining_backup_duration, in_cue = ret
                    case "attributes":
                        for attribute_child in measure_child:
                            match attribute_child.tag:
                                case "divisions":
                                    divisions = int(measure_child.find("divisions").text) * 4
                                case "key":
                                    key = key_dict[measure_child.find("key").find("fifths").text]
                                    measure_strs.append(f"\\key {key} \\major")
                                    if n_measures_rest > 0:
                                        end_extended_rest = True
                                case "time":
                                    time_num = int(measure_child.find("time").find("beats").text)
                                    time_den = int(measure_child.find("time").find("beat-type").text)
                                    measure_duration = time_num / time_den
                                    time_info = (divisions, measure_duration)
                                    measure_strs.append(f"\\time {time_num}/{time_den}")
                                    if n_measures_rest > 0:
                                        end_extended_rest = True
                                case "clef":
                                    clef = attribute_child.find("sign").text
                                    if attribute_child.find("clef-octave-change") is not None:
                                        if attribute_child.find("clef-octave-change").text == "-1" and clef == "G":
                                            clef = "GG"
                                    measure_strs.append(f'\\clef {clef}')
                                    if n_measures_rest > 0:
                                        end_extended_rest = True
                                case "measure-style":
                                    if attribute_child.find("multiple-rest") is not None:
                                        continue
                                    else:
                                        raise ImportError("Unrecognized attribute: " + attribute_child.tag)
                                case "transpose":
                                    # this is relevant only for the difference between sounded and written
                                    pass
                                case "staves" | "staff-details":
                                    # I don't know what these are
                                    warnings.warn(f"Unimplemented attribute \"{attribute_child.tag}\" in mm. {measure_num}")
                                    pass
                                case _:
                                    raise ImportError("Unrecognized attribute: " + attribute_child.tag)
                    case "direction":
                        if n_measures_rest > 0:
                            end_extended_rest = True
                        for direction_child in measure_child:
                            if direction_child.tag not in ["direction-type", "sound", "voice", "staff"]:
                                raise ImportError("Unrecognized direction: " + direction_child.tag)
                            if direction_child.tag == "voice" and direction_child.text != "1":
                                raise ImportError("Multiple voices in measure: " + measure_num)
                            for direction_type_child in direction_child:
                                this_buffer = ''
                                match direction_type_child.tag:
                                    case "dynamics":
                                        for dynamic in direction_type_child:
                                            assert dynamic.tag in ['pp', 'p', 'mp', 'mf', 'f', 'ff', 'fp', 'sf', 'sfz']
                                            this_buffer = '\\' + dynamic.tag
                                    case "wedge":
                                        wedge_dict = {
                                            "crescendo": "\\<",
                                            "diminuendo": "\\>",
                                            "stop": "\\!"
                                        }
                                        this_buffer = wedge_dict[direction_type_child.get("type")]
                                    case "words":
                                        text = direction_type_child.text
                                        if text in ["cresc."]:
                                            this_buffer = "\\cresc"
                                        else:
                                            this_buffer = '-\\markup{\\italic "' + text + '"}'
                                    case "dashes":
                                        if direction_type_child.get("type") == "stop":
                                            this_buffer = "\\!"
                                    case "metronome":
                                        beat_unit = Note.duration_dict[direction_type_child.find("beat-unit").text]
                                        tempo = direction_type_child.find("per-minute").text
                                        measure_strs.append(f'\\tempo {beat_unit} = {tempo}')
                                    case "octave-shift":
                                        shift_amount = direction_type_child.get("number")
                                        if direction_type_child.get("type") == "up":
                                            shift_amount = '-' + shift_amount
                                        elif direction_type_child.get("type") == "stop":
                                            shift_amount = '0'
                                        elif direction_type_child.get("type") == "down":
                                            pass
                                        else:
                                            raise ImportError("Unrecognized octave shift details")
                                        measure_strs.append(f'\\ottava #{shift_amount} ')
                                    case _:
                                        raise ImportError("Unrecognized direction type: " + direction_type_child.tag)
                                expression_buffer.add(this_buffer)
                    case "barline":
                        bars = {
                            "light-light": '"||"',
                            "light-heavy": '"|."'
                        }
                        bar_style = bars[measure_child.find("bar-style").text]
                        measure_strs.append(f"\\bar {bar_style}")
                        end_extended_rest = True
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
                        if n_measures_rest > 0:
                            n_measures_rest = 0
                            warnings.warn(f"Backup in measure {measure_num} during extended rest")

                    case "print":
                        # used for line breaks and page breaks
                        pass
                    case _:
                        raise ImportError("Unrecognized measure child: " + measure_child.tag)

            if remaining_backup_duration > 0:
                new_note = Note(None, time_info, in_cue=in_cue, cue=in_cue, pitch=['s'], duration_num=remaining_backup_duration)
                ret = add_note(new_note, instrument_strs, expression_buffer, measure_strs, remaining_backup_duration)
                expression_buffer, remaining_backup_duration, in_cue = ret
            if debug:
                print(f"Measure: {measure_num}")
            for s in measure_strs:
                instrument_strs.append(" ")
                if isinstance(s, Note) and s.same_chord(last_chord):
                    s.pitch = ['q']
                elif isinstance(s, Note) and s.chord:
                    last_chord = s
                instrument_strs.append(s)

            if end_extended_rest:
                if n_measures_rest > 1:
                    instrument_strs_idx = -1
                    first_rest_idx = None
                    last_rest_idx = None
                    n_measures_counted = 0
                    for s in reversed(instrument_strs[:-1]):
                        instrument_strs_idx -= 1
                        if isinstance(s, Note):
                            if s == measure_rest_note:
                                first_rest_idx = instrument_strs_idx
                                n_measures_counted += 1
                                if last_rest_idx is None:
                                    last_rest_idx = instrument_strs_idx
                            if n_measures_counted == n_measures_rest:
                                break
                    assert n_measures_counted == n_measures_rest
                    assert first_rest_idx is not None
                    assert last_rest_idx is not None
                    last_note = instrument_strs[first_rest_idx]
                    last_note.duration_num = n_measures_rest * measure_duration
                    last_note.duration = note.duration_num_to_str(last_note.duration_num, measure_duration)
                    instrument_strs[first_rest_idx+1:last_rest_idx+1] = []
                end_extended_rest = False
                n_measures_rest = 0

            instrument_strs.append("|\n")
        instrument_strs.append("}")
        self.instrument_str = "".join([str(s) for s in instrument_strs])
        self.full_name_var = self.var_name + "_name"
        self.short_name_var = self.var_name + "_short_name"
        self.name_str = f"""{self.full_name_var} = "{self.full_name}"\n{self.short_name_var} = "{self.full_name}"\n"""
        self.book_str = f"\\book {{ \\bookOutputSuffix \\{self.var_name}_name  \\header {{ instrument = \\{self.var_name}_name }}  \\score {{ \\{self.var_name} }} }}\n"
        self.book_part_str = f"\\bookpart {{ \\header {{ instrument = \\{self.var_name}_name }}  \\score {{ \\{self.var_name} }} }}\n"
