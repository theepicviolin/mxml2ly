import warnings
import xml.etree.ElementTree as ET
import configparser
import os
import tkinter as tk
from tkinter import filedialog
from instrument import Instrument
import argparse


def parse(filename, config_info):
    arranger = config_info['Preferences']['Arranger']
    version = config_info['Preferences']['Version']
    tree = ET.parse(filename)
    root = tree.getroot()
    if root.tag != "score-partwise":
        raise ImportError("MusicXML file must be partwise")
    part_list = root.find('part-list')
    title = root.find('work').find('work-title').text
    composer = root.find('identification').find('creator').text
    file_str = f'\\version "{version}"\n\\language "english"\n#(set-default-paper-size "letter")\n\n'
    file_str += f"""\\header {{
      title = "{title}"
      subtitle = \\markup {{the \\italic "Subtitle"}}
      composer = "{composer}"
      arranger = "arr. {arranger}"
      tagline = #f
    }}
    """
    instruments = [Instrument(instr_elem, part_list) for instr_elem in root if instr_elem.tag == 'part']
    file_str += '\n\n\n'.join([i.instrument_str for i in instruments])
    file_str += '\n\n'
    file_str += ''.join([i.name_str for i in instruments])
    file_str += '\n% Separate Files for Each Instrument\n'
    file_str += ''.join([i.book_str for i in instruments])

    file_str += '\n% One File for All Instruments'
    file_str += """
%%{
\\book {
  \\bookOutputSuffix "Parts"
  \\paper {
    print-page-number = ##f
  }
  """
    file_str += ''.join([i.book_part_str for i in instruments])
    file_str += "}\n%}\n"
    file_str += """
% Full Score
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
    config.read('.\\preferences.ini')

    parser = argparse.ArgumentParser(description='Convert MusicXML to LilyPond')
    parser.add_argument('-i', '--input', help='Input file (*.musicxml)')
    parser.add_argument('-o', '--output', help='Output file (*.ly)')
    args = parser.parse_args()

    if args.input is None:
        root = tk.Tk()
        root.withdraw()
        file = filedialog.askopenfilename(initialdir=config['Preferences']['DefaultInputDir'],
                                          filetypes=[("MusicXML Files", "*.musicxml")])
    else:
        file = args.input

    if file == "":
        print("Please select a file.")
    else:
        file_str = parse(file, config)

        if args.output is not None:
            output_file = args.output
        else:
            file_basename = os.path.splitext(os.path.basename(file))[0]
            output_file = filedialog.asksaveasfilename(initialdir=config['Preferences']['DefaultOutputDir'],
                                                       filetypes=[("LilyPond Files", "*.ly")],
                                                       initialfile=file_basename,
                                                       defaultextension=".ly")
        with open(output_file, "w") as out_file:
            out_file.write(file_str)
