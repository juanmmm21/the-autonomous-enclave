# AGENTS.md - Directrices de Flujo de Trabajo y Git

Bienvenido a **the-autonomous-enclave**. Ecosistema de simulación social y macroeconómica autónomo (Silicon Polis): ciudadanos LLM locales que perciben, piensan y actúan en ciclos de tick, comerciando en una economía de escasez computacional bajo la supervisión de un "Dios Observador" a través de una interfaz web.

Como mi copiloto de desarrollo, tu objetivo es guiar el proceso de codificación bajo estándares estrictos de ingeniería, robustez y modularidad, como lo haría un desarrollador senior en una empresa seria.

Este repositorio vive en `github.com/juanmmm21/the-autonomous-enclave`. La carpeta local y el repositorio remoto **siempre** comparten el mismo nombre.

**Antes de empezar:** si existe, lee `PROGRESS.md` para saber qué está hecho y qué toca a continuación. La visión completa del proyecto está en `docs/vision.md`.

---

## 1. Filosofía de Desarrollo Incremental

No se construyen módulos complejos de un solo golpe. El enfoque es estrictamente evolutivo y atómico:

*   **Diseño de interfaces primero:** antes de programar la lógica, se definen los tipos de datos (Dataclasses/Pydantic/Structs/interfaces) y las firmas de las funciones.
*   **Código humano y de producción:** prohibido dejar elipsis (`...`), comentarios tipo `// TODO: implementar después` o funciones vacías. Todo lo que se entrega es funcional y contempla el manejo de excepciones y casos límite.
*   **Comentarios con propósito:** no se comenta lo obvio. Los comentarios explican el **porqué** (una decisión de arquitectura, un truco de rendimiento, un workaround a un bug concreto), nunca el qué.
*   **Simplicidad sobre complejidad:** se evita la sobre-ingeniería. Una solución simple y clara que funciona es mejor que un patrón de diseño complicado que impresiona pero no aporta.
*   **Tipado estricto siempre** que el lenguaje lo permita (type hints en Python, tipos explícitos en TypeScript).

---

## 2. Estrategia de Git y Control de Versiones

Cada sesión de programación se traduce en progreso de Git limpio, reproducible y atómico. Cuantos más commits reales, mejor — reflejan el avance real, no un único volcado de código.

*   **Conventional Commits**, en minúsculas, describiendo la acción exacta:
    *   `feat({{modulo}}):` nueva funcionalidad.
    *   `fix({{modulo}}):` corrección de errores.
    *   `refactor({{modulo}}):` cambios que no alteran el comportamiento.
    *   `docs({{modulo}}):` documentación o comentarios.
    *   `test({{modulo}}):` pruebas.
    *   `chore({{modulo}}):` tareas de mantenimiento (dependencias, configuración, gitignore...).

*   **Autoría exclusiva del usuario:** todos los commits figuran únicamente como autor y committer `juanmmm21 <martoscuevasjuan@gmail.com>`. El asistente/IA **nunca** aparece en la metadata de Git. En cada commit se usa explícitamente:

    ```bash
    git commit --author="juanmmm21 <martoscuevasjuan@gmail.com>" -m "tipo(modulo): mensaje"
    ```

    Sin tocar `git config` global ni local.

*   **Sin trailers de co-autoría de IA** (`Co-authored-by: Claude`, `Co-authored-by: Cursor <cursoragent@cursor.com>`, etc.). Esto es inaceptable. Tras cada commit, verificar con `git log -1 --format=%B`. Si aparece cualquier trailer de este tipo, corregirlo antes de continuar:

    ```bash
    AUTHOR='juanmmm21 <martoscuevasjuan@gmail.com>'
    CLEAN_MSG=$(git log -1 --format=%B | grep -vE '^Co-authored-by:')
    git commit --amend --author="$AUTHOR" -m "$CLEAN_MSG"
    ```

*   **Verificación antes de cada push:**

    ```bash
    git log --format='%B' | grep -c 'Co-authored-by'   # debe ser 0
    git log --format='%an <%ae>' | sort -u              # solo juanmmm21 <martoscuevasjuan@gmail.com>
    ```

*   **Progreso real, no un solo commit gigante:** cada hito lógico (estructura del proyecto, modelos de datos, lógica core, tests, documentación...) es su propio commit. Al terminar el proyecto o una fase relevante, se hace `git push`.

---

## 3. Estructura y Documentación

*   El `README.md` sigue la estructura de `_templates/readme/PROJECT_README_TEMPLATE.md` del ecosistema.
*   Licencia MIT (`juanmmm21`).
*   `.gitignore` cubre ambos stacks (Python en `backend/`, Node en `frontend/`) desde el primer commit.

---

## 4. Protocolo de Respuesta Obligatorio

En cada interacción para escribir o modificar código:

1.  **Contexto del módulo:** en qué parte del proyecto se trabaja y qué archivos/dependencias se ven afectados.
2.  **Explicación de la lógica:** aproximación técnica elegida, de forma concisa.
3.  **Bloques de código limpios:** tipado estricto, control de errores explícito, nombres descriptivos en inglés, comentarios estratégicos en español.
4.  **Commit sugerido o ejecutado:** mensaje exacto siguiendo Conventional Commits.
