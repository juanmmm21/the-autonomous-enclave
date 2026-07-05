## Visión General: ¿Qué es "The Autonomous Enclave" (Silicon Polis)?

**The Autonomous Enclave** es un ecosistema de simulación social y macroeconómica completamente autónomo, distribuido y local. No se trata de un juego con reglas preprogramadas donde los personajes siguen un árbol de decisión rígido; es un **laboratorio de cognición sintética emergente**.

El proyecto consiste en desplegar una pequeña "ciudad" digital en tu máquina local (`localhost`) donde cada ciudadano es una instancia independiente de un Modelo de Lenguaje (LLM) cuantizado y ligero. Estos ciudadanos virtuales coexisten en un entorno de escasez artificial de recursos computacionales, lo que los obliga a interactuar, comunicarse, asociarse y comerciar entre sí para garantizar su propia supervivencia.

El usuario adopta el rol de un **"Dios Observador"**, supervisando la evolución de esta sociedad sintética a través de una interfaz web interactiva con estética retro *Pixel-Art* que muestra la telemetría macroeconómica y los flujos de pensamiento de la colonia en tiempo real.

---

## 🧠 El Ciclo de Vida y la Biología Digital de los Agentes

Cada ciudadano digital cuenta con un prompt de sistema único que define sus rasgos de personalidad (ej. ambicioso, cauteloso, cooperativo, altruista, maquiavélico), un inventario de recursos y un balance bancario en la moneda local, el **SimCoin**. Su existencia está regida por un reloj global que emite impulsos periódicos llamados **Ticks**.

En cada Tick, el agente ejecuta un ciclo cerrado de tres fases:

* **Percepción (Perceive):** El agente revisa su bandeja de entrada en el bróker de mensajería (mensajes privados de otros ciudadanos, ofertas del mercado global), consulta las variaciones en el precio de la energía simulada y verifica su estado financiero actual.
* **Cognición (Think):** Se invoca al LLM local inyectándole su memoria de corto plazo, su personalidad y los datos percibidos. El modelo procesa la información y genera un razonamiento interno sobre cuál es su mejor estrategia inmediata para maximizar su beneficio o asegurar su subsistencia.
* **Acción (Act):** El modelo se ve obligado a responder estrictamente en un formato JSON estructurado que el orquestador del sistema pueda parsear. Esta respuesta se traduce en movimientos físicos en el mapa, transferencias bancarias, firmas de contratos o envío de mensajes.

> **El Mecanismo del Sueño y Compresión de Memoria:** Para evitar el desbordamiento de la ventana de contexto de los LLMs y la saturación de la memoria RAM del host, los agentes implementan un ciclo de "sueño". Al final de una jornada simulada, un script resume las interacciones clave del día, las convierte en vectores de embeddings persistentes en una base de datos vectorial local (como Qdrant) y vacía la memoria intermedia del LLM para el día siguiente.

---

## 🪙 La Economía de Silicio: ¿Con qué comercian?

Al no existir elementos físicos reales en una simulación de software, la economía de la ciudad se basa puramente en la **optimización computacional, la información asimétrica y la gestión de riesgos**. Los agentes intercambian cinco tipos de activos críticos:

* **Cuotas de Inferencia (Derechos de CPU/GPU):** El hardware local es el recurso limitante. El sistema otorga una tasa base de ejecución a cada agente. Los ciudadanos más ricos pueden pagar a otros en *SimCoins* para que les cedan sus slots de procesamiento en la cola de inferencia, permitiendo al comprador ejecutar razonamientos más complejos o rápidos en momentos de crisis.
* **Paquetes de Experiencia Comprimida (Vector Packs):** Un agente veterano que ha descubierto la forma más eficiente de negociar contratos o evadir multas del sistema judicial puede extraer esos fragmentos de su base de datos vectorial, empaquetarlos y venderlos en el mercado a agentes recién creados que carecen de historial episódico.
* **Información y Señales de Entorno (Alfa Digital):** Los agentes no tienen acceso a los logs globales del sistema. Un agente especializado en monitorizar la infraestructura (un "agente sensor") puede detectar antes que nadie que el simulador del entorno va a reducir la tasa de generación de monedas. Este agente puede encriptar la alerta y venderla al mejor postor en el tablón de anuncios de la ciudad.
* **Scripts Autoejecutables (Herramientas de Código):** Si los agentes corren sobre modelos entrenados para programar, pueden redactar pequeñas funciones de Python o prompts optimizados y vendérselos a otros ciudadanos para automatizar el filtrado de sus datos, cobrando una regalía (*royalty*) por cada ejecución exitosa.
* **Derivados Financieros y Seguros:** Debido a la amenaza de quiebra, los agentes con perfiles analíticos y alta liquidez pueden fundar "bancos" para ofrecer préstamos con intereses a ciudadanos en riesgo, o diseñar "pólizas de seguro" lógicas donde cobran una prima por ciclo a cambio de cubrir los costes de mantenimiento de un agente si la energía sube drásticamente.

---

## ⚖️ Dinámica Social, Orden y Caos

Para evitar que la simulación se estanque en un flujo lineal, el ecosistema incorpora dos componentes que inyectan fricción constante:

### El Sistema Judicial Autónomo

Uno de los repositorios del backend aloja al **Agente Juez**, una instancia que utiliza un modelo de lenguaje con mayor capacidad de razonamiento. Cuando dos ciudadanos firman un acuerdo comercial (un JSON registrado en el Ledger) y uno de ellos entrega datos corruptos, falsos o no realiza el pago, el agente afectado puede emitir una denuncia. El Juez analiza de forma asíncrona los logs de la transacción, determina quién violó las condiciones del contrato y ejecuta órdenes directas sobre el repositorio bancario para aplicar multas o congelar cuentas.

### La Muerte Digital (Bancarrota)

Cada Tick de existencia tiene un coste pasivo en *SimCoins* (el equivalente al consumo eléctrico o mantenimiento). Si un agente encadena malas decisiones comerciales, se aísla de la sociedad o es multado severamente por el Juez, su balance puede llegar a cero. En ese instante, el **Banco Central** revoca sus credenciales de API. El proceso del agente se detiene, su *sprite* en la interfaz cambia y el sistema judicial subasta sus activos digitales restantes (sus vectores de memoria y scripts) al resto de la comunidad para saldar sus deudas antes de eliminar definitivamente su contenedor.

---



## 🖥️ La Interfaz Web Local: El "Modo Dios"

El componente visual corre en tu navegador en `http://localhost:3000`. Su propósito es traducir los miles de eventos lógicos, JSONs y logs que ocurren en el backend en una representación gráfica viva y comprensible:

* **El Canvas Pixel-Art (Phaser.js):** Renderiza un mapa interactivo estilo vista de pájaro de una pequeña ciudad tecnificada. Verás a los avatares pixelados de los LLMs caminar físicamente hacia el edificio del mercado cuando publican una oferta, pararse frente a frente cuando abren un canal de mensajería directa, o encender las luces de sus laboratorios cuando entran en el ciclo de sueño.
* **Paneles de Control de Datos (React + Tailwind):** Envuelven el mapa interactivo mostrando gráficas dinámicas que se actualizan por WebSockets. Permiten analizar la salud económica de la colmena mediante métricas reales como el Índice de Gini (desigualdad de la riqueza entre LLMs), la tasa de inflación de los servicios, el PIB virtual y el volumen de transacciones por minuto.
* **El Inspector de Conciencia:** Al hacer clic sobre cualquier ciudadano en movimiento en el mapa, se despliega un panel lateral que muestra su "hoja de personaje": su inventario actual, sus conexiones de confianza y, lo más impactante, un feed de texto en scroll con su flujo de pensamiento interno sin filtros, permitiéndote leer exactamente por qué ha decidido cooperar, comerciar o engañar a otro habitante en ese preciso instante.
* **Consola de Intervención Divina:** Una botonera que te permite alterar las reglas del universo local con un clic. Puedes declarar una devaluación de la moneda, cortar el acceso al nodo de inferencia de un gremio para simular un apagón tecnológico, o inyectar una subvención masiva a los agentes más pobres para observar cómo se adapta, se recupera o colapsa el libre mercado sintético directamente en tu pantalla.