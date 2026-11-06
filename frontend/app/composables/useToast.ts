/** Retroalimentación de toda acción (UX-04). */
export interface Toast {
  id: number
  tono: 'exito' | 'error' | 'aviso'
  mensaje: string
}

let siguienteId = 0

export function useToast() {
  const toasts = useState<Toast[]>('toasts', () => [])

  function mostrar(tono: Toast['tono'], mensaje: string) {
    const id = ++siguienteId
    toasts.value = [...toasts.value, { id, tono, mensaje }]
    setTimeout(() => cerrar(id), tono === 'error' ? 7000 : 4000)
  }

  function cerrar(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return {
    toasts,
    cerrar,
    exito: (m: string) => mostrar('exito', m),
    error: (m: string) => mostrar('error', m),
    aviso: (m: string) => mostrar('aviso', m),
  }
}
