import http from 'k6/http';
import { check } from 'k6';

const FRONTEND = (__ENV.AQAA_APP_FRONTEND_URL || 'http://localhost:3001').replace(/\/$/, '');
const VUS = Math.min(parseInt(__ENV.AQAA_LOAD_VUS || '10', 10), 10);
const DURATION = __ENV.AQAA_LOAD_DURATION || '30s';

export const options = {
  scenarios: {
    load: { executor: 'constant-vus', vus: VUS, duration: DURATION },
  },
};

// The pages' getServerSideProps only load translations; tournament data is fetched
// client-side from the backend, so any numeric id renders the page.
const TOURNAMENT_ID = 1;
const STAGE_ITEM_ID = 1;

const t = `/tournaments/${TOURNAMENT_ID}`;

const ENDPOINTS = [
  { name: 'frontend GET /', path: '/', weight: 10 },
  { name: 'frontend GET /login', path: '/login', weight: 8 },
  { name: 'frontend GET /tournaments/<id>/dashboard', path: `${t}/dashboard`, weight: 8 },
  { name: 'frontend GET /tournaments/<id>/schedule', path: `${t}/schedule`, weight: 7 },
  { name: 'frontend GET /tournaments/<id>/stages', path: `${t}/stages`, weight: 7 },
  { name: 'frontend GET /tournaments/<id>/results', path: `${t}/results`, weight: 6 },
  { name: 'frontend GET /tournaments/<id>/teams', path: `${t}/teams`, weight: 6 },
  { name: 'frontend GET /tournaments/<id>/players', path: `${t}/players`, weight: 5 },
  { name: 'frontend GET /tournaments/<id>/rankings', path: `${t}/rankings`, weight: 5 },
  { name: 'frontend GET /tournaments/<id>/settings', path: `${t}/settings`, weight: 4 },
  { name: 'frontend GET /tournaments/<id>/stages/swiss/<stage_item_id>', path: `${t}/stages/swiss/${STAGE_ITEM_ID}`, weight: 4 },
  { name: 'frontend GET /tournaments/<id>/dashboard/standings', path: `${t}/dashboard/standings`, weight: 5 },
  { name: 'frontend GET /tournaments/<id>/dashboard/present/courts', path: `${t}/dashboard/present/courts`, weight: 4 },
  { name: 'frontend GET /tournaments/<id>/dashboard/present/standings', path: `${t}/dashboard/present/standings`, weight: 4 },
  { name: 'frontend GET /clubs', path: '/clubs', weight: 4 },
  { name: 'frontend GET /user', path: '/user', weight: 3 },
  { name: 'frontend GET /create_account', path: '/create_account', weight: 3 },
  { name: 'frontend GET /demo', path: '/demo', weight: 3 },
  { name: 'frontend GET /password_reset', path: '/password_reset', weight: 2 },
  { name: 'frontend GET /nl/login', path: '/nl/login', weight: 2 },
  { name: 'frontend GET /locales/en/common.json', path: '/locales/en/common.json', weight: 3 },
  { name: 'frontend GET /does-not-exist', path: '/does-not-exist', weight: 1, status: 404 },
];

const TOTAL = ENDPOINTS.reduce((s, e) => s + e.weight, 0);

function pick() {
  let r = Math.random() * TOTAL;
  for (const e of ENDPOINTS) {
    r -= e.weight;
    if (r < 0) return e;
  }
  return ENDPOINTS[ENDPOINTS.length - 1];
}

export default function () {
  const e = pick();
  const expected = e.status || 200;
  const params = { tags: { endpoint: e.name } };
  if (e.status) params.responseCallback = http.expectedStatuses(e.status);
  const res = http.get(`${FRONTEND}${e.path}`, params);
  check(res, { [`status is ${expected}`]: (r) => r.status === expected }, { endpoint: e.name });
}
