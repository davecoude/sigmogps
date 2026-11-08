/**
 * Bucle de diagnóstico del vínculo conductor-vehículo.
 *
 *   node scripts/diagnose-bind.mjs
 *
 * Mide, contra el API y sin navegador, cuánto tarda en reflejarse un
 * bind/unbind. Si el API responde al instante, el bug está en la interfaz.
 *
 * Variables: API_URL, EMAIL, CLAVE
 */

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1'
const EMAIL = process.env.EMAIL ?? 'admin@sigmogps.app'
const CLAVE = process.env.CLAVE ?? 'Sigmo#GPS2026!ok'

const SONDEOS = 40
const INTERVALO = 500

let cookies = ''
let csrf = ''

function recogerCookies(res) {
  const crudas = res.headers.getSetCookie?.() ?? []
  for (const c of crudas) {
    const [par] = c.split(';')
    const [k, v] = par.split('=')
    cookies = cookies
      .split('; ')
      .filter((x) => x && !x.startsWith(`${k}=`))
      .concat(`${k}=${v}`)
      .join('; ')
    if (k === 'sigmogps_csrf') csrf = v
  }
}

async function api(ruta, opciones = {}) {
  const res = await fetch(API + ruta, {
    ...opciones,
    headers: {
      'Content-Type': 'application/json',
      Cookie: cookies,
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      ...(opciones.headers ?? {}),
    },
  })
  recogerCookies(res)
  const texto = await res.text()
  let cuerpo = null
  try { cuerpo = texto ? JSON.parse(texto) : null } catch { cuerpo = texto }
  return { status: res.status, cuerpo }
}

const esperar = (ms) => new Promise((r) => setTimeout(r, ms))

// ── 1. sesión ──
console.log('\n── login ──')
const login = await api('/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email: EMAIL, password: CLAVE }),
})
console.log(`  estado: ${login.status}`)
if (login.status !== 200) {
  console.log('  ' + JSON.stringify(login.cuerpo))
  process.exit(1)
}

// ── 2. elegir conductor y vehículo ──
const { cuerpo: conductores } = await api('/drivers')
const { cuerpo: pagina } = await api('/vehicles?page_size=5')
const vehiculos = pagina?.items ?? []

if (!conductores?.length || !vehiculos.length) {
  console.log('\n  Hacen falta al menos un conductor y un vehículo.')
  process.exit(1)
}

const conductor = conductores.find((d) => !d.bound_unit_id) ?? conductores[0]
const unidad = vehiculos[0]

console.log('\n── sujetos ──')
console.log(`  conductor: ${conductor.name} (id ${conductor.id})`)
console.log(`  vínculo actual: ${conductor.bound_unit_id ?? 'ninguno'}`)
console.log(`  unidad destino: ${unidad.display_name} (id ${unidad.id})`)

/** Relee la lista hasta que el conductor tenga el bu esperado. */
async function esperarVinculo(esperado) {
  const t0 = Date.now()
  for (let i = 0; i < SONDEOS; i++) {
    const { cuerpo } = await api('/drivers')
    const actual = (cuerpo ?? []).find((d) => d.id === conductor.id)
    const bu = actual?.bound_unit_id ?? null
    if (bu === esperado) {
      return { ok: true, ms: Date.now() - t0, sondeos: i + 1 }
    }
    await esperar(INTERVALO)
  }
  return { ok: false, ms: Date.now() - t0, sondeos: SONDEOS }
}

// ── 3. vincular ──
console.log('\n── POST /drivers/:id/bind ──')
const bind = await api(`/drivers/${conductor.id}/bind`, {
  method: 'POST',
  body: JSON.stringify({ unit_id: unidad.id }),
})
console.log(`  estado: ${bind.status}`)
if (bind.status >= 400) console.log('  ' + JSON.stringify(bind.cuerpo))

const rVincular = await esperarVinculo(unidad.id)
console.log(
  rVincular.ok
    ? `  ✓ reflejado tras ${rVincular.ms} ms (${rVincular.sondeos} lectura${rVincular.sondeos > 1 ? 's' : ''})`
    : `  ✗ NO se reflejó en ${rVincular.ms} ms`,
)

await esperar(1000)

// ── 4. desvincular ──
console.log('\n── POST /drivers/:id/unbind ──')
const unbind = await api(`/drivers/${conductor.id}/unbind`, {
  method: 'POST',
  body: JSON.stringify({ unit_id: unidad.id }),
})
console.log(`  estado: ${unbind.status}`)
if (unbind.status >= 400) console.log('  ' + JSON.stringify(unbind.cuerpo))

const rQuitar = await esperarVinculo(null)
console.log(
  rQuitar.ok
    ? `  ✓ reflejado tras ${rQuitar.ms} ms (${rQuitar.sondeos} lectura${rQuitar.sondeos > 1 ? 's' : ''})`
    : `  ✗ NO se reflejó en ${rQuitar.ms} ms`,
)

// ── veredicto ──
console.log('\n── veredicto ──')
const inmediato = (r) => r.ok && r.sondeos === 1
if (inmediato(rVincular) && inmediato(rQuitar)) {
  console.log('  VERDE: el API refleja el cambio en la primera lectura.')
  console.log('  Si la interfaz aún no lo muestra, el bug es del frontend.')
} else if (rVincular.ok && rQuitar.ok) {
  console.log(`  El API tarda: ${rVincular.sondeos} y ${rQuitar.sondeos} lecturas.`)
  console.log('  => el bug está en el BACKEND o en la propagación de Wialon.')
} else {
  console.log('  El API no refleja el cambio.')
  console.log('  => el bug está en el BACKEND.')
}
console.log()
