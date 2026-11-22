-- EJECUTAR SOLO TRAS REVISIÓN Y RESPALDO. No ejecutar sobre ISC sin autorización.
-- Requiere administrador de PostgreSQL. Crear previamente un rol LOGIN de mínimo privilegio
-- y establecer su contraseña en Render, NUNCA en este archivo.
CREATE SCHEMA IF NOT EXISTS frani_piloto;
CREATE TABLE IF NOT EXISTS frani_piloto.invitaciones (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 token_sha256 char(64) UNIQUE NOT NULL,
 etiqueta varchar(120) NOT NULL,
 activa boolean NOT NULL DEFAULT true,
 vence_en timestamptz
);
CREATE TABLE IF NOT EXISTS frani_piloto.entrevistas (
 envio_id uuid PRIMARY KEY,
 invitacion_id bigint NOT NULL REFERENCES frani_piloto.invitaciones(id),
 respuestas jsonb NOT NULL,
 consentimiento_en timestamptz NOT NULL,
 recibido_en timestamptz NOT NULL DEFAULT NOW(),
 estado varchar(30) NOT NULL DEFAULT 'recibida',
 CONSTRAINT diez_respuestas CHECK (jsonb_typeof(respuestas) = 'array' AND jsonb_array_length(respuestas) = 10)
);
-- No hay GRANT automático: otorgar al rol restringido USAGE del esquema,
-- SELECT de invitaciones y SELECT/INSERT de entrevistas; sin acceso a public.
-- Si se usan secuencias identity para invitaciones, solo el administrador las utiliza.
