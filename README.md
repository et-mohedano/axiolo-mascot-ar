# Axiolo · experiencia 3D + AR

Paquete web móvil para visualizar la mascota de Axiolo en 3D y realidad aumentada desde Android y iPhone.

## Archivos principales

- `index.html` — experiencia principal, completamente en inglés.
- `assets/axiolo-mascot-ios.glb` — modelo normalizado que debe usar la página.
- `assets/axiolo-mascot.usdz` — opcional; si existe, la página lo usa automáticamente para Apple Quick Look.
- `tools/normalize_glb_for_ios.py` — normaliza texturas WebP cuando es posible, elimina extensiones comprimidas cuando existe fallback compatible y agrega una animación `AxioloSpin` al modelo.
- `.htaccess` — MIME types recomendados para Apache.
- `nginx-mime.conf` — referencia para Nginx.

## Compatibilidad

La página usa `<model-viewer>` con:

- controles de cámara;
- rotación automática;
- pinch-to-zoom;
- AR mediante `webxr`, `scene-viewer` y `quick-look`;
- animación 3D integrada `AxioloSpin` cuando el modelo fue procesado con la herramienta incluida.

En iPhone, Quick Look funciona mejor con materiales y texturas estándar PNG/JPEG. El script de normalización convierte WebP embebido a PNG y desactiva extensiones comprimidas cuando el GLB ya incluye un fallback estándar. Si el archivo usa exclusivamente texturas KTX2/Basis sin fallback, se requiere convertirlas con una herramienta externa antes de publicar.

## Preparar el modelo

Coloca el archivo original como:

```text
assets/axiolo-mascot.glb
```

Después ejecuta desde la raíz de esta carpeta:

```bash
python tools/normalize_glb_for_ios.py assets/axiolo-mascot.glb assets/axiolo-mascot-ios.glb
```

El script genera también `model-report.json` con la información de compatibilidad detectada.

## Prueba local

No abras el HTML directamente con `file://`. Levanta un servidor local:

```bash
python -m http.server 8000
```

Y abre:

```text
http://localhost:8000/
```

Para AR real en teléfono debes publicar por **HTTPS**.

## Enlace externo

El CTA `Discover Axiolo` abre:

https://www.axiolo.com/
