# DEVELOPMENT LOG

## 2026-04-27

### Cambio realizado
- Bootstrap inicial del proyecto VoidMiner v0.1 (estructura, metadatos y documentación base).

### Motivo
- Establecer base modular para implementar el flujo de descubrimiento de parámetros ocultos.

### Archivos modificados
- README.md
- pyproject.toml
- requirements.txt
- CHANGELOG.md
- ROADMAP.md
- TODO.md

### Riesgos o deuda técnica
- Pendiente implementar motores core, scoring y validación con tests.

### Próximo paso
- Implementar modelos Pydantic y contratos de datos.

## 2026-04-27 (Bloque 2)

### Cambio realizado
- Implementación de modelos Pydantic para findings, evidence, baseline, diffs y reportes.

### Motivo
- Definir un contrato de datos consistente para core, scoring y output.

### Archivos modificados
- voidminer/models.py
- voidminer/config.py

### Riesgos o deuda técnica
- Campos de modelo podrían ampliarse cuando se habiliten modos JSON/header/form.

### Próximo paso
- Implementar requester HTTP, normalización y baseline.

## 2026-04-27 (Bloques 3, 4 y 5)

### Cambio realizado
- Implementados requester con rate limit/timeout/proxy/TLS, normalizador de ruido, baseline x3, motor de diff, scorer y modo query miner con canary.
- Implementada CLI MVP con flags requeridas.

### Motivo
- Cubrir el flujo completo de descubrimiento de parámetros ocultos en query para v0.1.

### Archivos modificados
- voidminer/core/requester.py
- voidminer/core/normalizer.py
- voidminer/core/baseline.py
- voidminer/core/injector.py
- voidminer/core/diff_engine.py
- voidminer/core/scorer.py
- voidminer/modes/query_miner.py
- voidminer/cli.py
- voidminer/main.py
- voidminer/utils/*

### Riesgos o deuda técnica
- `--threads` queda reservado para paralelización futura.
- Detección de errores técnicos y headers interesantes es heurística inicial.

### Próximo paso
- Implementar reportes JSON/Markdown y cobertura de tests.

## 2026-04-27 (Bloques 6, 7 y 8)

### Cambio realizado
- Implementados exportadores JSON/Markdown y consola centralizada.
- Añadidos tests unitarios base para normalizer, diff, scorer y burp parser placeholder.
- Actualizados documentos de soporte y listas de tareas.

### Motivo
- Dejar MVP utilizable con resultados persistentes y validación técnica inicial.

### Archivos modificados
- voidminer/output/json_report.py
- voidminer/output/markdown_report.py
- voidminer/output/console.py
- tests/test_normalizer.py
- tests/test_diff_engine.py
- tests/test_scorer.py
- tests/test_burp_parser.py
- TODO.md

### Riesgos o deuda técnica
- Entorno actual no dispone de `pip`/`pytest`, no se pudo ejecutar la batería localmente.

### Próximo paso
- Instalar toolchain Python en entorno objetivo y ejecutar `pytest`.

## 2026-04-27 (Hardening v0.1.1)

### Cambio realizado
- Activada paralelización real con `--threads` en query mining usando `ThreadPoolExecutor`.
- Baseline robustecido con medianas (content-length y timing) y selección de hash dominante.
- Añadidos tests de CLI para validación de entrada y ejecución con URL única.
- Añadido test de baseline para estabilidad ante outliers.

### Motivo
- Reducir tiempo de escaneo en objetivos con wordlists grandes.
- Disminuir falsos positivos por respuestas variables y picos de latencia.
- Aumentar confianza del flujo CLI con tests de regresión.

### Archivos modificados
- voidminer/modes/query_miner.py
- voidminer/core/baseline.py
- voidminer/cli.py
- tests/test_cli.py
- tests/test_baseline.py

### Riesgos o deuda técnica
- La paralelización comparte un `Requester` con rate limit global: funcional para MVP, pero puede migrarse a pool de clientes por worker para throughput más fino.
- Faltan tests end-to-end de salida JSON/Markdown con fixtures.

### Próximo paso
- Añadir tests de integración con `httpx.MockTransport` para validar pipeline completo sin red real.

## 2026-04-27 (Hardening v0.1.2)

### Cambio realizado
- Añadidos tests de integración de pipeline completo con `httpx.MockTransport` (sin red real).
- Validada la cadena `baseline -> query_miner -> diff/scorer -> finding` en un escenario controlado.
- Validada escritura real de reportes JSON y Markdown a disco en test.

### Motivo
- Incrementar confianza del MVP con pruebas end-to-end reproducibles.
- Evitar dependencia de objetivos externos o entornos inestables en testing.

### Archivos modificados
- tests/test_integration_pipeline.py
- TODO.md

### Riesgos o deuda técnica
- Falta incluir casos de error HTTP (timeouts, 5xx y respuestas no JSON) como integración adicional.

### Próximo paso
- Agregar suite de resiliencia para errores/transient failures en `Requester` y ejecución paralela.

## 2026-04-27 (Hardening v0.1.3)

### Cambio realizado
- `Requester` ahora encapsula errores `httpx` en `HTTPRequestError` con contexto (método, URL, tiempo).
- `query_miner` ahora tolera errores por baseline y por worker, y continúa el escaneo sin abortar el proceso completo.
- Se añadió métrica `request_errors` al `ScanSummary` y al reporte Markdown.
- Añadida suite de resiliencia para timeouts y fallos parciales en paralelo.

### Motivo
- Hacer el motor más robusto frente a fallos de red/targets inestables típicos en Bug Bounty.
- Evitar que un endpoint o parámetro problemático interrumpa toda la corrida.

### Archivos modificados
- voidminer/core/requester.py
- voidminer/modes/query_miner.py
- voidminer/models.py
- voidminer/cli.py
- voidminer/output/markdown_report.py
- tests/test_cli.py
- tests/test_integration_pipeline.py
- tests/test_resilience.py
- TODO.md

### Riesgos o deuda técnica
- Aún no hay política de retries/backoff configurable; actualmente se contabiliza el error y se continúa.

### Próximo paso
- Incorporar retries exponenciales opcionales (con jitter) para mejorar tasa de éxito en targets intermitentes.

## 2026-04-27 (Hardening v0.1.4)

### Cambio realizado
- Implementados retries opcionales con backoff exponencial y jitter en `Requester`.
- Añadidas opciones CLI/config para controlar retries (`--retries`, `--retry-backoff-ms`, `--retry-jitter-ms`).
- Añadidos tests de resiliencia para recuperación tras timeout transitorio y tras respuesta `5xx`.

### Motivo
- Mejorar robustez del escaneo frente a targets inestables sin romper el modo seguro por defecto.

### Archivos modificados
- voidminer/core/requester.py
- voidminer/config.py
- voidminer/cli.py
- tests/test_cli.py
- tests/test_resilience.py
- TODO.md

### Riesgos o deuda técnica
- No hay `Retry-After` awareness todavía; se usa backoff local configurable.

### Próximo paso
- Añadir soporte para `Retry-After` y métricas de intentos/reintentos por scan.

## 2026-04-27 (Hardening v0.1.5)

### Cambio realizado
- Implementado soporte de `Retry-After` en respuestas `429` para ajustar espera antes de reintento.
- Añadida métrica global de `retry_attempts` en `Requester` y exposición en `ScanSummary`.
- Actualizado reporte Markdown para incluir reintentos.
- Añadido test específico para verificar `Retry-After` y conteo de reintentos.

### Motivo
- Respetar señales del objetivo para reducir ruido y mejorar tasa de éxito frente a rate limiting.

### Archivos modificados
- voidminer/core/requester.py
- voidminer/models.py
- voidminer/cli.py
- voidminer/output/markdown_report.py
- tests/test_resilience.py
- TODO.md

### Riesgos o deuda técnica
- El parseo de `Retry-After` cubre segundos y fecha HTTP, pero no contempla políticas por dominio/endpoint.

### Próximo paso
- Añadir métricas por endpoint (errores, retries, findings) para análisis operacional más fino.

## 2026-04-27 (Hardening v0.1.6)

### Cambio realizado
- Añadidas métricas operacionales por endpoint en el reporte (`parameters_tested`, `request_errors`, `retry_attempts`, `findings`, severidades).
- `Requester` ahora mantiene también reintentos por endpoint además del total global.
- `query_miner` devuelve estadísticas por endpoint y la CLI las agrega en `Report.endpoints`.
- Reporte Markdown actualizado con sección `Endpoint Metrics`.

### Motivo
- Mejorar visibilidad operativa por URL objetivo para priorización y debugging de escaneos.

### Archivos modificados
- voidminer/models.py
- voidminer/core/requester.py
- voidminer/modes/query_miner.py
- voidminer/cli.py
- voidminer/output/markdown_report.py
- tests/test_cli.py
- tests/test_integration_pipeline.py
- tests/test_resilience.py
- TODO.md

### Riesgos o deuda técnica
- Agregación por endpoint usa URL base sin query; para algunos targets podría requerirse granularidad por path+method+template.

### Próximo paso
- Exponer estas métricas en consola `rich` con tabla resumida al terminar la corrida.

## 2026-04-27 (Hardening v0.1.7)

### Cambio realizado
- Añadida tabla de métricas por endpoint en salida de consola usando `rich`.
- Integrada en CLI al final de la corrida, respetando `--silent`.
- Añadido test CLI para validar que la tabla recibe los endpoints agregados.

### Motivo
- Facilitar lectura inmediata del estado operativo sin abrir archivos JSON/Markdown.

### Archivos modificados
- voidminer/output/console.py
- voidminer/cli.py
- tests/test_cli.py
- TODO.md

### Riesgos o deuda técnica
- En targets con muchos endpoints la tabla puede crecer; pendiente paginación/filtro en consola.

### Próximo paso
- Añadir opción CLI para limitar métricas de consola a top-N endpoints con más findings/errores.

## 2026-04-27 (Wordlists v0.1.8)

### Cambio realizado
- Ampliadas wordlists existentes (`params_base`, `params_debug`, `params_redirect_ssrf`, `params_mass_assignment`, `params_lfi_rce`) con cobertura más amplia y menos duplicados.
- Añadidas wordlists especializadas nuevas:
  - `data/params_cache_cdn.txt`
  - `data/params_auth_session.txt`
  - `data/params_search_filter.txt`

### Motivo
- Mejorar tasa de descubrimiento en bug bounty real con diccionarios más contextuales y reutilizables por superficie.

### Archivos modificados
- data/params_base.txt
- data/params_debug.txt
- data/params_redirect_ssrf.txt
- data/params_mass_assignment.txt
- data/params_lfi_rce.txt
- data/params_cache_cdn.txt
- data/params_auth_session.txt
- data/params_search_filter.txt
- TODO.md

### Riesgos o deuda técnica
- Faltaría incorporar fusión contextual automática de wordlists por fingerprint del endpoint.

### Próximo paso
- Añadir opción para combinar múltiples wordlists desde CLI y deduplicar en runtime.

## 2026-04-27 (Dictionary + MultiPayload v0.2.0)

### Cambio realizado
- Implementada gobernanza de wordlist con normalización, deduplicación y priorización por familias en runtime.
- Implementado motor multi-payload por parámetro con perfiles (`fast|balanced|deep`), límite por parámetro y early-stop por señal fuerte.
- Añadida agregación de evidencia entre payloads con scoring incremental por consistencia.
- Extendido `Finding` con trazabilidad por payload (`payloads_tested`, `payloads_with_signal`, `signal_hits`, `evidence_by_payload`).
- Añadidas métricas de payload en summary y métricas por endpoint (payloads/signals).
- Actualizados reportes Markdown y consola para mostrar métricas nuevas.
- Actualizada documentación de uso para flags de multi-payload.
- Añadidos tests de wordlist builder y ajustes de integración/resiliencia/CLI para nuevo flujo.

### Motivo
- Subir cobertura real de descubrimiento con mega diccionario minimizando ruido mediante confirmación multi-payload y scoring de consistencia.

### Archivos modificados
- voidminer/sources/wordlist_builder.py
- voidminer/utils/randoms.py
- voidminer/modes/query_miner.py
- voidminer/core/scorer.py
- voidminer/models.py
- voidminer/config.py
- voidminer/cli.py
- voidminer/output/console.py
- voidminer/output/markdown_report.py
- docs/usage.md
- tests/test_cli.py
- tests/test_integration_pipeline.py
- tests/test_resilience.py
- tests/test_scorer.py
- tests/test_query_miner.py
- TODO.md

### Riesgos o deuda técnica
- Falta combinar múltiples archivos de wordlist por CLI en una sola ejecución sin script externo.
- Podría añadirse calibración por endpoint para ajustar profile automáticamente según ruido detectado.

### Próximo paso
- Soportar `-w` repetible para fusionar varias wordlists y deduplicar antes del escaneo.

## 2026-04-27 (CLI Wordlists v0.2.1)

### Cambio realizado
- Añadido soporte de `-w/--wordlist` repetible en CLI para fusionar múltiples diccionarios en una sola corrida.
- Integrada carga multiarchivo con deduplicación centralizada en `wordlist_builder`.
- Añadido test de CLI para validar merge de wordlists y deduplicación en runtime.
- Actualizada documentación de uso con ejemplo multi-wordlist.

### Motivo
- Facilitar estrategia de máxima cobertura sin pasos manuales de concatenación previa.

### Archivos modificados
- voidminer/voidminer/cli.py
- voidminer/voidminer/sources/wordlist_builder.py
- voidminer/tests/test_cli.py
- voidminer/docs/usage.md
- TODO.md

### Riesgos o deuda técnica
- Falta soporte de exclusión (`--exclude-wordlist`) para pruebas de precisión avanzadas.

### Próximo paso
- Añadir opción `--wordlist-profile` predefinida (`base`, `mega`, `cache`, `auth`) para simplificar uso operativo.

## 2026-04-27 (Throughput Upgrade v0.3.0)

### Cambio realizado
- Añadidos perfiles operativos de escaneo orientados a throughput: `recon_fast`, `balanced`, `deep_confirm`.
- Añadidos perfiles de wordlist: `base`, `mega`, `cache`, `auth`, `redirect`, `debug`, `mass_assignment`, `mixed_recon`.
- Implementada estrategia opcional de dos fases (`phase1` candidatos + confirmación profunda).
- Añadidas métricas de productividad BB: tiempo total, tiempo al primer hallazgo, findings/min, params/min, candidatos fase1 y ratio candidato->confirmado.
- Añadida salida de `Quick Triage` en consola y sección equivalente en Markdown.
- Añadidos checkpoints de progreso durante ejecución larga.
- CLI ampliada para operar por perfiles y combinar `--wordlist` + `--wordlist-profile`.

### Motivo
- Maximizar hallazgos por hora en objetivos mixtos (API + HTML) reduciendo coste operativo de configuración manual.

### Archivos modificados
- voidminer/voidminer/config.py
- voidminer/voidminer/cli.py
- voidminer/voidminer/modes/query_miner.py
- voidminer/voidminer/sources/wordlist_builder.py
- voidminer/voidminer/models.py
- voidminer/voidminer/output/console.py
- voidminer/voidminer/output/markdown_report.py
- voidminer/docs/usage.md
- voidminer/tests/test_cli.py
- voidminer/tests/test_query_miner.py
- voidminer/tests/test_integration_pipeline.py
- TODO.md

### Riesgos o deuda técnica
- La aplicación de `--ops-profile` actualmente prioriza defaults de perfil sobre tuning manual fino en la misma invocación.

### Próximo paso
- Permitir override granular de parámetros cuando se usa `--ops-profile`, manteniendo presets como base.
