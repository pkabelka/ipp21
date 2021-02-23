#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""IPPcode21 language interpreter in Python
    Author: Petr Kabelka <xkabel09 at stud.fit.vutbr.cz>
"""

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
    UNDEF_REDEF = 52
    BAD_OPERAND_TYPE = 53
    UNDEF_VAR = 54
    UNDEF_FRAME = 55
    MISSING_VAL = 56
    BAD_OPERAND_VAL = 57
    STRING_ERR = 58

def exit_err(code, message=''):
    err_messages = {
        Code.BAD_PARAM: 'Error: Wrong combination of parameters\nRun only with --help to show help',
        Code.OPEN_ERR: 'Error: Cannot open file',
        Code.BAD_XML: 'Error: Wrong XML format. XML is not well-formed',
        Code.BAD_STRUCT: 'Error: Wrong XML structure'
    }
    if message == '':
        if code in err_messages:
            message = err_messages[code]
    
    print(message, file=sys.stderr)
    exit(code.value)

class Instruction():
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
    def opcode_exists(cls, opcode):
        if opcode in cls._INST_MAP:
            return True
        return False

    @classmethod
    def opcode_args(cls, opcode):
        if not cls.opcode_exists(opcode):
            return None
        return cls._INST_MAP[opcode]

    def __init__(self, opcode, args):
        self.opcode = opcode
        self.args = args


class Instructions:
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
        if self._pc < len(self._instructions):
            self._pc += 1
            self.executed_count += 1
            return self._instructions[self._pc - 1]
        return None

    def jump(self, label):
        if label not in self._labels:
            exit_err(Code.UNDEF_REDEF, f'Error: Label "{label}" is not defined')
        self._pc = self._labels[label]

    def get_pc(self):
        return self._pc

    def call(self):
        self._calls.append(self.get_pc())

    def return_(self):
        if len(self._calls) == 0:
            exit_err(Code.MISSING_VAL, f'Error: Cannot "RETURN", no address on the call stack')
        self._pc = self._calls.pop()

    def dec_executed(self):
        self.executed_count -= 1



class Var:
    """Class representing a variable, has type and value"""
    def __init__(self, type_, value):
        self.type = type_
        if self.type == 'int':
            try:
                self.value = int(value)
            except ValueError:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
        else:
            self.value = value

    def __repr__(self):
        if self.value == None:
            return ''
        return f'{str(self.value)}({self.type})'

    def __add__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                try:
                    return Var(self.type, int(self.value) + int(second.value))
                except ValueError:
                    exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
            elif self.type == 'string':
                return Var(self.type, str(self.value) + str(second.value))
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, both not of same type')

    def __sub__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                try:
                    return Var(self.type, int(self.value) - int(second.value))
                except ValueError:
                    exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot subtract the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot subtract the values, both not of same type')

    def __mul__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                try:
                    return Var(self.type, int(self.value) * int(second.value))
                except ValueError:
                    exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot multiply the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot multiply the values, both not of same type')

    def __floordiv__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                try:
                    val1 = int(self.value)
                    val2 = int(second.value)
                    if val2 == 0:
                        exit_err(Code.BAD_OPERAND_VAL, 'Error: Division by zero')
                    return Var(self.type, val1 // val2)
                except ValueError:
                    exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot floor divide the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot floor divide the values, both not of same type')

    def __lt__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                try:
                    return Var('bool', 'true' if int(self.value) < int(second.value) else 'false')
                except ValueError:
                    exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
            elif self.type == 'bool':
                return Var('bool', 'true' if self.value == 'false' else 'false')
            elif self.type == 'string':
                return Var('bool', 'true' if self.value < second.value else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __gt__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                try:
                    return Var('bool', str(int(self.value) > int(second.value)).lower())
                except ValueError:
                    exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
            elif self.type == 'bool':
                return Var('bool', 'true' if second.value == 'false' else 'false')
            elif self.type == 'string':
                return Var('bool', 'true' if self.value > second.value else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __eq__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                try:
                    return Var('bool', str(int(self.value) == int(second.value)).lower())
                except ValueError:
                    exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
            elif self.type in ['string', 'bool', 'nil']:
                return Var('bool', 'true' if self.value == second.value else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')
        exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, both not of same type')

    def __ne__(self, second):
        if self.type == second.type:
            if self.type == 'int':
                try:
                    return Var('bool', str(int(self.value) != int(second.value)).lower())
                except ValueError:
                    exit_err(Code.BAD_OPERAND_TYPE, 'Error: Wrong int type value')
            elif self.type in ['string', 'bool', 'nil']:
                return Var('bool', 'true' if self.value != second.value else 'false')
            else:
                exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare the values, wrong operand types')
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
    """Contains methods for controlling frame operations"""
    def __init__(self):
        self._lf_stack = []
        self._gf = {}
        self._tf = {}
        self._tf_created = False

    def createframe(self):
        self._tf = {}
        self._tf_created = True

    def pushframe(self):
        if not self._tf_created:
            exit_err(Code.UNDEF_FRAME, 'Error: TF (Temporary Frame) does not exist, use "CREATEFRAME" first')

        self._lf_stack.append(self._tf)
        self._tf = {}
        self._tf_created = False

    def popframe(self):
        if len(self._lf_stack) == 0:
            exit_err(Code.UNDEF_FRAME, 'Error: Cannot "POPFRAME", no frames on the frame stack')

        self._tf = self._lf_stack.pop()
        self._tf_created = True

    def defvar(self, id):
        """Defines a new variable

        The method get the frame and variable name from id, checks if the
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

    def getvar(self, id):
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

        return frame, var_name

    def setvar(self, id, var: Var):
        frame, var_name = self.getvar(id)
        frame[var_name] = var

    def get_gf(self):
        return self._gf

    def get_lf(self):
        if len(self._lf_stack) > 0:
            return self._lf_stack[-1]
        return {}

    def get_tf(self):
        return self._tf

    def const_var(self, var):
        if var['type'] in ['int', 'string', 'bool', 'nil']:
            return Var(var['type'], var['value'])
        elif var['type'] == 'var':
            frame, var_name = self.getvar(var['value'])
            return frame[var_name]

class Stack:
    def __init__(self):
        self._stack = []

    def pushs(self, var: Var):
        self._stack.append(var)

    def pops(self):
        if len(self._stack) == 0:
            exit_err(Code.MISSING_VAL, f'Error: Cannot "POPS", no value on the data stack')
        return self._stack.pop()

    def get_stack(self):
        return self._stack



class InstructionExecutor:
    def __init__(self, instructions):
        self.insts = instructions
        self.frames = Frames()
        self.stack = Stack()
        self.input_file = sys.stdin

    def set_input(self, input_file):
        try:
            self.input_file = open(input_file, 'r')
        except Exception:
            exit_err(Code.OPEN_ERR)

    def interpret(self):
        while True:
            inst = self.insts.next()
            if inst is None:
                break

            if Instruction.opcode_exists(inst.opcode):
                eval(f'self._{inst.opcode}(inst.args)')

    def _MOVE(self, args):
        if args[1]['type'] in ['int', 'string', 'bool', 'nil']:
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
        self.insts.call()
        self.insts.jump(args[0]['value'])

    def _RETURN(self, args):
        self.insts.return_()

    def _PUSHS(self, args):
        if args[0]['type'] in ['int', 'string', 'bool', 'nil']:
            self.stack.pushs(Var(args[0]['type'], args[0]['value']))
        elif args[0]['type'] == 'var':
            frame, var_name = self.frames.getvar(args[0]['value'])
            self.stack.pushs(frame[var_name])

    def _POPS(self, args):
        self.frames.setvar(args[0]['value'], self.stack.pops())

    def _ADD(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'int' and symb2.type == 'int':
            self.frames.setvar(args[0]['value'], symb1 + symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot add the values, both not type int')

    def _SUB(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'int' and symb2.type == 'int':
            self.frames.setvar(args[0]['value'], symb1 - symb2)
        elif symb1.type == 'string' or symb2.type == 'string':
            exit_err(Code.STRING_ERR, 'Error: Cannot subtract strings')
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot subtract the values, both not type int')

    def _MUL(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'int' and symb2.type == 'int':
            self.frames.setvar(args[0]['value'], symb1 * symb2)
        elif symb1.type == 'string' or symb2.type == 'string':
            exit_err(Code.STRING_ERR, 'Error: Cannot multiply strings')
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot multiply the values, both not type int')

    def _IDIV(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'int' and symb2.type == 'int':
            self.frames.setvar(args[0]['value'], symb1 // symb2)
        elif symb1.type == 'string' or symb2.type == 'string':
            exit_err(Code.STRING_ERR, 'Error: Cannot floor divide strings')
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot floor divide the values, both not type int')

    def _LT(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == symb2.type and symb1.type in ['int', 'string', 'bool']:
            self.frames.setvar(args[0]['value'], symb1 < symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _GT(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == symb2.type and symb1.type in ['int', 'string', 'bool']:
            self.frames.setvar(args[0]['value'], symb1 > symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _EQ(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == symb2.type and symb1.type in ['int', 'string', 'bool', 'nil']:
            self.frames.setvar(args[0]['value'], symb1 == symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _AND(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'bool' and symb2.type == 'bool':
            self.frames.setvar(args[0]['value'], symb1 and symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _OR(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == 'bool' and symb2.type == 'bool':
            self.frames.setvar(args[0]['value'], symb1 or symb2)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _NOT(self, args):
        symb = self.frames.const_var(args[1])
        if symb.type == 'bool':
            self.frames.setvar(args[0]['value'], ~symb)
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot negate value')

    def _INT2CHAR(self, args):
        symb = self.frames.const_var(args[1])
        if symb.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Cannot convert type "{symb.type}" to char')
        try:
            self.frames.setvar(args[0]['value'], Var('string', chr(symb.value)))
        except ValueError:
            exit_err(Code.BAD_OPERAND_VAL, f'Error: Cannot convert int to char, "{symb.value}" is not valid Unicode value')

    def _STRI2INT(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type != 'string' or symb2.type != 'int':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Wrong operand types')
        
        if symb2.value < 0 or symb2.value >= len(symb1.value):
            exit_err(Code.STRING_ERR, f'Error: Index out of range')

        self.frames.setvar(args[0]['value'], Var('int', ord(symb1.value[symb2.value])))

    def _READ(self, args):
        if args[1]['value'] not in ['int', 'string', 'bool']:
            exit_err(Code.BAD_OPERAND_VAL, f'Error: Wrong operand value')

        type_ = args[1]['value']

        res_val = ''
        res_type = type_
        try:
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
        elif type_ == 'string':
            res_val = input_val
        
        self.frames.setvar(args[0]['value'], Var(res_type, res_val))

    def _WRITE(self, args):
        symb = self.frames.const_var(args[0])
        if symb.type == 'nil':
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

        if var.type != symb1.type != 'int' or symb2.type != 'string':
            exit_err(Code.BAD_OPERAND_TYPE, f'Error: Wrong operand types')

        if symb1.value < 0 or symb1.value >= len(symb2.value):
            exit_err(Code.STRING_ERR, f'Error: Index out of range')

        if len(symb2.value) == 0:
            exit_err(Code.STRING_ERR, f'Error: Second operand is empty')

        self.frames.setvar(args[0]['value'], Var('string', var.value[:symb1.value] + symb2.value[0] + var.value[symb1.value + 1:]))

    def _TYPE(self, args):
        symb = self.frames.const_var(args[1])
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
        if symb1.type == symb2.type and symb1.type in ['int', 'string', 'bool', 'nil']:
            if (symb1 == symb2).value == 'true':
                self.insts.jump(args[0]['value'])
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _JUMPIFNEQ(self, args):
        symb1 = self.frames.const_var(args[1])
        symb2 = self.frames.const_var(args[2])
        if symb1.type == symb2.type and symb1.type in ['int', 'string', 'bool', 'nil']:
            if (symb1 != symb2).value == 'true':
                self.insts.jump(args[0]['value'])
        else:
            exit_err(Code.BAD_OPERAND_TYPE, 'Error: Cannot compare values')

    def _EXIT(self, args):
        symb = self.frames.const_var(args[0])
        if symb.type == 'int' and (symb.value >= 0 or symb.value <= 49):
            exit(symb.value)
        else:
            exit_err(Code.BAD_OPERAND_VAL, f'Error: Exit code "{symb.value}" not in range 0-49')

    def _DPRINT(self, args):
        if args[0]['type'] in ['int', 'string', 'bool', 'nil']:
            print('Const@={}({})'.format(args[0]['value'], args[0]['type']), file=sys.stderr)

        elif args[0]['type'] == 'var':
            frame, var_name = self.frames.getvar(args[0]['value'])

            if frame[var_name].value == None:
                print('{}()'.format(args[0]['value']), file=sys.stderr)
            else:
                print('{}={}({})'.format(args[0]['value'], frame[var_name].value, frame[var_name].type), file=sys.stderr)

    def _BREAK(self, args):
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


    def parse(self, source_path):
        """Parses the XML document, checks the structure and lexical and syntactical correctness

        Parameters:
            source_path: filename or file object containing XML data

        Returns:
            Instructions: Class containing the parsed instructions
        """

        try:
            tree = ET.parse(source_path)
        except FileNotFoundError:
            exit_err(Code.OPEN_ERR)
        except PermissionError:
            exit_err(Code.OPEN_ERR)
        except ET.ParseError:
            exit_err(Code.BAD_XML)

        root = tree.getroot()

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

        # check for missing order numbers
        if len(inst_orders.keys()) > 0:
            missing_orders = set(range(sorted(inst_orders.keys())[0], sorted(inst_orders.keys())[-1])) - set(inst_orders.keys())
            if len(missing_orders) > 0:
                exit_err(Code.BAD_STRUCT, f'Error: Missing instruction orders: {sorted(missing_orders)}')

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
        arg_i = 1
        for arg in inst:
            if arg.tag != f'arg{arg_i}':
                exit_err(Code.BAD_STRUCT, f'Error: expected "arg{arg_i}" tag, not "{arg.tag}"')

            if len(arg.attrib) > 1 or 'type' not in arg.attrib:
                exit_err(Code.BAD_STRUCT, f'Error: Order "{order}": Expected a single argument attribute "type"')

            pos_type = Instruction.opcode_args(opcode)[arg_i-1]
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

                        arg.text = re.sub(r'\\([0-9]{3})', self._escape_ascii, arg.text) # replace escape sequences with their characters
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
            arg_i += 1

        return args

    def _var_syntax(self, arg, order, arg_i):
        if arg.attrib['type'] != 'var':
            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": Var type attribute expected "var", not "{}"'.format(order, arg.attrib['type']))

        if arg.text is None or re.match(r'^(?:LF|TF|GF)@[a-zA-Z_\-\$\&\%\*\!\?][a-zA-Z0-9_\-\$\&\%\*\!\?]*$', arg.text) is None:
            exit_err(Code.BAD_STRUCT, 'Error: Order "{}": "arg{}" with type "{}" has incorrect value'.format(order, arg_i, arg.attrib['type']))

    def _escape_ascii(self, match):
        return chr(int(match.group(1)))


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help', action='store_true', help='show this help message and exit', default=False)
    parser.add_argument('-s', '--source', metavar='SOURCE_FILE', action='store', help='XML source code', default=sys.stdin)
    parser.add_argument('-i', '--input', metavar='INPUT_FILE', action='store', help='Input to feed into STDIN', default=None)
    args = parser.parse_args()

    if args.help == True and args.source == None and args.input == None:
        parser.print_help()
        exit(0)
    elif (args.help == True and (args.source != sys.stdin or args.input != None)) or (args.source == sys.stdin and args.input == None):
        exit_err(Code.BAD_PARAM)

    xmlparser = XMLParser()
    instructions = xmlparser.parse(args.source)

    inst_ex = InstructionExecutor(instructions)
    if args.input != None:
        inst_ex.set_input(args.input)
    inst_ex.interpret()


if __name__ == '__main__':
    main()
