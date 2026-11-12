/** Textos y enlaces fijos del sitio (atribución, licencias, titular). */

export const OWNER = 'Diego Francisco Granda Zhingre';
export const OWNER_GITHUB = 'https://github.com/DiegoFranciscoG';
export const REPOSITORY = 'https://github.com/DiegoFranciscoG/cpc-mini';

export const DATA_SOURCE = {
  publisher: 'Servicio Nacional de Contratación Pública (SERCOP)',
  registry: 'OCP Data Registry de Open Contracting Partnership',
  registryUrl: 'https://data.open-contracting.org/en/publication/110',
  portalUrl: 'https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos',
  license: 'Creative Commons Reconocimiento 3.0 Ecuador (CC BY 3.0 EC)',
  licenseShort: 'CC BY 3.0 EC',
  licenseUrl: 'https://creativecommons.org/licenses/by/3.0/ec/',
  cpcUrl: 'https://portal.compraspublicas.gob.ec/sercop/que-es-el-clasificador-central-de-productos-cpc/',
} as const;

export const ATTRIBUTION =
  'Datos: SERCOP, publicados en formato OCDS por el OCP Data Registry de Open Contracting Partnership, ' +
  'licencia CC BY 3.0 Ecuador. CPC-mini los normalizó, filtró, deduplicó y dividió por tiempo.';

export const EXAMPLES = [
  'Paracetamol 500 mg tabletas, caja x 100',
  'Resma de papel bond A4 de 75 g',
  'Servicio de limpieza de oficinas',
  'Tubería PVC de 110 mm para desagüe',
  'Mantenimiento preventivo de vehículos livianos',
] as const;

export const NOTICE_STORAGE_KEY = 'cpcmini.aviso-sin-cookies';
