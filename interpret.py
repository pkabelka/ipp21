#!/usr/bin/env python3

import sys
import argparse
import os
import re
from enum import Enum
import xml.etree.ElementTree as ET

class Code(Enum):
    SUCCESS = 0
    BAD_PARAM = 10
    OPEN_ERR = 11
    WRITE_ERR = 12
    BAD_XML = 31
    BAD_STRUCT = 32
    INTERNAL_ERR = 99

def exit_err(code, message=None):
    err_messages = {
        Code.BAD_PARAM: 'Error: Wrong combination of parameters\nRun only with --help to show help',
        Code.OPEN_ERR: 'Error: Cannot open file',
        Code.BAD_XML: 'Error: Wrong XML format. XML is not well-formed',
        Code.BAD_STRUCT: 'Error: Wrong XML structure'
    }
    if message != None:
        print(message, file=sys.stderr)
    else:
        print(err_messages[code], file=sys.stderr)
    exit(code.value)

class Inst():
    _INST_MAP = {
        'MOVE': ('var', 'symb'),
        'CREATEFRAME': tuple(),
        'PUSHFRAME': tuple(),
        'POPFRAME': tuple(),
        'DEFVAR': tuple(['var']),
        'CALL': tuple(['label']),
        'RETURN': tuple(),
        'PUSHS': tuple(['symb']),
        'POPS': tuple(['var']),
        'ADD': ('var', 'symb', 'symb'),
        'SUB': ('var', 'symb', 'symb'),
        'MUL': ('var', 'symb', 'symb'),
        'IDIV': ('var', 'symb', 'symb'),
        'LT': ('var', 'symb', 'symb'),
        'GT': ('var', 'symb', 'symb'),
        'EQ': ('var', 'symb', 'symb'),
        'AND': ('var', 'symb', 'symb'),
        'OR': ('var', 'symb', 'symb'),
        'NOT': ('var', 'symb'),
        'INT2CHAR': ('var', 'symb'),
        'STRI2INT': ('var', 'symb', 'symb'),
        'READ': ('var', 'type'),
        'WRITE': tuple(['symb']),
        'CONCAT': ('var', 'symb', 'symb'),
        'STRLEN': ('var', 'symb'),
        'GETCHAR': ('var', 'symb', 'symb'),
        'SETCHAR': ('var', 'symb', 'symb'),
        'TYPE': ('var', 'symb'),
        'LABEL': tuple(['label']),
        'JUMP': tuple(['label']),
        'JUMPIFEQ': ('label', 'symb', 'symb'),
        'JUMPIFNEQ': ('label', 'symb', 'symb'),
        'EXIT': tuple(['symb']),
        'DPRINT': tuple(['symb']),
        'BREAK': tuple()
    }

    @classmethod
    def opcode_args(cls, opcode):
        if not opcode in cls._INST_MAP:
            return None
        return cls._INST_MAP[opcode]

    def __init__(self, opcode, args):
        self.opcode = opcode
        self.args = args
        # self.argc = len(self.args)
        

class Instructions:
    def __init__(self):
        self.instructions = []
        self.pc = 0
        self.calls = []

    def add(self, inst: Inst):
        self.instructions.append(inst)

class XMLParser():
    def __init__(self):
        self.instructions = Instructions()


    def parse(self, source_path):
        if source_path == None:
            source_path = sys.stdin

        try:
            tree = ET.parse(source_path)
        except FileNotFoundError:
            exit_err(Code.OPEN_ERR)
        except PermissionError:
            exit_err(Code.OPEN_ERR)
        except ET.ParseError:
            exit_err(Code.BAD_XML)

        root = tree.getroot()

        # XML structure
        if root.tag != 'program':
            exit_err(Code.BAD_STRUCT, 'Error: "program" root element not found')

        for attr in root.attrib:
            if attr not in ['language', 'name', 'description']:
                exit_err(Code.BAD_STRUCT, 'Error: "program" root element not found')
            if 'language' not in root.attrib:
                exit_err(Code.BAD_STRUCT, 'Error: "program" element is missing "language" attribute')
            if root.attrib['language'].upper() != 'IPPCODE21':
                exit_err(Code.BAD_STRUCT, 'Error: Language attribute should be "IPPcode21", not "{}"'.format(root.attrib['language']))

        inst_orders = {}
        for inst in root:
            if inst.tag != 'instruction':
                exit_err(Code.BAD_STRUCT, f'Error: expected "instruction" tag, not "{inst.tag}"')
            if 'order' not in inst.attrib:
                exit_err(Code.BAD_STRUCT, 'Error: "instruction" element is missing "order" attribute')
            if 'opcode' not in inst.attrib:
                exit_err(Code.BAD_STRUCT, 'Error: "instruction" element is missing "opcode" attribute')
            opcode = inst.attrib['opcode'].upper()
            order = inst.attrib['order']

            try:
                if int(order) < 1:
                    exit_err(Code.BAD_STRUCT, 'Error: "order" attribute must have a positive non-zero integer value')
            except ValueError:
                exit_err(Code.BAD_STRUCT, 'Error: "order" attribute must have a positive non-zero integer value')

            if order in inst_orders: # duplicate instruction order
                exit_err(Code.BAD_STRUCT, f'Error: Duplicate instruction order found: {order}')
            inst_orders[order] = None

            args = self._inst_syntax(inst)
            self.instructions.add(Inst(opcode, args))

        return self.instructions


    def _inst_syntax(self, inst):
        args = []
        # args = {}
        opcode = inst.attrib['opcode'].upper()
        order = inst.attrib['order']
        if Inst.opcode_args(opcode) is None: # unknown instruction opcode
            exit_err(Code.BAD_STRUCT, 'Error: Unknown instruction opcode "{}" with order "{}"'.format(inst.attrib['opcode'], order))

        if len(inst) != len(Inst.opcode_args(opcode)): # wrong number of arguments
            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Wrong number of arguments, expected {} but {} given'.format(order, len(Inst.opcode_args(opcode)), len(inst)))

        # argument syntax
        arg_i = 1
        for arg in inst:
            if arg.tag != f'arg{arg_i}': # wrong argument order
                exit_err(Code.BAD_STRUCT, f'Error: expected "arg{arg_i}" tag, not "{arg.tag}"')

            if len(arg.attrib) > 1 or 'type' not in arg.attrib:
                exit_err(Code.BAD_STRUCT, f'Error: Order "{order}": Expected a single argument attribute "type"')

            pos_type = Inst.opcode_args(opcode)[arg_i-1]
            if pos_type == 'symb':
                if arg.attrib['type'] not in ['int', 'string', 'bool', 'nil', 'var']:
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Unexpected symb argument type "{}"'.format(order, arg.attrib['type']))

                if arg.attrib['type'] == 'int':
                    if arg.text is None:
                        exit_err(Code.BAD_STRUCT, f'Error: Order "{order}": arg{arg_i} with type "int" cannot have an empty value')

                elif arg.attrib['type'] == 'string':
                    if arg.text is not None:
                        if re.match(r'^(?:[^\s\#\\]|\\[0-9]{3})*$', arg.text) is None:
                            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

                elif arg.attrib['type'] == 'bool':
                    if arg.text is None or (arg.text != 'true' and arg.text != 'false'):
                        exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

                elif arg.attrib['type'] == 'nil':
                    if arg.text is None or arg.text != 'nil':
                        exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

                elif arg.attrib['type'] == 'var':
                    self._var_syntax(arg, order, arg_i)


            elif pos_type == 'var':
                self._var_syntax(arg, order, arg_i)


            elif pos_type == 'type':
                if arg.attrib['type'] != 'type':
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Unexpected type argument type "{}"'.format(order, arg.attrib['type']))

                if arg.text is None or arg.text not in ['int', 'string', 'bool']:
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))


            elif pos_type == 'label':
                if arg.attrib['type'] != 'label':
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Unexpected type argument type "{}"'.format(order, arg.attrib['type']))

                if arg.text is None or re.match(r'^[a-zA-Z_\-\$\&\%\*\!\?][a-zA-Z0-9_\-\$\&\%\*\!\?]*$', arg.text) is None:
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

            args.append({'type': arg.attrib['type'], 'value': arg.text})
            # args[f'arg{arg_i}'] = {'type': arg.attrib['type'], 'value': arg.text}
            arg_i += 1

        return args

    def _var_syntax(self, arg, order, arg_i):
        if arg.attrib['type'] != 'var':
            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Var type attribute expected "var", not "{}"'.format(order, arg.attrib['type']))

        if arg.text is None or re.match(r'^(?:LF|TF|GF)@[a-zA-Z_\-\$\&\%\*\!\?][a-zA-Z0-9_\-\$\&\%\*\!\?]*$', arg.text) is None:
            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))









        



def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help', action='store_true', help='show this help message and exit', default=False)
    parser.add_argument('-s', '--source', metavar='SOURCE_FILE', action='store', help='XML source code', default=None)
    parser.add_argument('-i', '--input', metavar='INPUT_FILE', action='store', help='Input to feed into STDIN', default=None)
    args = parser.parse_args()

    if args.help == True and args.source == None and args.input == None:
        parser.print_help()
        exit(0)
    elif (args.help == True and (args.source != None or args.input != None)) or (args.source == None and args.input == None):
        exit_err(Code.BAD_PARAM)

    # print(args.source)
    xmlparser = XMLParser()
    instructions = xmlparser.parse(args.source)
    for inst in instructions.instructions:
        print(inst)


if __name__ == '__main__':
    main()
