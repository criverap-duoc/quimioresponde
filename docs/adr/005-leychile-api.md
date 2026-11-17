# ADR-005: Uso de la API de LeyChile con key propia

## Contexto
El proyecto ingiere normativa chilena de la Biblioteca del Congreso Nacional (BCN) para responder consultas con citas verificables. La BCN ofrece una API oficial con autenticación por clave.

## Decisión
Usar la API oficial de LeyChile (`/servicio/7/`) con una API Key propia, solicitada con finalidad de portafolio sin fines comerciales. Solo se ingieren dos decretos específicos (Decreto 43/2015 y Decreto 594/1999), no el corpus completo.

## Alternativas
- Descarga directa del HTML de leychile.cl: no oficial, estructura inestable, riesgo legal.
- Scraping de terceros: viola términos de uso.
- No ingerir normativa: el producto no existe.

## Consecuencias
- Límite de 500 requests por 24h por key; suficiente para la ingesta acotada.
- Licencia CC BY-NC-ND 4.0 del contenido: se puede compartir sin modificaciones y sin fines comerciales, con atribución. El proyecto es sin fines comerciales y atribuye en la UI.
- Almacenamiento persistente del XML en `documents.raw_text` justificado por la finalidad declarada.
- No se entrena ningún modelo con el contenido.
- Se cita "Ley Chile – Biblioteca del Congreso Nacional" en el footer de la UI.
