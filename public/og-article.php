<?php
/**
 * LinkedIn/WhatsApp/X do not run JavaScript. This injects the article cover
 * into the SPA shell so paste-previews show the photo instead of a blank card.
 */
header('Content-Type: text/html; charset=UTF-8');
header('Cache-Control: public, max-age=60, s-maxage=120');

$site = 'https://agarwalglobalinvestments.com';
$api = 'https://finance-news-backend-19i5.onrender.com';
$fallbackImage = $site . '/agi-og-cover.png';
$slug = isset($_GET['slug']) ? rawurldecode((string) $_GET['slug']) : '';
$slug = strtolower(trim($slug, "/ \t\n\r\0\x0B"));
if (!preg_match('/^[a-z0-9][a-z0-9-]{0,119}$/', $slug)) {
  $slug = '';
}

function agi_esc($value) {
  return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
}

function agi_http_get($url, $headers = []) {
  $headerLines = array_merge(['Accept: application/json', 'User-Agent: AGI-OG/1'], $headers);
  if (function_exists('curl_init')) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
      CURLOPT_RETURNTRANSFER => true,
      CURLOPT_FOLLOWLOCATION => true,
      CURLOPT_TIMEOUT => 6,
      CURLOPT_HTTPHEADER => $headerLines,
    ]);
    $raw = curl_exec($ch);
    $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($status >= 200 && $status < 300 && is_string($raw) && $raw !== '') return $raw;
  }
  $context = stream_context_create([
    'http' => [
      'method' => 'GET',
      'timeout' => 6,
      'header' => implode("\r\n", $headerLines) . "\r\n",
      'ignore_errors' => true,
    ],
  ]);
  $raw = @file_get_contents($url, false, $context);
  return is_string($raw) && $raw !== '' ? $raw : null;
}

function agi_fetch_json($url, $headers = []) {
  $raw = agi_http_get($url, $headers);
  if ($raw === null) return null;
  $data = json_decode($raw, true);
  return is_array($data) ? $data : null;
}

$meta = [
  'title' => 'AGI — Agarwal Global Investments',
  'pageTitle' => 'AGI — Agarwal Global Investments',
  'description' => 'Institutional-quality market research updated every trading day from Agarwal Global Investments.',
  'image' => $fallbackImage,
  'url' => $slug ? $site . '/article/' . $slug : $site . '/',
  'author' => 'AGI Research',
  'publishedTime' => '',
];

$config = is_readable(__DIR__ . '/og-config.php') ? include __DIR__ . '/og-config.php' : null;

if ($slug && is_array($config) && !empty($config['supabaseUrl']) && !empty($config['anonKey'])) {
  $query = '/rest/v1/articles?select=title,slug,excerpt,cover_url,published_at&slug=eq.' . rawurlencode($slug) . '&status=eq.published&limit=1';
  $rows = agi_fetch_json(rtrim($config['supabaseUrl'], '/') . $query, [
    'apikey: ' . $config['anonKey'],
    'Authorization: Bearer ' . $config['anonKey'],
  ]);
  $row = is_array($rows) && isset($rows[0]) && is_array($rows[0]) ? $rows[0] : null;
  if ($row && !empty($row['title'])) {
    $image = trim((string) ($row['cover_url'] ?? ''));
    if ($image !== '' && stripos($image, 'http://') === 0) {
      $image = 'https://' . substr($image, 7);
    }
    $meta['title'] = (string) $row['title'];
    $meta['pageTitle'] = $row['title'] . ' • AGI';
    if (!empty($row['excerpt'])) $meta['description'] = (string) $row['excerpt'];
    if ($image !== '' && preg_match('#^https://#i', $image)) $meta['image'] = $image;
    $meta['url'] = $site . '/article/' . $slug;
    if (!empty($row['published_at'])) $meta['publishedTime'] = (string) $row['published_at'];
  }
}

if ($slug && $meta['title'] === 'AGI — Agarwal Global Investments') {
  $remote = agi_fetch_json($api . '/api/public/article-share/' . rawurlencode($slug));
  if (is_array($remote) && !empty($remote['title'])) {
    $meta['title'] = (string) $remote['title'];
    $meta['pageTitle'] = (string) ($remote['pageTitle'] ?: $remote['title'] . ' • AGI');
    $meta['description'] = (string) ($remote['description'] ?: $meta['description']);
    $meta['image'] = (string) ($remote['image'] ?: $fallbackImage);
    $meta['url'] = (string) ($remote['url'] ?: $meta['url']);
    if (!empty($remote['author'])) $meta['author'] = (string) $remote['author'];
    if (!empty($remote['publishedTime'])) $meta['publishedTime'] = (string) $remote['publishedTime'];
  }
}

$shellPath = __DIR__ . '/index.html';
$html = is_readable($shellPath) ? file_get_contents($shellPath) : '';
if (!is_string($html) || $html === '') {
  $html = "<!doctype html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title></title></head><body><div id=\"root\"></div></body></html>";
}

$html = preg_replace('/<title>[\s\S]*?<\/title>/i', '<title>' . agi_esc($meta['pageTitle']) . '</title>', $html, 1);
$html = preg_replace('/<meta\s+name=["\']description["\'][^>]*>\s*/i', '', $html);
$html = preg_replace('/<link\s+rel=["\']canonical["\'][^>]*>\s*/i', '', $html);
$html = preg_replace('/<meta\s+property=["\']og:[^"\']+["\'][^>]*>\s*/i', '', $html);
$html = preg_replace('/<meta\s+name=["\']twitter:[^"\']+["\'][^>]*>\s*/i', '', $html);

$tags = [
  '<meta name="description" content="' . agi_esc($meta['description']) . '" />',
  '<link rel="canonical" href="' . agi_esc($meta['url']) . '" />',
  '<meta property="og:site_name" content="Agarwal Global Investments" />',
  '<meta property="og:type" content="article" />',
  '<meta property="og:url" content="' . agi_esc($meta['url']) . '" />',
  '<meta property="og:title" content="' . agi_esc($meta['title']) . '" />',
  '<meta property="og:description" content="' . agi_esc($meta['description']) . '" />',
  '<meta property="og:image" content="' . agi_esc($meta['image']) . '" />',
  '<meta property="og:image:secure_url" content="' . agi_esc($meta['image']) . '" />',
  '<meta property="og:image:alt" content="' . agi_esc($meta['title']) . '" />',
  '<meta name="author" content="' . agi_esc($meta['author']) . '" />',
  '<meta property="article:author" content="' . agi_esc($meta['author']) . '" />',
  '<meta name="twitter:card" content="summary_large_image" />',
  '<meta name="twitter:title" content="' . agi_esc($meta['title']) . '" />',
  '<meta name="twitter:description" content="' . agi_esc($meta['description']) . '" />',
  '<meta name="twitter:image" content="' . agi_esc($meta['image']) . '" />',
];

if (!empty($meta['publishedTime'])) {
  array_splice($tags, -3, 0, [
    '<meta property="article:published_time" content="' . agi_esc($meta['publishedTime']) . '" />',
  ]);
}

$html = preg_replace('/<\/head>/i', "    " . implode("\n    ", $tags) . "\n  </head>", $html, 1);
echo $html;
