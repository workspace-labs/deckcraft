"""Write HTML slides: one file that presents in any browser.

Draws the elements from layout.py. Units become cqw (1% of the slide width), so a
slide looks the same at any size. Keys: arrows, space, Home, End; F = full screen.
Opening the file with #all shows every slide one under another (for checking and printing).
"""
from . import designs
from .htmlbits import STAR6, data_uri, esc, font_stack, head, pattern_svg, rgba

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:#1b1b1f;display:grid;place-items:center;overflow:hidden;font-synthesis:none}
.deck{width:min(100vw,177.78vh);aspect-ratio:16/9;position:relative}
.slide{position:absolute;inset:0;container-type:inline-size;overflow:hidden;display:none;background:var(--bg)}
.slide.on{display:block}
.slide>*{position:absolute}
.t{white-space:nowrap}
.bar{position:fixed;bottom:10px;left:50%;transform:translateX(-50%);font:12px/1 system-ui,sans-serif;color:#bbb;
  background:rgb(0 0 0/.45);padding:6px 10px;border-radius:99px;opacity:0;transition:opacity .3s;direction:ltr}
body:hover .bar{opacity:1}
body.all{display:block;overflow:auto;background:#d9dbe0;padding:24px 0}
body.all .deck{aspect-ratio:auto;width:min(1280px,96vw);margin:0 auto;display:grid;gap:24px}
body.all .slide{position:relative;display:block;aspect-ratio:16/9;inset:auto}
body.all .bar{display:none}
@media print{
  @page{size:13.333in 7.5in;margin:0}
  body,body.all{background:none;display:block;overflow:visible;padding:0}
  .deck,body.all .deck{width:13.333in;aspect-ratio:auto;display:block}
  .slide{position:relative;display:block;width:13.333in;height:7.5in;inset:auto;break-after:page}
  .bar{display:none}
}
@media (prefers-reduced-motion:no-preference){.slide.on{animation:in .25s ease-out}}
@keyframes in{from{opacity:.4}to{opacity:1}}
"""

SCRIPT = """
<script>
(function(){
  var s=[].slice.call(document.querySelectorAll('.slide')),i=0,bar=document.querySelector('.bar');
  if(location.hash==='#all'){document.body.classList.add('all');return;}
  function go(n){i=Math.max(0,Math.min(s.length-1,n));s.forEach(function(e,k){e.classList.toggle('on',k===i);});
    bar.textContent=(i+1)+' / '+s.length+'  \\u00b7  \\u2190 \\u2192  \\u00b7  F';history.replaceState(null,'','#'+(i+1));}
  var back=document.documentElement.dir==='rtl';
  document.addEventListener('keydown',function(e){
    var k=e.key;
    if(k==='ArrowRight'||k==='PageDown'||k===' ')go(i+(back&&k==='ArrowRight'?-1:1));
    else if(k==='ArrowLeft'||k==='PageUp')go(i+(back&&k==='ArrowLeft'?1:-1));
    else if(k==='Home')go(0);else if(k==='End')go(s.length-1);
    else if(k==='f'||k==='F'){if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen();}
  });
  document.querySelector('.deck').addEventListener('click',function(e){
    var r=this.getBoundingClientRect(),right=e.clientX>r.left+r.width/2;go(i+((right!==back)?1:-1));});
  go((parseInt(location.hash.slice(1),10)||1)-1);
})();
</script>
"""


def u(v):
    return f"{v:.3f}".rstrip("0").rstrip(".") + "cqw"


def render(slides, design, content):
    bg = designs.color(design, "bg")
    css = CSS + f":root{{--bg:{bg}}}"
    out = [head(content["title"], content["lang"], designs.google_fonts_url(design), css)]
    out.append("<body>\n<div class=\"deck\">\n")
    for n, slide in enumerate(slides, 1):
        out.append(f"<section class=\"slide\" aria-label=\"Slide {n}\">\n")
        out += [element(e) + "\n" for e in slide["elements"]]
        out.append("</section>\n")
    out.append("</div>\n<div class=\"bar\"></div>\n" + SCRIPT + "</body>\n</html>\n")
    return "".join(out)


def box(e):
    st = [f"left:{u(e['x'])}", f"top:{u(e['y'])}", f"width:{u(e['w'])}", f"height:{u(e['h'])}"]
    if e.get("rotate"):
        st.append(f"transform:rotate({e['rotate']:g}deg)")
    return st


def element(e):
    if e["kind"] == "text":
        return text(e)
    if e["kind"] == "image":
        return f"<img src=\"{data_uri(e['path'])}\" alt=\"\" style=\"{';'.join(box(e))}\">"
    return shape(e)


def text(e):
    st = box(e)
    st[3] = "min-height:" + u(e["h"])
    st += [f"font-family:{font_stack(e['family'], e['fallback'])}", f"font-size:{u(e['size'])}",
           f"font-weight:{e['weight']}", f"line-height:{e['leading']:g}", f"color:{rgba(e['color'], e['alpha'])}",
           f"text-align:{e['align']}"]
    if e["italic"]:
        st.append("font-style:italic")
    if e["tracking"]:
        st.append(f"letter-spacing:{e['tracking']:g}em")
    body = "<br>".join(esc(line) for line in e["lines"])
    direction = " dir=\"rtl\"" if e["rtl"] else ""
    return f"<div class=\"t\"{direction} style=\"{';'.join(st)}\">{body}</div>"


def shape(e):
    st = box(e)
    kind = e["shape"]
    fill = e["fill"]
    if kind == "glow":
        st.append(f"background:radial-gradient(closest-side,{rgba(fill)},{rgba(fill, 0)})")
    elif kind == "pattern":
        st.append(f"background:{rgba(fill)} url('{pattern_svg(e['line'], e['line_alpha'])}') 0 0/{u(e['tile'])} {u(e['tile'])}")
    elif fill:
        st.append(f"background:{rgba(fill, e['alpha'])}")
    if e["line"] and e["line_w"] and kind != "pattern":
        st.append(f"border:{u(e['line_w'])} solid {rgba(e['line'], e['line_alpha'])}")
    radius = e.get("radius", 0)
    if kind == "ellipse":
        st.append("border-radius:50%")
    elif kind == "leaf":
        st.append("border-radius:" + ("0 100% 0 100%" if e["corners"] == "tr-bl" else "100% 0 100% 0"))
    elif kind == "diamond":
        st.append("clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%)")
    elif kind == "star6":
        st.append(f"clip-path:polygon({STAR6})")
    elif radius:
        r = u(radius)
        st.append(f"border-radius:{r} {r} 0 0" if e.get("corners") == "top" else f"border-radius:{r}")
    sh = e.get("shadow")
    if sh:
        st.append(f"box-shadow:{u(sh['dx'])} {u(sh['dy'])} {u(sh['blur'])} {rgba(sh['color'], sh['alpha'])}")
    if kind != "glow" and e.get("deco") and e.get("alpha", 1) < 1 and not fill:
        st.append(f"opacity:{e['alpha']:g}")
    return f"<div aria-hidden=\"true\" style=\"{';'.join(st)}\"></div>"
