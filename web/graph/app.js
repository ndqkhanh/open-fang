const $ = (id) => document.getElementById(id);
const edgeColor = (kind) => ({
  cites: "#2b6bed",
  extends: "#e6a23c",
  refutes: "#e63946",
  "shares-author": "#8e8e93",
  "same-benchmark": "#8e8e93",
  "same-technique-family": "#8e8e93",
}[kind] || "#8e8e93");

const cy = cytoscape({
  container: $("cy"),
  style: [
    { selector: "node", style: {
      "background-color": "#1a1e26",
      "border-color": "#2b6bed",
      "border-width": 2,
      "color": "#e6e6e6",
      "label": "data(label)",
      "font-size": 11,
      "text-wrap": "wrap",
      "text-max-width": 160,
      "text-valign": "bottom",
      "text-margin-y": 6,
      "width": 22, "height": 22,
    }},
    { selector: "edge", style: {
      "line-color": (e) => edgeColor(e.data("kind")),
      "target-arrow-color": (e) => edgeColor(e.data("kind")),
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "width": 2,
      "arrow-scale": 0.9,
    }},
    { selector: "node:selected", style: { "border-color": "#ffd166", "border-width": 3 } },
  ],
  layout: { name: "cose", animate: false, padding: 20 },
});

async function load() {
  const seed = $("seed").value.trim();
  const query = $("query").value.trim();
  const depth = $("depth").value;
  if (!seed && !query) { alert("provide a seed or a query"); return; }
  const params = new URLSearchParams({ depth });
  if (seed) params.set("seed", seed);
  if (query) params.set("query", query);
  const resp = await fetch(`/v1/kb/graph?${params}`);
  if (!resp.ok) { $("meta").textContent = `error: ${resp.status}`; return; }
  const data = await resp.json();
  cy.elements().remove();
  cy.add(data.nodes);
  cy.add(data.edges);
  cy.layout({ name: "cose", animate: false, padding: 20 }).run();
  $("meta").textContent = `${data.nodes.length} nodes / ${data.edges.length} edges — seed ${data.seed_id || "(none)"}`;
}

$("go").addEventListener("click", load);
$("seed").addEventListener("keydown", (e) => { if (e.key === "Enter") load(); });
$("query").addEventListener("keydown", (e) => { if (e.key === "Enter") load(); });

cy.on("tap", "node", async (ev) => {
  const id = ev.target.id();
  const resp = await fetch(`/v1/kb/paper/${encodeURIComponent(id)}`);
  if (!resp.ok) { $("panel").style.display = "none"; return; }
  const p = await resp.json();
  $("panel").innerHTML = `
    <h3>${p.title || p.id}</h3>
    <div class="authors">${(p.authors || []).join(", ") || "<em>no authors</em>"}</div>
    <div>${p.published_at || ""}</div>
    <hr style="border-color:#2d333f" />
    <div style="white-space:pre-wrap">${p.abstract || ""}</div>
  `;
  $("panel").style.display = "block";
});

cy.on("tap", (ev) => { if (ev.target === cy) $("panel").style.display = "none"; });
