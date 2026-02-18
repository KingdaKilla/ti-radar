/** Shared country name mappings and EU classification. */

export const COUNTRY_NAMES = {
  // EU27
  AT: 'Österreich', BE: 'Belgien', BG: 'Bulgarien', CY: 'Zypern',
  CZ: 'Tschechien', DE: 'Deutschland', DK: 'Dänemark', EE: 'Estland',
  ES: 'Spanien', FI: 'Finnland', FR: 'Frankreich', GR: 'Griechenland',
  HR: 'Kroatien', HU: 'Ungarn', IE: 'Irland', IT: 'Italien',
  LT: 'Litauen', LU: 'Luxemburg', LV: 'Lettland', MT: 'Malta',
  NL: 'Niederlande', PL: 'Polen', PT: 'Portugal', RO: 'Rumänien',
  SE: 'Schweden', SI: 'Slowenien', SK: 'Slowakei',
  // EEA + CH + GB
  NO: 'Norwegen', IS: 'Island', LI: 'Liechtenstein', CH: 'Schweiz',
  GB: 'Großbritannien', UK: 'Großbritannien', EL: 'Griechenland',
  // EU-Kandidaten & Westbalkan
  RS: 'Serbien', TR: 'Türkei', ME: 'Montenegro', AL: 'Albanien',
  MK: 'Nordmazedonien', BA: 'Bosnien-Herzegowina', XK: 'Kosovo',
  // Europa sonstige
  UA: 'Ukraine', MD: 'Moldau', GE: 'Georgien', AM: 'Armenien',
  BY: 'Belarus', MC: 'Monaco', SM: 'San Marino', FO: 'Färöer',
  // Asien-Pazifik
  JP: 'Japan', CN: 'China', KR: 'Südkorea', IN: 'Indien',
  TW: 'Taiwan', SG: 'Singapur', HK: 'Hongkong', MY: 'Malaysia',
  TH: 'Thailand', ID: 'Indonesien', PH: 'Philippinen', VN: 'Vietnam',
  PK: 'Pakistan', BD: 'Bangladesch', KZ: 'Kasachstan', UZ: 'Usbekistan',
  // Naher Osten & Nordafrika
  IL: 'Israel', SA: 'Saudi-Arabien', AE: 'Ver. Arab. Emirate',
  EG: 'Ägypten', MA: 'Marokko', TN: 'Tunesien', DZ: 'Algerien',
  IR: 'Iran', IQ: 'Irak', JO: 'Jordanien', LB: 'Libanon',
  QA: 'Katar', KW: 'Kuwait', BH: 'Bahrain', OM: 'Oman', PS: 'Palästina',
  // Afrika
  ZA: 'Südafrika', NG: 'Nigeria', KE: 'Kenia', GH: 'Ghana',
  ET: 'Äthiopien', TZ: 'Tansania', RW: 'Ruanda', UG: 'Uganda',
  SN: 'Senegal', CM: 'Kamerun', CI: 'Elfenbeinküste',
  // Amerika
  US: 'USA', CA: 'Kanada', BR: 'Brasilien', MX: 'Mexiko',
  AR: 'Argentinien', CL: 'Chile', CO: 'Kolumbien', PE: 'Peru',
  CU: 'Kuba', CR: 'Costa Rica', UY: 'Uruguay', EC: 'Ecuador',
  // Ozeanien
  AU: 'Australien', NZ: 'Neuseeland',
  // Historisch (in Patentdaten)
  SU: 'Sowjetunion', DD: 'DDR', CS: 'Tschechoslowakei', YU: 'Jugoslawien',
  // Sonder-/Organisationscodes
  RU: 'Russland',
}

// Patent-Anmelderouten (keine Laender — aus Laendercharts filtern)
export const NON_COUNTRY_CODES = new Set([
  'WO', 'EP', 'EA', 'OA', 'AP', 'GC', 'EM', 'ZZ',
])

// EU27 + EEA + CH + GB
export const EU_COUNTRIES = new Set([
  'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR',
  'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO',
  'SE', 'SI', 'SK', 'CH', 'NO', 'IS', 'LI', 'GB', 'EL', 'UK',
])

export function isEuropean(code) { return EU_COUNTRIES.has(code) }
