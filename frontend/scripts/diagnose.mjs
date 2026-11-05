/**
 * Bucle de diagnóstico del frontend.
 *
 *   node scripts/diagnose.mjs /ingresar
 *   node scripts/diagnose.mjs /app/mapa
 *
 * Carga la ruta en un navegador real y reporta exactamente lo que pasa:
 * errores de JavaScript, peticiones fallidas, redirecciones y si el contenido
 * quedó en pantalla o desapareció tras la hidratación.
 */
import { chromium } from 'playwright'

// Git Bash en Windows convierte un argumento que empieza en "/" a una ruta
// de Windows (C:/Program Files/Git/...). Se deshace esa conversión.
function normalizarRuta(bruto) {
  let r = bruto ?? '/ingresar'
  const mangled = r.match(/^[A-Za-z]:[\\/].*?[\\/]Git(?:[\\/](.*))?$/)
  if (mangled) r = '/' + (mangled[1] ?? '').replace(/\\/g, '/')
  if (!r.startsWith('/')) r = '/' + r
  return r
}

const RUTA = normalizarRuta(process.argv[2])
const BASE = process.env.BASE_URL ?? 'http://localhost:3000'
const url = BASE + RUTA

const errores = []
const fallos = []
const navegaciones = []

const navegador = await chromium.launch()
const contexto = await navegador.newContext()
const pagina = await contexto.newPage()

pagina.on('console', (m) => {
  if (m.type() === 'error') errores.push(`[console] ${m.text()}`)
})
pagina.on('pageerror', (e) => errores.push(`[pageerror] ${e.message}`))
pagina.on('requestfailed', (r) =>
  fallos.push(`${r.method()} ${r.url()} -> ${r.failure()?.errorText}`),
)
pagina.on('response', (r) => {
  if (r.status() >= 400) fallos.push(`${r.status()} ${r.request().method()} ${r.url()}`)
})
pagina.on('framenavigated', (f) => {
  if (f === pagina.mainFrame()) navegaciones.push(f.url())
})

console.log(`\n→ ${url}\n`)

await pagina.goto(url, { waitUntil: 'domcontentloaded' })

// Instantánea inmediata: lo que pintó el servidor.
const antes = (await pagina.locator('body').innerText().catch(() => '')).trim()

await pagina.waitForTimeout(3000)

// Instantánea después de la hidratación y de cualquier redirección.
const despues = (await pagina.locator('body').innerText().catch(() => '')).trim()
const urlFinal = pagina.url()

const resumen = (t) => (t ? t.replace(/\s+/g, ' ').slice(0, 160) : '(VACÍO)')

console.log('── contenido al cargar ──')
console.log('  ' + resumen(antes))
console.log('\n── contenido 3 s después ──')
console.log('  ' + resumen(despues))

console.log('\n── url final ──')
console.log('  ' + urlFinal)
if (urlFinal !== url) console.log('  ⚠ HUBO REDIRECCIÓN')

console.log('\n── navegaciones ──')
navegaciones.forEach((n) => console.log('  ' + n))

console.log('\n── errores de javascript ──')
console.log(errores.length ? errores.map((e) => '  ' + e).join('\n') : '  ninguno')

console.log('\n── peticiones fallidas ──')
console.log(fallos.length ? fallos.map((f) => '  ' + f).join('\n') : '  ninguna')

// Visibilidad real: estar en el DOM no es estar en pantalla.
const campos = ['#email', '#password']
console.log('\n── campos del formulario ──')
for (const sel of campos) {
  const loc = pagina.locator(sel)
  if ((await loc.count()) === 0) {
    console.log(`  ${sel}: NO EXISTE`)
    continue
  }
  const visible = await loc.isVisible()
  const caja = await loc.boundingBox()
  let tapado = 'n/d'
  if (caja) {
    const x = caja.x + caja.width / 2
    const y = caja.y + caja.height / 2
    tapado = await pagina.evaluate(
      ([x, y, sel]) => {
        const arriba = document.elementFromPoint(x, y)
        const objetivo = document.querySelector(sel)
        if (!arriba || !objetivo) return 'sin elemento'
        return arriba === objetivo || objetivo.contains(arriba)
          ? 'alcanzable'
          : `TAPADO POR <${arriba.tagName.toLowerCase()} class="${arriba.className}">`
      },
      [x, y, sel],
    )
  }
  console.log(`  ${sel}: visible=${visible}  ${tapado}`)
}

console.log('\n── veredicto ──')
if (!despues) console.log('  LA PÁGINA QUEDÓ EN BLANCO')
else if (antes && !despues) console.log('  EL CONTENIDO DESAPARECIÓ TRAS HIDRATAR')
else console.log('  la página tiene contenido')
console.log()

await navegador.close()
