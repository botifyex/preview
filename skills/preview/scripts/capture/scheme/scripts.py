OVERLAY_BOUNDS_SCRIPT = """
() => {
  const overlay = document.querySelector('svg[data-preview="overlay"]');
  if (!overlay || !overlay.childElementCount) return null;
  const { x, y, width, height } = overlay.getBBox();
  return { x, y, width, height };
}
"""

TEXT_WIDTH_SCRIPT = """
(requests) => {
  const context = document.createElement("canvas").getContext("2d");
  return requests.map(({ font, text }) => {
    context.font = font;
    return context.measureText(text).width;
  });
}
"""

DRAW_SCRIPT = """
async ({ size, background, ink, panels, links, badges, headingFont, labelFont, labelPadding }) => {
  const HALO = "#FFFFFF", BORDER = "#98A2B3", LABEL_INK = "#FFFFFF";
  const NAMESPACE = "http://www.w3.org/2000/svg";
  const add = (parent, name, attributes, text) => {
    const node = document.createElementNS(NAMESPACE, name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    parent.appendChild(node);
    return node;
  };
  document.documentElement.style.margin = "0";
  document.body.style.margin = "0";
  document.body.style.background = background;
  const root = add(document.body, "svg", { width: size.width, height: size.height, style: "display:block" });
  const fontOf = (font) => ({ style: `font:${font}` });
  const loaded = (image) => new Promise((resolve, reject) => {
    image.addEventListener("load", resolve, { once: true });
    image.addEventListener("error", () => reject(new Error("cannot load a panel picture")), { once: true });
  });
  const stepBadge = (panel, color) => {
    const { x, y, number } = panel.step;
    add(root, "circle", { cx: x, cy: y, r: 12, fill: color, stroke: HALO, "stroke-width": 2 });
    add(root, "text", { x, y, fill: LABEL_INK, "text-anchor": "middle", "dominant-baseline": "central", ...fontOf(headingFont) }, number);
  };
  const panelImage = (panel) => {
    const { image, shown, natural, href } = panel;
    const frame = add(root, "svg", {
      x: image.x, y: image.y, width: image.width, height: image.height,
      viewBox: `${shown.x} ${shown.y} ${shown.width} ${shown.height}`, preserveAspectRatio: "none",
    });
    const picture = add(frame, "image", { width: natural.width, height: natural.height, preserveAspectRatio: "none" });
    const done = loaded(picture);
    picture.setAttribute("href", href);
    add(root, "rect", { x: image.x, y: image.y, width: image.width, height: image.height, fill: "none", stroke: BORDER });
    if (panel.step) stepBadge(panel, panel.color);
    if (panel.title) add(root, "text", { x: panel.titleAt.x, y: panel.titleAt.y, fill: ink, "dominant-baseline": "central", ...fontOf(headingFont) }, panel.title);
    return done;
  };
  const stroke = (points, color, dash) => {
    const line = points.map((point) => point.join(",")).join(" ");
    add(root, "polyline", { points: line, fill: "none", stroke: HALO, "stroke-width": 7, "stroke-opacity": 0.9, "stroke-linecap": "round", "stroke-linejoin": "round" });
    add(root, "polyline", { points: line, fill: "none", stroke: color, "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round", ...(dash ? { "stroke-dasharray": "10 8" } : {}) });
  };
  const head = (points, color) => {
    const tip = points[points.length - 1], before = points[points.length - 2];
    const angle = Math.atan2(tip[1] - before[1], tip[0] - before[0]);
    const wing = (turn) => (tip[0] - 18 * Math.cos(angle + turn)) + "," + (tip[1] - 18 * Math.sin(angle + turn));
    add(root, "polygon", { points: `${tip[0]},${tip[1]} ${wing(0.5)} ${wing(-0.5)}`, fill: color, stroke: HALO, "stroke-width": 2 });
  };
  const label = ({ box, text, color }) => {
    add(root, "rect", { ...box, rx: 4, fill: color, stroke: HALO, "stroke-width": 2 });
    add(root, "text", { x: box.x + labelPadding, y: box.y + box.height / 2, fill: LABEL_INK, "dominant-baseline": "central", ...fontOf(labelFont) }, text);
  };
  const badge = ({ x, y, number, color, radius }) => {
    add(root, "circle", { cx: x, cy: y, r: radius, fill: color, stroke: HALO, "stroke-width": 3 });
    add(root, "text", { x, y, fill: LABEL_INK, "font-family": "Arial, sans-serif", "font-size": radius + 1, "font-weight": 700, "text-anchor": "middle", "dominant-baseline": "central" }, String(number));
  };
  await Promise.all(panels.map(panelImage));
  links.forEach(({ points, color, dashed }) => { stroke(points, color, dashed); head(points, color); });
  links.filter((link) => link.label).forEach((link) => label({ ...link.label, color: link.color }));
  badges.forEach(badge);
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}
"""
