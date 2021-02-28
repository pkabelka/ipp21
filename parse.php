<?php

/**
 * Project name: IPP 1. project
 * 
 * @brief IPPcode21 parser
 * 
 * @author Petr Kabelka <xkabel09 at stud.fit.vutbr.cz>
 */

ini_set('display_errors', 'stderr');

/**
 * Enum for all the exit codes
 */
abstract class Code
{
    # errors
    const SUCCESS = 0;
    const BAD_PARAM = 10;
    const OPEN_ERR = 11;
    const WRITE_ERR = 12;
    const INTERNAL_ERR = 99;

    const BAD_HEADER = 21;
    const BAD_OPCODE = 22;
    const PARSE_ERR = 23;
}

/**
 * This function exits the script with the given exit code and message printer to STDERR
 * 
 * @param code Exit code
 * @param text Message printed to STDERR
 */
function exit_err($code, $text)
{
    fprintf(STDERR, $text);
    exit($code);
}

/**
 * Class for parsing arguments and IPPcode21 source code
 */
class Parser
{
    private $stats;
    private $stat_groups;

    public function __construct()
    {
        $this->stats = new Stats();
    }

    /**
     * Parses script arguments
     * 
     * If --stats is provided, it splits the input arguments into groups of statistics
     * 
     * @param argv Script arguments
     * @return array Array containing the output file names as keys and sub arrays with statistic identifiers
     */
    private function parse_args(array $argv): array
    {
        array_shift($argv);
        $argc = count($argv);
        if ($argc === 1 && in_array('--help', $argv))
        {
            exit_err(Code::BAD_PARAM, "This script reads IPPcode21 from standard input, performs lexical\nand syntactical analysis and converts the instructions into XML representation\n");
        }
        else if ($argc > 1 && (strpos($argv[0], '--stats') === false || in_array('--help', $argv)))
        {
            exit_err(Code::BAD_PARAM, "Wrong combination of parameters\nRun only with --help to show help\n");
        }

        $valid_args = array('loc', 'comments', 'labels', 'jumps', 'fwjumps', 'backjumps', 'badjumps');
        $stat_groups = array();
        $last_stats = '';

        foreach ($argv as $k => $v)
        {
            $v = ltrim($v, '-');
            if (strpos($v, 'stats=') !== false)
            {
                $pos = strpos($v, 'stats=');
                $last_stats = substr($v, $pos+6);

                if (strlen($last_stats) === 0)
                {
                    exit_err(Code::BAD_PARAM, "No stat file path given\n");
                }

                if (array_key_exists($last_stats, $stat_groups))
                {
                    exit_err(Code::WRITE_ERR, "Error trying to write multiple stats to the same file\n");
                }

                $stat_groups[$last_stats] = array();
            }
            else if (!in_array($v, $valid_args))
            {
                continue;
            }
            else
            {
                if ($last_stats === '')
                {
                    exit_err(Code::BAD_PARAM, "Wrong combination of parameters\nRun only with --help to show help\n");
                }
                $stat_groups[$last_stats][] = $v;
            }
        }
        
        return $stat_groups;
    }

    /**
     * Parses IPPcode21 source code and checks lexical and syntactical correctness
     * 
     * Each call of the Inst->next() method loads another instruction from
     * standard input and does lexical and syntactical analysis
     * 
     * After successful analysis of the instruction, we generate the XML tags
     * and attributes for the instruction and its arguments
     * 
     * @param argv Script arguments
     */
    public function parse(array $argv)
    {
        $this->stat_groups = $this->parse_args($argv);

        $out = new Output();
        $inst = new Inst();
        while ($inst->next())
        {
            $opcode = $inst->get_opcode();
            if ($opcode !== '')
            {
                $out->inst($opcode);
                $args = $inst->get_args();

                foreach ($args as $arr) {
                    $type = array_key_first($arr);
                    $out->arg($type, $arr[$type]);
                    $out->end_element();
                }
                $out->end_element();
            }
        }

        $inst->check_fwjumps();

        $out->end_element();
        $out->print();
    }

    public function get_stat_groups()
    {
        return $this->stat_groups;
    }
}

/**
 * Class for loading and checking instructions
 */
class Inst
{
    private $lnum;
    private $header_found;
    private $opcode;
    private $args;
    private $labels;
    private $fwjumps;

    /**
     * Template for instructions
     * 
     * Each instruction opcode points to an array with operand types which it
     * accepts
     */
    private const INST_MAP = array(
        'MOVE' => array('var', 'symb'),
        'CREATEFRAME' => array(),
        'PUSHFRAME' => array(),
        'POPFRAME' => array(),
        'DEFVAR' => array('var'),
        'CALL' => array('label'),
        'RETURN' => array(),
        'PUSHS' => array('symb'),
        'POPS' => array('var'),
        'ADD' => array('var', 'symb', 'symb'),
        'ADDS' => array(),
        'SUB' => array('var', 'symb', 'symb'),
        'SUBS' => array(),
        'MUL' => array('var', 'symb', 'symb'),
        'MULS' => array(),
        'IDIV' => array('var', 'symb', 'symb'),
        'IDIVS' => array(),
        'DIV' => array('var', 'symb', 'symb'),
        'DIVS' => array(),
        'LT' => array('var', 'symb', 'symb'),
        'LTS' => array(),
        'GT' => array('var', 'symb', 'symb'),
        'GTS' => array(),
        'EQ' => array('var', 'symb', 'symb'),
        'EQS' => array(),
        'AND' => array('var', 'symb', 'symb'),
        'ANDS' => array(),
        'OR' => array('var', 'symb', 'symb'),
        'ORS' => array(),
        'NOT' => array('var', 'symb'),
        'NOTS' => array(),
        'INT2CHAR' => array('var', 'symb'),
        'INT2CHARS' => array(),
        'STRI2INT' => array('var', 'symb', 'symb'),
        'STRI2INTS' => array(),
        'INT2FLOAT' => array('var', 'symb'),
        'INT2FLOATS' => array(),
        'FLOAT2INT' => array('var', 'symb'),
        'FLOAT2INTS' => array(),
        'READ' => array('var', 'type'),
        'WRITE' => array('symb'),
        'CONCAT' => array('var', 'symb', 'symb'),
        'STRLEN' => array('var', 'symb'),
        'GETCHAR' => array('var', 'symb', 'symb'),
        'SETCHAR' => array('var', 'symb', 'symb'),
        'TYPE' => array('var', 'symb'),
        'LABEL' => array('label'),
        'JUMP' => array('label'),
        'JUMPIFEQ' => array('label', 'symb', 'symb'),
        'JUMPIFEQS' => array(),
        'JUMPIFNEQ' => array('label', 'symb', 'symb'),
        'JUMPIFNEQS' => array(),
        'CLEARS' => array(),
        'EXIT' => array('symb'),
        'DPRINT' => array('symb'),
        'BREAK' => array());

    public function __construct()
    {
        $this->lnum = 0;
        $this->header_found = false;
        $this->opcode = '';
        $this->args = array();
        $this->labels = array();
        $this->fwjumps = array();
    }

    /**
     * Load the next line and checks lexical and syntactical correctness
     * 
     * @return bool false when the STDIN is empty
     */
    public function next(): bool
    {
        $this->opcode = '';
        $this->args = array();
        $line = fgets(STDIN);
        $this->lnum++;
        if ($line === false && !$this->header_found)
        {
            exit_err(Code::BAD_HEADER, ".IPPcode21 header not found\n");
        }
        else if ($line === false)
        {
            return false;
        }

        self::trim_comments($line);
        $line = preg_replace('/\s+/', ' ', $line);
        $line = trim($line);

        if ($line !== '')
        {
            if (!$this->header_found)
            {
                if (strtoupper($line) === '.IPPCODE21')
                {
                    $this->header_found = true;
                    return true;
                }
                else
                {
                    exit_err(Code::BAD_HEADER, ".IPPcode21 header not found\n");
                }
            }
            else
            {
                if (strtoupper($line) === '.IPPCODE21')
                {
                    exit_err(Code::PARSE_ERR, ".IPPcode21 header found multiple times\n");
                }
            }

            $res = $this->syntax(explode(' ', $line));
            switch ($res) {
                case Code::BAD_OPCODE:
                    exit_err(Code::BAD_OPCODE, "Unknown instruction $this->opcode on line $this->lnum\n");
                    break;
                case Code::PARSE_ERR:
                    exit_err(Code::PARSE_ERR, "Parsing error on line $this->lnum\n");
                    break;
                default:
                    break;
            }
        }

        return true;
    }

    /**
     * Checks if the instruction is lexiacally and syntactically correct and
     * parses it into opcode and args
     * 
     * Lexical analysis is done by checking if the opcode of the instruction on
     * the line is found in INST_MAP array
     * 
     * Syntactical analysis is done by checking if the number of arguments and
     * their type matches the template of the arguments in INST_MAP
     * 
     * Each argument type is checked with regular expressions
     * 
     * @param inst Array with an instruction delimited by ' '
     * @return int Return code
     */
    private function syntax(array $inst): int
    {
        if (count($inst) > 4)
        {
            return Code::PARSE_ERR;
        }

        $this->opcode = strtoupper($inst[0]);
        $this->args = array();
        $args = array_slice($inst, 1);

        if (array_key_exists($this->opcode, self::INST_MAP))
        {
            if (count(self::INST_MAP[$this->opcode]) !== count($args))
            {
                return Code::PARSE_ERR;
            }

            foreach (self::INST_MAP[$this->opcode] as $i => $pos_type)
            {
                switch ($pos_type) {
                    case 'symb':
                        if (preg_match('/^(?:int|string|bool|nil|float)@.*$/', $args[$i]))
                        {
                            $symb = explode('@', $args[$i], 2);
                            $symb_type = $symb[0];
                            $symb_val = $symb[1];

                            switch ($symb_type) {
                                case 'int':
                                    if ($symb_val === '')
                                    {
                                        return Code::PARSE_ERR;
                                    }
                                    $this->args[] = array($symb_type => $symb_val);
                                    break;

                                case 'string':
                                    if (!preg_match('/^(?:[^\s\#\\\\]|\\\\[0-9]{3})*$/', $symb_val))
                                    {
                                        return Code::PARSE_ERR;
                                    }
                                    $this->args[] = array($symb_type => $symb_val);
                                    break;

                                case 'bool':
                                    if (!preg_match('/^(?:true|false)$/', $symb_val))
                                    {
                                        return Code::PARSE_ERR;
                                    }
                                    $this->args[] = array($symb_type => $symb_val);
                                    break;

                                case 'nil':
                                    if (!preg_match('/^nil$/', $symb_val))
                                    {
                                        return Code::PARSE_ERR;
                                    }
                                    $this->args[] = array($symb_type => $symb_val);
                                    break;

                                case 'float':
                                    if (!preg_match('/^[+-]?(?:0[xX])?[0-9a-fA-F]+(?:\.[0-9a-fA-F]+)?(?:[pP][+-]?[0-9]+)?$/', $symb_val))
                                    {
                                        return Code::PARSE_ERR;
                                    }
                                    $this->args[] = array($symb_type => $symb_val);
                                    break;
                                default:
                                    break;
                            }
                            break;
                        }
                    // symb can fall through to var
                    case 'var':
                        if (!preg_match('/^(?:LF|TF|GF)@[a-zA-Z_\-\$\&\%\*\!\?][a-zA-Z0-9_\-\$\&\%\*\!\?]*$/', $args[$i]))
                        {
                            return Code::PARSE_ERR;
                        }
                        $this->args[] = array('var' => $args[$i]);
                        break;

                    case 'type':
                        if (!preg_match('/^(?:int|string|bool|float)$/', $args[$i]))
                        {
                            return Code::PARSE_ERR;
                        }
                        $this->args[] = array($pos_type => $args[$i]);
                        break;

                    case 'label':
                        if (!preg_match('/^[a-zA-Z_\-\$\&\%\*\!\?][a-zA-Z0-9_\-\$\&\%\*\!\?]*$/', $args[$i]))
                        {
                            return Code::PARSE_ERR;
                        }
                        $this->args[] = array($pos_type => $args[$i]);
                        break;
                    default:
                        break;
                }
            }

            Stats::inc('loc');

            switch ($this->opcode) {
                case 'RETURN':
                    Stats::inc('jumps');
                    break;
                case 'CALL':
                case 'JUMP':
                case 'JUMPIFEQ':
                case 'JUMPIFNEQ':
                    Stats::inc('jumps');
                    if (array_key_exists($this->args[0]['label'], $this->labels))
                    {
                        Stats::inc('backjumps');
                    }
                    else
                    {
                        $this->fwjumps[$this->args[0]['label']] = NULL;
                        Stats::inc('fwjumps');
                    }
                    break;
                case 'LABEL':
                    Stats::inc('labels');
                    $this->labels[$this->args[0]['label']] = NULL;
                    break;
                default:
                    break;
            }
        }
        else
        {
            return Code::BAD_OPCODE;
        }

        return Code::SUCCESS;
    }

    /**
     * Finds the first # and removes all content until end of line
     * 
     * The function works in-place on the line parameter
     * 
     * @param line String to trim comments in
     */
    public static function trim_comments(&$line)
    {
        if (($pos = strpos($line, '#')) !== false)
        {
            $line = substr($line, 0, $pos);
            Stats::inc('comments');
        }
    }

    /**
     * Returns instruction opcode
     */
    public function get_opcode(): string
    {
        return $this->opcode;
    }

    /**
     * Returns instruction arguments
     */
    public function get_args(): array
    {
        return $this->args;
    }

    /**
     * Checks fwjumps array if all labels are defined in labels array. If the
     * label is not found, it decrements fwjumps and increments badjumps stats.
     */
    public function check_fwjumps()
    {
        foreach ($this->fwjumps as $label => $null)
        {
            if (!array_key_exists($label, $this->labels))
            {
                Stats::dec('fwjumps');
                Stats::inc('badjumps');
            }
        }
    }
}

/**
 * Collects statistics about the analysed code
 */
class Stats
{
    public static $stats = array('loc' => 0, 'comments' => 0, 'labels' => 0, 'jumps' => 0, 'fwjumps' => 0, 'backjumps' => 0, 'badjumps' => 0); // contains the stat values

    /**
     * Increments the statistic with the given key
     * 
     * @param key Statistic key to increment
     */
    public static function inc($key)
    {
        if (array_key_exists($key, self::$stats))
        {
            self::$stats[$key]++;
        }
    }

    /**
     * Decrements the statistic with the given key
     * 
     * @param key Statistic key to decrement
     */
    public static function dec($key)
    {
        if (array_key_exists($key, self::$stats))
        {
            self::$stats[$key]--;
        }
    }

    /**
     * Writes the statistics into the file supplied in the key of the array
     * 
     * @param arr Associative array where the keys are output file names
     *            and values of the sub array are the statistics to write
     */
    public static function write(array $arr)
    {
        foreach ($arr as $fname => $stat_group)
        {
            $output = '';
            foreach ($stat_group as $stat) {
                $output .= self::$stats[$stat] . "\n";
            }
            if (file_put_contents($fname, $output) === false)
            {
                exit_err(Code::WRITE_ERR, "Cannot write stats to file $fname\n");
            }
        }
    }
}

class Output
{
    private $xmlw;
    private $order;
    private $arg_order;

    /**
     * Creates an instance of XMLWriter for writing XML output into memory
     */
    public function __construct()
    {
        $this->xmlw = new XMLWriter();
        $this->xmlw->openMemory();
        $this->xmlw->setIndent(true);
        $this->xmlw->startDocument('1.0', 'UTF-8');
        $this->xmlw->startElement('program');
        $this->xmlw->writeAttribute('language', 'IPPcode21');
        $this->order = 1;
        $this->arg_order = 1;
    }

    /**
     * Starts "instruction" element
     * 
     * Automatically increments order for each instruction element
     */
    public function inst(string $opcode)
    {
        $this->arg_order = 1;
        $this->xmlw->startElement('instruction');
        $this->xmlw->writeAttribute('order', $this->order++);
        $this->xmlw->writeAttribute('opcode', strtoupper($opcode));
    }

    /**
     * Starts "argN" element
     * 
     * Automatically increments order for each arg element
     */
    public function arg(string $type, string $val)
    {
        $this->xmlw->startElement('arg'.$this->arg_order++);
        $this->xmlw->writeAttribute('type', strtolower($type));
        $this->xmlw->text($val);
    }

    /**
     * Public wrapper of the XMLWriter endElement function
     */
    public function end_element()
    {
        $this->xmlw->endElement();
    }

    /**
     * Prints the XML output to STDOUT
     */
    public function print()
    {
        $this->xmlw->endDocument();
        echo $this->xmlw->outputMemory();
    }
}


$parser = new Parser();
$parser->parse($argv);
Stats::write($parser->get_stat_groups());
