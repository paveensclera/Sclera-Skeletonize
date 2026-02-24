# KD-Tree snapping + collinearity reduction (with intersection protection)
from svgpathtools import svg2paths
import re
import sys
import uuid
import math
from scipy.spatial import KDTree

input_svg = sys.argv[1] if len(sys.argv) > 1 else 'input.svg'
output_svg = sys.argv[2] if len(sys.argv) > 2 else 'snapped_simplified.svg'

# PARAMETERS
THRESHOLD = 20.0   # px for snapping cluster radius
SIMPLIFY_TOL = 2.0 # px perpendicular tolerance

print("KD-Tree snap + intersection-safe collinearity reduction running...")

# read svg header
with open(input_svg) as f:
    header = f.read(4096)
svg_tag = re.search(r'<svg[^>]*>', header).group()

paths, _ = svg2paths(input_svg)

# 1) linearize all paths
generated_paths = []   # list[list[(x,y)]]
all_points = []        # (x,y,path_idx,point_idx)
all_xy = []            # for KDTree

for original_path in paths:
    if original_path.length() < 30:
        continue

    for sub in original_path.continuous_subpaths():
        if sub.length() < 30:
            continue

        pts = []
        last = None
        for seg in sub:
            seg_len = seg.length()
            steps = max(2, int(seg_len / 8) + 1)
            for i in range(steps + 1):
                if i == 0 and pts:
                    continue
                t = i / steps
                p = seg.point(t)
                x = round(p.real * 2) / 2
                y = round(p.imag * 2) / 2
                if last is None or abs(x - last[0]) >= 1.0 or abs(y - last[1]) >= 1.0:
                    pts.append((x, y))
                    last = (x, y)

        if len(pts) < 2:
            continue

        path_idx = len(generated_paths)
        generated_paths.append(pts)
        for pi, (x, y) in enumerate(pts):
            all_points.append((x, y, path_idx, pi))
            all_xy.append((x, y))

print(f"Linearized {len(generated_paths)} paths; collected {len(all_points)} points.")

# 2) KD-tree clustering
tree = KDTree(all_xy)
clusters = []
visited = set()

for i, (x1, y1, p1, pt1) in enumerate(all_points):
    if i in visited:
        continue
    neighbor_ids = tree.query_ball_point((x1, y1), THRESHOLD)
    cluster = []
    for nid in neighbor_ids:
        if nid not in visited:
            x2, y2, p2, pt2 = all_points[nid]
            cluster.append((nid, x2, y2, p2, pt2))
            visited.add(nid)
    clusters.append(cluster)

print(f"Found {len(clusters)} clusters via KD-tree.")

# 3) canonical coordinates
canonical = {}
for cluster in clusters:
    xs = [c[1] for c in cluster]
    ys = [c[2] for c in cluster]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    for (_, _, _, p_idx, pt_idx) in cluster:
        canonical[(p_idx, pt_idx)] = (cx, cy)

# 4) rewrite all path points to canonical coords
for p_idx, pts in enumerate(generated_paths):
    for i in range(len(pts)):
        key = (p_idx, i)
        if key in canonical:
            pts[i] = canonical[key]

# ============================================================
# BUILD PROTECTED INTERSECTION POINTS
# ============================================================
protected_by_path = {i: set() for i in range(len(generated_paths))}

for cluster in clusters:
    path_ids = set(c[3] for c in cluster)  # all path_idx’s in this cluster
    if len(path_ids) > 1:
        # real intersection → protect all points in this cluster
        for (_, _, _, p_idx, pt_idx) in cluster:
            protected_by_path[p_idx].add(pt_idx)

# ============================================================
# 5) intersection-safe collinearity reduction
# ============================================================

def simplify_path(points, protected_indices, tol=SIMPLIFY_TOL):
    """Remove nearly-collinear internal points,
       but NEVER remove intersection-protected points."""
    
    if len(points) <= 2:
        return points[:]

    stack = [points[0], points[1]]
    idx_stack = [0, 1]

    for i in range(2, len(points)):
        C = points[i]

        while len(stack) >= 2:
            A = stack[-2]
            B = stack[-1]

            Aidx = idx_stack[-2]
            Bidx = idx_stack[-1]

            # DO NOT REMOVE PROTECTED POINTS
            if Bidx in protected_indices:
                break

            ACx = C[0] - A[0]
            ACy = C[1] - A[1]
            denom = math.hypot(ACx, ACy)
            if denom == 0:
                break

            cross = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
            perp_dist = abs(cross) / denom

            if perp_dist <= tol:
                stack.pop()
                idx_stack.pop()
            else:
                break

        stack.append(C)
        idx_stack.append(i)

    # remove duplicates
    if len(stack) >= 2:
        out = [stack[0]]
        for p in stack[1:]:
            if p != out[-1]:
                out.append(p)
        return out if len(out) >= 2 else stack[:2]

    return stack

# simplify all paths
before_pts = sum(len(p) for p in generated_paths)
for i, pts in enumerate(generated_paths):
    protected = protected_by_path[i]
    generated_paths[i] = simplify_path(pts, protected_indices=protected, tol=SIMPLIFY_TOL)
after_pts = sum(len(p) for p in generated_paths)

print(f"Simplified points: before={before_pts} after={after_pts} (tol={SIMPLIFY_TOL})")

# 6) write final svg
with open(output_svg, 'w') as f:
    f.write(f"{svg_tag}\n")
    total = 0
    for pts in generated_paths:
        d = f"M {pts[0][0]} {pts[0][1]}"
        for x, y in pts[1:]:
            d += f" L {x} {y}"
        f.write(
            f'<path d="{d}" stroke-width="2" stroke="#3182ce" '
            f'stroke-linejoin="round" stroke-linecap="round" fill="none" '
            f'data-drawing-path="true" '
            f'data-shape-type="polyline" '
            f'data-user-drawn="true" '
            f'data-auto-snapped="true" '
            f'data-drawing-id="{uuid.uuid4()}"/>\n'
        )
        total += 1
    f.write("</svg>\n")

print(f"DONE! {total} snapped & INTERSECTION-SAFE simplified polylines written.")