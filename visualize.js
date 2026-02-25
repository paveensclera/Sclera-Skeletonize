// main.js

const svgContainer = document.getElementById("svg-container");
const routeBtn = document.getElementById("route-btn");
const clearBtn = document.getElementById("clear-btn");

let svgElement;
let graph = {};
let startNode = null;
let endNode = null;
let currentRoute = [];

// -------------------- LOAD SVG --------------------
async function loadSVG() {
  const res = await fetch("big.svg");
  const text = await res.text();
  svgContainer.innerHTML = text;

  svgElement = svgContainer.querySelector("svg");
  if (!svgElement) return;

  svgElement.style.border = "1px solid #ccc";

  buildGraph();
  enableClickSelection();
}

loadSVG();

// -------------------- GRAPH BUILD --------------------

function parsePathPoints(d) {
  const tokens = d.match(/-?\d+(\.\d+)?/g);
  const points = [];
  for (let i = 0; i < tokens.length; i += 2) {
    points.push([parseFloat(tokens[i]), parseFloat(tokens[i + 1])]);
  }
  return points;
}

function pointKey(p) {
  return p[0].toFixed(3) + "_" + p[1].toFixed(3);
}

function buildGraph() {
  graph = {};

  const paths = svgElement.querySelectorAll(
    'path[data-user-drawn="true"]'
  );

  paths.forEach((p) => {
    const d = p.getAttribute("d");
    if (!d) return;

    const pts = parsePathPoints(d);

    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i];
      const b = pts[i + 1];
      const aKey = pointKey(a);
      const bKey = pointKey(b);

      const dist = Math.hypot(b[0] - a[0], b[1] - a[1]);

      if (!graph[aKey]) graph[aKey] = { point: a, edges: [] };
      if (!graph[bKey]) graph[bKey] = { point: b, edges: [] };

      graph[aKey].edges.push({ to: bKey, weight: dist });
      graph[bKey].edges.push({ to: aKey, weight: dist });
    }
  });
}

// -------------------- NODE SELECTION --------------------

function enableClickSelection() {
  svgElement.addEventListener("click", (e) => {
    const pt = getMouseSVGPoint(e);

    const nearest = findNearestNode(pt);
    if (!nearest) return;

    if (!startNode) {
      startNode = nearest;
      drawMarker(nearest, "green");
    } else if (!endNode) {
      endNode = nearest;
      drawMarker(nearest, "red");
    }
  });
}

function getMouseSVGPoint(evt) {
  const pt = svgElement.createSVGPoint();
  pt.x = evt.clientX;
  pt.y = evt.clientY;
  return pt.matrixTransform(svgElement.getScreenCTM().inverse());
}

function findNearestNode(pt) {
  let minDist = Infinity;
  let nearest = null;

  Object.keys(graph).forEach((key) => {
    const p = graph[key].point;
    const d = Math.hypot(pt.x - p[0], pt.y - p[1]);
    if (d < minDist) {
      minDist = d;
      nearest = key;
    }
  });

  return nearest;
}

// -------------------- DIJKSTRA --------------------

function dijkstra(start, end) {
  const dist = {};
  const prev = {};
  const visited = new Set();

  Object.keys(graph).forEach((k) => (dist[k] = Infinity));
  dist[start] = 0;

  while (true) {
    let u = null;
    let min = Infinity;

    Object.keys(dist).forEach((k) => {
      if (!visited.has(k) && dist[k] < min) {
        min = dist[k];
        u = k;
      }
    });

    if (!u || u === end) break;

    visited.add(u);

    graph[u].edges.forEach((edge) => {
      const alt = dist[u] + edge.weight;
      if (alt < dist[edge.to]) {
        dist[edge.to] = alt;
        prev[edge.to] = u;
      }
    });
  }

  const path = [];
  let curr = end;
  while (curr) {
    path.unshift(curr);
    curr = prev[curr];
  }

  return path;
}

// -------------------- ROUTE DRAW --------------------

function drawRoute(path) {
  if (path.length < 2) return;

  const points = path.map((k) => graph[k].point);

  const polyline = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "polyline"
  );

  polyline.setAttribute(
    "points",
    points.map((p) => p.join(",")).join(" ")
  );
  polyline.setAttribute("fill", "none");
  polyline.setAttribute("stroke", "orange");
  polyline.setAttribute("stroke-width", "4");
  polyline.setAttribute("stroke-linejoin", "round");
  polyline.setAttribute("stroke-linecap", "round");
  polyline.setAttribute("id", "route-line");

  svgElement.appendChild(polyline);
  currentRoute = path;
}

function drawMarker(nodeKey, color) {
  const p = graph[nodeKey].point;

  const circle = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "circle"
  );

  circle.setAttribute("cx", p[0]);
  circle.setAttribute("cy", p[1]);
  circle.setAttribute("r", 6);
  circle.setAttribute("fill", color);
  circle.setAttribute("class", "marker");

  svgElement.appendChild(circle);
}

// -------------------- BUTTONS --------------------

routeBtn.addEventListener("click", () => {
  if (!startNode || !endNode) return;

  const path = dijkstra(startNode, endNode);
  drawRoute(path);
});

clearBtn.addEventListener("click", () => {
  startNode = null;
  endNode = null;
  currentRoute = [];

  svgElement.querySelectorAll("#route-line").forEach((e) => e.remove());
  svgElement.querySelectorAll(".marker").forEach((e) => e.remove());
});