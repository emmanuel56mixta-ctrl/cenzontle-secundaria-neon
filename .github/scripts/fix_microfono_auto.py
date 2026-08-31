from pathlib import Path
import sys

PATH = Path('index.html')
MARKER = 'CENZONTLE_MIC_AUTO_HOTFIX_20260831'
html = PATH.read_text(encoding='utf-8')
original = html

required = [
    'Mic.iniciar', 'Mic.vivo', 'Mic.liberar', 'MicUI', 'AyudaMic',
    'id="mic-global"', 'const MicAuto', 'MicAuto.init', 'MicAuto.alEntrar'
]
missing = [x for x in required if x not in html]
print('Dependencias faltantes:', missing)
if missing:
    print('ABORTADO: no se toca index.html porque el subsistema actual no coincide.')
    sys.exit(41)
if MARKER in html:
    print('ABORTADO: existe un marcador previo; el workflow debe revertirlo antes de aplicar el parche correcto.')
    sys.exit(42)

js = r'''
<script id="cenzontle-mic-auto-hotfix">
/* CENZONTLE_MIC_AUTO_HOTFIX_20260831
   Corrige la regresión de navegación de v6.9.1 sin sustituir MicAuto:
   al cambiar .screen.active vuelve a llamar MicAuto.alEntrar(). */
(() => {
  const ctl = () => {
    try { return (typeof MicAuto !== 'undefined' && MicAuto) ? MicAuto : null; }
    catch (_) { return null; }
  };
  let ultimoId = null;
  let pendiente = false;
  const sincronizar = () => {
    if (pendiente) return;
    pendiente = true;
    queueMicrotask(() => {
      pendiente = false;
      const c = ctl();
      const activa = document.querySelector('.screen.active');
      const id = activa ? activa.id : '';
      if (!c || !id || typeof c.alEntrar !== 'function' || id === ultimoId) return;
      ultimoId = id;
      Promise.resolve(c.alEntrar(id)).catch(() => {});
      try { if (typeof c.pintar === 'function') c.pintar(); } catch (_) {}
    });
  };
  const iniciar = () => {
    const c = ctl();
    if (!c) return;
    /* Refuerzo de arranque: no sustituye el init existente. */
    try {
      if (!window.__cenzontleMicAutoHotfixInit && typeof c.init === 'function') {
        window.__cenzontleMicAutoHotfixInit = true;
        Promise.resolve(c.init()).catch(() => {});
      }
    } catch (_) {}
    sincronizar();
    const obs = new MutationObserver(cambios => {
      if (cambios.some(m => m.type === 'attributes' && m.attributeName === 'class')) sincronizar();
    });
    document.querySelectorAll('.screen').forEach(el =>
      obs.observe(el, {attributes:true, attributeFilter:['class']})
    );
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) { ultimoId = null; sincronizar(); }
    });
  };
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', iniciar, {once:true});
  else iniciar();
})();
</script>
'''

pos = html.rfind('</body>')
if pos < 0:
    print('ABORTADO: no se encontró el cierre real </body>.')
    sys.exit(43)

# Seguridad: el cierre usado debe estar prácticamente al final del documento, no dentro
# de una cadena HTML generada por una función intermedia.
if len(html) - pos > 1000:
    print('ABORTADO: el último </body> está demasiado lejos del final del archivo.')
    sys.exit(44)

html = html[:pos] + js + '\n' + html[pos:]
if html.count(MARKER) != 1:
    print('ABORTADO: el marcador no quedó exactamente una vez.')
    sys.exit(45)

PATH.write_text(html, encoding='utf-8')
delta = len(html.encode('utf-8')) - len(original.encode('utf-8'))
print('Bytes añadidos:', delta)
print('Posición del cierre real:', pos, 'de', len(original))
if not (0 < delta < 6000):
    PATH.write_text(original, encoding='utf-8')
    print('ABORTADO: tamaño de cambio fuera del límite de seguridad.')
    sys.exit(46)
