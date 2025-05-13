import xml.etree.ElementTree as ET
import configparser
import os
import tkinter as tk
from tkinter import filedialog
from instrument import Instrument
import argparse


def parse(args, config_info):
    filename = args.input
    arranger = config_info['Preferences']['Arranger']
    version = config_info['Preferences']['Version']
    subtitle = args.subtitle
    tree = ET.parse(filename)
    root = tree.getroot()
    if root.tag != "score-partwise":
        raise ImportError("MusicXML file must be partwise")
    part_list = root.find('part-list')
    title = None
    work = root.find('work')
    if work is not None:
        title = work.find('work-title').text
    if title is None:
        title = os.path.splitext(os.path.basename(filename))[0]
    composer = root.find('identification').find('creator')
    if composer is None:
        composer = 'Composer Unknown'
    else:
        composer = composer.text
    file_str = f'\\version "{version}"\n\\language "english"\n#(set-default-paper-size "letter")\n%\\pointAndClickOff\n\n'
    file_str += f"""\\header {{
      title = "{title}"
      subtitle = {subtitle}
      composer = "{composer}"
      arranger = "arr. {arranger}"
      tagline = #f
    }}
    ub = \\upbow
    db = \\downbow
    """
    instruments = [Instrument(instr_elem, part_list, args.debug) for instr_elem in root if instr_elem.tag == 'part']
    instruments = [i for i in instruments if not i.percussion]

    file_str += '\n\n\n'.join([i.instrument_str for i in instruments])
    file_str += '\n\n'
    file_str += ''.join([i.name_str for i in instruments])
    if args.parts == 'together':
        file_str += '\n% Separate Files for Each Instrument\n%{\n'
    else:
        file_str += '\n% Separate Files for Each Instrument\n%%{\n'
    file_str += ''.join([i.book_str for i in instruments])

    if args.parts == 'together':
        file_str += '%}\n\n% One File for All Instruments\n%%{'
    else:
        file_str += '%}\n\n% One File for All Instruments\n%{'
    file_str += """
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
    config.read(os.path.join(".", "preferences.ini"))

    parser = argparse.ArgumentParser(description='Convert MusicXML to LilyPond')
    parser.add_argument('-i', '--input', help='Input file (*.musicxml;*.xml)')
    parser.add_argument('-o', '--output', help='Output file (*.ly)')
    parser.add_argument('-p', '--parts', help='Output parts separately or together')
    parser.add_argument('-d', '--debug', help='Debug mode')
    parser.add_argument('-s', '--subtitle', help='Subtitle in Lilypond markup (including \\markup)')
    args = parser.parse_args()

    if args.input is None or not os.path.isfile(args.input) or (not args.input.endswith('.musicxml') and not args.input.endswith('.xml')):
        args.input = None

    if args.output is None or not args.output.endswith('.ly'):
        args.output = None

    if args.parts is None:
        args.parts = 'together'
    args.parts = args.parts.lower()
    if args.parts in ['separate', 's']:
        args.parts = 'separate'
    else:
        args.parts = 'together'

    if args.subtitle is None:
        args.subtitle = "\\markup {the \\italic \"Subtitle\"}"

    if isinstance(args.debug, str):
        args.debug = args.debug.lower()
    if args.debug in ['true', 't', 'yes', 'y', '1']:
        args.debug = True
    else:
        args.debug = False

    if args.input is None:
        root = tk.Tk()
        root.withdraw()
        args.input = filedialog.askopenfilename(initialdir=config['Preferences']['DefaultInputDir'],
                                                filetypes=[("MusicXML Files", "*.musicxml;*.xml"), ("All files", "*.*")])
        
    if args.input == "":
        print("Please select a file.")
    else:
        file_str = parse(args, config)

        if args.output is not None:
            output_file = args.output
        else:
            file_basename = os.path.splitext(os.path.basename(args.input))[0]
            output_file = filedialog.asksaveasfilename(initialdir=config['Preferences']['DefaultOutputDir'],
                                                       filetypes=[("LilyPond Files", "*.ly")],
                                                       initialfile=file_basename,
                                                       defaultextension=".ly")
        with open(output_file, "w") as out_file:
            out_file.write(file_str)
