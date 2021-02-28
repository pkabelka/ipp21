<?php

/**
 * Project name: IPP 2. project
 * 
 * @brief Testing script for parse.php and interpret.py
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
    const INVALID_PATH = 41;
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

array_shift($argv);
$argc = count($argv);
if ($argc === 1 && $argv[0] == '--help')
{
    $message = "This script reads IPPcode21 from standard input, performs lexical\nand syntactical analysis and converts the instructions into XML\nrepresentation printed to standard output.\n\n";
    $message .= "usage: test.php [--help] [--directory=PATH] [--recursive] [--parse-script=parse.php] [--int-script=interpret.py] [--parse-only] [--int-only] [--jexamxml=JEXAMXML_JAR] [--jexamcfg=OPTIONS_FILE]\n\n";
    $message .= "arguments:\n\n";
    $message .= "  --help                              show this help message and exit\n";
    $message .= "  --directory=PATH                    directory to search tests in\n";
    $message .= "  --recursive                         search the test directory recursively\n";
    $message .= "  --parse-script=PARSER_SCRIPT        path to the parser script, default: parse.php\n";
    $message .= "  --int-script=INTERPRETER_SCRIPT     path to the interpreter script, default: interpret.py\n";
    $message .= "  --parse-only                        run only parser tests\n";
    $message .= "  --int-only                          run only interpreter tests\n";
    $message .= "  --jexamxml=JEXAMXML_JAR             path to A7Soft JExamXML JAR\n";
    $message .= "  --jexamcfg=OPTIONS_FILE             path to A7Soft JExamXML configuration\n";
    fprintf(STDOUT, $message);
    exit(Code::SUCCESS);
}
else if ($argc > 1 && in_array('--help', $argv))
{
    exit_err(Code::BAD_PARAM, "Wrong combination of parameters\nRun only with --help to show help\n");
}

// defaults
$args = array(
    'directory=' => '.',
    'recursive' => false,
    'parse-script=' => 'parse.php',
    'int-script=' => 'interpret.py',
    'parse-only' => false,
    'int-only' => false,
    'jexamxml=' => '/pub/courses/ipp/jexamxml/jexamxml.jar',
    'jexamcfg=' => '/pub/courses/ipp/jexamxml/options'
);

foreach ($argv as $arg) {
    $arg = ltrim($arg, '-');
    if (strpos($arg, '=') !== false)
    {
        $arg = explode('=', $arg, 2);
        $match = preg_grep('/^--'.$arg[0].'=/', $argv);
        if (!array_key_exists($arg[0].'=', $args))
        {
            exit_err(Code::BAD_PARAM, "Wrong combination of parameters\nRun only with --help to show help\n");
        }
        if ($arg[1] === '')
        {
            exit_err(Code::BAD_PARAM, "Error: --".$arg[0]." requires a value\n");
        }
        if (count($match) == 1)
        {
            $args[$arg[0].'='] = $arg[1];
        }
        else if (count($match) > 1)
        {
            exit_err(Code::BAD_PARAM, "Wrong combination of parameters\nRun only with --help to show help\n");
        }
    }
    else
    {
        $match = preg_grep('/^--'.$arg.'/', $argv);
        if (!array_key_exists($arg, $args))
        {
            exit_err(Code::BAD_PARAM, "Wrong combination of parameters\nRun only with --help to show help\n");
        }
        if (count($match) == 1)
        {
            $args[$arg] = true;
        }
        else if (count($match) > 1)
        {
            exit_err(Code::BAD_PARAM, "Wrong combination of parameters\nRun only with --help to show help\n");
        }
    }
}

print_r($args);

if (!is_readable($args['directory=']) || !is_readable($args['parse-script=']) || !is_readable($args['int-script='])/* || !is_readable($args['jexamxml=']) || !is_readable($args['jexamcfg='])*/)
{
    exit_err(Code::INVALID_PATH, "Error: Path to one of the required files is not readable\n");
}


$test_names = array();
if ($args['recursive'])
{
    foreach (new RegexIterator(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($args['directory='])), '/^.+\.src$/', RecursiveRegexIterator::GET_MATCH) as $x)
    {
        foreach ($x as $path)
        {
            if (preg_match('/^(.+)\.src$/', $path, $m))
            {
                $test_names[] = $m[1];
            }
        }
    }
}
else
{
    $dir = preg_grep('/^.+\.src$/', scandir($args['directory=']));
    foreach ($dir as $fname)
    {
        if (preg_match('/^(.+)\.src$/', $fname, $m))
        {
            $test_names[] = $m[1];
        }
    }
}

print_r($test_names);

// $parser_output = tempnam('/tmp', 'ipp');
$parser_output = tempnam($args['directory='], 'ipp');
$interpreter_output = tempnam($args['directory='], 'ipp');

foreach ($test_names as $test)
{
    if (!file_exists($test.'.in'))
    {
        touch($test.'.in');
    }
    if (!file_exists($test.'.out'))
    {
        touch($test.'.out');
    }
    $rc_ref = 0;
    if (!file_exists($test.'.rc'))
    {
        file_put_contents($test.'.rc', '0');
    }
    else
    {
        $rc_ref = intval(file_get_contents($test.'.rc'));
    }

    unset($output);
    // exec('php.exe ' . $args['parse-script='] . ' < ' . $test . '.src > ' . $parser_output, $output, $rc);
    exec('php.exe ' . $args['parse-script='] . ' < ' . $test . '.src', $output, $parser_rc);
    file_put_contents($parser_output, implode(PHP_EOL, $output));

    if ($parser_rc == 0)
    {
        exec('py ' . $args['int-script='] . ' < ' . $test . '.src', $output, $interpreter_rc);
        file_put_contents($interpreter_output, implode(PHP_EOL, $output));
    }
}

unlink($parser_output);
unlink($interpreter_output);
