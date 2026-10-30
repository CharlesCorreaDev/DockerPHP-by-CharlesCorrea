<?php
/**
 * Campo honeypot para formularios (anti-bot de spam), sem captcha.
 *
 * Bots preenchem todos os inputs; humanos nao veem o campo oculto.
 * Tambem rejeita envios rapidos demais (< 3s apos renderizar o form).
 *
 *   // No formulario:
 *   <?= HoneypotField::render() ?>
 *
 *   // No processamento do POST:
 *   if (HoneypotField::isBot($_POST)) { http_response_code(400); exit; }
 */
final class HoneypotField
{
    private const FIELD = 'website_url';   // nome "atraente" para bots
    private const TS    = '_hp_ts';
    private const MIN_SECONDS = 3;

    public static function render(): string
    {
        $ts  = time();
        $sig = hash_hmac('sha256', (string) $ts, self::key());
        return '<div style="position:absolute;left:-10000px" aria-hidden="true">'
             . '<label>Website<input type="text" name="' . self::FIELD . '" tabindex="-1" autocomplete="off"></label>'
             . '</div>'
             . '<input type="hidden" name="' . self::TS . '" value="' . $ts . '.' . $sig . '">';
    }

    public static function isBot(array $post): bool
    {
        if (!empty($post[self::FIELD])) {
            return true;
        }
        $parts = explode('.', (string) ($post[self::TS] ?? ''), 2);
        if (count($parts) !== 2 || !hash_equals(hash_hmac('sha256', $parts[0], self::key()), $parts[1])) {
            return true;
        }
        return (time() - (int) $parts[0]) < self::MIN_SECONDS;
    }

    private static function key(): string
    {
        return getenv('HONEYPOT_FORM_KEY') ?: 'troque-esta-chave';
    }
}

