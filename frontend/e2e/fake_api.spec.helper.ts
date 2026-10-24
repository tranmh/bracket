/**
 * Shared helpers for the Playwright e2e specs.
 *
 * The Bracket frontend talks to a separate FastAPI backend (default http://localhost:8400,
 * see getBaseApiUrl in src/services/adapter.tsx). That backend is not part of the e2e
 * environment, so every request leaving the Next.js origin is intercepted and answered by
 * a small in-test fake that the individual specs drive.
 */
import { Page, Request, expect } from '@playwright/test';

export const BASE_URL = (process.env.AQAA_BASE_URL || 'http://localhost:3000').replace(/\/$/, '');

export interface ApiCall {
  method: string;
  path: string;
  query: URLSearchParams;
  body: any;
  headers: Record<string, string>;
}

export interface ApiReply {
  status?: number;
  body: any;
}

export type ApiHandler = (call: ApiCall) => ApiReply | undefined;

function parseMultipart(raw: string): Record<string, string> {
  const result: Record<string, string> = {};
  const re = /name="([^"]+)"\r\n\r\n([\s\S]*?)\r\n--/g;
  let m = re.exec(raw);
  while (m != null) {
    result[m[1]] = m[2];
    m = re.exec(raw);
  }
  return result;
}

function parseBody(request: Request): any {
  const raw = request.postData();
  if (raw == null || raw === '') return null;
  const contentType = request.headers()['content-type'] || '';
  if (contentType.includes('multipart/form-data')) return parseMultipart(raw);
  if (contentType.includes('application/x-www-form-urlencoded')) {
    return Object.fromEntries(new URLSearchParams(raw).entries());
  }
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

/**
 * Routes every non-app request of the page to `handler`. Unhandled GETs answer `{ data: [] }`,
 * other unhandled requests answer 404. All API calls are recorded in the returned array.
 */
export async function installFakeApi(page: Page, handler: ApiHandler): Promise<ApiCall[]> {
  const appOrigin = new URL(BASE_URL).origin;
  const calls: ApiCall[] = [];

  await page.route(
    (url) => url.origin !== appOrigin,
    async (route) => {
      const request = route.request();
      const type = request.resourceType();
      if (type !== 'xhr' && type !== 'fetch') {
        // Logos, placeholder images, analytics etc.: never leave the sandbox.
        await route.abort();
        return;
      }

      const headers = request.headers();
      const cors = {
        'access-control-allow-origin': headers.origin || appOrigin,
        'access-control-allow-methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
        'access-control-allow-headers':
          headers['access-control-request-headers'] || 'authorization, content-type, accept',
      };
      if (request.method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: cors });
        return;
      }

      const url = new URL(request.url());
      const call: ApiCall = {
        method: request.method(),
        path: url.pathname,
        query: url.searchParams,
        body: parseBody(request),
        headers,
      };
      calls.push(call);

      let reply = handler(call);
      if (reply === undefined) {
        reply =
          call.method === 'GET'
            ? { status: 200, body: { data: [] } }
            : { status: 404, body: { detail: `fake api: no handler for ${call.method} ${call.path}` } };
      }
      await route.fulfill({
        status: reply.status ?? 200,
        headers: { ...cors, 'content-type': 'application/json' },
        body: JSON.stringify(reply.body),
      });
    }
  );
  return calls;
}

/** Waits until the Next.js pages router has hydrated, so form input reaches React state. */
export async function waitForHydration(page: Page) {
  await page.waitForFunction(() => (window as any).next?.router?.isReady === true);
}

/** Navigates to an app path and waits for hydration. */
export async function open(page: Page, path: string) {
  await page.goto(`${BASE_URL}${path}`);
  await waitForHydration(page);
}

export async function expectPath(page: Page, path: string) {
  await expect.poll(() => new URL(page.url()).pathname).toBe(path);
}
