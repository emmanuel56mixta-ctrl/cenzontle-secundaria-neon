from pathlib import Path
import sys

PATH = Path('index.html')
MARKER = 'CENZONTLE_MIC_AUTO_HOTFIX_20260831'

html = PATH.read_text(encoding='utf-8')
original = html

checks = {
    'Mic.iniciar': 'Mic.iniciar' in html,
    'Mic.vivo': 'Mic.vivo' in html,
    'Mic.liberar': 'Mic.liberar' in html,
    'MicUI': 'MicUI' in html,
    'AyudaMic': 'AyudaMic' in html,
    'mic-global': 'id="mic-global"' in html,
    'MicAuto existente': ('const MicAuto' in html or 'let MicAuto' in html or 'var MicAuto' in html),
    'MicAuto.init': 'MicAuto.init' in html,
    'MicAuto.alEntrar': 'MicAuto.alEntrar' in html,
}
print('Diagnóstico previo:', checks)

required = ['Mic.iniciar', 'Mic.vivo', 'Mic.liberar', 'MicUI', 'AyudaMic', 'id="mic-global"']
missing = [x for x in required if x not in html]
if missing:
    print('ABORTADO: faltan dependencias del subsistema de micrófono:', ', '.join(missing))
    sys.exit(41)

if MARKER in html:
    print('La reparación ya está presente; no se modifica index.html.')
    sys.exit(0)

has_auto = checks['MicAuto existente']

if has_auto:
    js = r'''
<script id="cenzontle-mic-auto-hotfix">
/* CENZONTLE_MIC_AUTO_HOTFIX_20260831
   Reparación de regresión v6.9.1: conserva MicAuto y garantiza que el cambio de
   .screen.active reactive alEntrar(). No altera actividades, estilos, assets ni rutas. */
(() => {
  const obtenerControlador = () => {
    try { return (typeof MicAuto !== 'undefined' && MicAuto) ? MicAuto : null; }
    catch (_) { return null; }
  };
  let ultimoId = null;
  let programado = false;
  const sincronizar = () => {
    if (programado) return;
    programado = true;
    queueMicrotask(() => {
      programado = false;
      const ctl = obtenerControlador();
      const activa = document.querySelector('.screen.active');
      const id = activa ? activa.id : '';
      if (!ctl || !id || typeof ctl.alEntrar !== 'function' || id === ultimoId) return;
      ultimoId = id;
      Promise.resolve(ctl.alEntrar(id)).catch(() => {});
      try { if (typeof ctl.pintar === 'function') ctl.pintar(); } catch (_) {}
    });
  };
  const arrancar = () => {
    const ctl = obtenerControlador();
    if (!ctl) return;
    /* MicAuto.init() es idempotente en lo esencial; lo invocamos sólo si la integración
       actual no dejó constancia de haberlo arrancado en esta pestaña. */
    try {
      if (!window.__cenzontleMicAutoInit && typeof ctl.init === 'function') {
        window.__cenzontleMicAutoInit = true;
        Promise.resolve(ctl.init()).catch(() => {});
      }
    } catch (_) {}
    sincronizar();
    const observer = new MutationObserver(muts => {
      for (const m of muts) {
        if (m.type === 'attributes' && m.attributeName === 'class' &&
            m.target.classList && m.target.classList.contains('screen')) {
          sincronizar();
          break;
        }
      }
    });
    document.querySelectorAll('.screen').forEach(el =>
      observer.observe(el, {attributes:true, attributeFilter:['class']})
    );
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) { ultimoId = null; sincronizar(); }
    });
  };
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', arrancar, {once:true});
  else arrancar();
})();
</script>
'''
else:
    js = r'''
<script id="cenzontle-mic-auto-hotfix">
/* CENZONTLE_MIC_AUTO_HOTFIX_20260831
   Reparación de regresión v6.9.1. Restaura sólo el controlador automático usando
   Mic/MicUI ya presentes. La primera autorización sigue naciendo de un clic del usuario. */
(() => {
  const PANTALLAS_VOZ_HOTFIX = new Set([
    'prim-eco','prim-nota','prim-diccion',
    'sec-afinador','sec-solfeo','sec-grabar','sec-dictado',
    'doc-sesion','doc-conductor','coral-actividad','coral-rutina','dir-vocaliza'
  ]);
  const CLAVE_OK = 'cenzontle:microfono-autorizado';
  const seguro = fn => { try { return fn(); } catch (_) { return undefined; } };
  const refrescarUI = () => seguro(() => {
    if (typeof MicUI !== 'undefined' && MicUI.refrescar) MicUI.refrescar();
  });
  const decir = txt => seguro(() => { if (typeof toast === 'function') toast(txt); });

  const ctl = {
    activado:true,
    pedido:false,
    _ocio:null,
    ESPERA:25000,
    async concedido(){
      if (seguro(() => Mic.vivo())) return true;
      try {
        if (navigator.permissions && navigator.permissions.query) {
          const p = await navigator.permissions.query({name:'microphone'});
          if (p.state === 'granted') return true;
          if (p.state === 'denied') return false;
        }
      } catch (_) {}
      return seguro(() => localStorage.getItem(CLAVE_OK) === '1') === true;
    },
    async alEntrar(id){
      clearTimeout(this._ocio);
      if (!this.activado) return;
      if (!PANTALLAS_VOZ_HOTFIX.has(id)) { this.soltarSiOcioso(); return; }
      if (seguro(() => Mic.vivo())) { this.pintar(); return; }
      const entornoOk = seguro(() =>
        (typeof Entorno === 'undefined' || !Entorno.revisar) ? true : Entorno.revisar().ok
      );
      if (entornoOk === false) return;
      if (!(await this.concedido())) return;
      const ok = await Mic.iniciar();
      if (ok) seguro(() => localStorage.setItem(CLAVE_OK, '1'));
      refrescarUI();
      this.pintar();
    },
    async autorizar(){
      this.activado = true;
      this.pedido = true;
      const ok = await Mic.iniciar();
      if (ok) {
        seguro(() => localStorage.setItem(CLAVE_OK, '1'));
        document.querySelectorAll('.aviso-mic').forEach(a => a.classList.remove('ver'));
        decir('Micrófono autorizado. A partir de ahora se enciende solo en las actividades de voz.');
      } else {
        seguro(() => {
          if (typeof AyudaMic !== 'undefined' && AyudaMic.abrir) AyudaMic.abrir();
        });
      }
      refrescarUI();
      this.pintar();
      return !!ok;
    },
    soltarSiOcioso(){
      clearTimeout(this._ocio);
      this._ocio = setTimeout(() => {
        seguro(() => Mic.liberar());
        this.pintar();
        refrescarUI();
      }, this.ESPERA);
    },
    async tocar(){
      if (this.activado && !(await this.concedido())) {
        await this.autorizar();
        return;
      }
      this.alternar();
    },
    alternar(){
      this.activado = !this.activado;
      if (!this.activado) {
        clearTimeout(this._ocio);
        seguro(() => Mic.liberar());
        decir('Micrófono apagado. Las actividades de voz ofrecerán su alternativa sin micrófono.');
      } else {
        decir('Micrófono automático activo.');
        const a = document.querySelector('.screen.active');
        this.alEntrar(a ? a.id : '');
      }
      this.pintar();
      refrescarUI();
    },
    pintar(){
      const b = document.getElementById('mic-global');
      if (!b) return;
      const vivo = !!seguro(() => Mic.vivo());
      b.classList.toggle('on', vivo);
      b.classList.toggle('off', !this.activado);
      b.setAttribute('aria-pressed', String(this.activado));
      b.setAttribute('aria-label', !this.activado
        ? 'Micrófono apagado. Tocar para permitir que se encienda solo.'
        : vivo ? 'Micrófono encendido. Tocar para apagarlo.'
               : 'Micrófono automático activo, en espera. Tocar para apagarlo.');
      const t = document.getElementById('mic-global-txt');
      if (t) t.textContent = !this.activado
        ? 'Micrófono apagado' : vivo ? 'Micrófono activo' : 'Micrófono automático';
    },
    async init(){
      this.pintar();
      if (await this.concedido()) this.pedido = true;
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          clearTimeout(this._ocio);
          seguro(() => Mic.liberar());
          this.pintar();
        } else {
          const a = document.querySelector('.screen.active');
          if (a) this.alEntrar(a.id);
        }
      });
      this.pintar();
    }
  };

  window.CenzontleMicAuto = ctl;
  let ultimoId = null;
  let programado = false;
  const sincronizar = () => {
    if (programado) return;
    programado = true;
    queueMicrotask(() => {
      programado = false;
      const activa = document.querySelector('.screen.active');
      const id = activa ? activa.id : '';
      if (!id || id === ultimoId) return;
      ultimoId = id;
      Promise.resolve(ctl.alEntrar(id)).catch(() => {});
    });
  };
  const arrancar = () => {
    ctl.init().catch(() => {});
    sincronizar();
    const boton = document.getElementById('mic-global');
    if (boton && !boton.dataset.hotfixMic) {
      boton.dataset.hotfixMic = '1';
      boton.addEventListener('click', ev => {
        ev.stopPropagation();
        ctl.tocar().catch(() => {});
      }, true);
    }
    const observer = new MutationObserver(muts => {
      for (const m of muts) {
        if (m.type === 'attributes' && m.attributeName === 'class' &&
            m.target.classList && m.target.classList.contains('screen')) {
          sincronizar();
          break;
        }
      }
    });
    document.querySelectorAll('.screen').forEach(el =>
      observer.observe(el, {attributes:true, attributeFilter:['class']})
    );
  };
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', arrancar, {once:true});
  else arrancar();
})();
</script>
'''

if '</body>' not in html:
    print('ABORTADO: no se encontró </body>.')
    sys.exit(42)

html = html.replace('</body>', js + '\n</body>', 1)
if html.count(MARKER) != 1:
    print('ABORTADO: el marcador no quedó exactamente una vez.')
    sys.exit(43)

PATH.write_text(html, encoding='utf-8')
delta = abs(len(html.encode('utf-8')) - len(original.encode('utf-8')))
print('MicAuto preexistente:', has_auto)
print('Bytes añadidos:', delta)
if delta > 16000:
    PATH.write_text(original, encoding='utf-8')
    print('ABORTADO: el cambio excede el límite de seguridad de 16 KB.')
    sys.exit(44)
