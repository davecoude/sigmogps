/**
 * Dónde se va el tiempo en cada endpoint.
 *
 *   node scripts/diagnose-latencia.mjs
 *   API_URL=https://sigmogps.onrender.com/api/v1 node scripts/diagnose-latencia.mjs
 *
 * Separa el costo de la aplicación, el de la base y el de Wialon.
 */
const API = process.env.API_URL ?? 'http://localhost:8000/api/v1'
const EMAIL = process.env.EMAIL ?? 'admin@sigmogps.app'
const CLAVE = process.env.CLAVE ?? 'Sigmo#GPS2026!ok'

let cookies = ''
let csrf = ''

function recoger(res) {
  for (const c of res.headers.getSetCookie?.() ?? []) {
    const [k, v] = c.split(';')[0].split('=')
    cookies = cookies.split('; ').filter((x) => x && !x.startsWith(`${k}=`)).concat(`${k}=${v}`).join('; ')
    if (k === 'sigmogps_csrf') csrf = v
  }
}

async function medir(etiqueta, ruta, opciones = {}, repeticiones = 5) {
  const tiempos = []
  for (let i = 0; i < repeticiones; i++) {
    const t0 = performance.now()
    const res = await fetch(API + ruta, {
      ...opciones,
      headers: {
        'Content-Type': 'application/json',
        Cookie: cookies,
        ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      },
    })
    await res.text()
    recoger(res)
    tiempos.push(performance.now() - t0)
  }
  tiempos.sort((a, b) => a - b)
  const mediana = tiempos[Math.floor(tiempos.length / 2)]
  console.log(
    `  ${etiqueta.padEnd(34)} mediana ${mediana.toFixed(0).padStart(5)} ms   ` +
    `min ${tiempos[0].toFixed(0)}  max ${tiempos.at(-1).toFixed(0)}`,
  )
  return mediana
}

console.log(`\nMidiendo contra ${API}\n`)

console.log('── sin base de datos ──')
const salud = await medir('GET /health', '/health')

console.log('\n── con base de datos ──')
await fetch(API + '/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: EMAIL, password: CLAVE }),
}).then((r) => { recoger(r); return r.text() })

const me = await medir('GET /auth/me', '/auth/me')
const usuarios = await medir('GET /users', '/users')
const login = await medir(
  'POST /auth/login (Argon2)',
  '/auth/login',
  { method: 'POST', body: JSON.stringify({ email: EMAIL, password: CLAVE }) },
  3,
)

console.log('\n── con Wialon ──')
const resumen = await medir('GET /vehicles/summary (cacheado)', '/vehicles/summary')
const conductores = await medir('GET /drivers', '/drivers')

console.log('\n── desglose ──')
console.log(`  aplicación sola        ${salud.toFixed(0)} ms`)
console.log(`  + una consulta a Neon  ${(me - salud).toFixed(0)} ms`)
console.log(`  + Argon2 y auditoría   ${(login - me).toFixed(0)} ms`)
console.log(`  + Wialon               ${(conductores - usuarios).toFixed(0)} ms`)
console.log()
