/**
 * Diagnóstico CON sesión iniciada: reproduce el estado real del navegador.
 *
 *   node scripts/diagnose-auth.mjs                 (va a /app/mapa)
 *   node scripts/diagnose-auth.mjs ingresar        (va a /ingresar con sesión)
 *
 * Credenciales por variable de entorno:
 *   EMAIL=... CLAVE=... node scripts/diagnose-auth.mjs
 */
import { chromium } from 'playwright'

function normalizarRuta(bruto) {
  let r = bruto ?? '/app/mapa'
  const mangled = r.match(/^[A-Za-z]:[\\/].*?[\\/]Git(?:[\\/](.*))?$/)
  if (mangled) r = '/' + (mangled[1] ?? '').replace(/\\/g, '/')
  if (!r.startsWith('/')) r = '/' + r
  return r
}

const RUTA = normalizarRuta(process.argv[2])
const BASE = process.env.BASE_URL ?? 'http://localhost:3000'
const API = process.env.API_URL ?? 'http://localhost:8000/api/v1'
const EMAIL = process.env.EMAIL ?? 'admin@sigmogps.app'
const CLAVE = process.env.CLAVE ?? 'Sigmo#GPS2026!ok'

const errores = []
const fallos = []
const navegaciones = []

const navegador = await chromium.launch()
const contexto = await navegador.newContext()
const pagina = await contexto.newPage()

pagina.on('console', (m) => {
  if (m.type() === 'error') errores.push(`[console] ${m.text()}`)
})
pagina.on('pageerror', (e) => errores.push(`[pageerror] ${e.message}\n${e.stack ?? ''}`))
pagina.on('requestfailed', (r) =>
  fallos.push(`${r.method()} ${r.url()} -> ${r.failure()?.errorText}`),
)
pagina.on('response', (r) => {
  if (r.status() >= 400) fallos.push(`${r.status()} ${r.request().method()} ${r.url()}`)
})
pagina.on('framenavigated', (f) => {
  if (f === pagina.mainFrame()) navegaciones.push(f.url())
})

// 1. Iniciar sesión contra el API para quedar con las mismas cookies.
console.log(`\n── login contra ${API} ──`)
const login = await contexto.request.post(`${API}/auth/login`, {
  data: { email: EMAIL, password: CLAVE },
})
console.log(`  estado: ${login.status()}`)
if (!login.ok()) {
  console.log('  cuerpo: ' + (await login.text()).slice(0, 300))
  console.log('\n  No se pudo iniciar sesión. Revisa EMAIL y CLAVE.\n')
  await navegador.close()
  process.exit(1)
}
const cookies = await contexto.cookies()
console.log('  cookies: ' + cookies.map((c) => c.name).join(', '))

// 2. Visitar la ruta con sesión activa.
const url = BASE + RUTA
console.log(`\n→ ${url}  (con sesión)\n`)
await pagina.goto(url, { waitUntil: 'domcontentloaded' })
const antes = (await pagina.locator('body').innerText().catch(() => '')).trim()
await pagina.waitForTimeout(9000)
const despues = (await pagina.locator('body').innerText().catch(() => '')).trim()

const resumen = (t) => (t ? t.replace(/\s+/g, ' ').slice(0, 220) : '(VACÍO)')

console.log('── contenido al cargar ──')
console.log('  ' + resumen(antes))
console.log('\n── contenido 9 s después ──')
console.log('  ' + resumen(despues))
console.log('\n── url final ──')
console.log('  ' + pagina.url())
console.log('\n── navegaciones ──')
navegaciones.forEach((n) => console.log('  ' + n))
console.log('\n── errores de javascript ──')
console.log(errores.length ? errores.map((e) => '  ' + e).join('\n') : '  ninguno')
console.log('\n── peticiones fallidas ──')
console.log(fallos.length ? fallos.map((f) => '  ' + f).join('\n') : '  ninguna')
console.log('\n── veredicto ──')
console.log(despues ? '  la página tiene contenido' : '  LA PÁGINA QUEDÓ EN BLANCO')
console.log()

await navegador.close()
