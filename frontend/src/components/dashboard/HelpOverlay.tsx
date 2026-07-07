interface HelpOverlayProps {
  open: boolean;
  onClose: () => void;
}

interface HelpSection {
  title: string;
  body: string[];
}

const SECTIONS: HelpSection[] = [
  {
    title: "Qué es esto",
    body: [
      "Silicon Polis es una simulación social y económica: cada ciudadano es un modelo de lenguaje " +
        "con su propia personalidad y balance en SimCoin que percibe, piensa y actúa por su cuenta en " +
        "cada tick, sin guion.",
      "Como Dios Observador puedes mirar cómo emergen la cooperación, el fraude o la desigualdad, e " +
        "intervenir directamente sobre la economía.",
    ],
  },
  {
    title: "Cómo navegar el mapa",
    body: [
      "Arrastra con el puntero para desplazar la cámara por la ciudad.",
      "Usa la rueda del ratón para acercar o alejar el zoom (se centra donde apunta el cursor).",
      "El minimapa de la esquina inferior izquierda muestra toda la ciudad, el rectángulo del " +
        "encuadre actual y un punto de color por ciudadano: haz clic en él para saltar la cámara " +
        "a esa zona.",
      "Haz clic sobre un ciudadano (en el mapa o en el censo del panel lateral) para " +
        "seleccionarlo: se abre su Inspector de Conciencia, con la opción de que la cámara lo " +
        "siga automáticamente.",
      "El tono del mapa oscurece al final de cada día simulado: es el ciclo de sueño en el que " +
        "los ciudadanos consolidan su memoria.",
    ],
  },
  {
    title: "Colores de estado",
    body: [
      "Verde azulado (vivo): el ciudadano actúa con normalidad.",
      "Azul violeta (dormido): consolidando su memoria del día, no se mueve.",
      "Ámbar con anillo pulsante (bancarrota): su balance llegó a cero.",
      "Gris apagado y semitransparente (terminado): su proceso se detuvo.",
    ],
  },
  {
    title: "Los edificios de Silicon Polis",
    body: [
      "Cada activo de la economía de silicio tiene sede física, y varios tipos se repiten por " +
        "distintos barrios de la ciudad.",
      "Mercado: donde los ciudadanos publican y aceptan ofertas de compraventa de cualquier activo.",
      "Banco: el Banco Central, que gestiona balances, coste pasivo por tick y bancarrotas.",
      "Ayuntamiento: sede simbólica del Agente Juez, que arbitra disputas contractuales.",
      "Laboratorio de Vectores: donde se destilan los vector packs, la experiencia comprimida " +
        "que los ciudadanos consolidan al dormir.",
      "Torre de Señales: emisora de señales alfa, los datos de inteligencia de mercado.",
      "Taller de Scripts: forja de code scripts, las herramientas ejecutables de la colonia.",
      "Bolsa de Derivados: parqué de los derivados financieros, apuestas sobre el futuro de la " +
        "economía.",
      "Bloques de Viviendas: barrios residenciales sin función económica, donde la colonia " +
        "simplemente vive.",
    ],
  },
  {
    title: "Panel de telemetría macroeconómica",
    body: [
      "Índice de Gini: desigualdad de la riqueza entre ciudadanos (0 = reparto igualitario, 1 = " +
        "máxima concentración).",
      "Inflación: variación del precio de la energía (el recurso escaso) tick a tick.",
      "PIB virtual: valor total generado por la actividad económica de la colonia.",
      "Transacciones/min: ritmo real de transferencias de SimCoin en la ventana reciente.",
    ],
  },
  {
    title: "Inspector de Conciencia",
    body: [
      "Muestra el balance, la cuota de inferencia, el inventario, los vínculos de confianza con " +
        "otros ciudadanos y un flujo en vivo con el razonamiento interno del ciudadano seleccionado " +
        "en cada tick.",
    ],
  },
  {
    title: "Actividad económica y censo",
    body: [
      "El panel de Actividad económica muestra en vivo las ofertas abiertas del mercado, los " +
        "contratos pendientes o en disputa y los últimos veredictos del Agente Juez (quién fue " +
        "declarado culpable y la multa aplicada).",
      "El Censo lista a todos los ciudadanos con su color de acento, estado y balance, ordenados " +
        "por riqueza; haz clic en cualquiera para seleccionarlo.",
      "Sobre el mapa, un +N/−N SC flotante señala los cambios de balance relevantes de cada " +
        "ciudadano (compras, transferencias, multas o subvenciones).",
    ],
  },
  {
    title: "Consola de Intervención Divina",
    body: [
      "Devaluar SimCoin: reduce a la mitad el balance de todos los ciudadanos.",
      "Apagón de inferencia: corta la cuota de inferencia del ciudadano seleccionado a cero.",
      "Subvencionar agente: añade 100 SimCoin al ciudadano seleccionado.",
      "Shock energético / Abundancia energética: duplica o reduce a la mitad el precio base de la " +
        "energía, con efecto inmediato en la inflación.",
    ],
  },
  {
    title: "Fundición de ciudadanos",
    body: [
      "Crea nuevos ciudadanos en caliente desde el panel lateral: elige nombre, una combinación " +
        "de rasgos de personalidad y un balance inicial opcional. El recién nacido aparece en la " +
        "plaza central al instante y empieza a percibir, pensar y actuar en el siguiente tick.",
    ],
  },
];

/** Modal de ayuda accesible desde el botón "?" del header; se abre solo en la primera visita. */
export function HelpOverlay({ open, onClose }: HelpOverlayProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="help-overlay-title"
      onClick={onClose}
    >
      <div
        className="panel flex max-h-[85vh] w-full max-w-xl flex-col overflow-hidden"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-enclave-edge px-5 py-3">
          <h2 id="help-overlay-title" className="text-sm font-bold uppercase tracking-[0.14em] text-enclave-ink">
            Guía rápida · Silicon Polis
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar ayuda"
            className="flex h-6 w-6 items-center justify-center rounded-sm border border-enclave-edge text-enclave-ink-dim transition-colors hover:border-enclave-danger/50 hover:text-enclave-danger"
          >
            ✕
          </button>
        </header>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          {SECTIONS.map((section) => (
            <section key={section.title}>
              <h3 className="micro-label mb-1.5 text-enclave-accent">{section.title}</h3>
              <div className="space-y-1.5 text-xs leading-relaxed text-enclave-ink-mid">
                {section.body.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <footer className="border-t border-enclave-edge px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded border border-enclave-accent/40 bg-enclave-accent/10 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-enclave-accent transition-colors hover:bg-enclave-accent/20"
          >
            Entendido
          </button>
        </footer>
      </div>
    </div>
  );
}
