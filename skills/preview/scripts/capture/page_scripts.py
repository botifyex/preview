SETTLE_SCRIPT = """
async (limit) => {
  await document.fonts.ready;
  const endless = (animation) => animation.effect?.getComputedTiming().iterations === Infinity;
  const animations = document.getAnimations();
  animations.filter(endless).forEach((animation) => animation.cancel());
  const running = animations.filter((animation) => !endless(animation) && animation.playState === "running");
  const finished = Promise.allSettled(running.map((animation) => animation.finished)).then(() => true);
  const expired = new Promise((resolve) => setTimeout(() => resolve(false), limit));
  const settled = await Promise.race([finished, expired]);
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  return settled;
}
"""

MEASURE_SCRIPT = """
(element) => {
  const rectangle = element.getBoundingClientRect();
  let left = rectangle.left, top = rectangle.top, right = rectangle.right, bottom = rectangle.bottom;
  for (let parent = element.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
    if (getComputedStyle(parent).overflow === "visible") continue;
    const outer = parent.getBoundingClientRect();
    left = Math.max(left, outer.left);
    top = Math.max(top, outer.top);
    right = Math.min(right, outer.right);
    bottom = Math.min(bottom, outer.bottom);
  }
  if (right <= left || bottom <= top) return null;
  return { x: left + scrollX, y: top + scrollY, width: right - left, height: bottom - top };
}
"""

PAGE_SCRIPT = """
() => ({
  width: Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth ?? 0),
  height: Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight ?? 0),
  left: scrollX,
  top: scrollY,
  viewportWidth: innerWidth,
  viewportHeight: innerHeight,
})
"""

HIDE_SCRIPT = "(elements) => elements.forEach((element) => element.style.setProperty('display', 'none', 'important'))"

SCROLL_TOP_SCRIPT = "() => window.scrollTo({ top: 0, left: 0, behavior: 'instant' })"

WRAP_SCRIPT = """
({ text, limit }) => {
  const context = document.createElement("canvas").getContext("2d");
  context.font = "700 14px Arial, sans-serif";
  const wide = (value) => context.measureText(value).width;
  const glyphs = (word) => Array.from(new Intl.Segmenter().segment(word), (part) => part.segment);
  const lines = [];
  let line = "";
  const flush = () => { if (line) lines.push(line); line = ""; };
  const breakWord = (word) => glyphs(word).forEach((glyph) => {
    if (wide(line + glyph) > limit) flush();
    line += glyph;
  });
  const place = (word) => {
    const longer = line ? line + " " + word : word;
    if (wide(longer) <= limit) { line = longer; return; }
    flush();
    if (wide(word) <= limit) line = word;
    else breakWord(word);
  };
  text.trim().split("\\n").forEach((paragraph) => {
    paragraph.split(/\\s+/).filter(Boolean).forEach(place);
    flush();
  });
  return { lines, width: Math.max(...lines.map(wide)) };
}
"""

DRAW_SCRIPT = """
({ marks, page, area, radius }) => {
  const HALO = "#FFFFFF", INK = "#FFFFFF";
  const NAMESPACE = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NAMESPACE, "svg");
  svg.setAttribute("data-preview", "overlay");
  svg.setAttribute("width", page.width);
  svg.setAttribute("height", page.height);
  Object.assign(svg.style, {
    position: "absolute", left: "0", top: "0", width: page.width + "px", height: page.height + "px",
    zIndex: "2147483647", pointerEvents: "none", overflow: "visible", margin: "0", maxWidth: "none",
  });
  document.documentElement.appendChild(svg);
  const origin = svg.getBoundingClientRect();
  svg.style.left = -(origin.left + scrollX) + "px";
  svg.style.top = -(origin.top + scrollY) + "px";
  const add = (name, attributes, text) => {
    const node = document.createElementNS(NAMESPACE, name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    svg.appendChild(node);
    return node;
  };
  const outlined = (name, attributes, color, dash) => {
    add(name, { ...attributes, fill: "none", stroke: HALO, "stroke-width": 7, "stroke-opacity": 0.9, "stroke-linecap": "round" });
    add(name, { ...attributes, fill: "none", stroke: color, "stroke-width": 3, "stroke-linecap": "round", ...(dash ? { "stroke-dasharray": dash } : {}) });
  };
  const frame = (mark, color, dash) => outlined("rect", { x: mark.rectangle.x, y: mark.rectangle.y, width: mark.rectangle.width, height: mark.rectangle.height, rx: 4 }, color, dash);
  const head = (tail, tip, color) => {
    const angle = Math.atan2(tip.y - tail.y, tip.x - tail.x);
    const wing = (turn) => (tip.x - 14 * Math.cos(angle + turn)) + "," + (tip.y - 14 * Math.sin(angle + turn));
    const points = tip.x + "," + tip.y + " " + wing(0.5) + " " + wing(-0.5);
    add("polygon", { points, fill: color, stroke: HALO, "stroke-width": 2 });
  };
  const segment = (start, end, color) => outlined("line", { x1: start.x, y1: start.y, x2: end.x, y2: end.y }, color);
  const arrow = (mark, color) => {
    segment(mark.tail, mark.tip, color);
    head(mark.tail, mark.tip, color);
  };
  const retreat = (from, to) => {
    const share = 8 / Math.hypot(to.x - from.x, to.y - from.y);
    return { x: to.x + (from.x - to.x) * share, y: to.y + (from.y - to.y) * share };
  };
  const connector = (mark, color) => {
    const { start, end, heads } = mark;
    segment(heads === "both" ? retreat(end, start) : start, heads === "none" ? end : retreat(start, end), color);
    if (heads !== "none") head(start, end, color);
    if (heads === "both") head(end, start, color);
  };
  const ellipse = (mark, color) => {
    const { x, y, width, height } = mark.bounds;
    outlined("ellipse", { cx: x + width / 2, cy: y + height / 2, rx: width / 2, ry: height / 2 }, color);
  };
  const highlight = (mark) => add("rect", { ...mark.rectangle, rx: 4, fill: mark.color, "fill-opacity": mark.opacity });
  const spotlight = (mark) => {
    const { x, y, width, height } = mark.rectangle;
    const hole = "M" + x + " " + y + "h" + width + "v" + height + "h" + -width + "Z";
    const d = "M0 0H" + mark.veil.width + "V" + mark.veil.height + "H0Z" + hole;
    add("path", { d, "data-preview": "veil", "fill-rule": "evenodd", fill: "#000000", "fill-opacity": mark.opacity });
    add("path", { d: hole, fill: "none", stroke: HALO, "stroke-width": 2 });
  };
  const callout = (mark, color) => {
    segment(mark.start, mark.end, color);
    add("rect", { ...mark.rectangle, rx: 4, fill: color, stroke: HALO, "stroke-width": 2 });
    mark.lines.forEach((line) => add("text", { x: line.x, y: line.y, fill: INK, "font-family": "Arial, sans-serif", "font-size": 14, "font-weight": 700, "dominant-baseline": "central" }, line.text));
  };
  const badge = (mark, color) => {
    const { x, y } = mark.badge;
    add("circle", { cx: x, cy: y, r: radius, fill: color, stroke: HALO, "stroke-width": 3 });
    add("text", { x, y, fill: INK, "font-family": "Arial, sans-serif", "font-size": 15, "font-weight": 700, "text-anchor": "middle", "dominant-baseline": "central" }, String(mark.number));
  };
  const label = (mark, color) => {
    const text = add("text", { x: 0, y: 0, fill: INK, "font-family": "Arial, sans-serif", "font-size": 14, "font-weight": 700, "dominant-baseline": "central" }, mark.text);
    const width = text.getBBox().width + 16, height = 24;
    if (width > page.width) throw new Error("label is wider than the page: " + mark.text);
    const above = (mark.top ?? mark.corner.y) - height - 8;
    const y = above >= area.y ? above : mark.bottom + 8;
    const start = mark.corner.x + (mark.number === null ? 0 : 20);
    const x = Math.max(area.x, Math.min(area.x + area.width - width, start));
    const back = add("rect", { x, y, width, height, rx: 4, fill: color, stroke: HALO, "stroke-width": 2 });
    svg.insertBefore(back, text);
    text.setAttribute("x", x + 8);
    text.setAttribute("y", y + height / 2);
    return { x, y, width, height };
  };
  marks.filter((mark) => mark.kind === "spotlight").forEach(spotlight);
  marks.filter((mark) => mark.kind === "highlight").forEach(highlight);
  return marks.map((mark) => {
    const { color } = mark;
    if (mark.kind === "box") frame(mark, color);
    if (mark.kind === "removed") frame(mark, color, "10 7");
    if (mark.kind === "arrow") arrow(mark, color);
    if (mark.kind === "connector") connector(mark, color);
    if (mark.kind === "ellipse") ellipse(mark, color);
    if (mark.kind === "underline") segment(mark.start, mark.end, color);
    if (mark.kind === "callout") callout(mark, color);
    const box = mark.text !== null && mark.kind !== "callout" ? label(mark, color) : null;
    if (mark.number !== null) badge(mark, color);
    return box;
  });
}
"""
