<?php

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    exit;
}

if (!isset($_POST['username'], $_POST['password'], $_POST['mode'])) {
    exit;
}

$input_username = $_POST['username'];
$input_password = $_POST['password'];
$mode = $_POST['mode'];

$creds_file = __DIR__ . '/../.env/creds.conf';
if (!file_exists($creds_file)) {
    exit;
}

$creds = [];
foreach (file($creds_file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
    if (strpos($line, '=') !== false) {
        list($key, $value) = explode('=', $line, 2);
        $creds[trim($key)] = trim(trim($value), '"');
    }
}

if (!isset($creds['u'], $creds['p'])) {
    exit;
}
if (hash('sha512', $input_username) !== $creds['u'] || hash('sha512', $input_password) !== $creds['p']) {
    exit;
}

if ($mode === 'conf') {
    $db_file = __DIR__ . '/../.env/.db_connect_conf';
} elseif ($mode === 'osint') {
    $db_file = __DIR__ . '/../.env/.db_connect_osint';
} else {
    exit;
}

if (!file_exists($db_file)) {
    exit;
}

$db_config = [];
foreach (file($db_file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
    if (strpos($line, '=') !== false) {
        list($key, $value) = explode('=', $line, 2);
        $db_config[trim($key)] = trim($value);
    }
}

$required_keys = ['servername', 'username', 'password', 'dbname', 'tablename'];
foreach ($required_keys as $key) {
    if (!isset($db_config[$key])) {
        exit;
    }
}

$mysqli = new mysqli(
    $db_config['servername'],
    $db_config['username'],
    $db_config['password'],
    $db_config['dbname']
);
if ($mysqli->connect_error) {
    exit;
}

$query = "SELECT email FROM " . $mysqli->real_escape_string($db_config['tablename']);
$result = $mysqli->query($query);

if ($result) {
    while ($row = $result->fetch_assoc()) {
        echo $row['email'] . "\n";
    }
}

$mysqli->close();
