"""PyVis network builder for the sitemap graph."""

from pyvis.network import Network


# Node colors by depth
DEPTH_COLORS = {
    0: "#3498db",  # blue
    1: "#e67e22",  # orange
    2: "#2ecc71",  # green
}
FAILED_COLOR = "#e74c3c"  # red

# Graph defaults
DEFAULT_BG_COLOR = "#0d0d0d"
DEFAULT_NODE_SIZE = 15
MIN_NODE_SIZE = 10
MAX_NODE_SIZE = 50


def _get_color(depth: int, failed: bool = False) -> str:
    """Get node color based on depth or failure status."""
    if failed:
        return FAILED_COLOR
    return DEPTH_COLORS.get(depth, DEPTH_COLORS[2])


def _get_size(outbound_count: int) -> int:
    """Calculate node size from outbound link count."""
    if outbound_count <= 0:
        return MIN_NODE_SIZE
    size = min(MIN_NODE_SIZE + outbound_count * 3, MAX_NODE_SIZE)
    return size


class GraphBuilder:
    """
    Builds a PyVis Network graph from crawled page data.
    """

    def __init__(self):
        self.network = Network(
            height="100vh",
            width="100%",
            bgcolor=DEFAULT_BG_COLOR,
            font_color="#ffffff",
            directed=True,
            notebook=False,
        )
        self._edges: set[tuple[str, str]] = set()
        self._node_data: dict[str, dict] = {}

    def add_page(self, url: str, title: str, depth: int, outbound_count: int,
                 screenshot_b64: str, failed: bool = False):
        """
        Add a crawled page as a node in the graph.
        
        Args:
            url: Normalized URL (node ID and label).
            title: Page title for tooltip.
            depth: Crawl depth (affects color).
            outbound_count: Number of outgoing links (affects size).
            screenshot_b64: Base64-encoded screenshot or "Screenshot unavailable".
            failed: Whether the page fetch/screenshot failed.
        """
        color = _get_color(depth, failed)
        size = _get_size(outbound_count)

        # Build tooltip HTML with inline screenshot
        if screenshot_b64 and screenshot_b64 != "Screenshot unavailable":
            img_tag = f'<img src="data:image/jpeg;base64,{screenshot_b64}" width="320" height="200">'
        else:
            img_tag = f'<div style="width:320px;height:200px;background:#1a1a1a;display:flex;align-items:center;justify-content:center;color:#999;font-size:14px;">Screenshot unavailable</div>'

        title_html = f"""
        <div style="max-width:340px;color:#fff;font-family:sans-serif;">
            <div style="font-weight:bold;margin-bottom:6px;font-size:13px;word-break:break-all;">{title}</div>
            {img_tag}
            <div style="margin-top:6px;font-size:11px;color:#aaa;word-break:break-all;">{url}</div>
            <div style="font-size:11px;color:#888;">Depth: {depth} | Links: {outbound_count}</div>
        </div>
        """

        self._node_data[url] = {
            "title": title_html,
            "color": color,
            "size": size,
            "depth": depth,
        }

    def add_edge(self, source_url: str, target_url: str):
        """Add a directed edge between two nodes."""
        edge_key = (source_url, target_url)
        if edge_key not in self._edges:
            self._edges.add(edge_key)

    def build(self) -> Network:
        """
        Build and return the PyVis Network with all nodes and edges.
        Must be called after all pages and edges have been added.
        """
        # Add all nodes
        for url, data in self._node_data.items():
            self.network.add_node(
                url,
                label=url.split("//")[-1].rstrip("/")[:40],
                title=data["title"],
                color=data["color"],
                size=data["size"],
            )

        # Add all edges
        for source, target in self._edges:
            if source in self._node_data and target in self._node_data:
                self.network.add_edge(source, target, color="#555555", width=1)

        return self.network
