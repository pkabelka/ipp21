#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""IPPcode21 language interpreter in Python
    Author: Petr Kabelka <xkabel09 at stud.fit.vutbr.cz>
"""

import sys
import os
import re
from enum import Enum
import xml.etree.ElementTree as ET

class Code(Enum):
    """Contains all exit codes"""
    SUCCESS = 0
    BAD_PARAM = 10
    OPEN_ERR = 11
    WRITE_ERR = 12
    BAD_XML = 31
    BAD_STRUCT = 32
    UNDEF_REDEF = 52
    BAD_OPERAND_TYPE = 53
    UNDEF_VAR = 54
    UNDEF_FRAME = 55
    MISSING_VAL = 56
    BAD_OPERAND_VAL = 57
    STRING_ERR = 58

def exit_err(code, message=''):
    """Exits the program with the specified exit code and optional message
    
    Parameters:
        code: Exit code
    """
    err_messages = {
        Code.BAD_PARAM: 'Error: Wrong combination of parameters\nRun only with --help to show help',
        Code.OPEN_ERR: 'Error: Cannot open file',
        Code.WRITE_ERR: 'Error cannot open file for writing',
        Code.BAD_XML: 'Error: Wrong XML format. XML is not well-formed',
        Code.BAD_STRUCT: 'Error: Wrong XML structure'
    }
    if message == '':
        if code in err_messages:
            message = err_messages[code]
    else:
        print(message, file=sys.stderr)
    sys.exit(code.value)

class Instruction():
    """Represents the instruction with opcode and arguments"""
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
        'ADDS': tuple(),
        'SUB': ('var', 'symb', 'symb'),
        'SUBS': tuple(),
        'MUL': ('var', 'symb', 'symb'),
        'MULS': tuple(),
        'IDIV': ('var', 'symb', 'symb'),
        'IDIVS': tuple(),
        'DIV': ('var', 'symb', 'symb'),
        'DIVS': tuple(),
        'LT': ('var', 'symb', 'symb'),
        'LTS': tuple(),
        'GT': ('var', 'symb', 'symb'),
        'GTS': tuple(),
        'EQ': ('var', 'symb', 'symb'),
        'EQS': tuple(),
        'AND': ('var', 'symb', 'symb'),
        'ANDS': tuple(),
        'OR': ('var', 'symb', 'symb'),
        'ORS': tuple(),
        'NOT': ('var', 'symb'),
        'NOTS': tuple(),
        'INT2CHAR': ('var', 'symb'),
        'INT2CHARS': tuple(),
        'STRI2INT': ('var', 'symb', 'symb'),
        'STRI2INTS': tuple(),
        'INT2FLOAT': ('var', 'symb'),
        'INT2FLOATS': tuple(),
        'FLOAT2INT': ('var', 'symb'),
        'FLOAT2INTS': tuple(),
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
        'JUMPIFEQS': tuple(['label']),
        'JUMPIFNEQ': ('label', 'symb', 'symb'),
        'JUMPIFNEQS': tuple(['label']),
        'CLEARS': tuple(),
        'EXIT': tuple(['symb']),
        'DPRINT': tuple(['symb']),
        'BREAK': tuple()
    }

    @classmethod
    def opcode_exists(cls, opcode):
        """Checks if the specified opcode exists in the instruction map

        Parameters:
            opcode: Opcode to check
        """
        if opcode in cls._INST_MAP:
            return True
        return False

    @classmethod
    def opcode_args(cls, opcode):
        """Returns the arguments that the instruction accepts

        Parameters:
            opcode: Instruction opcode
        """
        if not cls.opcode_exists(opcode):
            return None
        return cls._INST_MAP[opcode]

    def __init__(self, opcode, args):
        self.opcode = opcode
        self.args = args


class Instructions:
    """Contains the instruction list, program counter, call stack and labels"""
    def __init__(self):
        self._instructions = []
        self._pc = 0
        self._calls = []
        self._labels = {}
        self.executed_count = 0

    def add(self, inst: Instruction):
        """Appends the instruction to the instruction list

        It also adds new labels into the labels dict

        Parameters:
            inst: Inst object to add to the list
        """
        self._instructions.append(inst)
        if inst.opcode == 'LABEL':
            if inst.args[0]['value'] in self._labels:
                exit_err(Code.UNDEF_REDEF, 'Error: Label "{}" is already defined'.format(inst.args[0]['value']))

            self._labels[inst.args[0]['value']] = len(self._instructions)

    def next(self):
        """Loads the next instruction by incrementing program counter"""
        if self._pc < len(self._instructions):
            self._pc += 1
            self.executed_count += 1
            return self._instructions[self._pc - 1]
        return None

    def label_exists(self, label):
        """Checks if the specified label exists

        Parameters:
            label: Label to check
        """
        return label in self._labels

    def jump(self, label):
        """Jumps to specified label if it exists

        Parameters:
            label: Label to jump to
        """
        if not self.label_exists(label):
            exit_err(Code.UNDEF_REDEF, f'Error: Label "{label}" is not defined')
        self._pc = self._labels[label]

    def get_pc(self):
        """Returns the value of program counter"""
        return self._pc

    def call(self, label):
        """Saves the program counter and jumps to the specified label

        Parameters:
            label: Label to jump to
        """
        self._calls.append(self.get_pc())
        self.jump(label)

    def return_(self):
        """Returns from the call"""
        if len(self._calls) == 0:
            exit_err(Code.MISSING_VAL, f'Error: Cannot "RETURN", no address on the call stack')
        self._pc = self._calls.pop()

    def dec_executed(self):
        """Decreases the number of executed instructions statistic"""
        self.executed_count -= 1



class Var:
    """Class representing a variable, has type and value
    
    Implements all necessary magic methods for operators used with the variables
    """
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        if self.value == None:
            return ''
        return f'{str(self.value)}({self.type})'

    def __add__(self, second):
        if self.type == second.type:
            if self.type in ['int', 'float', 'string']:
                return Var(self.type, self.value + second.value)
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, both not of same type')

    def __sub__(self, second):
        if self.type == second.type:
            if self.type in ['int', 'float']:
                return Var(self.type, self.value - second.value)
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot subtract the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot subtract the values, both not of same type')

    def __mul__(self, second):
        if self.type == second.type:
            if self.type in ['int', 'float']:
                return Var(self.type, self.value * second.value)
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot multiply the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot multiply the values, both not of same type')

    def __floordiv__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                val1 = self.value
                val2 = second.value
                if val2 == 0:
                    exit_err(Code.BAD_OPERAND_VAL, 'Error: Division by zero')
                return Var(self.type, val1 // val2)
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot floor divide the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot floor divide the values, both not of same type')

    def __truediv__(self, second):
        if self.type == second.type:
            if self.type == 'float':
                val1 = self.value
                val2 = second.value
                if val2 == 0.0:
                    exit_err(Code.BAD_OPERAND_VAL, 'Error: Division by zero')
                return Var(self.type, val1 / val2)
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot divide the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot divide the values, both not of same type')

    def __lt__(self, second):
        if self.type == second.type:
            if self.type in ['int', 'float']:
                return Var('bool', 'true' if self.value < second.value else 'false')
            elif self.type == 'bool':
                return Var('bool', 'true' if self.value == 'false' and second.value == 'true' else 'false')
            elif self.type == 'string':
                return Var('bool', 'true' if self.value < second.value else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __gt__(self, second):
        if self.type == second.type:
            if self.type in ['int', 'float']:
                return Var('bool', str(self.value > second.value).lower())
            elif self.type == 'bool':
                return Var('bool', 'true' if self.value == 'true' and second.value == 'false' else 'false')
            elif self.type == 'string':
                return Var('bool', 'true' if self.value > second.value else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __eq__(self, second):
        if self.type == second.type:
            if self.type in ['int', 'float']:
                return Var('bool', str(self.value == second.value).lower())
            elif self.type in ['string', 'bool', 'nil']:
                return Var('bool', 'true' if self.value == second.value else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')

        elif self.type == 'nil' or second.type == 'nil':
            return Var('bool', 'false')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __ne__(self, second):
        if self.type == second.type:
            if self.type in ['int', 'float']:
                return Var('bool', str(self.value != second.value).lower())
            elif self.type in ['string', 'bool', 'nil']:
                return Var('bool', 'true' if self.value != second.value else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')

        elif self.type == 'nil' or second.type == 'nil':
            return Var('bool', 'true')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __and__(self, second):
        if self.type == second.type:
            if self.type == 'bool':
                return Var('bool', 'true' if self.value == 'true' and second.value == 'true' else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __or__(self, second):
        if self.type == second.type:
            if self.type == 'bool':
                return Var('bool', 'true' if self.value == 'true' or second.value == 'true' else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __invert__(self):
        if self.type == 'bool':
            return Var('bool', 'true' if self.value == 'false' else 'false')
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot negate the values, wrong operand type')


class Frames():
    """Contains frames and methods for controlling frame operations"""
    def __init__(self):
        self._lf_stack = []
        self._gf = {}
        self._tf = {}
        self._tf_created = False
        self._init_vars = 0

    def createframe(self):
        """Creates a new Temporary Frame"""
        self._tf = {}
        self._tf_created = True

    def pushframe(self):
        """Pushes the existing Local Frame to the stack and moves the Temporary Frame to a new Local Frame"""
        if not self._tf_created:
            exit_err(Code.UNDEF_FRAME, 'Error: TF (Temporary Frame) does not exist, use "CREATEFRAME" first')

        self._lf_stack.append(self._tf)
        self._tf = {}
        self._tf_created = False

    def popframe(self):
        """Moves an existing Local Frame to the Temporary Frame and pops a new Local Frame from the stack"""
        if len(self._lf_stack) == 0:
            exit_err(Code.UNDEF_FRAME, 'Error: Cannot "POPFRAME", no frames on the frame stack')

        self._tf = self._lf_stack.pop()
        self._tf_created = True

        self._check_init_vars()

    def defvar(self, id):
        """Defines a new variable

        The method gets the frame and variable name from id, checks if the
        destination frame exists and creates a Var object containing the variable values

        Parameters:
            id: Variable identifier in this format: frame@identifier, e.g. LF@foo
        """
        frame_name, var_name = id.split('@', 1)
        if frame_name == 'LF':
            if len(self._lf_stack) == 0:
                exit_err(Code.UNDEF_FRAME, 'Error: Cannot "DEFVAR", no frames on the frame stack')
            frame = self._lf_stack[-1]

        elif frame_name == 'TF':
            if not self._tf_created:
                exit_err(Code.UNDEF_FRAME, f'Error: Cannot "DEFVAR" "TF@{var_name}" because TF (Temporary Frame) does not exist, use "CREATEFRAME" first')
            frame = self._tf

        elif frame_name == 'GF':
            frame = self._gf

        if var_name in frame:
            exit_err(Code.UNDEF_REDEF, f'Error: Cannot "DEFVAR", "{frame_name}@{var_name}" is already defined')

        frame[var_name] = Var(None, None)

    def getvar(self, id, check_init=True):
        """Finds and returns a Var instance specified by the identifier

        Parameters:
            id: Full variable identifier with the frame specification
            check_init: Whether or not to check if the variable is initialized
        """
        frame_name, var_name = id.split('@', 1)
        if frame_name == 'LF':
            if len(self._lf_stack) == 0:
                exit_err(Code.UNDEF_FRAME, f'Error: Cannot access "LF@{var_name}, no frames on the frame stack')
            frame = self._lf_stack[-1]

        elif frame_name == 'TF':
            if not self._tf_created:
                exit_err(Code.UNDEF_FRAME, f'Error: "TF@{var_name}" because TF (Temporary Frame) does not exist, use "CREATEFRAME" first')
            frame = self._tf

        elif frame_name == 'GF':
            frame = self._gf

        if var_name not in frame:
            exit_err(Code.UNDEF_VAR, f'Error: "{frame_name}@{var_name}" is not defined')

        if check_init and (frame[var_name].type is None or frame[var_name].value is None):
            exit_err(Code.MISSING_VAL, f'Error: Cannot read from "{frame_name}@{var_name}" because it is not initialized')

        return frame, var_name

    def setvar(self, id, var: Var):
        """Finds and returns a Var instance specified by the identifier

        Parameters:
            id: Full variable identifier with the frame specification
            var: Variable represented with a Var instance
        """
        frame, var_name = self.getvar(id, check_init=False)
        frame[var_name] = var

        self._check_init_vars()

    def get_gf(self):
        """Returns the Global Frame"""
        return self._gf

    def get_lf(self):
        """Returns the Local Frame"""
        if len(self._lf_stack) > 0:
            return self._lf_stack[-1]
        return {}

    def get_tf(self):
        """Returns the Temporary Frame"""
        return self._tf

    def const_var(self, var, check_init=True):
        """Finds and returns a variable Var instance specified by the identifier
        in var['value'] or Var instace of the constant

        Parameters:
            var: Dict with data type and value
            check_init: Whether or not to check if the variable is initialized
        """
        if var['type'] in ['int', 'string', 'bool', 'nil', 'float']:
            return Var(var['type'], var['value'])
        elif var['type'] == 'var':
            frame, var_name = self.getvar(var['value'], check_init=check_init)
            return frame[var_name]

    def _check_init_vars(self):
        """Counts the number of initialized variables"""
        count = sum(var.value is not None for var in self.get_tf().values()) + \
                sum(var.value is not None for var in self.get_lf().values()) + \
                sum(var.value is not None for var in self.get_gf().values())
        if count > self._init_vars:
            self._init_vars = count

    def get_init_vars(self):
        return self._init_vars

class Stack:
    """Data stack"""
    def __init__(self):
        self._stack = []

    def pushs(self, var: Var):
        """Pushes the variable to the data stack

        Parameters:
            var: Variable to push to the data stack
        """
        self._stack.append(var)

    def pops(self):
        """Pops the variable from the data stack and returns it"""
        if len(self._stack) == 0:
            exit_err(Code.MISSING_VAL, 'Error: Cannot "POPS", no value on the data stack')
        return self._stack.pop()

    def clears(self):
        """Clears the data stack"""
        self._stack = []

    def get_stack(self):
        """Returns the data stack"""
        return self._stack



class InstructionExecutor:
    """Contains methods which execute the instruction operations"""
    def __init__(self, instructions, input_file, xmlroot, stats_path, stats_group):
        self.insts = instructions
        self.frames = Frames()
        self.stack = Stack()
        self.exec_per_inst = {}
        if input_file == sys.stdin:
            self.input_file = input_file
        else:
            try:
                self.input_file = open(input_file, 'r')
            except Exception:
                exit_err(Code.OPEN_ERR)
        self.xmlroot = xmlroot
        self.stats_path = stats_path
        self.stats_group = stats_group

    def interpret(self):
        """Starts the instruction interpretation"""
        while True:
            inst = self.insts.next()
            if inst is None:
                break

            if Instruction.opcode_exists(inst.opcode):
                eval(f'self._{inst.opcode}(inst.args)') # instruction is executed by evaluating this string and calling the method
                if inst.opcode in self.exec_per_inst:
                    self.exec_per_inst[inst.opcode] += 1
                else:
                    self.exec_per_inst[inst.opcode] = 1

        # do not count these instructions in number of executions
        if 'LABEL' in self.exec_per_inst: del(self.exec_per_inst['LABEL'])
        if 'BREAK' in self.exec_per_inst: del(self.exec_per_inst['BREAK'])
        if 'DPRINT' in self.exec_per_inst: del(self.exec_per_inst['DPRINT'])
        self.exec_per_inst = dict(reversed(sorted(self.exec_per_inst.items(), key=lambda item: item[1])))
        self.write_stats()
        exit_err(Code.SUCCESS)

    def write_stats(self):
        """Writes the statistics into the statistics file"""
        if self.stats_path:
            if (len(self.exec_per_inst)) > 0:
                most_exec = list(self.exec_per_inst.keys())[0]
                insts = self.xmlroot.findall(f'.//instruction[@opcode="{most_exec}"]')
                min_order = int(insts[0].attrib['order'])
                if len(insts) > 1:
                    for inst in insts:
                        min_order = min(min_order, int(inst.attrib['order']))

            try:
                with open(self.stats_path, 'w') as stat_file:
                    for stat in self.stats_group:
                        if stat == '--insts':
                            stat_file.write(f'{self.insts.executed_count}\n')
                        elif stat == '--hot':
                            stat_file.write(f'{min_order}\n')
                        elif stat == '--vars':
                            stat_file.write(f'{self.frames.get_init_vars()}\n')
            except Exception:
                exit_err(Code.WRITE_ERR)

    def _MOVE(self, args):
        if args[1]['type'] in ['int', 'string', 'bool', 'nil', 'float']:
            self.frames.setvar(args[0]['value'], Var(args[1]['type'], args[1]['value']))
        elif args[1]['type'] == 'var':
            frame, var_name = self.frames.getvar(args[1]['value'])
            self.frames.setvar(args[0]['value'], frame[var_name])

    def _CREATEFRAME(self, args):
        self.frames.createframe()

    def _PUSHFRAME(self, args):
        self.frames.pushframe()

    def _POPFRAME(self, args):
        self.frames.popframe()

    def _DEFVAR(self, args):
        self.frames.defvar(args[0]['value'])

    def _CALL(self, args):
        self.insts.call(args[0]['value'])

    def _RETURN(self, args):
        self.insts.return_()

    def _PUSHS(self, args):
        if args[0]['type'] in ['int', 'string', 'bool', 'nil', 'float']:
            self.stack.pushs(Var(args[0]['type'], args[0]['value']))
        elif args[0]['type'] == 'var':
            frame, var_name = self.frames.getvar(args[0]['value'])
            self.stack.pushs(frame[var_name])

    def _POPS(self, args):
        self.frames.setvar(args[0]['value'], self.stack.pops())

    def _ADD(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'int' and symb2.type == 'int' or symb1.type == 'float' and symb2.type == 'float':
            self.frames.setvar(args[0]['value'], symb1 + symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, both not type int')

    def _ADDS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == 'int' and symb2.type == 'int' or symb1.type == 'float' and symb2.type == 'float':
            self.stack.pushs(symb1 + symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, both not type int')

    def _SUB(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'int' and symb2.type == 'int' or symb1.type == 'float' and symb2.type == 'float':
            self.frames.setvar(args[0]['value'], symb1 - symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot subtract the values, both not type int')

    def _SUBS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == 'int' and symb2.type == 'int' or symb1.type == 'float' and symb2.type == 'float':
            self.stack.pushs(symb1 - symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, both not type int')

    def _MUL(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'int' and symb2.type == 'int' or symb1.type == 'float' and symb2.type == 'float':
            self.frames.setvar(args[0]['value'], symb1 * symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot multiply the values, both not type int')

    def _MULS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == 'int' and symb2.type == 'int' or symb1.type == 'float' and symb2.type == 'float':
            self.stack.pushs(symb1 * symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, both not type int')

    def _IDIV(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'int' and symb2.type == 'int':
            self.frames.setvar(args[0]['value'], symb1 // symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot floor divide the values, both not type int')

    def _IDIVS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == 'int' and symb2.type == 'int':
            self.stack.pushs(symb1 // symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot floor divide the values, both not type int')

    def _DIV(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'float' and symb2.type == 'float':
            self.frames.setvar(args[0]['value'], symb1 / symb2)
        elif symb1.type == 'string' or symb2.type == 'string':
            exit_err(Code.STRING_ERR, 'Error: Cannot divide strings')
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot divide the values, both not type float')

    def _DIVS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == 'float' and symb2.type == 'float':
            self.stack.pushs(symb1 / symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot divide the values, both not type float')

    def _LT(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == symb2.type and symb1.type != 'nil':
            self.frames.setvar(args[0]['value'], symb1 < symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _LTS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == symb2.type and symb1.type != 'nil':
            self.stack.pushs(symb1 < symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _GT(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == symb2.type and symb1.type != 'nil':
            self.frames.setvar(args[0]['value'], symb1 > symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _GTS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == symb2.type and symb1.type != 'nil':
            self.stack.pushs(symb1 > symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _EQ(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == symb2.type or symb1.type == 'nil' or symb2.type == 'nil':
            self.frames.setvar(args[0]['value'], symb1 == symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _EQS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == symb2.type or symb1.type == 'nil' or symb2.type == 'nil':
            self.stack.pushs(symb1 == symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _AND(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'bool' and symb2.type == 'bool':
            self.frames.setvar(args[0]['value'], symb1 & symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _ANDS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == 'bool' and symb2.type == 'bool':
            self.stack.pushs(symb1 & symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _OR(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'bool' and symb2.type == 'bool':
            self.frames.setvar(args[0]['value'], symb1 | symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _ORS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type == 'bool' and symb2.type == 'bool':
            self.stack.pushs(symb1 | symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _NOT(self, args):
        symb = self.frames.const_var(args[1])
        if symb.type == 'bool':
            self.frames.setvar(args[0]['value'], ~symb)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot negate value')

    def _NOTS(self, args):
        symb = self.stack.pops()
        if symb.type == 'bool':
            self.stack.pushs(~symb)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot negate value')

    def _INT2CHAR(self, args):
        symb = self.frames.const_var(args[1])
        if symb.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Cannot convert type "{symb.type}" to char')
        try:
            self.frames.setvar(args[0]['value'], Var('string', chr(symb.value)))
        except ValueError:
            exit_err(Code.STRING_ERR, f'Error: Cannot convert int to char, "{symb.value}" is not valid Unicode value')

    def _INT2CHARS(self, args):
        symb = self.stack.pops()
        if symb.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Cannot convert type "{symb.type}" to char')
        try:
            self.stack.pushs(Var('string', chr(symb.value)))
        except ValueError:
            exit_err(Code.STRING_ERR, f'Error: Cannot convert int to char, "{symb.value}" is not valid Unicode value')

    def _STRI2INT(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type != 'string' or symb2.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Wrong operand types')

        if symb2.value < 0 or symb2.value >= len(symb1.value):
            exit_err(Code.STRING_ERR, f'Error: Index out of range')

        self.frames.setvar(args[0]['value'], Var('int', ord(symb1.value[symb2.value])))

    def _STRI2INTS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if symb1.type != 'string' or symb2.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Wrong operand types')

        if symb2.value < 0 or symb2.value >= len(symb1.value):
            exit_err(Code.STRING_ERR, f'Error: Index out of range')

        self.stack.pushs(Var('int', ord(symb1.value[symb2.value])))

    def _INT2FLOAT(self, args):
        symb = self.frames.const_var(args[1])
        if symb.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Cannot convert type "{symb.type}" to float')

        self.frames.setvar(args[0]['value'], Var('float', float(symb.value)))

    def _INT2FLOATS(self, args):
        symb = self.stack.pops()
        if symb.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Cannot convert type "{symb.type}" to float')

        self.stack.pushs(Var('float', float(symb.value)))

    def _FLOAT2INT(self, args):
        symb = self.frames.const_var(args[1])
        if symb.type != 'float':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Cannot convert type "{symb.type}" to int')

        self.frames.setvar(args[0]['value'], Var('int', int(symb.value)))

    def _FLOAT2INTS(self, args):
        symb = self.stack.pops()
        if symb.type != 'float':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Cannot convert type "{symb.type}" to int')

        self.stack.pushs(Var('int', int(symb.value)))

    def _READ(self, args):
        if args[1]['value'] not in ['int', 'string', 'bool', 'float']:
            exit_err(Code.BAD_OPERAND_VAL, f'Error: Wrong operand value')

        type_ = args[1]['value']

        res_val = ''
        res_type = type_
        try:
            if self.input_file == sys.stdin:
                input_val = input().rstrip('\n')
            else:
                input_val = self.input_file.readline().rstrip('\n')
        except Exception:
            res_val = 'nil'
            res_type = 'nil'

        if type_ == 'bool':
            if input_val.upper() == 'TRUE':
                res_val = 'true'
            else:
                res_val = 'false'
        elif type_ == 'int':
            try:
                res_val = int(input_val)
            except Exception:
                res_val = 'nil'
                res_type = 'nil'
        elif type_ == 'float':
            try:
                res_val = float.fromhex(input_val)
            except Exception:
                res_val = 'nil'
                res_type = 'nil'
        elif type_ == 'string':
            res_val = input_val

        self.frames.setvar(args[0]['value'], Var(res_type, res_val))

    def _WRITE(self, args):
        symb = self.frames.const_var(args[0])
        if symb.type == 'float':
            print(symb.value.hex(), end='')
        elif symb.type == 'nil':
            print('', end='')
        else:
            print(symb.value, end='')

    def _CONCAT(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'string' and symb2.type == 'string':
            self.frames.setvar(args[0]['value'], symb1 + symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot concatenate the values, both not type string')

    def _STRLEN(self, args):
        symb = self.frames.const_var(args[1])
        if symb.type != 'string':
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot get string length operand is not string')
        self.frames.setvar(args[0]['value'], Var('int', len(symb.value)))

    def _GETCHAR(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type != 'string' or symb2.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Wrong operand types')

        if symb2.value < 0 or symb2.value >= len(symb1.value):
            exit_err(Code.STRING_ERR, f'Error: Index out of range')

        self.frames.setvar(args[0]['value'], Var('string', symb1.value[symb2.value]))

    def _SETCHAR(self, args):
        var = self.frames.const_var(args[0])
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])

        if var.type != 'string' or symb1.type != 'int' or symb2.type != 'string':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Wrong operand types')

        if symb1.value < 0 or symb1.value >= len(var.value):
            exit_err(Code.STRING_ERR, f'Error: Index out of range')

        if len(symb2.value) == 0:
            exit_err(Code.STRING_ERR, f'Error: Second operand is empty')

        self.frames.setvar(args[0]['value'], Var('string', var.value[:symb1.value] + symb2.value[0] + var.value[symb1.value + 1:]))

    def _TYPE(self, args):
        symb = self.frames.const_var(args[1], check_init=False)
        if symb.type is None:
            self.frames.setvar(args[0]['value'], Var('string', ''))
        else:
            self.frames.setvar(args[0]['value'], Var('string', symb.type))

    def _LABEL(self, args):
        self.insts.dec_executed()

    def _JUMP(self, args):
        self.insts.jump(args[0]['value'])

    def _JUMPIFEQ(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if not self.insts.label_exists(args[0]['value']):
            exit_err(Code.UNDEF_REDEF, 'Error: Label "{}" does not exist'.format(args[0]['value']))
        if symb1.type == symb2.type or symb1.type == 'nil' or symb2.type == 'nil':
            if (symb1 == symb2).value == 'true':
                self.insts.jump(args[0]['value'])
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _JUMPIFEQS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if not self.insts.label_exists(args[0]['value']):
            exit_err(Code.UNDEF_REDEF, 'Error: Label "{}" does not exist'.format(args[0]['value']))
        if symb1.type == symb2.type or symb1.type == 'nil' or symb2.type == 'nil':
            if (symb1 == symb2).value == 'true':
                self.insts.jump(args[0]['value'])
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _JUMPIFNEQ(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if not self.insts.label_exists(args[0]['value']):
            exit_err(Code.UNDEF_REDEF, 'Error: Label "{}" does not exist'.format(args[0]['value']))
        if symb1.type == symb2.type or symb1.type == 'nil' or symb2.type == 'nil':
            if (symb1 != symb2).value == 'true':
                self.insts.jump(args[0]['value'])
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _JUMPIFNEQS(self, args):
        symb2 = self.stack.pops()
        symb1 = self.stack.pops()
        if not self.insts.label_exists(args[0]['value']):
            exit_err(Code.UNDEF_REDEF, 'Error: Label "{}" does not exist'.format(args[0]['value']))
        if symb1.type == symb2.type or symb1.type == 'nil' or symb2.type == 'nil':
            if (symb1 != symb2).value == 'true':
                self.insts.jump(args[0]['value'])
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _CLEARS(self, args):
        self.stack.clears()

    def _EXIT(self, args):
        symb = self.frames.const_var(args[0])
        if symb.type == 'int':
            if symb.value >= 0 and symb.value <= 49:
                self.write_stats()
                sys.exit(symb.value)
            else:
                exit_err(Code.BAD_OPERAND_VAL, f'Error: Exit code "{symb.value}" not in range 0-49')
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong EXIT operand type')

    def _DPRINT(self, args):
        self.insts.dec_executed()
        if args[0]['type'] in ['int', 'string', 'bool', 'nil']:
            print('Const@={}({})'.format(args[0]['value'], args[0]['type']), file=sys.stderr)

        elif args[0]['type'] == 'var':
            frame, var_name = self.frames.getvar(args[0]['value'])

            if frame[var_name].value == None:
                print('{}()'.format(args[0]['value']), file=sys.stderr)
            else:
                print('{}={}({})'.format(args[0]['value'], frame[var_name].value, frame[var_name].type), file=sys.stderr)

    def _BREAK(self, args):
        self.insts.dec_executed()
        gf = self.frames.get_gf()
        lf = self.frames.get_lf()
        tf = self.frames.get_tf()
        stack = self.stack.get_stack()

        print(f'Current instruction: {self.insts.get_pc()}', file=sys.stderr)
        print(f'Number of executed instructions: {self.insts.executed_count}\n', file=sys.stderr)

        print('Global Frame:', file=sys.stderr)
        for name in gf:
            print(f'GF@{name}{"="+str(gf[name]) if str(gf[name]) != "" else "()"}', file=sys.stderr)

        print('\nLocal Frame:', file=sys.stderr)
        for name in lf:
            print(f'LF@{name}{"="+str(lf[name]) if str(lf[name]) != "" else "()"}', file=sys.stderr)

        print('\nTemporary Frame:', file=sys.stderr)
        for name in tf:
            print(f'TF@{name}{"="+str(tf[name]) if str(tf[name]) != "" else "()"}', file=sys.stderr)

        print('\nStack:', file=sys.stderr)
        for var in reversed(stack):
            print(f'Stack@={str(var) if str(var) != "" else ""}', file=sys.stderr)




class XMLParser():
    """Contains parse function to parse XML document into Instructions class"""
    def __init__(self):
        self.instructions = Instructions()
        self.tree = None


    def parse(self, source_path):
        """Parses the XML document, checks the structure and lexical and syntactical correctness

        Parameters:
            source_path: filename or file object containing XML data

        Returns:
            Instructions: Class containing the parsed instructions
        """

        try:
            self.tree = ET.parse(source_path)
        except FileNotFoundError:
            exit_err(Code.OPEN_ERR)
        except PermissionError:
            exit_err(Code.OPEN_ERR)
        except ET.ParseError:
            exit_err(Code.BAD_XML)

        root = self.tree.getroot()

        # check XML structure
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
                exit_err(Code.BAD_STRUCT, f'Error: Expected "instruction" tag, not "{inst.tag}"')
            if len(inst.attrib) > 2:
                exit_err(Code.BAD_STRUCT, 'Error: Too many argument attributes')
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

            if int(order) in inst_orders: # duplicate instruction order
                exit_err(Code.BAD_STRUCT, f'Error: Duplicate instruction order found: {order}')
            inst_orders[int(order)] = None

            # check instruction syntax
            args = self._inst_syntax(inst)

            inst_orders[int(order)] = Instruction(opcode, args)

        # append the instructions in the correct order
        for i in sorted(inst_orders):
            self.instructions.add(inst_orders[i])

        return self.instructions


    def _inst_syntax(self, inst):
        args = []
        opcode = inst.attrib['opcode'].upper()
        order = inst.attrib['order']
        if Instruction.opcode_args(opcode) is None:
            exit_err(Code.BAD_STRUCT, 'Error: Unknown instruction opcode "{}" with order "{}"'.format(inst.attrib['opcode'], order))

        if len(inst) != len(Instruction.opcode_args(opcode)):
            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Wrong number of arguments, expected {} but {} given'.format(order, len(Instruction.opcode_args(opcode)), len(inst)))

        # argument syntax
        arg_orders = {}
        for arg in inst:
            if 'arg' not in arg.tag:
                exit_err(Code.BAD_STRUCT, 'Error: Invalid arg tag')

            try:
                arg_i = int(arg.tag[3:])
                if arg_i < 1 or arg_i > 3 or arg_i > len(Instruction.opcode_args(opcode)):
                    exit_err(Code.BAD_STRUCT, 'Error: "arg" tag order must have a positive non-zero integer value')
            except ValueError:
                exit_err(Code.BAD_STRUCT, 'Error: "arg" tag order must have a positive non-zero integer value')
            
            if arg_i in arg_orders:
                exit_err(Code.BAD_STRUCT, 'Error: Duplicate "arg" tag value')

            if len(arg.attrib) > 1 or 'type' not in arg.attrib:
                exit_err(Code.BAD_STRUCT, f'Error: Order "{order}": Expected a single argument attribute "type"')

            pos_type = Instruction.opcode_args(opcode)[arg_i-1]
            if pos_type == 'symb':
                if arg.attrib['type'] not in ['int', 'string', 'bool', 'nil', 'var', 'float']:
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Unexpected symb argument type "{}"'.format(order, arg.attrib['type']))

                if arg.attrib['type'] == 'int':
                    try:
                        arg.text = int(arg.text)
                    except ValueError:
                        exit_err(Code.BAD_STRUCT, f'Error: Order "{order}": arg{arg_i} with type "int" has wrong value')

                elif arg.attrib['type'] == 'string':
                    if arg.text is not None:
                        if re.match(r'^(?:[^\s\#\\]|\\[0-9]{3})*$', arg.text) is None:
                            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

                        arg.text = re.sub(r'\\([0-9]{3})', self._escape_ascii, arg.text) # replaces escape sequences with their characters
                    else:
                        arg.text = ''

                elif arg.attrib['type'] == 'bool':
                    if arg.text is None or (arg.text != 'true' and arg.text != 'false'):
                        exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

                elif arg.attrib['type'] == 'nil':
                    if arg.text is None or arg.text != 'nil':
                        exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

                elif arg.attrib['type'] == 'var':
                    self._var_syntax(arg, order, arg_i)

                elif arg.attrib['type'] == 'float':
                    try:
                        arg.text = float.fromhex(arg.text)
                    except ValueError:
                        exit_err(Code.BAD_STRUCT, f'Error: Order "{order}": arg{arg_i} with type "float" has wrong value')


            elif pos_type == 'var':
                self._var_syntax(arg, order, arg_i)


            elif pos_type == 'type':
                if arg.attrib['type'] != 'type':
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Unexpected type argument type "{}"'.format(order, arg.attrib['type']))

                if arg.text is None or arg.text not in ['int', 'string', 'bool', 'float']:
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))


            elif pos_type == 'label':
                if arg.attrib['type'] != 'label':
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Unexpected type argument type "{}"'.format(order, arg.attrib['type']))

                if arg.text is None or re.match(r'^[a-zA-Z_\-\$\&\%\*\!\?][a-zA-Z0-9_\-\$\&\%\*\!\?]*$', arg.text) is None:
                    exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

            arg_orders[arg_i] = {'type': arg.attrib['type'], 'value': arg.text}

        for i in sorted(arg_orders):
            args.append(arg_orders[i])
        return args

    def _var_syntax(self, arg, order, arg_i):
        if arg.attrib['type'] != 'var':
            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Var type attribute expected "var", not "{}"'.format(order, arg.attrib['type']))

        if arg.text is None or re.match(r'^(?:LF|TF|GF)@[a-zA-Z_\-\$\&\%\*\!\?][a-zA-Z0-9_\-\$\&\%\*\!\?]*$', arg.text) is None:
            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

    def _escape_ascii(self, match):
        return chr(int(match.group(1)))


def parse_args():
    if len(sys.argv) <= 1:
        exit_err(Code.BAD_PARAM)

    args = sys.argv[1:]

    for arg in args:
        valid = any(arg.startswith(valid_arg) for valid_arg in ['--help', '--source=', '--input=', '--stats=', '--insts', '--hot', '--vars'])
        if not valid:
            exit_err(Code.BAD_PARAM)

    source_arg = [arg for arg in args if arg.startswith('--source=')]
    input_arg = [arg for arg in args if arg.startswith('--input=')]
    stats_arg = [arg for arg in args if arg.startswith('--stats=')]
    stats_path = False
    stats_group = []

    if len(args) == 1 and '--help' in args:
        print('usage: interpret.py [--help] [--source=SOURCE_FILE] [--input=INPUT_FILE] [--stats=OUTPUT_FILE [--insts] [--hot] [--vars]]\n')
        print('arguments:')
        print('  --help                  show this help message and exit')
        print('  --source=SOURCE_FILE    IPPcode21 source XML')
        print('  --input=INPUT_FILE      inputs to pass into READ instruction')
        print('  --stats=OUTPUT_FILE     file to write stats into')
        print('  --insts                 write number of executed instructions into stats')
        print('  --hot                   write the smallest order of the most executed instruction into stats')
        print('  --vars                  write the maximum number of initialized variables across all frames into stats\n')
        print('Statistic arguments can only be used after --stats argument is specified')
        sys.exit(0)

    elif len(args) > 0 and '--help' not in args and (any(source_arg) or any(input_arg)):
        if any(source_arg):
            if len(source_arg) == 1:
                _, source_file = source_arg[0].split('=', 1)
                args.remove(source_arg[0])
            else:
                exit_err(Code.BAD_PARAM)
        else:
            source_file = sys.stdin

        if any(input_arg):
            if len(input_arg) == 1:
                _, input_file = input_arg[0].split('=', 1)
                args.remove(input_arg[0])
            else:
                exit_err(Code.BAD_PARAM)
        else:
            input_file = sys.stdin
    else:
        exit_err(Code.BAD_PARAM)

    if len(stats_arg) == 1:
        if args[0] == stats_arg[0]:
            _, stats_path = stats_arg[0].split('=', 1)
            stats_group = args[1:]
        else:
            exit_err(Code.BAD_PARAM)

    return source_file, input_file, stats_path, stats_group


def main():
    source_file, input_file, stats_path, stats_group = parse_args()
    xmlparser = XMLParser()
    instructions = xmlparser.parse(source_file)

    inst_ex = InstructionExecutor(instructions, input_file, xmlparser.tree.getroot(), stats_path, stats_group)
    inst_ex.interpret()

if __name__ == '__main__':
    main()
