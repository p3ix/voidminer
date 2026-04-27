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
