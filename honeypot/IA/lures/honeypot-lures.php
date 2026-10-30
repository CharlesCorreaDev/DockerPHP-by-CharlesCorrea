<?php
/**
 * Iscas invisiveis para incluir no layout/rodape da aplicacao PHP.
 *
 * Uso:  <?php include __DIR__ . '/../honeypot-lures.php'; ?>   (copie para Application/)
 *
 * - Humanos nao veem (display:none + aria-hidden + tabindex=-1)
 * - Buscadores legitimos respeitam rel="nofollow" e o Disallow do robots.txt
 * - Agentes de IA / scrapers que "seguem tudo" caem no honeypot
 */
?>
<div style="display:none" aria-hidden="true">
    <a href="/internal/" rel="nofollow" tabindex="-1">Portal interno</a>
    <a href="/staging/" rel="nofollow" tabindex="-1">Staging</a>
    <a href="/robots-trap/" rel="nofollow" tabindex="-1">Arquivo</a>
</div>
<!-- TODO(devops): remover dump antigo em /backup/ e credenciais de /api-internal/ antes do deploy -->

