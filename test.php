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
    'parse-script=' => '',
    'int-script=' => '',
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

$directory = rtrim($args['directory='], '/');
$parse_only = $args['parse-only'];
$int_only = $args['int-only'];
$int_script = $args['int-script='];
$parse_script = $args['parse-script='];
$jexamxml = $args['jexamxml='];
$jexamcfg = $args['jexamcfg='];

if ($parse_only && ($int_only || $int_script !== ''))
{
    exit_err(Code::BAD_PARAM, "Error: Cannot combine --parse-only with --int-only and --int-script\nRun only with --help to show help\n");
}
if ($int_only && ($parse_only || $parse_script !== ''))
{
    exit_err(Code::BAD_PARAM, "Error: Cannot combine --int-only with --parse-only and --parse-script\nRun only with --help to show help\n");
}

if (!is_readable($directory) || $parse_script !== '' && !is_readable($parse_script) || $int_script !== '' && !is_readable($int_script)/* || !is_readable($args['jexamxml=']) || !is_readable($args['jexamcfg='])*/)
{
    exit_err(Code::INVALID_PATH, "Error: Path to one of the required files is not readable\n");
}

if ($parse_script === '')
{
    $parse_script = 'parse.php';
    if (!is_readable($parse_script) && !$int_only)
    {
        exit_err(Code::INVALID_PATH, "Error: parse.php is not readable\n");
    }
}
if ($int_script === '')
{
    $int_script = 'interpret.py';
    if (!is_readable($int_script) && !$parse_only)
    {
        exit_err(Code::INVALID_PATH, "Error: interpret.py is not readable\n");
    }
}

$test_names = array();
if ($args['recursive'])
{
    foreach (new RegexIterator(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($directory)), '/^.+\.src$/', RecursiveRegexIterator::GET_MATCH) as $x)
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
    $dir = preg_grep('/^.+\.src$/', scandir($directory));
    foreach ($dir as $fname)
    {
        if (preg_match('/^(.+)\.src$/', $fname, $m))
        {
            $test_names[] = $directory . '/' . $m[1];
        }
    }
}

// $parser_output = tempnam('/tmp', 'ipp');
$parser_output = tempnam($directory, 'ipp');
$interpreter_output = tempnam($directory, 'ipp');
$diff_output = tempnam($directory, 'ipp');

$test_res = array_fill_keys($test_names, array());

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

    $test_res[$test]['rc_ref'] = $rc_ref;
    $test_res[$test]['diff_rc'] = 0;

    if (!$int_only)
    {
        unset($output);
        exec("php.exe $parse_script < $test.src > $parser_output", $output, $parser_rc);
        // exec("php.exe $parse_script < $test.src", $output, $parser_rc);
        // file_put_contents($parser_output, implode(PHP_EOL, $output));
        $test_res[$test]['parser_rc'] = $parser_rc;

        if (!$parse_only && $parser_rc === 0)
        {
            unset($output);
            exec("python3.8 $int_script --source=$parser_output --input=$test.in > $interpreter_output", $output, $int_rc);
            // exec("python3.8 $int_script --source=$parser_output --input=$test.in", $output, $int_rc);
            // file_put_contents($interpreter_output, implode(PHP_EOL, $output));
            $test_res[$test]['int_rc'] = $int_rc;
        }
    }
    else
    {
        unset($output);
        exec("python3.8 $int_script --source=$test.src --input=$test.in > $interpreter_output", $output, $int_rc);
        // exec("python3.8 $int_script --source=$test.src --input=$test.in", $output, $int_rc);
        // file_put_contents($interpreter_output, implode(PHP_EOL, $output));
        $test_res[$test]['int_rc'] = $int_rc;
    }

    if ($parse_only && $parser_rc === 0)
    {
        unset($output);
        // exec("diff $test.out $parser_output > $diff_output", $output, $diff_rc);
        exec("java -jar $jexamxml $parser_output $test.out $diff_output $jexamcfg", $output, $diff_rc);
        $test_res[$test]['diff_output'] = file_get_contents($diff_output);
        $test_res[$test]['diff_rc'] = $diff_rc;
        // print_r($output);
    }
    else if (!$parse_only && $int_rc >= 0 && $int_rc <= 49)
    {
        unset($output);
        exec("diff $test.out $interpreter_output > $diff_output", $output, $diff_rc);
        // exec("diff $test.out $interpreter_output", $output, $diff_rc);
        // $diff_output = implode(PHP_EOL, $output);
        $test_res[$test]['diff_output'] = file_get_contents($diff_output);
        $test_res[$test]['diff_rc'] = $diff_rc;
    }
}

// print_r($test_res);

unlink($parser_output);
unlink($interpreter_output);
unlink($diff_output);

$html = "<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>IPP test.php results</title>
    <style>
        html, body {
            font-family: sans-serif;
            background-color: #d4d4d4;
        }
        h1, h2 {
            text-align: center;
        }
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        th, td {
            padding: 5px;
            text-align: center;
        }
        .passed {
            background-color: rgb(147, 235, 147);
        }
        table tr.passed:nth-child(even) {
            background-color: rgb(97, 228, 97);
        }
        .failed {
            background-color: rgb(208, 136, 136);
        }
        table tr.failed:nth-child(even) {
            background-color: rgb(226, 108, 108);
        }
    </style>
</head>
<body>
    <h1>IPP test.php results</h1>\n";

$rows = '';
$passed_count = 0;
$failed_count = 0;
foreach ($test_res as $test_path => $res_arr)
{
    $passed = false;
    if ($parse_only && $res_arr['parser_rc'] === $res_arr['rc_ref'] && $res_arr['diff_rc'] === 0)
    {
        $passed = true;
    }
    else if (/*$int_only && */$res_arr['int_rc'] === $res_arr['rc_ref'] && $res_arr['diff_rc'] === 0)
    {
        $passed = true;
    }

    if ($passed === true)
    {
        $passed = 'passed';
        $passed_count++;
    }
    else
    {
        $passed = 'failed';
        $failed_count++;
    }
    $rows .= "        <tr class=\"$passed\"><td>$test_path</td><td>".$res_arr['parser_rc']."</td><td>".$res_arr['int_rc']."</td><td>".$res_arr['diff_rc']."</td></tr>\n";
}


$html .= "<h2 style=\"color: green;\">PASSED: $passed_count<span></span></h2>
<h2 style=\"color: red;\">FAILED: $failed_count<span></span></h2>
<table>
    <tr><th>Test path</th><th>Parser return code</th><th>Interpreter return code</th><th>Diff return code</th></tr>\n";

$html .= $rows;

$html .= "    </table>
</body>
</html>
";

echo $html;
