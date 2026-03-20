// main.js

const svgContainer = document.getElementById("svg-container");
const routeBtn = document.getElementById("route-btn");
const clearBtn = document.getElementById("clear-btn");
const floorSelect = document.getElementById("floor-select");
const FLOOR_FOLDER = "temp/dim1000/";

let svgElement;
let graph = {};
let startNode = null;
let endNode = null;
let routeStack = [];

// -------------------- LOAD SVG --------------------
async function loadSVG(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error("SVG load failed");

    const text = await res.text();
    svgContainer.innerHTML = text;

    svgElement = svgContainer.querySelector("svg");
    if (!svgElement) return;

    svgElement.style.border = "1px solid #ccc";

    buildGraph();
    enableClickSelection();
  } catch (err) {
    console.error(err);
  }
}


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

    // if both already selected → start new route
    if (startNode && endNode) {
      startNode = null;
      endNode = null;
    }

    if (!startNode) {
  startNode = nearest;
  currentStartMarker = drawMarker(nearest, "green");
} else if (!endNode) {
  endNode = nearest;
  currentEndMarker = drawMarker(nearest, "red");

  // ✅ let UI update first
  setTimeout(() => {
    const path = dijkstra(startNode, endNode);

    if (!path) {
      alert("No path found");

      routeStack.push({
        route: null,
        startMarker: currentStartMarker,
        endMarker: currentEndMarker,
      });
    } else {
      const routeEl = drawRoute(path);

      routeStack.push({
        route: routeEl,
        startMarker: currentStartMarker,
        endMarker: currentEndMarker,
      });
    }

    // reset
    startNode = null;
    endNode = null;
    currentStartMarker = null;
    currentEndMarker = null;

  }, 0); // 👈 key trick
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

  // ❗ NO PATH CHECK
  if (dist[end] === Infinity) {
    return null;
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
  if (path.length < 2) return null;

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
  polyline.setAttribute("stroke-width", "50");
  polyline.setAttribute("stroke-linejoin", "round");
  polyline.setAttribute("stroke-linecap", "round");

  svgElement.appendChild(polyline);

  return polyline; // ✅ return element
}

function drawMarker(nodeKey, color) {
  const p = graph[nodeKey].point;

  const circle = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "circle"
  );

  circle.setAttribute("cx", p[0]);
  circle.setAttribute("cy", p[1]);
  circle.setAttribute("r", 50);
  circle.setAttribute("fill", color);

  svgElement.appendChild(circle);

  return circle; // ✅ return element
}

// -------------------- BUTTONS --------------------

let currentStartMarker = null;
let currentEndMarker = null;

routeBtn.addEventListener("click", () => {
  if (!startNode || !endNode) return;

  const path = dijkstra(startNode, endNode);

  // ❗ ALWAYS push markers
  if (!path) {
    alert("No path found");

    routeStack.push({
      route: null, // no route
      startMarker: currentStartMarker,
      endMarker: currentEndMarker,
    });

    // reset for next input
    startNode = null;
    endNode = null;
    currentStartMarker = null;
    currentEndMarker = null;

    return;
  }

  const routeEl = drawRoute(path);

  routeStack.push({
    route: routeEl,
    startMarker: currentStartMarker,
    endMarker: currentEndMarker,
  });

  startNode = null;
  endNode = null;
  currentStartMarker = null;
  currentEndMarker = null;
});

clearBtn.addEventListener("click", () => {
  if (routeStack.length === 0) return;

  const last = routeStack.pop();

  last.route?.remove();
  last.startMarker?.remove();
  last.endMarker?.remove();
});

// floor fetching
async function initFloors() {
  try {
    const res = await fetch(FLOOR_FOLDER + "floors.json");
    if (!res.ok) throw new Error("floors.json not found");

    const floors = await res.json();

    floors.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = FLOOR_FOLDER + name;
      opt.textContent = name.includes("_merged")
  ? name.slice(0, 8) + "..." + name.slice(name.indexOf("_merged") - 4, name.indexOf("_merged"))
  : name;
      floorSelect.appendChild(opt);
    });

    loadSVG(FLOOR_FOLDER + floors[0]);
  } catch (err) {
    console.error(err);
  }
}

floorSelect.addEventListener("change", () => {
  startNode = null;
  endNode = null;
  routeStack = [];
  loadSVG(floorSelect.value);
});

initFloors();