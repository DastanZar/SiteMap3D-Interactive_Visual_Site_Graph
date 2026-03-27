"""Self-contained HTML generator with custom tooltip handling."""

import re
import requests
from pyvis.network import Network


# Cache for fetched CDN assets
_cdn_cache: dict[str, str] = {}

# CDN URLs for vis-network
_VIS_NETWORK_JS_URL = "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"
_VIS_NETWORK_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css"


def _fetch_cdn_asset(url: str) -> str:
    """Fetch a CDN asset and cache it for the session."""
    if url not in _cdn_cache:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        _cdn_cache[url] = resp.text
    return _cdn_cache[url]


# Inline replacement for the broken lib/bindings/utils.js
_UTILS_REPLACEMENT = """<script>
var edges;
var nodes;
var allNodes;
var allEdges;
var nodeColors;
var originalNodes;
var network;
var container;
var options, data;
var filter = { item: '', property: '', value: '' };
</script>"""

# Custom JS/CSS injection for dark theme tooltips
_CUSTOM_TOOLTIP_JS = """
<script>
(function() {
    function initTooltipHandler() {
        var container = document.getElementById('mynetwork');
        if (!container) return;

        var tooltipDiv = document.createElement('div');
        tooltipDiv.id = 'custom-tooltip';
        tooltipDiv.style.cssText = 'position:fixed;z-index:9999;background:#1a1a1a;border:1px solid #555;padding:6px;border-radius:6px;display:none;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,0.5);max-width:360px;';
        document.body.appendChild(tooltipDiv);

        var canvas = container.querySelector('canvas');
        if (canvas) {
            attachTooltipHandlers(canvas, container, tooltipDiv);
        } else {
            var observer = new MutationObserver(function() {
                var c = container.querySelector('canvas');
                if (c) {
                    observer.disconnect();
                    attachTooltipHandlers(c, container, tooltipDiv);
                }
            });
            observer.observe(container, { childList: true, subtree: true });
        }
    }

    function attachTooltipHandlers(canvas, container, tooltipDiv) {
        canvas.addEventListener('mousemove', function(e) {
            if (typeof network === 'undefined') return;
            var rect = container.getBoundingClientRect();
            var nodeId = network.getNodeAt({ x: e.clientX - rect.left, y: e.clientY - rect.top });
            if (nodeId !== undefined && nodeId !== null) {
                var nodeData = network.body.data.nodes.get(nodeId);
                if (nodeData && nodeData.title) {
                    tooltipDiv.innerHTML = nodeData.title;
                    tooltipDiv.style.display = 'block';
                    var x = e.clientX + 15;
                    var y = e.clientY + 15;
                    var tRect = tooltipDiv.getBoundingClientRect();
                    if (x + tRect.width > window.innerWidth) x = e.clientX - tRect.width - 15;
                    if (y + tRect.height > window.innerHeight) y = e.clientY - tRect.height - 15;
                    tooltipDiv.style.left = x + 'px';
                    tooltipDiv.style.top = y + 'px';
                    return;
                }
            }
            tooltipDiv.style.display = 'none';
        });

        canvas.addEventListener('mouseleave', function() {
            tooltipDiv.style.display = 'none';
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTooltipHandler);
    } else {
        setTimeout(initTooltipHandler, 500);
    }
})();
</script>
"""

_CUSTOM_CSS = """
<style>
body {
    margin: 0;
    padding: 0;
    background: #0d0d0d;
    overflow: hidden;
}
#mynetwork {
    width: 100%;
    height: 100vh;
}
#custom-tooltip img {
    border-radius: 4px;
}
.vis-tooltip {
    display: none !important;
}
</style>
"""


def generate_html(network: Network, output_path: str) -> str:
    """
    Generate a self-contained HTML file from a PyVis Network.

    Post-processes the generated HTML to:
    1. Remove broken <script src="lib/bindings/utils.js"></script> reference
    2. Replace it with inline globals declaration
    3. Inline vis-network CDN JS and CSS instead of external links
    4. Inject custom dark theme CSS and tooltip JS
    5. Set page title

    Args:
        network: The built PyVis Network.
        output_path: Path to write the HTML file.

    Returns:
        Path to the generated HTML file.
    """
    html = network.generate_html(notebook=False)

    # ── Step 0: Ensure DOCTYPE declaration ──
    if not html.strip().startswith('<!DOCTYPE'):
        html = '<!DOCTYPE html>\n' + html

    # ── Step 1: Remove broken utils.js and replace with inline globals ──
    html = re.sub(
        r'<script\s+src="lib/bindings/utils\.js">\s*</script>',
        _UTILS_REPLACEMENT,
        html,
    )

    # ── Step 2: Inline vis-network CDN assets ──
    # Fetch and inline the JS
    vis_js = _fetch_cdn_asset(_VIS_NETWORK_JS_URL)
    js_pattern = r'<script\s+[^>]*' + re.escape(_VIS_NETWORK_JS_URL) + r'[^>]*></script>'
    html = re.sub(
        js_pattern,
        lambda m: f'<script type="text/javascript">\n{vis_js}\n</script>',
        html,
    )

    # Fetch and inline the CSS
    vis_css = _fetch_cdn_asset(_VIS_NETWORK_CSS_URL)
    css_pattern = r'<link\s+[^>]*' + re.escape(_VIS_NETWORK_CSS_URL) + r'[^>]*/>'
    html = re.sub(
        css_pattern,
        lambda m: f'<style>\n{vis_css}\n</style>',
        html,
    )

    # ── Step 3: Remove any remaining CDN / lib-bindings references ──
    html = re.sub(r'<script\s+src="lib/bindings/[^"]*">\s*</script>', '', html)
    html = re.sub(r'<link[^>]*cdn\.jsdelivr[^>]*>', '', html)
    html = re.sub(r'<script[^>]*cdn\.jsdelivr[^>]*>[^<]*</script>', '', html)
    html = re.sub(r'<link[^>]*unpkg\.com[^>]*>', '', html)
    html = re.sub(r'<script[^>]*unpkg\.com[^>]*>[^<]*</script>', '', html)

    # ── Step 4: Inject custom CSS before </head> ──
    if '</head>' in html:
        html = html.replace('</head>', _CUSTOM_CSS + '\n</head>')
    else:
        html = _CUSTOM_CSS + '\n' + html

    # ── Step 5: Inject custom tooltip JS before </body> ──
    if '</body>' in html:
        html = html.replace('</body>', _CUSTOM_TOOLTIP_JS + '\n</body>')
    else:
        html = html + '\n' + _CUSTOM_TOOLTIP_JS

    # ── Step 6: Set page title ──
    if '<title>' in html:
        html = re.sub(
            r'<title>[^<]*</title>',
            '<title>SiteMap3D - Interactive Site Graph</title>',
            html,
        )
    else:
        html = html.replace(
            '<head>',
            '<head>\n<title>SiteMap3D - Interactive Site Graph</title>',
        )

    # ── Step 7: Replace physics configuration for better layout ──
    _PHYSICS_CONFIG = """{
  "enabled": true,
  "barnesHut": {
    "gravitationalConstant": -8000,
    "centralGravity": 0.1,
    "springLength": 200,
    "springConstant": 0.04,
    "damping": 0.5,
    "avoidOverlap": 0.8
  },
  "stabilization": {
    "enabled": true,
    "iterations": 300,
    "updateInterval": 10,
    "fit": true
  },
  "minVelocity": 0.75
}"""
    # Find "physics": { ... } with brace counting to handle nested objects
    match = re.search(r'"physics"\s*:\s*\{', html)
    if match:
        start = match.start()
        brace_start = match.end() - 1  # position of opening {
        depth = 0
        end = brace_start
        for i in range(brace_start, len(html)):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        html = html[:start] + '"physics": ' + _PHYSICS_CONFIG + html[end:]

    # ── Write output ──
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
