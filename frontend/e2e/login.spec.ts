import { expect, test } from '@playwright/test';

import { ApiCall, expectPath, installFakeApi, open } from './fake_api.spec.helper';

const VALID_EMAIL = 'organiser@example.org';
const VALID_PASSWORD = 'correct-horse-battery';
const ACCESS_TOKEN = 'e2e-fake-access-token';

const tournament = {
  id: 1,
  name: 'Spring Swiss Open',
  created: '2026-01-01T09:00:00+00:00',
  start_time: '2026-03-01T10:00:00+00:00',
  club_id: 1,
  dashboard_public: false,
  dashboard_endpoint: 'spring-swiss-open',
  players_can_be_in_multiple_teams: false,
  auto_assign_courts: true,
  logo_path: null,
  duration_minutes: 15,
  margin_minutes: 5,
  status: 'OPEN',
};

function backend(call: ApiCall) {
  if (call.method === 'POST' && /\/token$/.test(call.path)) {
    if (call.body?.username === VALID_EMAIL && call.body?.password === VALID_PASSWORD) {
      return {
        status: 200,
        body: { access_token: ACCESS_TOKEN, token_type: 'bearer', user_id: 1 },
      };
    }
    return { status: 401, body: { detail: 'Incorrect email or password' } };
  }
  if (call.method === 'GET' && /\/tournaments$/.test(call.path)) {
    return { body: { data: [tournament] } };
  }
  if (call.method === 'GET' && /\/clubs$/.test(call.path)) {
    return { body: { data: [{ id: 1, name: 'Chess Club', created: tournament.created }] } };
  }
  return undefined;
}

async function fillLoginForm(page: import('@playwright/test').Page, email: string, pw: string) {
  const emailInput = page.getByLabel('Email Address');
  const passwordInput = page.getByLabel('Password');
  await emailInput.fill(email);
  await passwordInput.fill(pw);
  await expect(emailInput).toHaveValue(email);
  await expect(passwordInput).toHaveValue(pw);
}

test.describe('login flow', () => {
  test('valid credentials store the token and redirect to the tournaments page', async ({
    page,
  }) => {
    const calls = await installFakeApi(page, backend);
    await open(page, '/login');

    await expect(page.getByRole('heading', { name: /Welcome to\s+Bracket/ })).toBeVisible();
    await fillLoginForm(page, VALID_EMAIL, VALID_PASSWORD);
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByText('Login successful')).toBeVisible();
    await expectPath(page, '/');
    await expect(page.getByRole('heading', { name: 'Tournaments' })).toBeVisible();
    await expect(page.getByText('Spring Swiss Open')).toBeVisible();

    // The token request is an OAuth2 password grant.
    const tokenCall = calls.find((c) => c.method === 'POST' && /\/token$/.test(c.path));
    expect(tokenCall?.body).toMatchObject({
      grant_type: 'password',
      username: VALID_EMAIL,
      password: VALID_PASSWORD,
    });

    // The token is persisted and used for subsequent API requests.
    const stored = await page.evaluate(() => window.localStorage.getItem('login'));
    expect(JSON.parse(stored ?? '{}').access_token).toBe(ACCESS_TOKEN);
    const tournamentsCall = calls.find((c) => c.method === 'GET' && /\/tournaments$/.test(c.path));
    expect(tournamentsCall?.query.get('filter_')).toBe('OPEN');
    expect(tournamentsCall?.headers.authorization).toBe(`bearer ${ACCESS_TOKEN}`);

    // The tournament card links to the tournament's stages page.
    await expect(page.getByRole('link', { name: 'OPEN', exact: true })).toHaveAttribute(
      'href',
      '/tournaments/1/stages'
    );
  });

  test('invalid credentials show the backend error and keep the user on the login page', async ({
    page,
  }) => {
    const calls = await installFakeApi(page, backend);
    await open(page, '/login');

    await fillLoginForm(page, VALID_EMAIL, 'wrong-password-123');
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByText('Incorrect email or password')).toBeVisible();
    await expect(page.getByText('Login successful')).toHaveCount(0);
    await expectPath(page, '/login');
    expect(await page.evaluate(() => window.localStorage.getItem('login'))).toBeNull();
    expect(calls.filter((c) => /\/token$/.test(c.path))).toHaveLength(1);
  });

  test('a too short password is rejected client side without calling the backend', async ({
    page,
  }) => {
    const calls = await installFakeApi(page, backend);
    await open(page, '/login');

    await fillLoginForm(page, VALID_EMAIL, 'short');
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByText('Invalid password')).toBeVisible();
    await expectPath(page, '/login');
    expect(calls.filter((c) => /\/token$/.test(c.path))).toHaveLength(0);
  });

  test('an already logged in user is sent from the login page to the tournaments page', async ({
    page,
  }) => {
    await installFakeApi(page, backend);
    await page.addInitScript((token) => {
      window.localStorage.setItem(
        'login',
        JSON.stringify({ access_token: token, token_type: 'bearer', user_id: 1 })
      );
    }, ACCESS_TOKEN);

    await open(page, '/login');

    await expectPath(page, '/');
    await expect(page.getByText('Spring Swiss Open')).toBeVisible();
  });
});
